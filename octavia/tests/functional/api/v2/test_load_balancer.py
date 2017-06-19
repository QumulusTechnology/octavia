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

import copy

import mock
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.tests.functional.api.v2 import base


class TestLoadBalancer(base.BaseAPITest):
    root_tag = 'loadbalancer'
    root_tag_list = 'loadbalancers'
    root_tag_links = 'loadbalancers_links'

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertTrue(uuidutils.is_uuid_like(resp.get('id')))
        req_name = req.get('name')
        req_description = req.get('description')
        if not req_name:
            self.assertEqual('', resp.get('name'))
        else:
            self.assertEqual(req.get('name'), resp.get('name'))
        if not req_description:
            self.assertEqual('', resp.get('description'))
        else:
            self.assertEqual(req.get('description'), resp.get('description'))
        self.assertEqual(constants.PENDING_CREATE,
                         resp.get('provisioning_status'))
        self.assertEqual(constants.OFFLINE, resp.get('operating_status'))
        self.assertEqual(req.get('admin_state_up', True),
                         resp.get('admin_state_up'))
        self.assertIsNotNone(resp.get('created_at'))
        self.assertIsNone(resp.get('updated_at'))
        for key, value in optionals.items():
            self.assertEqual(value, req.get(key))
        self.assert_final_lb_statuses(resp.get('id'))

    def test_empty_list(self):
        response = self.get(self.LBS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        return api_lb

    def test_create_without_vip(self):
        lb_json = {'name': 'test1',
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ('Validation failure: VIP must contain one of: '
                   'vip_port_id, vip_network_id, vip_subnet_id.')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_empty_vip(self):
        lb_json = {'vip_subnet_id': '',
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute vip_subnet_id. "
                   "Value: ''. Value should be UUID format")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_invalid_vip_subnet(self):
        subnet_id = uuidutils.generate_uuid()
        lb_json = {'vip_subnet_id': subnet_id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            mock_get_subnet.side_effect = network_base.SubnetNotFound
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = 'Subnet {} not found.'.format(subnet_id)
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_invalid_vip_network_subnet(self):
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[])
        subnet_id = uuidutils.generate_uuid()
        lb_json = {
            'vip_subnet_id': subnet_id,
            'vip_network_id': network.id,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_network") as mock_get_network:
            mock_get_network.return_value = network
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = 'Subnet {} not found.'.format(subnet_id)
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_subnet_fills_network(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        lb_json = {'vip_subnet_id': subnet.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(subnet.network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_network_has_no_subnet(self):
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[])
        lb_json = {
            'vip_network_id': network.id,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_network") as mock_get_network:
            mock_get_network.return_value = network
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = ("Validation failure: "
                       "Supplied network does not contain a subnet.")
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_network_picks_subnet_ipv4(self):
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet2.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_network_picks_subnet_ipv6(self):
        network_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id,
                                       ip_version=6)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet.id])
        lb_json = {'vip_network_id': network_id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_full(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_address': '10.0.0.1', 'vip_subnet_id': subnet.id,
            'vip_network_id': network.id, 'vip_port_id': port.id,
            'admin_state_up': False, 'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual('10.0.0.1', api_lb.get('vip_address'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(port.id, api_lb.get('vip_port_id'))

    def test_create_with_long_name(self):
        lb_json = {'name': 'n' * 256,
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute name',
                      response.json.get('faultstring'))

    def test_create_with_long_description(self):
        lb_json = {'description': 'n' * 256,
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute description',
                      response.json.get('faultstring'))

    def test_create_with_nonuuid_vip_attributes(self):
        lb_json = {'vip_subnet_id': 'HI',
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute vip_subnet_id',
                      response.json.get('faultstring'))

    def test_create_with_allowed_network_id(self):
        network_id = uuidutils.generate_uuid()
        self.conf.config(group="networking", valid_vip_networks=network_id)
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id,
                                       ip_version=4)
        network = network_models.Network(id=network_id, subnets=[subnet.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_disallowed_network_id(self):
        network_id1 = uuidutils.generate_uuid()
        network_id2 = uuidutils.generate_uuid()
        self.conf.config(group="networking", valid_vip_networks=network_id1)
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id2,
                                       ip_version=4)
        network = network_models.Network(id=network_id2, subnets=[subnet.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Supplied VIP network_id is not allowed",
                      response.json.get('faultstring'))

    def test_create_with_disallowed_vip_objects(self):
        self.conf.config(group="networking", allow_vip_network_id=False)
        self.conf.config(group="networking", allow_vip_subnet_id=False)
        self.conf.config(group="networking", allow_vip_port_id=False)

        lb_json = {'vip_network_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_network_id is disallowed',
                      response.json.get('faultstring'))

        lb_json = {'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_subnet_id is disallowed',
                      response.json.get('faultstring'))

        lb_json = {'vip_port_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_port_id is disallowed',
                      response.json.get('faultstring'))

    def test_create_with_project_id(self):
        project_id = uuidutils.generate_uuid()
        api_lb = self.test_create(project_id=project_id)
        self.assertEqual(project_id, api_lb.get('project_id'))

    def test_get_all_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=self.project_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2', project_id=project_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3', project_id=project_id)
        response = self.get(self.LBS_PATH)
        lbs = response.json.get(self.root_tag_list)
        self.assertEqual(3, len(lbs))
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        lb1 = lb1.get(self.root_tag)
        lb2 = lb2.get(self.root_tag)
        lb3 = lb3.get(self.root_tag)
        self.assertIn((lb1.get('id'), lb1.get('name')), lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name')), lb_id_names)
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_non_admin(self):
        project_id = uuidutils.generate_uuid()
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1', project_id=project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2', project_id=project_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3', project_id=self.project_id)
        lb3 = lb3.get(self.root_tag)

        auth_strategy = self.conf.conf.get('auth_strategy')
        self.conf.config(auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            response = self.get(self.LBS_PATH)
        self.conf.config(auth_strategy=auth_strategy)

        lbs = response.json.get(self.root_tag_list)
        self.assertEqual(1, len(lbs))
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1',
                                        project_id=project1_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2',
                                        project_id=project1_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3',
                                        project_id=project2_id)
        response = self.get(self.LBS_PATH,
                            params={'project_id': project1_id})
        lbs = response.json.get(self.root_tag_list)

        self.assertEqual(2, len(lbs))

        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        lb1 = lb1.get(self.root_tag)
        lb2 = lb2.get(self.root_tag)
        lb3 = lb3.get(self.root_tag)
        self.assertIn((lb1.get('id'), lb1.get('name')), lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name')), lb_id_names)
        response = self.get(self.LBS_PATH,
                            params={'project_id': project2_id})
        lbs = response.json.get(self.root_tag_list)
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertEqual(1, len(lbs))
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_sorted(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3',
                                  project_id=self.project_id)
        response = self.get(self.LBS_PATH,
                            params={'sort': 'name:desc'})
        lbs_desc = response.json.get(self.root_tag_list)
        response = self.get(self.LBS_PATH,
                            params={'sort': 'name:asc'})
        lbs_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(lbs_desc))
        self.assertEqual(3, len(lbs_asc))

        lb_id_names_desc = [(lb.get('id'), lb.get('name')) for lb in lbs_desc]
        lb_id_names_asc = [(lb.get('id'), lb.get('name')) for lb in lbs_asc]
        self.assertEqual(lb_id_names_asc, list(reversed(lb_id_names_desc)))

    def test_get_all_limited(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3',
                                  project_id=self.project_id)

        # First two -- should have 'next' link
        first_two = self.get(self.LBS_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.LBS_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.LBS_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get(self):
        project_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port

            lb = self.create_load_balancer(subnet.id,
                                           vip_address='10.0.0.1',
                                           vip_network_id=network.id,
                                           vip_port_id=port.id,
                                           name='lb1',
                                           project_id=project_id,
                                           description='desc1',
                                           admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        response = self.get(
            self.LB_PATH.format(
                lb_id=lb_dict.get('id'))).json.get(self.root_tag)
        self.assertEqual('lb1', response.get('name'))
        self.assertEqual(project_id, response.get('project_id'))
        self.assertEqual('desc1', response.get('description'))
        self.assertFalse(response.get('admin_state_up'))
        self.assertEqual('10.0.0.1', response.get('vip_address'))
        self.assertEqual(subnet.id, response.get('vip_subnet_id'))
        self.assertEqual(network.id, response.get('vip_network_id'))
        self.assertEqual(port.id, response.get('vip_port_id'))

    def test_get_hides_deleted(self):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)

        response = self.get(self.LBS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.lb_repo, api_lb.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.LBS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.get(path, status=404)

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.LoadBalancer)
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        self.post(self.LBS_PATH, body, status=403)

    def test_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'lb2'})
        lb = self.set_lb_status(lb_dict.get('id'))
        response = self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                            lb_json)
        api_lb = response.json.get(self.root_tag)
        self.assertIsNotNone(api_lb.get('vip_subnet_id'))
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assertEqual(lb.get('operational_status'),
                         api_lb.get('operational_status'))
        self.assertIsNotNone(api_lb.get('created_at'))
        self.assertIsNotNone(api_lb.get('updated_at'))
        self.assert_final_lb_statuses(api_lb.get('id'))

    def test_update_with_vip(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'vip_subnet_id': '1234'})
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=400)

    def test_update_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.put(path, body={}, status=404)

    def test_update_pending_create(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'Roberto'})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_delete_pending_create(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_update_pending_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'Bob'})
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')), lb_json)
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_delete_pending_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_json = self._build_body({'name': 'Steve'})
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')), lb_json)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_delete_with_error_status(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'), status=constants.ERROR)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=204)

    def test_update_pending_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        lb_json = self._build_body({'name': 'John'})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_delete_pending_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        response = self.get(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assertEqual(lb.get('operational_status'),
                         api_lb.get('operational_status'))
        self.assert_final_lb_statuses(api_lb.get('id'), delete=True)

    def test_delete_fails_with_pool(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        self.create_pool(
            lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id), status=400)
        self.assert_correct_status(lb_id=lb_id)

    def test_delete_fails_with_listener(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 80, lb_id)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id), status=400)
        self.assert_correct_status(lb_id=lb_id)

    def test_cascade_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb_id).get('listener')
        listener_id = listener.get('id')
        self.set_lb_status(lb_id)
        self.create_pool(
            lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener_id)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id),
                    params={'cascade': "true"})

    def test_delete_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='bad_uuid')
        self.delete(path, status=404)

    def test_create_with_bad_handler(self):
        self.handler_mock().load_balancer.create.side_effect = Exception()
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.assert_correct_status(
            lb_id=api_lb.get('id'),
            lb_prov_status=constants.ERROR,
            lb_op_status=constants.OFFLINE)

    def test_update_with_bad_handler(self):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        new_listener = {'name': 'new_name'}
        self.handler_mock().load_balancer.update.side_effect = Exception()
        self.put(self.LB_PATH.format(lb_id=api_lb.get('id')),
                 self._build_body(new_listener))
        self.assert_correct_status(
            lb_id=api_lb.get('id'),
            lb_prov_status=constants.ERROR)

    def test_delete_with_bad_handler(self):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_lb['provisioning_status'] = constants.ACTIVE
        api_lb['operating_status'] = constants.ONLINE
        response = self.get(self.LB_PATH.format(
            lb_id=api_lb.get('id'))).json.get(self.root_tag)

        self.assertIsNone(api_lb.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_lb, response)
        self.handler_mock().load_balancer.delete.side_effect = Exception()
        self.delete(self.LB_PATH.format(lb_id=api_lb.get('id')))
        self.assert_correct_status(
            lb_id=api_lb.get('id'),
            lb_prov_status=constants.ERROR)


class TestLoadBalancerGraph(base.BaseAPITest):

    root_tag = 'loadbalancer'

    def setUp(self):
        super(TestLoadBalancerGraph, self).setUp()
        self._project_id = uuidutils.generate_uuid()

    def _build_body(self, json):
        return {self.root_tag: json}

    def _assert_graphs_equal(self, expected_graph, observed_graph):
        observed_graph_copy = copy.deepcopy(observed_graph)
        del observed_graph_copy['created_at']
        del observed_graph_copy['updated_at']

        obs_lb_id = observed_graph_copy.pop('id')
        self.assertTrue(uuidutils.is_uuid_like(obs_lb_id))

        expected_listeners = expected_graph.pop('listeners', [])
        observed_listeners = observed_graph_copy.pop('listeners', [])
        expected_pools = expected_graph.pop('pools', [])
        observed_pools = observed_graph_copy.pop('pools', [])
        self.assertEqual(expected_graph, observed_graph_copy)

        self.assertEqual(len(expected_pools), len(observed_pools))

        self.assertEqual(len(expected_listeners), len(observed_listeners))
        for observed_listener in observed_listeners:
            del observed_listener['created_at']
            del observed_listener['updated_at']

            self.assertTrue(uuidutils.is_uuid_like(
                observed_listener.pop('id')))
            if observed_listener.get('default_pool_id'):
                self.assertTrue(uuidutils.is_uuid_like(
                    observed_listener.pop('default_pool_id')))

            default_pool = observed_listener.get('default_pool')
            if default_pool:
                observed_listener.pop('default_pool_id')
                self.assertTrue(default_pool.get('id'))
                default_pool.pop('id')
                default_pool.pop('created_at')
                default_pool.pop('updated_at')
                hm = default_pool.get('healthmonitor')
                if hm:
                    self.assertTrue(hm.get('id'))
                    hm.pop('id')
                for member in default_pool.get('members', []):
                    self.assertTrue(member.get('id'))
                    member.pop('id')
                    member.pop('created_at')
                    member.pop('updated_at')
            if observed_listener.get('sni_containers'):
                observed_listener['sni_containers'].sort()
            o_l7policies = observed_listener.get('l7policies')
            if o_l7policies:
                for o_l7policy in o_l7policies:
                    o_l7policy.pop('created_at')
                    o_l7policy.pop('updated_at')
                    if o_l7policy.get('redirect_pool_id'):
                        r_pool_id = o_l7policy.pop('redirect_pool_id')
                        self.assertTrue(uuidutils.is_uuid_like(r_pool_id))
                    o_l7policy_id = o_l7policy.pop('id')
                    self.assertTrue(uuidutils.is_uuid_like(o_l7policy_id))
                    o_l7policy_l_id = o_l7policy.pop('listener_id')
                    self.assertTrue(uuidutils.is_uuid_like(o_l7policy_l_id))
                    l7rules = o_l7policy.get('rules') or []
                    for l7rule in l7rules:
                        l7rule.pop('created_at')
                        l7rule.pop('updated_at')
                        self.assertTrue(l7rule.pop('id'))
            self.assertIn(observed_listener, expected_listeners)

    def _get_lb_bodies(self, create_listeners, expected_listeners,
                       create_pools=None):
        create_lb = {
            'name': 'lb1',
            'project_id': self._project_id,
            'vip_subnet_id': uuidutils.generate_uuid(),
            'listeners': create_listeners,
            'pools': create_pools or []
        }
        expected_lb = {
            'description': '',
            'admin_state_up': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'vip_address': None,
            'vip_network_id': None,
            'vip_port_id': None,
            'flavor': '',
            'provider': 'octavia'
        }
        expected_lb.update(create_lb)
        expected_lb['listeners'] = expected_listeners
        expected_lb['pools'] = create_pools or []
        return create_lb, expected_lb

    def _get_listener_bodies(self, name='listener1', protocol_port=80,
                             create_default_pool_name=None,
                             create_default_pool_id=None,
                             create_l7policies=None,
                             expected_l7policies=None,
                             create_sni_containers=None,
                             expected_sni_containers=None):
        create_listener = {
            'name': name,
            'protocol_port': protocol_port,
            'protocol': constants.PROTOCOL_HTTP
        }
        expected_listener = {
            'description': '',
            'default_tls_container_ref': None,
            'sni_container_refs': [],
            'connection_limit': -1,
            'admin_state_up': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'insert_headers': {},
            'project_id': self._project_id
        }
        if create_sni_containers:
            create_listener['sni_container_refs'] = create_sni_containers
        expected_listener.update(create_listener)
        if create_default_pool_name:
            pool = {'name': create_default_pool_name}
            create_listener['default_pool'] = pool
        elif create_default_pool_id:
            create_listener['default_pool_id'] = create_default_pool_id
            expected_listener['default_pool_id'] = create_default_pool_id
        else:
            expected_listener['default_pool_id'] = None
        if create_l7policies:
            l7policies = create_l7policies
            create_listener['l7policies'] = l7policies
        if expected_sni_containers:
            expected_listener['sni_container_refs'] = expected_sni_containers
        if expected_l7policies:
            expected_listener['l7policies'] = expected_l7policies
        else:
            expected_listener['l7policies'] = []
        return create_listener, expected_listener

    def _get_pool_bodies(self, name='pool1', create_members=None,
                         expected_members=None, create_hm=None,
                         expected_hm=None, protocol=constants.PROTOCOL_HTTP,
                         session_persistence=True):
        create_pool = {
            'name': name,
            'protocol': protocol,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
        }
        if session_persistence:
            create_pool['session_persistence'] = {
                'type': constants.SESSION_PERSISTENCE_SOURCE_IP,
                'cookie_name': None}
        if create_members:
            create_pool['members'] = create_members
        if create_hm:
            create_pool['healthmonitor'] = create_hm
        expected_pool = {
            'description': None,
            'session_persistence': None,
            'members': [],
            'enabled': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'project_id': self._project_id
        }
        expected_pool.update(create_pool)
        if expected_members:
            expected_pool['members'] = expected_members
        if expected_hm:
            expected_pool['healthmonitor'] = expected_hm
        return create_pool, expected_pool

    def _get_member_bodies(self, protocol_port=80):
        create_member = {
            'address': '10.0.0.1',
            'protocol_port': protocol_port
        }
        expected_member = {
            'weight': 1,
            'enabled': True,
            'subnet_id': None,
            'operating_status': constants.OFFLINE,
            'project_id': self._project_id
        }
        expected_member.update(create_member)
        return create_member, expected_member

    def _get_hm_bodies(self):
        create_hm = {
            'type': constants.HEALTH_MONITOR_PING,
            'delay': 1,
            'timeout': 1,
            'max_retries_down': 1,
            'max_retries': 1
        }
        expected_hm = {
            'http_method': 'GET',
            'url_path': '/',
            'expected_codes': '200',
            'admin_state_up': True,
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE
        }
        expected_hm.update(create_hm)
        return create_hm, expected_hm

    def _get_sni_container_bodies(self):
        create_sni_container1 = uuidutils.generate_uuid()
        create_sni_container2 = uuidutils.generate_uuid()
        create_sni_containers = [create_sni_container1, create_sni_container2]
        expected_sni_containers = [create_sni_container1,
                                   create_sni_container2]
        expected_sni_containers.sort()
        return create_sni_containers, expected_sni_containers

    def _get_l7policies_bodies(self,
                               create_pool_name=None, create_pool_id=None,
                               create_l7rules=None, expected_l7rules=None):
        create_l7policies = []
        if create_pool_name:
            create_l7policy = {
                'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                'redirect_pool': {'name': create_pool_name},
                'position': 1,
                'admin_state_up': False
            }
        else:
            create_l7policy = {
                'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                'redirect_url': 'http://127.0.0.1/',
                'position': 1,
                'admin_state_up': False
            }
        create_l7policies.append(create_l7policy)
        expected_l7policy = {
            'name': '',
            'description': '',
            'redirect_url': None,
            'rules': [],
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE
        }
        expected_l7policy.update(create_l7policy)
        expected_l7policy.pop('redirect_pool', None)
        expected_l7policies = []
        if not create_pool_name:
            expected_l7policy['redirect_pool_id'] = create_pool_id
        expected_l7policies.append(expected_l7policy)
        if expected_l7rules:
            expected_l7policies[0]['rules'] = expected_l7rules
        if create_l7rules:
            create_l7policies[0]['rules'] = create_l7rules
        return create_l7policies, expected_l7policies

    def _get_l7rules_bodies(self, value="localhost"):
        create_l7rules = [{
            'type': constants.L7RULE_TYPE_HOST_NAME,
            'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'value': value,
            'invert': False,
            'admin_state_up': True
        }]
        expected_l7rules = [{
            'key': None,
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE
        }]
        expected_l7rules[0].update(create_l7rules[0])
        return create_l7rules, expected_l7rules

    def test_with_one_listener(self):
        create_listener, expected_listener = self._get_listener_bodies()
        create_lb, expected_lb = self._get_lb_bodies([create_listener],
                                                     [expected_listener])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_many_listeners(self):
        create_listener1, expected_listener1 = self._get_listener_bodies()
        create_listener2, expected_listener2 = self._get_listener_bodies(
            name='listener2', protocol_port=81)
        create_lb, expected_lb = self._get_lb_bodies(
            [create_listener1, create_listener2],
            [expected_listener1, expected_listener2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_pool(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_many_listeners_one_pool(self):
        create_pool1, expected_pool1 = self._get_pool_bodies()
        create_pool2, expected_pool2 = self._get_pool_bodies(name='pool2')
        create_listener1, expected_listener1 = self._get_listener_bodies(
            create_default_pool_name=create_pool1['name'])
        create_listener2, expected_listener2 = self._get_listener_bodies(
            create_default_pool_name=create_pool2['name'],
            name='listener2', protocol_port=81)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener1, create_listener2],
            expected_listeners=[expected_listener1, expected_listener2],
            create_pools=[create_pool1, create_pool2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_member(self):
        create_member, expected_member = self._get_member_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_members=[create_member],
            expected_members=[expected_member])
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_hm(self):
        create_hm, expected_hm = self._get_hm_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_hm=create_hm,
            expected_hm=expected_hm)
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_sni_containers(self):
        create_sni_containers, expected_sni_containers = (
            self._get_sni_container_bodies())
        create_listener, expected_listener = self._get_listener_bodies(
            create_sni_containers=create_sni_containers,
            expected_sni_containers=expected_sni_containers)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_no_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'])
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_one_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policies_one_redirect_pool_one_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        c_l7policies_url, e_l7policies_url = self._get_l7policies_bodies()
        for policy in c_l7policies_url:
            policy['position'] = 2
            create_l7policies.append(policy)
        for policy in e_l7policies_url:
            policy['position'] = 2
            expected_l7policies.append(policy)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policies_redirect_pools_no_rules(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'])
        r_create_pool, r_expected_pool = self._get_pool_bodies(name='pool2')
        c_l7policies_url, e_l7policies_url = self._get_l7policies_bodies(
            create_pool_name=r_create_pool['name'])
        for policy in c_l7policies_url:
            policy['position'] = 2
            create_l7policies.append(policy)
        for policy in e_l7policies_url:
            policy['position'] = 2
            expected_l7policies.append(policy)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool, r_create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_bad_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies(
            value="local host")
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn('L7Rule: Invalid characters',
                      response.json.get('faultstring'))

    def _test_with_one_of_everything_helper(self):
        create_member, expected_member = self._get_member_bodies()
        create_hm, expected_hm = self._get_hm_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_members=[create_member],
            expected_members=[expected_member],
            create_hm=create_hm,
            expected_hm=expected_hm,
            protocol=constants.PROTOCOL_TCP)
        create_sni_containers, expected_sni_containers = (
            self._get_sni_container_bodies())
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        r_create_member, r_expected_member = self._get_member_bodies(
            protocol_port=88)
        r_create_pool, r_expected_pool = self._get_pool_bodies(
            create_members=[r_create_member],
            expected_members=[r_expected_member])
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=r_create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'],
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies,
            create_sni_containers=create_sni_containers,
            expected_sni_containers=expected_sni_containers)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        return body, expected_lb

    def test_with_one_of_everything(self):
        body, expected_lb = self._test_with_one_of_everything_helper()
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_db_create_failure(self):
        create_listener, expected_listener = self._get_listener_bodies()
        create_lb, _ = self._get_lb_bodies([create_listener],
                                           [expected_listener])
        body = self._build_body(create_lb)
        with mock.patch('octavia.db.repositories.Repositories.'
                        'create_load_balancer_and_vip') as repo_mock:
            repo_mock.side_effect = Exception('I am a DB Error')
            self.post(self.LBS_PATH, body, status=500)

    def test_pool_names_not_unique(self):
        create_pool1, expected_pool1 = self._get_pool_bodies()
        create_pool2, expected_pool2 = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool1['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool1, create_pool2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Pool names must be unique",
                      response.json.get('faultstring'))

    def test_pool_names_must_have_specs(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name="my_nonexistent_pool")
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("referenced but no full definition",
                      response.json.get('faultstring'))

    def test_pool_mandatory_attributes(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_pool.pop('protocol')
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("missing required attribute: protocol",
                      response.json.get('faultstring'))

    def test_create_over_quota_lb(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.LoadBalancer)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_pools(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Pool)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_listeners(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Listener)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_members(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Member)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_hms(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.HealthMonitor)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_sanity_check(self):
        # This one should create, as we don't check quotas on L7Policies
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.L7Policy)
        self.post(self.LBS_PATH, body)