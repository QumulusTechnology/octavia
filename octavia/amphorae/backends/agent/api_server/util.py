# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
#    under the License.


import os
import re
import stat
import subprocess
import typing as tp

import jinja2
from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.utils import ip_advertisement
from octavia.amphorae.backends.utils import network_utils
from octavia.common import constants as consts

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

FRONTEND_BACKEND_PATTERN = re.compile(r'\n(frontend|backend)\s+(\S+)\n')
LISTENER_MODE_PATTERN = re.compile(r'^\s+mode\s+(.*)$', re.MULTILINE)
TLS_CERT_PATTERN = re.compile(r'^\s+bind\s+\S+\s+ssl crt-list\s+(\S*)',
                              re.MULTILINE)
STATS_SOCKET_PATTERN = re.compile(r'stats socket\s+(\S+)')


class ParsingError(Exception):
    pass


def init_path(lb_id):
    return os.path.join(consts.SYSTEMD_DIR, f'haproxy-{lb_id}.service')


def keepalived_lvs_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'lvs')


def keepalived_lvs_init_path(listener_id):
    return os.path.join(consts.SYSTEMD_DIR,
                        consts.KEEPALIVEDLVS_SYSTEMD %
                        str(listener_id))


def keepalived_backend_check_script_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'lvs/check/')


def keepalived_backend_check_script_path():
    return os.path.join(keepalived_backend_check_script_dir(),
                        'udp_check.sh')


def keepalived_lvs_pids_path(listener_id):
    pids_path = {}
    for file_ext in ['pid', 'vrrp.pid', 'check.pid']:
        pids_path[file_ext] = (
            os.path.join(CONF.haproxy_amphora.base_path,
                         f"lvs/octavia-keepalivedlvs-{str(listener_id)}."
                         f"{file_ext}"))
    return pids_path['pid'], pids_path['vrrp.pid'], pids_path['check.pid']


def keepalived_lvs_cfg_path(listener_id):
    return os.path.join(CONF.haproxy_amphora.base_path,
                        f"lvs/octavia-keepalivedlvs-{str(listener_id)}.conf")


def haproxy_dir(lb_id):
    return os.path.join(CONF.haproxy_amphora.base_path, lb_id)


def pid_path(lb_id):
    return os.path.join(haproxy_dir(lb_id), lb_id + '.pid')


def config_path(lb_id):
    return os.path.join(haproxy_dir(lb_id), 'haproxy.cfg')


def state_file_path(lb_id):
    return os.path.join(haproxy_dir(lb_id), 'servers-state')


def get_haproxy_pid(lb_id):
    with open(pid_path(lb_id), encoding='utf-8') as f:
        return f.readline().rstrip()


def get_keepalivedlvs_pid(listener_id):
    pid_file = keepalived_lvs_pids_path(listener_id)[0]
    with open(pid_file, encoding='utf-8') as f:
        return f.readline().rstrip()


def haproxy_sock_path(lb_id):
    return os.path.join(CONF.haproxy_amphora.base_path, lb_id + '.sock')


def haproxy_check_script_path():
    return os.path.join(keepalived_check_scripts_dir(),
                        'haproxy_check_script.sh')


def keepalived_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'vrrp')


def keepalived_init_path():
    return os.path.join(consts.SYSTEMD_DIR, consts.KEEPALIVED_SYSTEMD)


def keepalived_pid_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.pid')


def keepalived_cfg_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.conf')


def keepalived_log_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.log')


def keepalived_check_scripts_dir():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/check_scripts')


def keepalived_check_script_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/check_script.sh')


def get_listeners():
    """Get Listeners

    :returns: An array with the ids of all listeners, e.g. ['123', '456', ...]
              or [] if no listeners exist
    """
    listeners = []
    for lb_id in get_loadbalancers():
        listeners_on_lb = parse_haproxy_file(lb_id)[1]
        listeners.extend(list(listeners_on_lb.keys()))
    return listeners


def get_loadbalancers():
    """Get Load balancers

    :returns: An array with the uuids of all load balancers,
              e.g. ['123', '456', ...] or [] if no loadbalancers exist
    """
    if os.path.exists(CONF.haproxy_amphora.base_path):
        return [f for f in os.listdir(CONF.haproxy_amphora.base_path)
                if os.path.exists(config_path(f))]
    return []


def is_lb_running(lb_id):
    return os.path.exists(pid_path(lb_id)) and os.path.exists(
        os.path.join('/proc', get_haproxy_pid(lb_id)))


def get_lvs_listeners():
    result = []
    if os.path.exists(keepalived_lvs_dir()):
        for f in os.listdir(keepalived_lvs_dir()):
            if f.endswith('.conf'):
                prefix = f.split('.')[0]
                if re.search("octavia-keepalivedlvs-", prefix):
                    result.append(f.split(
                        'octavia-keepalivedlvs-')[1].split('.')[0])
    return result


def is_lvs_listener_running(listener_id):
    pid_file = keepalived_lvs_pids_path(listener_id)[0]
    return os.path.exists(pid_file) and os.path.exists(
        os.path.join('/proc', get_keepalivedlvs_pid(listener_id)))


def install_netns_systemd_service():
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00644
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    # TODO(bcafarel): implement this for other init systems
    # netns handling depends on a separate unit file
    netns_path = os.path.join(consts.SYSTEMD_DIR,
                              consts.AMP_NETNS_SVC_PREFIX + '.service')

    jinja_env = jinja2.Environment(
        autoescape=True, loader=jinja2.FileSystemLoader(os.path.dirname(
            os.path.realpath(__file__)
        ) + consts.AGENT_API_TEMPLATES))

    if not os.path.exists(netns_path):
        with os.fdopen(os.open(netns_path, flags, mode), 'w') as text_file:
            text = jinja_env.get_template(
                consts.AMP_NETNS_SVC_PREFIX + '.systemd.j2').render(
                    amphora_nsname=consts.AMPHORA_NAMESPACE)
            text_file.write(text)


def run_systemctl_command(command, service, raise_error=True):
    cmd = f"systemctl {command} {service}"
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT,
                                encoding='utf-8')
    except subprocess.CalledProcessError as e:
        LOG.debug("Failed to %(cmd)s %(srvc)s service: "
                  "%(err)s %(out)s", {'cmd': command, 'srvc': service,
                                      'err': e, 'out': e.output})
        if raise_error:
            raise


def get_backend_for_lb_object(object_id):
    """Returns the backend for a listener.

    If the listener is a TCP based listener return 'HAPROXY'.
    If the listener is a UDP or SCTP based listener return 'LVS'
    If the listener is not identifiable, return None.

    :param listener_id: The ID of the listener to identify.
    :returns: HAPROXY_BACKEND, LVS_BACKEND or None
    """
    if os.path.exists(config_path(object_id)):
        return consts.HAPROXY_BACKEND
    if os.path.exists(keepalived_lvs_cfg_path(object_id)):
        return consts.LVS_BACKEND
    return None


def parse_haproxy_file(lb_id):
    with open(config_path(lb_id), encoding='utf-8') as file:
        cfg = file.read()

        listeners = {}

        m = FRONTEND_BACKEND_PATTERN.split(cfg)
        last_token = None
        last_id = None
        for section in m:
            if last_token is None:
                # We aren't in a section yet, see if this line starts one
                if section == 'frontend':
                    last_token = section
            elif last_token == 'frontend':
                # We're in a frontend section, save the id for later
                last_token = last_token + "_id"
                last_id = section
            elif last_token == 'frontend_id':
                # We're in a frontend section and already have the id
                # Look for the mode
                mode_matcher = LISTENER_MODE_PATTERN.search(section)
                if not mode_matcher:
                    raise ParsingError()
                listeners[last_id] = {
                    'mode': mode_matcher.group(1).upper(),
                }
                # Now see if this is a TLS frontend
                tls_matcher = TLS_CERT_PATTERN.search(section)
                if tls_matcher:
                    # TODO(rm_work): Can't we have terminated tcp?
                    listeners[last_id]['mode'] = 'TERMINATED_HTTPS'
                    listeners[last_id]['ssl_crt'] = tls_matcher.group(1)
                # Clear out the token and id and start over
                last_token = last_id = None

        m = STATS_SOCKET_PATTERN.search(cfg)
        if not m:
            raise ParsingError()
        stats_socket = m.group(1)

        return stats_socket, listeners


def vrrp_check_script_update(lb_id, action):
    os.makedirs(keepalived_dir(), exist_ok=True)
    os.makedirs(keepalived_check_scripts_dir(), exist_ok=True)

    lb_ids = get_loadbalancers()
    lvs_ids = get_lvs_listeners()
    # If no LBs are found, so make sure keepalived thinks haproxy is down.
    if not lb_ids:
        if not lvs_ids:
            with open(haproxy_check_script_path(),
                      'w', encoding='utf-8') as text_file:
                text_file.write('exit 1')
        else:
            try:
                LOG.debug("Attempting to remove old haproxy check script...")
                os.remove(haproxy_check_script_path())
                LOG.debug("Finished removing old haproxy check script.")
            except FileNotFoundError:
                LOG.debug("No haproxy check script to remove.")
        return
    if action == consts.AMP_ACTION_STOP:
        lb_ids.remove(lb_id)
    args = []
    for lbid in lb_ids:
        args.append(haproxy_sock_path(lbid))

    cmd = f"haproxy-vrrp-check {' '.join(args)}; exit $?"
    with open(haproxy_check_script_path(), 'w', encoding='utf-8') as text_file:
        text_file.write(cmd)


def get_haproxy_vip_addresses(lb_id):
    """Get the VIP addresses for a load balancer.

    :param lb_id: The load balancer ID to get VIP addresses from.
    :returns: List of VIP addresses (IPv4 and IPv6)
    """
    vips = []
    with open(config_path(lb_id), encoding='utf-8') as file:
        for line in file:
            current_line = line.strip()
            if current_line.startswith('bind'):
                for section in current_line.split(' '):
                    # We will always have a port assigned per the template.
                    if ':' in section:
                        if ',' in section:
                            addr_port = section.rstrip(',')
                            vips.append(addr_port.rpartition(':')[0])
                        else:
                            vips.append(section.rpartition(':')[0])
                            break
    return vips


def get_lvs_vip_addresses(listener_id: str) -> list[str]:
    """Get the VIP addresses for a LVS load balancer.

    :param listener_id: The listener ID to get VIP addresses from.
    :returns: List of VIP addresses (IPv4 and IPv6)
    """
    vips = []
    # Extract the VIP addresses from keepalived configuration
    # Format is
    # virtual_server_group ipv<n>-group {
    #     vip_address1 port1
    #     vip_address2 port2
    # }
    # it can be repeated in case of dual-stack LBs
    with open(keepalived_lvs_cfg_path(listener_id), encoding='utf-8') as file:
        vsg_section = False
        for line in file:
            current_line = line.strip()
            if vsg_section:
                if current_line.startswith('}'):
                    vsg_section = False
                else:
                    vip_address = current_line.split(' ')[0]
                    vips.append(vip_address)
            elif line.startswith('virtual_server_group '):
                vsg_section = True
    return vips


def send_vip_advertisements(lb_id: tp.Optional[str] = None,
                            listener_id: tp.Optional[str] = None):
    """Sends address advertisements for each load balancer VIP.

    This method will send either GARP (IPv4) or neighbor advertisements (IPv6)
    for the VIP addresses on a load balancer.

    :param lb_id: The load balancer ID to send advertisements for.
    :returns: None
    """
    try:
        if lb_id:
            vips = get_haproxy_vip_addresses(lb_id)
        else:
            vips = get_lvs_vip_addresses(listener_id)

        for vip in vips:
            interface = network_utils.get_interface_name(
                vip, net_ns=consts.AMPHORA_NAMESPACE)
            ip_advertisement.send_ip_advertisement(
                interface, vip, net_ns=consts.AMPHORA_NAMESPACE)
    except Exception as e:
        LOG.debug('Send VIP advertisement failed due to :%s. '
                  'This amphora may not be the MASTER. Ignoring.', str(e))

def send_member_advertisements(fixed_ips: tp.Iterable[tp.Dict[str, str]]):
    """Sends advertisements for each fixed_ip of a list

    This method will send either GARP (IPv4) or neighbor advertisements (IPv6)
    for the addresses of the subnets of the members.

    :param fixed_ips: a list of dicts that contain 'ip_address' elements
    :returns: None
    """
    try:
        for fixed_ip in fixed_ips:
            ip_address = fixed_ip[consts.IP_ADDRESS]
            interface = network_utils.get_interface_name(
                ip_address, net_ns=consts.AMPHORA_NAMESPACE)
            ip_advertisement.send_ip_advertisement(
                interface, ip_address, net_ns=consts.AMPHORA_NAMESPACE)
    except Exception as e:
        LOG.debug('Send member advertisement failed due to: %s', str(e))


import json
import urllib.request

def update_alloy_configuration(loadbalancer_id, cloud_fqdn):
    # Fetch project_id from metadata service
    with urllib.request.urlopen("http://169.254.169.254/openstack/2025-04-04/meta_data.json") as response:
        metadata = json.load(response)
        project_id = metadata.get("project_id")
        if project_id is None:
            raise ValueError("project_id is missing in metadata service response")

    project_id = str(project_id)

    with open('/etc/alloy/environment', 'r') as env_file:
        environment = env_file.read().strip()

    # Update /etc/alloy/config.alloy
    with open('/etc/alloy/config.alloy', 'r') as f:
        config = f.read()

    if project_id is None or not isinstance(project_id, str):
        raise ValueError("project_id must be a non-None string before replacing in config")

    if loadbalancer_id is None or not isinstance(loadbalancer_id, str):
        raise ValueError("loadbalancer_id must be a non-None string before replacing in config")

    if environment is None or not isinstance(environment, str):
        raise ValueError("environment must be a non-None string before replacing in config")

    if cloud_fqdn is None or not isinstance(cloud_fqdn, str):
        raise ValueError("cloud_fqdn must be a non-None string before replacing in config")

    config = config.replace('%PROJECT_ID%', project_id)
    config = config.replace('%LB_ID%', loadbalancer_id)
    config = config.replace('%ENV%', environment)
    config = config.replace('%CLOUD_FQDN%', cloud_fqdn)
    with open('/etc/alloy/config.alloy', 'w') as f:
        f.write(config)

    # Update /etc/systemd/system/alloy.service.d/override.conf
    try:
        with open('/etc/systemd/system/alloy.service.d/override.conf', 'r') as f:
            override_conf = f.read()
        override_conf = override_conf.replace('%LB_ID%', loadbalancer_id)
        with open('/etc/systemd/system/alloy.service.d/override.conf', 'w') as f:
            f.write(override_conf)
    except Exception as e:
        LOG.error(f"Failed to update override.conf: {e}")
