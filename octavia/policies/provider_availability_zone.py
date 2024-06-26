#    Copyright 2018 Rackspace, US Inc.
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
        f'{constants.RBAC_PROVIDER_AVAILABILITY_ZONE}{constants.RBAC_GET_ALL}',
        constants.RULE_API_ADMIN,
        "List the provider availability zone capabilities.",
        [{'method': 'GET',
          'path': '/v2/lbaas/providers/{provider}/'
                  'availability_zone_capabilities'}]
    ),
]


def list_rules():
    return rules
