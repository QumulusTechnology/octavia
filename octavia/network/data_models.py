#    Copyright 2014 Rackspace
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia.common import constants
from octavia.common import data_models


class Interface(data_models.BaseDataModel):

    def __init__(self, id=None, compute_id=None, network_id=None,
                 fixed_ips=None, port_id=None, vnic_type=None):
        self.id = id
        self.compute_id = compute_id
        self.network_id = network_id
        self.port_id = port_id
        self.fixed_ips = fixed_ips
        self.vnic_type = vnic_type


class Delta(data_models.BaseDataModel):

    def __init__(self, amphora_id=None, compute_id=None,
                 add_nics=None, delete_nics=None,
                 add_subnets=None, delete_subnets=None):
        self.compute_id = compute_id
        self.amphora_id = amphora_id
        self.add_nics = add_nics
        self.delete_nics = delete_nics
        self.add_subnets = add_subnets
        self.delete_subnets = delete_subnets


class Network(data_models.BaseDataModel):

    def __init__(self, id=None, name=None, subnets=None,
                 project_id=None, admin_state_up=None, mtu=None,
                 provider_network_type=None,
                 provider_physical_network=None,
                 provider_segmentation_id=None,
                 router_external=None,
                 port_security_enabled=None):
        self.id = id
        self.name = name
        self.subnets = subnets
        self.project_id = project_id
        self.admin_state_up = admin_state_up
        self.provider_network_type = provider_network_type
        self.provider_physical_network = provider_physical_network
        self.provider_segmentation_id = provider_segmentation_id
        self.router_external = router_external
        self.mtu = mtu
        self.port_security_enabled = port_security_enabled


class Subnet(data_models.BaseDataModel):

    def __init__(self, id=None, name=None, network_id=None, project_id=None,
                 gateway_ip=None, cidr=None, ip_version=None,
                 host_routes=None):
        self.id = id
        self.name = name
        self.network_id = network_id
        self.project_id = project_id
        self.gateway_ip = gateway_ip
        self.cidr = cidr
        self.ip_version = ip_version
        self.host_routes = host_routes


class Port(data_models.BaseDataModel):

    def __init__(self, id=None, name=None, device_id=None, device_owner=None,
                 mac_address=None, network_id=None, status=None,
                 project_id=None, admin_state_up=None, fixed_ips=None,
                 network=None, qos_policy_id=None, security_group_ids=None,
                 vnic_type=constants.VNIC_TYPE_NORMAL):
        self.id = id
        self.name = name
        self.device_id = device_id
        self.device_owner = device_owner
        self.mac_address = mac_address
        self.network_id = network_id
        self.status = status
        self.project_id = project_id
        self.admin_state_up = admin_state_up
        self.fixed_ips = fixed_ips or []
        self.network = network
        self.qos_policy_id = qos_policy_id
        self.security_group_ids = security_group_ids or []
        self.vnic_type = vnic_type

    def get_subnet_id(self, fixed_ip_address):
        for fixed_ip in self.fixed_ips:
            if fixed_ip.ip_address == fixed_ip_address:
                return fixed_ip.subnet_id
        return None


class FixedIP(data_models.BaseDataModel):

    def __init__(self, subnet_id=None, ip_address=None, subnet=None):
        self.subnet_id = subnet_id
        self.ip_address = ip_address
        self.subnet = subnet


class FloatingIP(data_models.BaseDataModel):
    def __init__(self, id=None, description=None, project_id=None,
                 status=None, router_id=None, port_id=None,
                 floating_network_id=None, floating_ip_address=None,
                 fixed_ip_address=None, fixed_port_id=None):
        self.id = id
        self.description = description
        self.project_id = project_id
        self.status = status
        self.router_id = router_id
        self.port_id = port_id
        self.floating_network_id = floating_network_id
        self.floating_ip_address = floating_ip_address
        self.fixed_ip_address = fixed_ip_address
        self.fixed_port_id = fixed_port_id

        # Need to provide this for compatibility in case it is used as a VIP
        self.network_id = floating_network_id


class AmphoraNetworkConfig(data_models.BaseDataModel):

    def __init__(self, amphora=None, vip_subnet=None, vip_port=None,
                 vrrp_subnet=None, vrrp_port=None, ha_subnet=None,
                 ha_port=None, additional_vip_data=None):
        self.amphora = amphora
        self.vip_subnet = vip_subnet
        self.vip_port = vip_port
        self.vrrp_subnet = vrrp_subnet
        self.vrrp_port = vrrp_port
        self.ha_subnet = ha_subnet
        self.ha_port = ha_port
        self.additional_vip_data = additional_vip_data or []


class AdditionalVipData(data_models.BaseDataModel):

    def __init__(self, ip_address=None, subnet=None):
        self.ip_address = ip_address
        self.subnet = subnet


class HostRoute(data_models.BaseDataModel):

    def __init__(self, nexthop=None, destination=None):
        self.nexthop = nexthop
        self.destination = destination


class QosPolicy(data_models.BaseDataModel):
    def __init__(self, id):
        self.id = id


class Network_IP_Availability(data_models.BaseDataModel):

    def __init__(self, network_id=None, tenant_id=None, project_id=None,
                 network_name=None, total_ips=None, used_ips=None,
                 subnet_ip_availability=None):
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.network_name = network_name
        self.total_ips = total_ips
        self.used_ips = used_ips
        self.subnet_ip_availability = subnet_ip_availability


class SecurityGroup(data_models.BaseDataModel):

    def __init__(self, id=None, project_id=None, name=None, description=None,
                 security_group_rule_ids=None, tags=None, stateful=None):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.description = description
        self.security_group_rule_ids = security_group_rule_ids or []
        self.tags = tags or []
        self.stateful = stateful
