# Copyright 2017 Walmart Stores Inc..
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
        f'{constants.RBAC_FLAVOR_PROFILE}{constants.RBAC_GET_ALL}',
        constants.RULE_API_ADMIN,
        "List Flavor Profiles",
        [{'method': 'GET', 'path': '/v2.0/lbaas/flavorprofiles'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_FLAVOR_PROFILE}{constants.RBAC_POST}',
        constants.RULE_API_ADMIN,
        "Create a Flavor Profile",
        [{'method': 'POST', 'path': '/v2.0/lbaas/flavorprofiles'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_FLAVOR_PROFILE}{constants.RBAC_PUT}',
        constants.RULE_API_ADMIN,
        "Update a Flavor Profile",
        [{'method': 'PUT',
          'path': '/v2.0/lbaas/flavorprofiles/{flavor_profile_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_FLAVOR_PROFILE}{constants.RBAC_GET_ONE}',
        constants.RULE_API_ADMIN,
        "Show Flavor Profile details",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/flavorprofiles/{flavor_profile_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_FLAVOR_PROFILE}{constants.RBAC_DELETE}',
        constants.RULE_API_ADMIN,
        "Remove a Flavor Profile",
        [{'method': 'DELETE',
          'path': '/v2.0/lbaas/flavorprofiles/{flavor_profile_id}'}]
    ),
]


def list_rules():
    return rules
