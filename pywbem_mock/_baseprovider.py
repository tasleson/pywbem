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
A CIM provider creates WBEM server responses to operations defined in DSP0200.

The BaseProvider module contains methods required by both builtin
providers and user-defined providers. This module includes methods for the
following functionality:

  * Managing namespaces in the CIM repository
  * Methods that provide access to specific objects in the CIM repository
    including the processing consistent with filtering the returned objects.
    For example, `get_class(...)` the internal equilavent of the GetClass
    and `find_instance(...)` the internal equivalent of GetInstance.
"""

from __future__ import absolute_import, print_function

from pywbem import CIMError, \
    CIM_ERR_NOT_FOUND, CIMInstance, CIMClass, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_NAMESPACE, \
    CIM_ERR_NAMESPACE_NOT_EMPTY, \
    WBEMServer

from pywbem._nocasedict import NocaseDict

from pywbem._utils import _format

# pywbem_mock implementation configuration variables that are used in
# request responsders.


class BaseProvider(object):
    """
    BaseProvider is the top level class in the provider hiearchy and includes
    methods required by both builtin providers and user-defined providers.
    This class is not intended to be executed directly.
    """

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the repository to be used by request responders.  The
            repository is fully initialized.
        """
        self.cimrepository = cimrepository

    def __repr__(self):
        return _format(
            "(self.__class__.__name__)("
            "cimrepository={s.cimrepository}, ",
            s=self)

    @property
    def namespaces(self):
        """
        list of :term:`string`: List of the namespaces that exist in the CIM
        repository.
        """
        return self.cimrepository.namespaces

    @property
    def interop_namespace_names(self):
        """
        list of :term:`string`: List of the valid Interop namespace names.
        Only these names may be the Interop namespace and only one
        Interop namespace may exist in a WBEM server environment.

        This list is defined in :attr:`pywbem.WBEMServer.INTEROP_NAMESPACES`.

        Namespace names need to be considered case insensitive.
        """
        return WBEMServer.INTEROP_NAMESPACES

    def get_instance_store(self, namespace):
        """
        Returns the instance object store for the specified CIM namespace
        within the CIM repository.  This method validates that the namespace
        exists.

        This method does not validate that the namespace exists. Be certain
        namespace is validated against CIM repository before calling this
        method

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Returns:

          :class:`~pywbem_mock.BaseObjectStore`: Object store for instances
          in the CIM repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        return self.cimrepository.get_instance_store(namespace)

    def get_qualifier_store(self, namespace):
        """
        Returns the qualifier declaration object store for the specified CIM
        namespace within the CIM repository.  This method validates that the
        namespace exists.

        This method does not validate that the namespace exists. Be certain
        namespace is validated against CIM repository before calling this
        method

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Returns:

          :class:`~pywbem_mock.BaseObjectStore`: Object store for qualifier
          declarations in the CIM repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        return self.cimrepository.get_qualifier_store(namespace)

    ################################################################
    #
    #   Methods to manage namespaces
    #
    ################################################################

    def validate_namespace(self, namespace):
        """
        Validates that a namespace is defined in the CIM repository.
        Returns only if namespace is valid. Otherwise it generates an
        exception.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Any leading or trailing
            slash characters are ignored.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
              Namespace does not exist.
        """
        try:
            self.cimrepository.validate_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format("Namespace does not exist in CIM repository: {0!A}",
                        namespace))

    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the CIM repository.

        The namespace must not yet exist in the CIM repository and the
        repository can contain only one Interop namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. Must not be
            `None`. Any leading or trailing slash characters are removed before
            the string is used to define the namespace name.

        Raises:

          ValueError: Namespace argument must not be None.
          :exc:`~pywbem.CIMError`: CIM_ERR_ALREADY_EXISTS if the namespace
            already exists in the CIM repository.
          :exc:`~pywbem.CIMError`: CIM_ERR_ALREADY_EXISTS if the namespace
            is one of the possible Interop namespace names and an interop
            namespace already exists in the CIM repository.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        # Cannot add more than one of the possible Interop namespace names
        if self.is_interop_namespace(namespace):
            if self.find_interop_namespace():
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    _format("An Interop namespace {0!A} already exists in the "
                            "CIM repository. {1!A} cannot be added. ",
                            self.find_interop_namespace(), namespace))
        try:
            self.cimrepository.add_namespace(namespace)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Namespace {0!A} already exists in the CIM repository ",
                        namespace))

    def remove_namespace(self, namespace):
        """
        Remove a CIM namespace from the CIM repository.

        The namespace must exist in the CIM repository and must be empty.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Raises:

          ValueError: Namespace argument must not be None.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NOT_FOUND if the namespace does
            not exist in the CIM repository.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if the
            namespace icontains objects.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if attempting
            to delete the default connection namespace.  This namespace cannot
            be deleted from the CIM repository
        """
        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        try:
            self.cimrepository.remove_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Namespace {0!A} does not exist in the CIM repository ",
                        namespace))
        except ValueError:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Namespace {0!A} contains objects.", namespace))

    def is_interop_namespace(self, namespace):  # pylint: disable=no-self-use
        """
        Tests if a namespace name is a valid Interop namespace name.

        This method does not access the CIM repository for this test; it
        merely compares the specified namespace name against the list of valid
        Interop namespace names returned by :meth:`interop_namespace_names`.

        Parameters:

          namespace (:term:`string`):
            The namespace name that is to be tested.

        Returns:

          :class:`py:bool`: Indicates whether the namespace name is a valid
          Interop namespace name.
        """
        ns_lower = [ns.lower() for ns in self.interop_namespace_names]
        return namespace.lower() in ns_lower

    def find_interop_namespace(self):
        """
        Find the Interop namespace in the CIM repository, or return `None`.

        The Interop namespace is identified by comparing all namespace names
        in the CIM repository against the list of valid Interop namespace names
        returned by :meth:`interop_namespace_names`.

        Returns:

          :term:`string`: The name of the Interop namespace if one exists in
          the CIM repository or otherwise `None`.
        """
        ns_dict = NocaseDict({ns: ns for ns in self.cimrepository.namespaces})
        for name in self.interop_namespace_names:
            if name in ns_dict:
                return ns_dict[name]
        return None

    ################################################################
    #
    #   Common Repository access methods used by MainProvider and
    #   InstanceProviders
    #
    ################################################################

    @staticmethod
    def _remove_qualifiers(obj):
        """
        Remove all qualifiers from the input object where the object may
        be an CIMInstance or CIMClass. Removes qualifiers from the object and
        from properties, methods, and parameters

        This is used to process the IncludeQualifier parameter for CIMClass
        and CIMInstance objects.

        Parameters:

          obj(:class:`~pywbem.CIMClass` or :class:`~pywbem.Instance`)
            Object from which qualifiers are to be removed
        """
        assert isinstance(obj, (CIMInstance, CIMClass))
        obj.qualifiers = NocaseDict()
        for prop in obj.properties:
            obj.properties[prop].qualifiers = NocaseDict()
        if isinstance(obj, CIMClass):
            for method in obj.methods:
                obj.methods[method].qualifiers = NocaseDict()
                for param in obj.methods[method].parameters:
                    obj.methods[method].parameters[param].qualifiers = \
                        NocaseDict()

    @staticmethod
    def _remove_classorigin(obj):
        """
        Remove all ClassOrigin attributes from the input object. The object
        may be a CIMInstance or CIMClass.

        Used to process the IncludeClassOrigin parameter of CIMInstance and
        CIMClass objects

        Parameters:

          obj(:class:`~pywbem.CIMClass` or :class:`~pywbem.Instance`)
            Object from which classorigin attribute is to be removed.
        """
        assert isinstance(obj, (CIMInstance, CIMClass))
        for prop in obj.properties:
            obj.properties[prop].class_origin = None
        if isinstance(obj, CIMClass):
            for method in obj.methods:
                obj.methods[method].class_origin = None

    def get_class(self, namespace, classname, local_only=None,
                  include_qualifiers=None, include_classorigin=None,
                  property_list=None):
        # pylint: disable=invalid-name
        """
        Get class from CIM repository.  Gets the class defined by classname
        from the CIM repository, creates a copy, expands the copied class to
        include superclass properties if not localonly, and filters the
        class based on propertylist and includeClassOrigin.

        This method executes all of the filter actions on the class that are
        defined for the GetClass operation and so returns a class that
        satisfies the behavior requirements of the GetClass client request
        operation defined in :term:`DSP0200` .
        (see: :meth:`pywbem.WBEMConnection.GetClass`)

        It also sets the propagated attribute.

        Parameters:

          classname (:term:`string`):
            Name of class to retrieve

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          local_only (:class:`py:bool`):
            If `True` or `None`, only properties and methods in this specific
            class are returned. `None` means not supplied by client and the
            normal server default is `True`.
            If `False`, properties and methods from the superclasses
            are included.

          include_qualifiers (:class:`py:bool`):
            If `True` or `None`, include qualifiers.  `None` is the server
            default if the parameter is not provided by the client.
            If `False`, do not include qualifiers.

          include_classorigin (:class:`py:bool`):
            If `True`, return the class_origin attributes of properties and
            methods.
            If `False` or `None` (use server default), class_origin attributes
            of properties and methods are not returned

          property_list (list of :term:`string`):
            Properties to be included in returned class.  If None, all
            properties are returned.  If empty list, no properties are returned

        Returns:

            :class:`~pywbem.CIMClass`: Copy of the CIM class in the CIM
            repository if found. Includes superclass properties installed and
            filtered in accord with the local_only, etc. arguments.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND) if class not found in
              CIM repository.
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE) if namespace
              does not exist.
        """

        class_store = self.cimrepository.get_class_store(namespace)

        # Try to get the target class and create a copy for response
        try:
            klass = class_store.get(classname, copy=True)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        # local_only server default is True so True or None remove properties
        if local_only is True or local_only is None:
            for prop, pvalue in klass.properties.items():
                if pvalue.propagated:
                    del klass.properties[prop]
            for method, mvalue in klass.methods.items():
                if mvalue.propagated:
                    del klass.methods[method]

        self.filter_properties(klass, property_list)

        # Remove qualifiers if specified.  Note that the server default
        # is to include_qualifiers if include_qualifiers is None
        if include_qualifiers is False:
            self._remove_qualifiers(klass)

        # class_origin default is False so None or False cause removal
        if not include_classorigin:
            self._remove_classorigin(klass)
        return klass

    def class_exists(self, namespace, classname):
        """
        Test if class defined by classname parameter exists in
        CIM repository defined by namespace parameter.

        Returns:

          bool: `True` if class exists and `False` if it does not exist.

        Raises:

          Exception if the namespace does not exist
        """
        class_store = self.cimrepository.get_class_store(namespace)
        return class_store.object_exists(classname)

    @staticmethod
    def filter_properties(obj, property_list):
        """
        Remove properties from an instance or class that aren't in the
        property_list parameter.

        Parameters:

          obj (:class:`~pywbem.CIMClass` or :class:`~pywbem.CIMInstance`):
            The class or instance from which properties are to be filtered

          property_list (list of :term:`string`):
            List of properties which are to be included in the result. If
            None, remove nothing.  If empty list, remove everything. else
            remove properties that are not in property_list. Duplicated names
            are allowed in the list and ignored.
        """
        if property_list is not None:
            property_list = [p.lower() for p in property_list]
            for pname in obj.properties.keys():
                if pname.lower() not in property_list:
                    del obj.properties[pname]

    @staticmethod
    def find_instance(instance_name, instance_store, copy=None):
        """
        Find an instance in the CIM repository by `instance_name` and return
        that instance. the `copy` parameter controls whether the original
        instance in the CIM repository is returned or a copy.  The
        only time the original should be returned is when the user is
        certain that the returned object WILL NOT be modified.

        Parameters:

          instance_name (:class:`~pywbem.CIMInstanceName`):
            Instance path of the instance to find in the CIM repository

          instance_store (:class:`~pywbem_mock.BaseObjectStore`):
            Instance store of the CIM repository to search for the instance

          copy (bool):
            If True do copy of the instance and return the copy. Otherwise
            return the instance in the CIM repository

        Returns:
            :class:`~pywbem.CIMInstance`: the complete CIM instance or copy of
            the CIM instance is returned if it is found in the CIM repository
            or `None` if the instance defined by `instance_name` is not found
            in the CIM repository.


        """

        if instance_store.object_exists(instance_name):
            return instance_store.get(instance_name, copy=copy)

        return None