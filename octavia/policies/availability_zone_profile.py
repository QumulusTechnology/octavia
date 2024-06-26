# Copyright 2019 Verizon Media
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

from oslo_policy import policy

from octavia.common import constants


rules = [
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_AVAILABILITY_ZONE_PROFILE}{constants.RBAC_GET_ALL}',
        constants.RULE_API_ADMIN,
        "List Availability Zones",
        [{'method': 'GET', 'path': '/v2.0/lbaas/availabilityzoneprofiles'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_AVAILABILITY_ZONE_PROFILE}{constants.RBAC_POST}',
        constants.RULE_API_ADMIN,
        "Create an Availability Zone",
        [{'method': 'POST', 'path': '/v2.0/lbaas/availabilityzoneprofiles'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_AVAILABILITY_ZONE_PROFILE}{constants.RBAC_PUT}',
        constants.RULE_API_ADMIN,
        "Update an Availability Zone",
        [{'method': 'PUT',
          'path': '/v2.0/lbaas/availabilityzoneprofiles/'
                  '{availability_zone_profile_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_AVAILABILITY_ZONE_PROFILE}{constants.RBAC_GET_ONE}',
        constants.RULE_API_ADMIN,
        "Show Availability Zone details",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/availabilityzoneprofiles/'
                  '{availability_zone_profile_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_AVAILABILITY_ZONE_PROFILE}{constants.RBAC_DELETE}',
        constants.RULE_API_ADMIN,
        "Remove an Availability Zone",
        [{'method': 'DELETE',
          'path': '/v2.0/lbaas/availabilityzoneprofiles/'
                  '{availability_zone_profile_id}'}]
    ),
]


def list_rules():
    return rules
