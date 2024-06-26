#
# Copyright 2014 OpenStack Foundation.  All rights reserved
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
import datetime
from unittest import mock

from cryptography import x509

from octavia.common import data_models
import octavia.common.exceptions as exceptions
import octavia.common.tls_utils.cert_parser as cert_parser
from octavia.tests.common import sample_certs
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs_combined


class TestTLSParseUtils(base.TestCase):
    def test_alt_subject_name_parses(self):
        hosts = cert_parser.get_host_names(sample_certs.ALT_EXT_CRT)
        self.assertIn('www.cnfromsubject.org', hosts['cn'])
        self.assertIn('www.hostFromDNSName1.com', hosts['dns_names'])
        self.assertIn('www.hostFromDNSName2.com', hosts['dns_names'])
        self.assertIn('www.hostFromDNSName3.com', hosts['dns_names'])
        self.assertIn('www.hostFromDNSName4.com', hosts['dns_names'])

    def test_x509_parses(self):
        self.assertRaises(exceptions.UnreadableCert,
                          cert_parser.validate_cert, "BAD CERT")
        self.assertTrue(cert_parser.validate_cert(sample_certs.X509_CERT))
        self.assertTrue(cert_parser.validate_cert(sample_certs.X509_CERT,
                        private_key=sample_certs.X509_CERT_KEY))

    def test_read_private_key_pkcs8(self):
        self.assertRaises(exceptions.NeedsPassphrase,
                          cert_parser._read_private_key,
                          sample_certs.ENCRYPTED_PKCS8_CRT_KEY)
        cert_parser._read_private_key(
            sample_certs.ENCRYPTED_PKCS8_CRT_KEY,
            passphrase=sample_certs.ENCRYPTED_PKCS8_CRT_KEY_PASSPHRASE)

    def test_read_private_key_pem(self):
        self.assertRaises(exceptions.NeedsPassphrase,
                          cert_parser._read_private_key,
                          sample_certs.X509_CERT_KEY_ENCRYPTED)
        cert_parser._read_private_key(
            sample_certs.X509_CERT_KEY_ENCRYPTED,
            passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE)

    def test_prepare_private_key(self):
        self.assertEqual(
            cert_parser.prepare_private_key(
                sample_certs.X509_CERT_KEY_ENCRYPTED,
                passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE),
            sample_certs.X509_CERT_KEY)

    def test_prepare_private_key_orig_not_encrypted(self):
        self.assertEqual(
            cert_parser.prepare_private_key(
                sample_certs.X509_CERT_KEY),
            sample_certs.X509_CERT_KEY)

    def test_validate_cert_and_key_match(self):
        self.assertTrue(
            cert_parser.validate_cert(
                sample_certs.X509_CERT,
                private_key=sample_certs.X509_CERT_KEY))
        self.assertTrue(
            cert_parser.validate_cert(
                sample_certs.X509_CERT,
                private_key=sample_certs.X509_CERT_KEY.decode('utf-8')))
        self.assertRaises(exceptions.MisMatchedKey,
                          cert_parser.validate_cert,
                          sample_certs.X509_CERT,
                          private_key=sample_certs.X509_CERT_KEY_2)

    def test_validate_cert_handles_intermediates(self):
        self.assertTrue(
            cert_parser.validate_cert(
                sample_certs.X509_CERT,
                private_key=sample_certs.X509_CERT_KEY,
                intermediates=(sample_certs.X509_IMDS +
                               b"\nParser should ignore junk\n")))
        self.assertTrue(
            cert_parser.validate_cert(
                sample_certs.X509_CERT,
                private_key=sample_certs.X509_CERT_KEY,
                intermediates=sample_certs.X509_IMDS_LIST))

    def test_split_x509s(self):
        imds = []
        for x509Pem in cert_parser._split_x509s(sample_certs.TEST_X509_IMDS):
            imds.append(cert_parser._get_x509_from_pem_bytes(x509Pem))

        for i in range(0, len(imds)):
            self.assertEqual(sample_certs.EXPECTED_IMD_TEST_SUBJS[i],
                             imds[i].subject.get_attributes_for_oid(
                                 x509.OID_COMMON_NAME)[0].value)

    def test_get_intermediates_pem_chain(self):
        self.assertEqual(
            sample_certs.X509_IMDS_LIST,
            list(cert_parser.get_intermediates_pems(sample_certs.X509_IMDS)))

    def test_get_intermediates_pkcs7_pem(self):
        self.assertEqual(
            sample_certs.X509_IMDS_LIST,
            list(cert_parser.get_intermediates_pems(sample_certs.PKCS7_PEM)))

    def test_get_intermediates_pkcs7_pem_bad(self):
        self.assertRaises(
            exceptions.UnreadableCert,
            lambda: list(cert_parser.get_intermediates_pems(
                b'-----BEGIN PKCS7-----\nbad data\n-----END PKCS7-----')))

    def test_get_intermediates_pkcs7_der(self):
        self.assertEqual(
            sample_certs.X509_IMDS_LIST,
            list(cert_parser.get_intermediates_pems(sample_certs.PKCS7_DER)))

    def test_get_intermediates_pkcs7_der_bad(self):
        self.assertRaises(
            exceptions.UnreadableCert,
            lambda: list(cert_parser.get_intermediates_pems(
                b'\xfe\xfe\xff\xff')))

    def test_get_x509_from_der_bytes_bad(self):
        self.assertRaises(
            exceptions.UnreadableCert,
            cert_parser._get_x509_from_der_bytes, b'bad data')

    @mock.patch('oslo_context.context.RequestContext')
    def test_load_certificates(self, mock_oslo):
        listener = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True)
        client = mock.MagicMock()
        context = mock.Mock()
        context.project_id = '12345'
        with mock.patch.object(cert_parser,
                               'get_host_names') as cp:
            with mock.patch.object(cert_parser,
                                   '_map_cert_tls_container'):
                cp.return_value = {'cn': 'fakeCN'}
                cert_parser.load_certificates_data(client, listener, context)

                # Ensure upload_cert is called three times
                calls_cert_mngr = [
                    mock.call.get_cert(context, 'cont_id_1', check_only=True),
                    mock.call.get_cert(context, 'cont_id_2', check_only=True),
                    mock.call.get_cert(context, 'cont_id_3', check_only=True)
                ]
                client.assert_has_calls(calls_cert_mngr)

        # Test asking for nothing
        listener = sample_configs_combined.sample_listener_tuple(
            tls=False, sni=False, client_ca_cert=False)
        client = mock.MagicMock()
        with mock.patch.object(cert_parser,
                               '_map_cert_tls_container') as mock_map:
            result = cert_parser.load_certificates_data(client, listener)

            mock_map.assert_not_called()
            ref_empty_dict = {'tls_cert': None, 'sni_certs': []}
            self.assertEqual(ref_empty_dict, result)
            mock_oslo.assert_called()

    def test_load_certificates_get_cert_errors(self):
        mock_cert_mngr = mock.MagicMock()
        mock_obj = mock.MagicMock()
        mock_sni_container = mock.MagicMock()
        mock_sni_container.tls_container_id = 2

        mock_cert_mngr.get_cert.side_effect = [Exception, Exception]

        # Test tls_certificate_id error
        mock_obj.tls_certificate_id = 1

        self.assertRaises(exceptions.CertificateRetrievalException,
                          cert_parser.load_certificates_data,
                          mock_cert_mngr, mock_obj)

        # Test sni_containers error
        mock_obj.tls_certificate_id = None
        mock_obj.sni_containers = [mock_sni_container]

        self.assertRaises(exceptions.CertificateRetrievalException,
                          cert_parser.load_certificates_data,
                          mock_cert_mngr, mock_obj)

    @mock.patch('octavia.certificates.common.cert.Cert')
    def test_map_cert_tls_container(self, cert_mock):
        tls = data_models.TLSContainer(
            id=sample_certs.X509_CERT_SHA1,
            primary_cn=sample_certs.X509_CERT_CN,
            certificate=sample_certs.X509_CERT,
            private_key=sample_certs.X509_CERT_KEY_ENCRYPTED,
            passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE,
            intermediates=sample_certs.X509_IMDS_LIST)
        cert_mock.get_private_key.return_value = tls.private_key
        cert_mock.get_certificate.return_value = tls.certificate
        cert_mock.get_intermediates.return_value = tls.intermediates
        cert_mock.get_private_key_passphrase.return_value = tls.passphrase
        with mock.patch.object(cert_parser, 'get_host_names') as cp:
            cp.return_value = {'cn': sample_certs.X509_CERT_CN}
            self.assertEqual(
                tls.id, cert_parser._map_cert_tls_container(
                    cert_mock).id)
            self.assertEqual(
                tls.primary_cn, cert_parser._map_cert_tls_container(
                    cert_mock).primary_cn)
            self.assertEqual(
                tls.certificate, cert_parser._map_cert_tls_container(
                    cert_mock).certificate)
            self.assertEqual(
                sample_certs.X509_CERT_KEY,
                cert_parser._map_cert_tls_container(
                    cert_mock).private_key)
            self.assertEqual(
                tls.intermediates, cert_parser._map_cert_tls_container(
                    cert_mock).intermediates)

    def test_build_pem(self):
        expected = b'imacert\nimakey\nimainter\nimainter2\n'
        tls_tuple = sample_configs_combined.sample_tls_container_tuple(
            certificate=b'imacert', private_key=b'imakey',
            intermediates=[b'imainter', b'imainter2'])
        self.assertEqual(expected, cert_parser.build_pem(tls_tuple))

    def test_get_primary_cn(self):
        cert = sample_certs.X509_CERT

        with mock.patch.object(cert_parser, 'get_host_names') as cp:
            cp.return_value = {'cn': 'fakeCN'}
            cn = cert_parser.get_primary_cn(cert)
            self.assertEqual('fakeCN', cn)

    def test_get_cert_expiration(self):
        exp_date = cert_parser.get_cert_expiration(sample_certs.X509_EXPIRED)
        self.assertEqual(
            datetime.datetime(2016, 9, 25, 18, 1, 54,
                              tzinfo=datetime.timezone.utc),
            exp_date)

        # test the exception
        self.assertRaises(exceptions.UnreadableCert,
                          cert_parser.get_cert_expiration, 'bad-cert-file')
