# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0201,R0921
# pylint-version = 0.7.0
#
# Copyright 2004-2005 André Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Base classes for setting loader implementations

:Groups:
 - `Settings Containers`: `GroupSettingsContainer`, `GeneralSettingsContainer`,
   `RuntimeSettingsContainer`
 - `Base Classes`: `BaseSettings`, `BaseMapper`, `BaseConfig`, `BaseMember`,
   `BasePremapMember`, `BasePostmapMember`
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'Error',
    'NotSupportedError',
    'GroupSettingsContainer',
    'GeneralSettingsContainer',
    'RuntimeSettingsContainer',
    'BaseSettings',
    'MapFinder',
    'BaseMapper',
    'BaseConfig',
    'BaseMember',
    'BasePremapMember',
    'BasePostmapMember',
]

# global imports
from svnmailer import settings
from svnmailer.settings import _typedstruct

# Exceptions
class Error(settings.Error):
    """ Base exception for this module """
    pass

class NotSupportedError(Error):
    """ This method is not supported """
    pass


class GroupSettingsContainer(_typedstruct.Struct):
    """ Container for group settings """
    pass


class GeneralSettingsContainer(_typedstruct.Struct):
    """ Container for general settings """
    pass


class RuntimeSettingsContainer(_typedstruct.Struct):
    """ Container for runtime settings """
    pass


class BaseSettings(object):
    """ Settings management

        :note: The `init` method must be overridden to do the actual
               initialization.

        :Groups:
         - `Section Names`: `MAPSECTION`, `DEFAULTSECTION`, `GENERALSECTION`
         - `Settings Containers Classes`: `_GROUP_CONTAINER`,
           `_GENERAL_CONTAINER`, `_RUNTIME_CONTAINER`

        :CVariables:
         - `MAPSECTION`: The mapping section name; if ``None``, mapping is
           effectively disabled
         - `DEFAULTSECTION`: The name of the ``[defaults]`` section
         - `GENERALSECTION`: The name of the ``[general]`` section

         - `_GROUP_CONTAINER`: group configuration container
         - `_GENERAL_CONTAINER`: ``[general]`` configuration container
         - `_RUNTIME_CONTAINER`: runtime configuration container

         - `_DEFAULT_CHARSET`: The default settings charset

        :IVariables:
         - `groups`: group settings list (``[GroupSettingsContainer(), ...]``)
         - `general`: General settings container
         - `runtime`: Runtime settigs container
         - `_charset`: The charset used for settings recoding
         - `_fcharset`: The charset used for filename recoding
         - `_maps`: The value mappers to use or ``None``
         - `_mappers`: The map finder classes (``[class, ...]``)
         - `_creators`: The container creator classes
           (``{'general': creator1, 'group': creator2, 'runtime': creator3}``)

        :Types:
         - `MAPSECTION`: ``unicode``
         - `DEFAULTSECTION`: ``unicode``
         - `GENERALSECTION`: ``unicode``
         - `_GROUP_CONTAINER`: `_typedstruct.Struct`
         - `_GENERAL_CONTAINER`: `_typedstruct.Struct`
         - `_RUNTIME_CONTAINER`: `_typedstruct.Struct`
         - `_DEFAULT_CHARSET`: ``str``

         - `groups`: ``list``
         - `general`: `GeneralSettingsContainer`
         - `runtime`: `RuntimeSettingsContainer`
         - `_charset`: ``str``
         - `_fcharset`: ``str``
         - `_maps`: ``dict``
         - `_mappers`: sequence
         - `_creators`: ``dict``
    """
    MAPSECTION     = u"maps"
    DEFAULTSECTION = u"defaults"
    GENERALSECTION = u"general"

    _DEFAULT_CHARSET = "us-ascii"

    _GROUP_CONTAINER = GroupSettingsContainer
    _GENERAL_CONTAINER = GeneralSettingsContainer
    _RUNTIME_CONTAINER = RuntimeSettingsContainer


    def __init__(self, options, members, typemap, mappers):
        """ Constructor

            Don't override this one. Override `init` instead.

            :Parameters:
             - `options`: runtime options
             - `members`: The member definitions
             - `typemap`: The member type descriptors
             - `mappers`: The map finder classes

            :Types:
             - `options`: ``optparse.OptionContainer``
             - `members`: ``dict``
             - `typemap`: ``dict``
             - `mappers`: sequence
        """
        # supply default values
        self._charset   = self._DEFAULT_CHARSET
        self._fcharset  = options.path_encoding
        self._maps      = None
        self._mappers   = mappers
        self._creators  = self._createCreators(members, typemap)

        # create public config nodes
        self.groups  = []
        self.general = None
        self.runtime = self._initRuntime(options)

        # run initializer
        self.init()

        # check for sanity
        self._checkInitialization()


    def init(self):
        """ Abstract custom initializer """
        raise NotImplementedError()


    def _checkInitialization(self):
        """ Checks if all containers are filled

            :exception AssertionError: A config was not initialized
        """
        if not(self.general and self.runtime and self.groups):
            raise AssertionError("Settings are not completely initialized")


    def _initRuntime(self, options):
        """ Initializes the runtime from options

            :param `options`: runtime options
            :type `options`: ``optparse.OptionParser``

            :return: A new runtime container, filled from `options`
            :rtype: `RuntimeSettingsContainer`
        """
        return self._createRuntimeContainer(
            revision      = options.revision,
            repository    = options.repository,
            path_encoding = options.path_encoding,
            debug         = options.debug,
            config        = options.config,
            mode          = options.mode,
            author        = options.author,
            propname      = options.propname,
            action        = options.action,
        )


    def _createGroupContainer(self, **kwargs):
        """ Returns an initialized group settings container

            :param `kwargs`: Initial settings

            :return: A new `GroupSettingsContainer` instance
            :rtype: `GroupSettingsContainer`
        """
        return self._creators['group'].create(
            maps   = self._maps,
            arg    = {'encoding': self._charset,
                    'path_encoding': self._fcharset},
            initkw = kwargs,
        )


    def _createDefaultGroupContainer(self, **kwargs):
        """ Returns an initialized default group settings container

            :param kwargs: Initial settings

            :return: A new `GroupSettingsContainer` instance (with maps
                     disabled)
            :rtype: `GroupSettingsContainer`
        """
        return self._creators['group'].create(
            maps    = None, # default container doesn't get a map
            arg     = {'encoding': self._charset,
                       'path_encoding': self._fcharset},
            initkw  = kwargs,
        )


    def _createGeneralContainer(self, **kwargs):
        """ Returns an initialized general settings container

            :param `kwargs`: Initial settings

            :return: A new `GeneralSettingsContainer` instance
            :rtype: `GeneralSettingsContainer`
        """
        return self._creators['general'].create(
            maps    = self._maps,
            arg     = {'encoding': self._charset,
                       'path_encoding': self._fcharset},
            initkw  = kwargs,
        )


    def _createRuntimeContainer(self, **kwargs):
        """ Returns an initialized runtime settings container

            Note that the runtime settings (from commandline)
            are always assumed to be utf-8 encoded.

            :param `kwargs`: Initial settings

            :return: A new `RuntimeSettingsContainer` instance
            :rtype: `RuntimeSettingsContainer`
        """
        return self._creators['runtime'].create(
            maps    = None, # maps don't make sense here
            arg     = {'encoding': 'utf-8',
                       'path_encoding': self._fcharset},
            initkw  = kwargs,
        )


    def _createMapFinder(self, config):
        """ Returns a map finder

            :param `config`: The config object
            :type `config`: `BaseConfig`

            :return: A new `MapFinder` instance
            :rtype: `MapFinder`
        """
        return MapFinder(self._mappers, config)


    def _createCreators(self, members, typemap):
        """ Returns new container creator instances

            :Parameters:
             - `members`: The member definitions
             - `typemap`: The member type descriptors

            :Types:
             - `members`: ``dict``
             - `typemap`: ``dict``

            :return: The container creators
            :rtype: ``dict``
        """
        create = _typedstruct.StructCreator
        group_members = members['group']
        general_members = members['general']
        runtime_members = members['runtime']

        return {
            'group'  : create(cls = self._GROUP_CONTAINER,
                members  = group_members['members'],
                aliases  = group_members['aliases'],
                eqignore = group_members['eqignore'],
                typemap  = typemap,
            ),
            'general': create(cls = self._GENERAL_CONTAINER,
                members  = general_members['members'],
                aliases  = general_members['aliases'],
                typemap  = typemap,
            ),
            'runtime': create(cls = self._RUNTIME_CONTAINER,
                members  = runtime_members['members'],
                aliases  = runtime_members['aliases'],
                typemap  = typemap,
            ),
        }


class MapFinder(object):
    """ Logic to run the map finder classes

        :ivar `_mappers`: The map finder class instances
        :type `_mappers`: ``list``
    """

    def __init__(self, mappers, config):
        """ Initialization

            :Parameters:
             - `mappers`: The map finder classes
             - `config`: The config object

            :Types:
             - `mappers`: sequence
             - `config`: `BaseConfig`
        """
        self._mappers = [mapper(config) for mapper in mappers]


    def find(self, spec):
        """ Asks the map finder classes for a matching mapper

            :param spec: The mapping spec
            :type spec: ``str``

            :return: A new mapper based on the spec or ``None`` if no mapper
                    found the spec suitable
        """
        for mapper in self._mappers:
            result = mapper.create(spec)
            if result is not None:
                return result

        return None


    def cleanup(self):
        """ Asks the map finder classes to cleanup behind them """
        for mapper in self._mappers:
            mapper.cleanup()


class BaseMapper(object):
    """ Base class for mapper generators

        :ivar `_config`: The config object
        :type `_config`: `BaseConfig`
    """

    def __init__(self, config):
        """ Initialization

            Don't override this method, use `init` instead

            :param config: The config object
            :type config: `BaseConfig`
        """
        self._config = config
        self.init()


    def init(self):
        """ Custom initialization """
        pass


    def create(self, spec):
        """ Returns the actual mapper based on `spec`

            This method must be implemented by subclasses

            :param `spec`: The mapping spec
            :type `spec`: ``str``

            :return: The new mapper function or ``None`` if `spec` was not
                     suitable for this mapper
            :rtype: ``callable``
        """
        raise NotImplementedError()


    def cleanup(self):
        """ Cleanup. Called after all maps are resolved """
        pass


class BaseConfig(object):
    """ Representation of the loaded config

        :ivar `charset`: Charset of the config file
        :type `charset`: ``str``
    """

    def __init__(self, settingsobj):
        """ Initialization

            :param `settingsobj`: The settings object
            :type `settingsobj`: `BaseSettings`
        """
        self.charset = settingsobj._charset


    def extractSection(self, section, xform = True, keep = False, check = True):
        """ Returns the options of the specified section

            The section is also removed. (except `keep` is True)

            :Groups:
             - `Flags`: `xform`, `keep`, `check`

            :Parameters:
             - `section`: The config section name
             - `xform`: Shall the option names be normalized?
             - `keep`: Keep the section after processing?
             - `check`: Check the option name for sanity?

            :Types:
             - `section`: ``str``
             - `xform`: ``bool``
             - `keep`: ``bool``
             - `check`: ``bool``

            :return: A sequence of tuples (``[('name', 'value'), ...]``)
            :rtype: generator

            :Exceptions:
             - `ConfigSectionNotFoundError`: The specified section was
               not found in the config file

             - `ConfigOptionUnkownError`: There was an unknown config option.
        """
        raise NotImplementedError()


    def __iter__(self):
        """ Iterator over the section names

            :return: The section name iterator
            :rtype: ``iter``
        """
        raise NotImplementedError()


    def __delitem__(self, section):
        """ Removes a section to prevent further processing

            :param `section`: The section to remove
            :type `section`: ``str``

            :exception KeyError: The section doesn't exist
        """
        raise NotImplementedError()


class BaseMember(_typedstruct.Member):
    """ Base class for svnmailer descriptors """

    def init(self):
        """ Initialization """
        if self.param is None:
            self.param = {}

        self.MAP = bool(self.param.get('map'))
        self.SUBST = bool(self.param.get('subst'))

        arg = self.arg
        self.CHARSET = (arg and arg["encoding"]) or 'us-ascii'
        self.FILECHARSET = arg and arg["path_encoding"]


    def transform(self, value):
        """ Transform if value is not None """
        if value is not None:
            value = self.doTransform(value)

        return value


    def substitute(self, value, subst):
        """ Substitute the value if it's activated """
        if self.SUBST and value is not None:
            value = self.doSubstitute(value, subst)

        return value


    def premap(self, value):
        """ Premap the value if it's activated """
        if self.MAP and value is not None:
            value = self.doPremap(value)

        return value


    def postmap(self, value):
        """ Postmap the value if it's activated """
        if self.MAP and value is not None:
            value = self.doPostmap(value)

        return value


    def doPremap(self, value):
        """ abstract method

            :param `value`: The value to premap
            :type `value`: any

            :return: The mapped value
            :rtype: any
        """
        raise NotSupportedError()


    def doTransform(self, value):
        """ abstract method

            :param `value`: The value to tranform
            :type `value`: any

            :return: The transformed value
            :rtype: any
        """
        raise NotSupportedError()


    def doSubstitute(self, value, subst):
        """ abstract method

            :Parameters:
             - `value`: The value to substitute
             - `subst`: The substitution dictionary

            :Types:
             - `value`: any
             - `subst`: ``dict``

            :return: The substituted value
            :rtype: any
        """
        raise NotSupportedError()


    def doPostmap(self, value):
        """ abstract method

            :param `value`: The value to premap
            :type `value`: any

            :return: The mapped value
            :rtype: any
        """
        raise NotSupportedError()


class BasePremapMember(BaseMember):
    """ Base class for premap only descriptors """

    def doPremap(self, value):
        """ Maps the value """
        return self.mapper(value)


    def doPostmap(self, value):
        """ Passes through """
        return value


class BasePostmapMember(BaseMember):
    """ Base class for postmap only descriptors """

    def doPremap(self, value):
        """ Passes through """
        return value
