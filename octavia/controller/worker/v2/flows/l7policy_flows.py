# Copyright 2016 Blue Box, an IBM Company
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
# under the License.
#

from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import lifecycle_tasks


class L7PolicyFlows:

    def get_create_l7policy_flow(self):
        """Create a flow to create an L7 policy

        :returns: The flow for creating an L7 policy
        """
        create_l7policy_flow = linear_flow.Flow(constants.CREATE_L7POLICY_FLOW)
        create_l7policy_flow.add(lifecycle_tasks.L7PolicyToErrorOnRevertTask(
            requires=[constants.L7POLICY,
                      constants.LISTENERS,
                      constants.LOADBALANCER_ID]))
        create_l7policy_flow.add(database_tasks.MarkL7PolicyPendingCreateInDB(
            requires=constants.L7POLICY))
        create_l7policy_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        create_l7policy_flow.add(database_tasks.MarkL7PolicyActiveInDB(
            requires=constants.L7POLICY))
        create_l7policy_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=(constants.LOADBALANCER_ID, constants.LISTENERS)))

        return create_l7policy_flow

    def get_delete_l7policy_flow(self):
        """Create a flow to delete an L7 policy

        :returns: The flow for deleting an L7 policy
        """
        delete_l7policy_flow = linear_flow.Flow(constants.DELETE_L7POLICY_FLOW)
        delete_l7policy_flow.add(lifecycle_tasks.L7PolicyToErrorOnRevertTask(
            requires=[constants.L7POLICY,
                      constants.LISTENERS,
                      constants.LOADBALANCER_ID]))
        delete_l7policy_flow.add(database_tasks.MarkL7PolicyPendingDeleteInDB(
            requires=constants.L7POLICY))
        delete_l7policy_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        delete_l7policy_flow.add(database_tasks.DeleteL7PolicyInDB(
            requires=constants.L7POLICY))
        delete_l7policy_flow.add(database_tasks.DecrementL7policyQuota(
            requires=constants.L7POLICY))
        delete_l7policy_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=(constants.LOADBALANCER_ID, constants.LISTENERS)))

        return delete_l7policy_flow

    def get_update_l7policy_flow(self):
        """Create a flow to update an L7 policy

        :returns: The flow for updating an L7 policy
        """
        update_l7policy_flow = linear_flow.Flow(constants.UPDATE_L7POLICY_FLOW)
        update_l7policy_flow.add(lifecycle_tasks.L7PolicyToErrorOnRevertTask(
            requires=[constants.L7POLICY,
                      constants.LISTENERS,
                      constants.LOADBALANCER_ID]))
        update_l7policy_flow.add(database_tasks.MarkL7PolicyPendingUpdateInDB(
            requires=constants.L7POLICY))
        update_l7policy_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        update_l7policy_flow.add(database_tasks.UpdateL7PolicyInDB(
            requires=[constants.L7POLICY, constants.UPDATE_DICT]))
        update_l7policy_flow.add(database_tasks.MarkL7PolicyActiveInDB(
            requires=constants.L7POLICY))
        update_l7policy_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=(constants.LOADBALANCER_ID, constants.LISTENERS)))

        return update_l7policy_flow
