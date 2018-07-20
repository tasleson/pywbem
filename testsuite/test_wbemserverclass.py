#
# (C) Copyright 2018 InovaDevelopment.com
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
Test for the WBEMServer class  in pywbem._server.py that uses the pywbem_mock
support package the methods of the class. Mock is required since, testing
WBEMServer requires access to a WBEM server.
"""
from __future__ import absolute_import, print_function

import os
import pytest

from pywbem import ValueMapping, CIMInstanceName, CIMError
from pywbem._nocasedict import NocaseDict
from wbemserver_mock import WbemServerMock
import pytest_extensions

VERBOSE = True

# location of testsuite/schema dir used by all tests as test DMTF CIM Schema
# This directory is permanent and should not be removed.
TEST_DIR = os.path.dirname(__file__)
TESTSUITE_SCHEMA_DIR = os.path.join(TEST_DIR, 'schema')


class BaseMethodsForTests(object):
    """
    Common methods for test of WBEMServer class.  This includes methods to
    build the DMTF schema and to build individual instances.
    """


class TestServerClass(BaseMethodsForTests):
    # pylint: disable=too-few-public-methods
    """
    Conduct tests on the WBEMServer class.
    """

    @pytest.mark.parametrize(
        "tst_namespace",
        ['interop', 'root/interop', 'root/PG_Interop'])
    def test_wbemserver_basic(self, tst_namespace):
        # pylint: disable=no-self-use
        """
        Test the basic functions that access server information. This test
        creates the mock repository and adds classes and instances for
        the WBEMServer tests that involve namespaces, brand, profiles and
        a subset of the central_instance tests.  It includes no tests for
        errors. The primary goal of this test was to develop the mechanisms
        for easily getting classes and instances into the repo and to provide
        a basic test of functionality.
        """

        # Build the wbem server mock using the  WbemServerMock default test
        # data except that we define the interop namespace
        mock_wbemserver = WbemServerMock(interop_ns=tst_namespace)
        server = mock_wbemserver.wbem_server

        # Build instances for get_central instance
        # Using central methodology, i.e. ElementConformsToProfile

        # Test basic brand, version, namespace methods
        assert server.namespace_classname == 'CIM_Namespace'

        assert server.url == 'http://FakedUrl'

        assert server.brand == "OpenPegasus"
        assert server.version == "2.15.0"
        assert server.interop_ns == tst_namespace
        assert set(server.namespaces) == set([tst_namespace])

        # Test basic profiles methods
        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']

            tst_tup = (org, name, vers)
            pass_tst = False
            for tup in mock_wbemserver.registered_profiles:
                if tst_tup == tup:
                    pass_tst = True
                    break
            assert pass_tst

        sel_prof = server.get_selected_profiles(registered_org='DMTF',
                                                registered_name='Indications')
        assert len(sel_prof) == 1
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'
            assert inst['RegisteredName'] == 'Indications'

        sel_prof = server.get_selected_profiles(registered_org='DMTF')
        assert len(sel_prof) == 2
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'

        # Simple get_cental_instance.
        # profile_path, central_class=None,
        #                       scoping_class=None, scoping_path=None
        profile_insts = server.get_selected_profiles(registered_org='SNIA',
                                                     registered_name='Server',
                                                     registered_version='1.1.0')
        profile_path = profile_insts[0].path
        insts = server.get_central_instances(profile_path, 'CIM_ObjectManager')
        assert len(insts) == 1
        kb = NocaseDict([('SystemCreationClassName', 'CIM_ComputerSystem'),
                         ('SystemName', mock_wbemserver.system_name),
                         ('CreationClassName', 'CIM_ObjectManager')])
        assert insts[0] == CIMInstanceName('CIM_ObjectManager', keybindings=kb,
                                           namespace=tst_namespace,
                                           host=server.conn.host)


TESTCASES_CREATE_NAMESPACE = [

    # Testcases for WBEMServer.create_namespace()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * new_namespace: Name of the namespace to be created.
    #   * exp_namespace: Expected returned namespace name.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "New top level namespace",
        dict(
            new_namespace='abc',
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "New top level namespace with leading and trailing slash",
        dict(
            new_namespace='/abc/',
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "New two-segment namespace with leading and trailing slash",
        dict(
            new_namespace='/abc/def/',
            exp_namespace=u'abc/def',
        ),
        None, None, True
    ),
    (
        "New two-segment namespace where first segment already exists",
        dict(
            new_namespace='interop/def',
            exp_namespace=u'interop/def',
        ),
        None, None, True
    ),
    (
        "Existing top level namespace",
        dict(
            new_namespace='interop',
            exp_namespace=None,
        ),
        CIMError, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CREATE_NAMESPACE)
@pytest_extensions.simplified_test_function
def test_create_namespace_2(testcase,
                            new_namespace, exp_namespace):
    """
    Test creation of a namespace using approach 2.
    """

    mock_wbemserver = WbemServerMock(interop_ns='interop')
    server = mock_wbemserver.wbem_server

    act_namespace = server.create_namespace(new_namespace)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_namespace == exp_namespace


# TODO Break up tests to do individual tests for each group of methds so we can
#      test for errors, variations on what is in the repo with each method.
#      Right now we build it all in a single test.  Thus, for example we
#      need to create a test group for find_central_instances since the
#      definition of the repo is different for each method of getting the
#      central instances Iex. If the server method exists, no other methods
#      are tried.
