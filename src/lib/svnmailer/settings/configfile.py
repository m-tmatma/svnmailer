# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0142,W0201
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
============================
 Configfile Settings Loader
============================

This module provides a settings loader, which pulls the config from an
INI like text file.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'Error',
    'ConfigIOError',
    'ConfigMissingError',
    'ConfigInvalidError',
    'ConfigMappingSpecInvalidError',
    'ConfigSectionNotFoundError',
    'ConfigOptionUnknownError',
    'ConfigFileSettings',
]

# global imports
import errno, os, sys
from svnmailer import util
from svnmailer.settings import _base, _fileparser


# Exceptions
class Error(_base.Error):
    """ Base exception for this module """
    pass

class ConfigIOError(Error):
    """ Config file could not be loaded """
    pass

class ConfigMissingError(Error):
    """ Config not specified and not found on default locations """
    pass

class ConfigInvalidError(Error):
    """ Config file has errors """
    pass

class ConfigMappingSpecInvalidError(ConfigInvalidError):
    """ Config mapping spec was not recognized """
    pass

class ConfigSectionNotFoundError(ConfigInvalidError):
    """ Specified config section was not found """
    pass

class ConfigOptionUnknownError(ConfigInvalidError):
    """ An unknown option was parsed """
    pass


class ConfigFileSettings(_base.BaseSettings):
    """ Provide settings from config

        :cvar `_PARSEERROR`: Config exception to catch
        :type `_PARSEERROR`: ``Exception``
    """
    __implements__ = [_base.BaseSettings]

    _PARSEERROR = _fileparser.Error


    def init(self):
        """ Implements `_base.BaseSettings.init`

            :exception Error: Some error occured
        """
        try:
            config = self._createFileConfig()
            self._charset = config.charset
            self._maps = self._extractMapSections(config)

            self.general = self._extractGeneralSection(config)
            self.groups = self._extractGroupSections(config) # needs general
        except (ValueError, TypeError, self._PARSEERROR), exc:
            raise ConfigInvalidError, str(exc), sys.exc_info()[2]


    def _extractGroupSections(self, config):
        """ Extracts the group configurations

            :param `config`: The `FileConfig` instance
            :type `config`: `FileConfig`

            :return: The group sections (``[container, ...]``)
            :rtype: ``list``

            :exception ConfigOptionUnkownError: There was an unknown config
                                                option in the file.
        """
        defaults, ddict = self._getGroupDefaults(config)

        groups = []
        container = self._createGroupContainer
        passconfig = self._passConfig
        for section in config:
            ddict['_name'] = section
            groups.append(passconfig(config, container(**ddict), section))

        if not groups:
            groups.append(container(**defaults('values')))

        return groups


    def _extractGeneralSection(self, config):
        """ Extracts the general config

            :param `config`: The `FileConfig` instance
            :type `config`: `FileConfig`

            :return: A new ``GeneralSettingsContainer``
            :rtype: `_base.GeneralSettingsContainer`

            :Exceptions:
             - `ConfigSectionNotFoundError`: ``[general]`` not found
             - `ConfigOptionUnkownError`: There was an unknown config option
               in the file.
        """
        section = self.GENERALSECTION.encode(self._charset)

        return self._passConfig(
            config, self._createGeneralContainer(), section
        )


    def _extractMapSections(self, config):
        """ Returns the map definitions

            :TODO: raise an error on unknown options

            :param `config`: The `FileConfig` instance
            :type `config`: `FileConfig`

            :return: The mapper table (``{'option': mapper, ...}``)
            :rtype: ``dict``

            :exception ConfigMappingSpecInvalidError: The mapping spec was
                                                      invalid
        """
        maps = {}

        section = self.MAPSECTION
        if section is None:
            return maps

        finder = self._createMapFinder(config)
        try:
            section = section.encode(self._charset)
            try:
                for option, value in config.extractSection(section):
                    mapper = finder.find(value)
                    if mapper is not None:
                        maps[option] = mapper
                    else:
                        raise ConfigMappingSpecInvalidError(
                            "Invalid mapping specification %r = %r" %
                            (option, value)
                        )
            except ConfigSectionNotFoundError:
                """ [maps] are optional """
                pass
        finally:
            finder.cleanup()

        return maps


    def _getGroupDefaults(self, config):
        """ Returns the default groups container

            :param `config`: The `FileConfig` instance
            :type `config`: `FileConfig`

            :return: The defaults (groupcontainer without maps) as container
                     and dict (``(_base.GroupSettingsContainer, dict)``)
            :rtype: ``tuple``
        """
        section = self.DEFAULTSECTION.encode(self._charset)
        defaults = self._createDefaultGroupContainer(
            _name = self.DEFAULTSECTION,
            diff_command = self.general.diff_command, # backwards compat
        )

        try:
            self._passConfig(config, defaults, section)
        except ConfigSectionNotFoundError:
            """ ``[defaults]`` is optional """
            pass

        ddict = dict(defaults('values'))
        ddict.update({
            "_def_for_repos": defaults.for_repos,
            "_def_for_paths": defaults.for_paths,
        })

        return (defaults, ddict)


    def _passConfig(self, config, container, section):
        """ Passes the options to the specified container

            :Parameters:
             - `config`: The `FileConfig` instance
             - `container`: The container object to fill
             - `section`: The config section name

            :Types:
             - `config`: `FileConfig`
             - `container`: `_typedstruct.Struct`
             - `section`: ``str``

            :return: The container again (convenience return)
            :rtype: `_typedstruct.Struct`

            :Exceptions:
             - `ConfigSectionNotFoundError`: The specified section was
               not found in the config file
             - `ConfigOptionUnkownError`: There was an unknown config option
               in the file.
        """
        for option, value in config.extractSection(section):
            try:
                setattr(container, option, value)
            except AttributeError:
                raise ConfigOptionUnknownError(
                    "Unknown option '%s' in section [%s]" %
                    (option, section)
                )

        return container


    def _createFileConfig(self):
        """ Returns a loaded config file object

            :return: A new `FileConfig` instance
            :rtype: `FileConfig`

            :exception ConfigInvalidError: Config format error
        """
        return FileConfig(self)


class FileConfig(_base.BaseConfig):
    """ Representation of the loaded config file

        :CVariables:
         - `_CHARSETOPTION`: Normalized name of the ``config_charset`` option
         - `_INCLUDEOPTION`: Normalized name of the ``include_config`` option

        :IVariables:
         - `_parsed`: The `_fileparser.FileParser` instance

        :Types:
         - `_CHARSETOPTION`: ``str``
         - `_INCLUDEOPTION`: ``str``
         - `_parsed`: `_fileparser.FileParser`
    """
    __implements__ = [_base.BaseConfig]

    _CHARSETOPTION  = "config_charset"
    _INCLUDEOPTION  = "include_config"


    def __init__(self, settingsobj):
        """ Initialization

            :param `settingsobj`: The settings object
            :type `settingsobj`: `_base.BaseSettings`

            :Exceptions:
             - `ConfigIOError`: some configfile could not be opened
             - `ConfigMissingError`: see `_findConfig`
             - `ValueError`: Syntax Error detected or unicode failure
               in ``include_config`` preoption
             - `ConfigInvalidError`: some error occured while parsing the
               config
        """
        super(FileConfig, self).__init__(settingsobj)
        self._parsed = self._loadConfig(settingsobj)


    def __iter__(self):
        """ Iterator over the section names """
        for section in self._parsed:
            yield section.name


    def __delitem__(self, section):
        """ Removes the specified section """
        del self._parsed[section]


    def extractSection(self, section, xform = True, keep = False, check = True):
        """ Returns the options of the specified section

            :Exceptions:
             - `ConfigSectionNotFoundError`: The section was not found
             - `ConfigOptionUnknownError`: A option name was invalid
        """
        try:
            section = self._parsed[section]
        except KeyError, exc:
            raise ConfigSectionNotFoundError(str(exc))

        if xform:
            transform = self._optionxform
        else:
            transform = lambda val: val

        for option in section:
            xoption = transform(option.name)

            # options starting with _ are for internal usage
            if check and xoption.startswith('_'):
                raise ConfigOptionUnknownError(
                    "Unknown option '%s' in section [%s]" %
                    (option.name, section.name)
                )

            yield (xoption, option.value)

        if not keep:
            try:
                del self._parsed[section.name]
            except KeyError:
                """ ignore """
                pass


    def _optionxform(self, option):
        """ Returns the transformed option

            :return: The normalized option
            :rtype: ``str``
        """
        return option.lower().replace('-', '_')


    def _loadConfig(self, settingsobj):
        """ Load and parse main config file

            :param `settingsobj`: The settings object
            :type `settingsobj`: `_base.BaseSettings`

            :return: The parsed config
            :rtype: `_fileparser.FileParser`

            :Exceptions:
             - `ConfigIOError`: some configfile could not be opened
             - `ConfigMissingError`: see `_findConfig`
             - `ValueError`: Syntax Error detected or unicode failure
               in includes
        """
        parser = self._createFileParser()
        config_fp = self._findConfig(settingsobj)
        try:
            parser.slurp(config_fp, config_fp.name)
            config_fp.close()
        except IOError, exc:
            raise ConfigIOError("%s: %s" % (config_fp.name, str(exc)))

        self._processPreOptions(parser, settingsobj, config_fp.name)

        return parser


    def _processPreOptions(self, parsed, settingsobj, name):
        """ Processes the pre section options

            These options are specified *before* the first section
            If there aren't any of such options specified, they are
            looked up in ``[general]`` (backwards compat).

            :Parameters:
             - `parsed`: The parsed config
             - `settingsobj`: The settings object
             - `name`: The name of the main config file (used to determine
               relative includes)

            :Types:
             - `parsed`: `_fileparser.FileParser`
             - `settingsobj`: `_base.BaseSettings`
             - `name`: ``basestring``

            :Exceptions:
             - `ConfigIOError`: Error reading an included file
             - `ValueError`: Syntax Error detected or unicode failure
               in includes
             - `ConfigInvalidError`: There are unknown options without a
               section
        """
        section = None
        if section not in parsed:
            section = settingsobj.GENERALSECTION.encode(self.charset)
            if section not in parsed:
                return

        section = parsed[section]
        charset = self._extractOption(section, self._CHARSETOPTION)
        if charset is not None and charset.value:
            self.charset = charset.value

        includes = self._extractOption(section, self._INCLUDEOPTION)
        if section.name is None:
            if len(section) > 0:
                raise ConfigInvalidError(
                    "Unrecognized sectionless options: %s" %
                    ', '.join(["'%s'" % opt.name for opt in section])
                )

            del parsed[None]

        if includes and includes.value:
            self._attachIncludes(parsed, settingsobj, includes.value, name)


    def _attachIncludes(self, parsed, settingsobj, includes, mainfile):
        """ Attaches the includes to the main config

            :Parameters:
             - `parsed`: The parsed config

             - `settingsobj`: The settings object

             - `includes`: Whitespace separated sequence of quoted strings
               where each represents a file name to include (this is the
               specification of the option value)

             - `mainfile`: main config filename

            :Types:
             - `parsed`: `_fileparser.FileParser`
             - `settingsobj`: `_base.BaseSettings`
             - `includes`: ``str``
             - `mainfile`: ``str``

            :Exceptions:
             - `ConfigIOError`: Error reading an included file
             - `ValueError`: Syntax Error detected or unicode failure
               in `includes`
             - `ConfigInvalidError`: sectionless option in include file
               detected
        """
        path = os.path
        mainpath = path.abspath(path.dirname(mainfile))
        fcharset = settingsobj.runtime.path_encoding

        includes = [
            util.filename.toLocale(config_file, self.charset, fcharset)
            for config_file in util.splitCommand(includes) if config_file
        ]

        for config_file in includes:
            thisfile = path.join(mainpath, config_file)
            try:
                config_fp = file(thisfile)
                parsed.slurp(config_fp, config_fp.name)
                config_fp.close()
            except IOError, exc:
                raise ConfigIOError("%s: %s" % (config_file, str(exc)))

            if None in parsed:
                raise ConfigInvalidError(
                    "Options without a section found in included config '%s'" %
                    thisfile
                )


    def _extractOption(self, section, option):
        """ Returns the specified option or ``None``

            All options of the section are scanned and transformed
            using `_optionxform`. The first matching option
            wins and is removed after retrieving the value.

            :Parameters:
             - `section`: The section to scan
             - `option`: The option name in question

            :Types:
             - `section`: `_fileparser.Section`
             - `option`: ``str``

            :return: The option
            :rtype: `_fileparser.Option`
        """
        for opt in section:
            if option == self._optionxform(opt.name):
                del section[opt.name]
                return opt

        return None


    def _findConfig(self, settingsobj):
        """ Finds and opens the main config file

            :param `settingsobj`: The settings object
            :type `settingsobj`: `_base.BaseSettings`

            :return: The open descriptor
            :rtype: ``file``

            :Exceptions:
             - `ConfigMissingError`: config neither specified nor
               on default locations found. Default locations are (tried
               in that order):

               * <repos>/conf/mailer.conf
               * <scriptdir>/mailer.conf
               * /etc/svn-mailer.conf

             - `ConfigIOError`: specified configfile could not be opened
        """
        config_file = settingsobj.runtime.config
        if config_file:
            try:
                return file(os.path.abspath(util.filename.toLocale(
                    config_file,
                    self.charset,
                    settingsobj.runtime.path_encoding
                )))
            except IOError, exc:
                raise ConfigIOError("%s: %s" % (config_file, str(exc)))

        # try default locations
        for config_file in self._getDefaultConfigFiles(settingsobj):
            try:
                return file(config_file)
            except IOError, exc:
                if exc[0] != errno.ENOENT: # try next one only if not found
                    raise ConfigIOError("%s: %s" % (
                        config_file, str(exc)
                    ))

        raise ConfigMissingError("No config file found")


    def _getDefaultConfigFiles(self, settingsobj):
        """ Returns the default config file locations

            :param `settingsobj`: The settings object
            :type `settingsobj`: `_base.BaseSettings`

            :return: The list of config file locations
            :rtype: ``list``
        """
        path = os.path
        fcharset = settingsobj.runtime.path_encoding
        argv0 = util.filename.fromLocale(sys.argv[0], fcharset)
        scriptpath = path.dirname(argv0)
        repospath = settingsobj.runtime.repository

        if isinstance(argv0, unicode):
            tolocale = util.filename.toLocale
            candidates = [tolocale(name, locale_enc = fcharset) for name in [
                path.join(repospath, u'conf', u'mailer.conf'),
                path.join(scriptpath, u'mailer.conf'),
                path.join(unicode(path.sep), u'etc', u'svn-mailer.conf'),
            ]]
        else: # --path-encoding=none
            candidates = [
                path.join(repospath, 'conf', 'mailer.conf'),
                path.join(scriptpath, 'mailer.conf'),
                path.join(path.sep, 'etc', 'svn-mailer.conf'),
            ]

        return [path.abspath(name) for name in candidates]


    def _createFileParser(self):
        """ Returns a new ``FileParser`` instance

            :return: The ``FileParser`` instance
            :rtype: `_fileparser.FileParser`
        """
        return _fileparser.FileParser()
