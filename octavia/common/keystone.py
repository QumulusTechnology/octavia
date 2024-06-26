#    Copyright 2015 Rackspace
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

from keystoneauth1 import exceptions as ks_exceptions
from keystoneauth1 import loading as ks_loading
from keystonemiddleware import auth_token
from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import constants

LOG = logging.getLogger(__name__)

_NOAUTH_PATHS = ['/', '/load-balancer/', '/healthcheck',
                 '/load-balancer/healthcheck']


class KeystoneSession:

    def __init__(self, section=constants.SERVICE_AUTH):
        self._session = None
        self._auth = None

        self.section = section

    def get_session(self, auth=None):
        """Initializes a Keystone session.

        :return: a Keystone Session object
        """
        if auth:
            # Do not use the singleton with custom auth params
            return ks_loading.load_session_from_conf_options(
                cfg.CONF, self.section, auth=auth)

        if not self._session:
            self._session = ks_loading.load_session_from_conf_options(
                cfg.CONF, self.section, auth=self.get_auth())

        return self._session

    def get_auth(self):
        if not self._auth:
            try:
                self._auth = ks_loading.load_auth_from_conf_options(
                    cfg.CONF, self.section)
            except ks_exceptions.auth_plugins.MissingRequiredOptions as e:
                if self.section == constants.SERVICE_AUTH:
                    raise e
                # NOTE(gthiemonge): MissingRequiredOptions is raised: there is
                # one or more missing auth options in the config file. It may
                # be due to the migration from python-neutronclient to
                # openstacksdk.
                # With neutronclient, most of the auth settings were in
                # [service_auth] with a few overrides in [neutron],
                # but with openstacksdk, we have all the auth settings in the
                # [neutron] section. In order to support smooth upgrades, in
                # case those options are missing, we override the undefined
                # options with the existing settings from [service_auth].

                # This code should be removed when all the deployment tools set
                # the correct options in [neutron]

                # The config options are lazily registered/loaded by keystone,
                # it means that we cannot get/set them before invoking
                # 'load_auth_from_conf_options' on 'service_auth'.
                ks_loading.load_auth_from_conf_options(
                    cfg.CONF, constants.SERVICE_AUTH)

                config = getattr(cfg.CONF, self.section)
                for opt in config:
                    # For each option in the [section] section, get its setting
                    # location, if the location is 'opt_default', it means that
                    # the option is not configured in the config file.
                    # if the option is also defined in [service_auth], the
                    # option of the [section] can be replaced by the one from
                    # [service_auth]
                    loc = cfg.CONF.get_location(opt, self.section)
                    if not loc or loc.location == cfg.Locations.opt_default:
                        if hasattr(cfg.CONF.service_auth, opt):
                            cur_value = getattr(config, opt)
                            value = getattr(cfg.CONF.service_auth, opt)
                            if value != cur_value:
                                log_value = (value if opt != "password"
                                             else "<hidden>")
                                LOG.debug("Overriding [%s].%s with '%s'",
                                          self.section, opt, log_value)
                                cfg.CONF.set_override(opt, value, self.section)

                # Now we can call load_auth_from_conf_options for this specific
                # service with the newly defined options.
                self._auth = ks_loading.load_auth_from_conf_options(
                    cfg.CONF, self.section)

        return self._auth

    def get_service_user_id(self):
        return self.get_auth().get_user_id(self.get_session())


class SkippingAuthProtocol(auth_token.AuthProtocol):
    """SkippingAuthProtocol to reach special endpoints

    Bypasses keystone authentication for special request paths, such
    as the api version discovery path.

    Note:
        SkippingAuthProtocol is lean customization
        of :py:class:`keystonemiddleware.auth_token.AuthProtocol`
        that disables keystone communication if the request path
        is in the _NOAUTH_PATHS list.

    """

    def process_request(self, request):
        path = request.path
        if path in _NOAUTH_PATHS:
            LOG.debug('Request path is %s and it does not require keystone '
                      'authentication', path)
            return None  # return NONE to reach actual logic

        return super().process_request(request)
