#    Copyright 2016 Rackspace
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

""" Methods common to the controller work tasks."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import tenacity

from octavia.common import constants
from octavia.db import api as db_apis
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class TaskUtils:
    """Class of helper/utility methods used by tasks."""

    status_update_retry = tenacity.retry(
        retry=tenacity.retry_if_exception_type(Exception),
        wait=tenacity.wait_incrementing(
            CONF.controller_worker.db_commit_retry_initial_delay,
            CONF.controller_worker.db_commit_retry_backoff,
            CONF.controller_worker.db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.controller_worker.db_commit_retry_attempts),
        after=tenacity.after_log(LOG, logging.DEBUG))

    def __init__(self, **kwargs):
        self.amphora_repo = repo.AmphoraRepository()
        self.health_mon_repo = repo.HealthMonitorRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()
        self.amp_health_repo = repo.AmphoraHealthRepository()
        self.l7policy_repo = repo.L7PolicyRepository()
        self.l7rule_repo = repo.L7RuleRepository()
        super().__init__(**kwargs)

    def unmark_amphora_health_busy(self, amphora_id):
        """Unmark the amphora_health record busy for an amphora.

        NOTE: This should only be called from revert methods.

        :param amphora_id: The amphora id to unmark busy
        """
        LOG.debug('Unmarking health monitoring busy on amphora: %s',
                  amphora_id)
        try:
            with db_apis.session().begin() as session:
                self.amp_health_repo.update(session,
                                            amphora_id=amphora_id,
                                            busy=False)
        except Exception as e:
            LOG.debug('Failed to update amphora health record %(amp)s '
                      'due to: %(except)s',
                      {'amp': amphora_id, 'except': str(e)})

    def mark_amphora_status_error(self, amphora_id):
        """Sets an amphora status to ERROR.

        NOTE: This should only be called from revert methods.

        :param amphora_id: Amphora ID to set the status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.amphora_repo.update(session,
                                         id=amphora_id,
                                         status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update amphora %(amp)s "
                      "status to ERROR due to: "
                      "%(except)s", {'amp': amphora_id, 'except': str(e)})

    def mark_health_mon_prov_status_error(self, health_mon_id):
        """Sets a health monitor provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param health_mon_id: Health Monitor ID to set prov status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.health_mon_repo.update(
                    session, id=health_mon_id,
                    provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update health monitor %(health)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s",
                      {'health': health_mon_id, 'except': str(e)})

    def mark_l7policy_prov_status_active(self, l7policy_id):
        """Sets a L7 policy provisioning status to ACTIVE.

        NOTE: This should only be called from revert methods.

        :param l7policy_id: L7 Policy ID to set provisioning status to ACTIVE
        """
        try:
            with db_apis.session().begin() as session:
                self.l7policy_repo.update(session,
                                          id=l7policy_id,
                                          provisioning_status=constants.ACTIVE)
        except Exception as e:
            LOG.error("Failed to update l7policy %(l7p)s "
                      "provisioning status to ACTIVE due to: "
                      "%(except)s", {'l7p': l7policy_id, 'except': str(e)})

    def mark_l7policy_prov_status_error(self, l7policy_id):
        """Sets a L7 policy provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param l7policy_id: L7 Policy ID to set provisioning status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.l7policy_repo.update(session,
                                          id=l7policy_id,
                                          provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update l7policy %(l7p)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s", {'l7p': l7policy_id, 'except': str(e)})

    def mark_l7rule_prov_status_error(self, l7rule_id):
        """Sets a L7 rule provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param l7rule_id: L7 Rule ID to set provisioning status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.l7rule_repo.update(session,
                                        id=l7rule_id,
                                        provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update l7rule %(l7r)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s", {'l7r': l7rule_id, 'except': str(e)})

    def mark_listener_prov_status_error(self, listener_id):
        """Sets a listener provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param listener_id: Listener ID to set provisioning status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.listener_repo.update(session,
                                          id=listener_id,
                                          provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update listener %(list)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s", {'list': listener_id, 'except': str(e)})

    @status_update_retry
    def mark_loadbalancer_prov_status_error(self, loadbalancer_id):
        """Sets a load balancer provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param loadbalancer_id: Load balancer ID to set provisioning
                                status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.loadbalancer_repo.update(
                    session,
                    id=loadbalancer_id,
                    provisioning_status=constants.ERROR)
        except Exception as e:
            # Reraise for tenacity
            with excutils.save_and_reraise_exception():
                LOG.error("Failed to update load balancer %(lb)s "
                          "provisioning status to ERROR due to: "
                          "%(except)s", {'lb': loadbalancer_id,
                                         'except': str(e)})

    def mark_listener_prov_status_active(self, listener_id):
        """Sets a listener provisioning status to ACTIVE.

        NOTE: This should only be called from revert methods.

        :param listener_id: Listener ID to set provisioning
                            status to ACTIVE
        """
        try:
            with db_apis.session().begin() as session:
                self.listener_repo.update(session,
                                          id=listener_id,
                                          provisioning_status=constants.ACTIVE)
        except Exception as e:
            LOG.error("Failed to update listener %(list)s "
                      "provisioning status to ACTIVE due to: "
                      "%(except)s", {'list': listener_id, 'except': str(e)})

    def mark_pool_prov_status_active(self, pool_id):
        """Sets a pool provisioning status to ACTIVE.

        NOTE: This should only be called from revert methods.

        :param pool_id: Pool ID to set provisioning status to ACTIVE
        """
        try:
            with db_apis.session().begin() as session:
                self.pool_repo.update(session,
                                      id=pool_id,
                                      provisioning_status=constants.ACTIVE)
        except Exception as e:
            LOG.error("Failed to update pool %(pool)s provisioning status "
                      "to ACTIVE due to: %(except)s", {'pool': pool_id,
                                                       'except': str(e)})

    @status_update_retry
    def mark_loadbalancer_prov_status_active(self, loadbalancer_id):
        """Sets a load balancer provisioning status to ACTIVE.

        NOTE: This should only be called from revert methods.

        :param loadbalancer_id: Load balancer ID to set provisioning
                                status to ACTIVE
        """
        try:
            with db_apis.session().begin() as session:
                self.loadbalancer_repo.update(
                    session,
                    id=loadbalancer_id,
                    provisioning_status=constants.ACTIVE)
        except Exception as e:
            # Reraise for tenacity
            with excutils.save_and_reraise_exception():
                LOG.error("Failed to update load balancer %(lb)s "
                          "provisioning status to ACTIVE due to: "
                          "%(except)s", {'lb': loadbalancer_id,
                                         'except': str(e)})

    def mark_member_prov_status_error(self, member_id):
        """Sets a member provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param member_id: Member ID to set provisioning status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.member_repo.update(session,
                                        id=member_id,
                                        provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update member %(member)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s", {'member': member_id, 'except': str(e)})

    def mark_pool_prov_status_error(self, pool_id):
        """Sets a pool provisioning status to ERROR.

        NOTE: This should only be called from revert methods.

        :param pool_id: Pool ID to set provisioning status to ERROR
        """
        try:
            with db_apis.session().begin() as session:
                self.pool_repo.update(session,
                                      id=pool_id,
                                      provisioning_status=constants.ERROR)
        except Exception as e:
            LOG.error("Failed to update pool %(pool)s "
                      "provisioning status to ERROR due to: "
                      "%(except)s", {'pool': pool_id, 'except': str(e)})

    def get_current_loadbalancer_from_db(self, loadbalancer_id):
        """Gets a Loadbalancer from db.

        :param: loadbalancer_id: Load balancer ID which to get from db
        """
        try:
            with db_apis.session().begin() as session:
                return self.loadbalancer_repo.get(session,
                                                  id=loadbalancer_id)
        except Exception as e:
            LOG.error("Failed to get loadbalancer %(loadbalancer)s "
                      "due to: %(except)s",
                      {'loadbalancer': loadbalancer_id, 'except': str(e)})
        return None
