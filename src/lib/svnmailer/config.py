# -*- coding: utf-8 -*-
# pylint: disable-msg = W0201
#
# Copyright 2004-2006 André Malo or his licensors, as applicable
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
Configfile parsing
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = [
    'ConfigFileSettings',
    'Error',
    'ConfigNotFoundError',
    'ConfigMissingError',
    'ConfigInvalidError',
    'ConfigMappingSectionNotFoundError',
    'ConfigMappingSpecInvalidError',
    'ConfigSectionNotFoundError',
    'ConfigOptionUnknownError',
]

# global imports
import ConfigParser, sys, os
from svnmailer import settings, util


# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class ConfigNotFoundError(Error):
    """ Config file not found """
    pass

class ConfigMissingError(ConfigNotFoundError):
    """ Config not specified and not found on default locations """
    pass

class ConfigInvalidError(Error):
    """ Config file has errors """
    pass

class ConfigMappingSectionNotFoundError(ConfigInvalidError):
    """ Config mapping section was not found """
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


class ConfigFileSettings(settings.Settings):
    """ Provide settings from config

        @cvar MAPSECTION: The mapping section name; if C{None},
            mapping is effectively disabled
        @type MAPSECTION: C{str}

        @ivar _config: The config object
        @type _config: C{ConfigParser.ConfigParser}
    """
    __implements__ = [settings.Settings]

    MAPSECTION = "maps"

    def init(self, *args, **kwargs):
        """ Implements the C{init} method of L{settings.Settings}

            @exception ConfigInvalidError: invalid config options
            @exception ConfigMissingError: see L{_loadConfig}
            @exception ConfigNotFoundError: see L{_loadConfig}
            @exception ConfigSectionNotFoundError: see L{_passConfig}
            @exception ConfigOptionUnkownError: see L{_passConfig}
            @exception ConfigMappingSpecInvalidError: see L{_applyMaps}
            @exception ConfigMappingSectionNotFoundError: see L{_getPlainMap}
        """
        try:
            self._init(*args, **kwargs)
        except (ValueError, TypeError, UnicodeError, ConfigParser.Error), exc:
            raise ConfigInvalidError, str(exc), sys.exc_info()[2]


    def _init(self, options):
        """ Actual implementation of C{self.init()}

            @param options: runtime options
            @type options: C{optparse.OptionParser}

            @exception ConfigMissingError: see L{_loadConfig}
            @exception ConfigNotFoundError: see L{_loadConfig}
            @exception ConfigSectionNotFoundError: see L{_passConfig}
            @exception ConfigOptionUnkownError: see L{_passConfig}
            @exception ConfigMappingSpecInvalidError: see L{_applyMaps}
            @exception ConfigMappingSectionNotFoundError: see L{_getPlainMap}
        """
        self._initRuntime(options)
        self._loadConfig()  # needs runtime
        self._initGeneral() # needs _config
        self._initGroups()  # needs _config and general


    def _initGroups(self):
        """ Initializes the Group config """
        defaults = self._getGroupDefaults()
        ddict = self._getDefaultGroupDict(defaults)

        for group in self._config.sections():
            ddict["_name"] = group
            container = self.getGroupContainer(**ddict)
            self._passConfig(container, group)
            self.groups.append(container)

        if not self.groups:
            self.groups.append(self.getGroupContainer(**defaults._dict_))


    def _getDefaultGroupDict(self, container):
        """ Returns the default group dict

            @param container: The default container
            @type container: C{svnmailer.settings.GroupSettingsContainer}

            @return: The default dict
            @rtype: C{dict}
        """
        ddict = dict(container._dict_)
        ddict.update({
            "_def_for_repos": container.for_repos,
            "_def_for_paths": container.for_paths,
        })

        return ddict


    def _getGroupDefaults(self):
        """ Returns the default groups container

            @return: The defaults (groupcontainer without maps)
            @rtype: C{svnmailer.settings.GroupSettingsContainer}
        """
        defaults = self.getDefaultGroupContainer(
            _name = "defaults",
            diff_command = self.general.diff_command,
            cia_rpc_server = self.general.cia_rpc_server,
        )
        try:
            self._passConfig(defaults, "defaults")
        except ConfigSectionNotFoundError:
            # [defaults] is optional
            pass
        else:
            self._config.remove_section('defaults')

        return defaults


    def _initGeneral(self):
        """ Initializes the general config

            @exception ConfigSectionNotFoundError: [general] not found
        """
        self.general = self.getGeneralContainer()
        self._passConfig(self.general, 'general')
        self._config.remove_section('general')


    def _initRuntime(self, options):
        """ Initializes the runtime from options

            @param options: runtime options
            @type options: C{optparse.OptionParser}
        """
        # This is needed for every container
        self._fcharset_ = options.path_encoding

        self.runtime = self.getRuntimeContainer(
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


    def _passConfig(self, container, section):
        """ Passes the options to the specified container

            @param container: The container object
            @type container: C{svnmailer.util.Struct}

            @param section: The config section name
            @type section: C{str}

            @exception ConfigSectionNotFoundError: The specified section was
                not found in the config file
            @exception ConfigOptionUnkownError: There was an unknown
                config option in the config file.
        """
        try:
            for option in self._config.options(section):
                # options starting with _ are for internal usage
                if option[:1] in ('_', '-'):
                    raise ConfigOptionUnknownError(
                        "Unknown option '%s' in section [%s]" %
                        (option, section)
                    )

                try:
                    container._set_(
                        option.replace('-', '_'),
                        self._config.get(section, option, raw = True)
                    )
                except AttributeError:
                    raise ConfigOptionUnknownError(
                        "Unknown option '%s' in section [%s]" %
                        (option, section)
                    )
        except ConfigParser.NoSectionError, exc:
            raise ConfigSectionNotFoundError(str(exc))


    def _loadConfig(self):
        """ Parse config file

            @return: parsed config
            @rtype: C{ConfigParser.ConfigParser}

            @exception ConfigNotFoundError: some configfile could not
                be opened
            @exception ConfigMissingError: see L{_findConfig}
            @exception ConfigMappingSpecInvalidError: see L{_applyMaps}
            @exception ConfigMappingSectionNotFoundError: see L{_getPlainMap}
        """
        config_fp = self._findConfig()
        self._config = self._createConfigParser()
        try:
            self._config.readfp(config_fp, config_fp.name)
            config_fp.close()
        except IOError, exc:
            raise ConfigNotFoundError("%s: %s" % (config_fp.name, str(exc)))

        if self._config.has_section("general"):
            self._applyCharset()
            self._applyIncludes(config_fp.name)

        self._applyMaps()


    def _createConfigParser(self):
        """ Returns a ConfigParser instance

            @return: The ConfigParser instance
            @rtype: C{ConfigParser.ConfigParser}
        """
        return ConfigParser.ConfigParser()


    def _findConfig(self, _file = file):
        """ Finds and opens the main config file

            @param _file: The function to open the file
            @type _file: C{callable}

            @return: The open descriptor
            @rtype: file like object

            @exception ConfigMissingError: config neither specified nor
                on default locations found. Default locations are (tried
                in that order):
                     - <repos>/conf/mailer.conf
                     - <scriptdir>/mailer.conf
                     - /etc/svn-mailer.conf
            @exception ConfigNotFoundError: specified configfile could not
                be opened
        """
        import errno

        config_file = self.runtime.config
        if config_file:
            try:
                return config_file == '-' and sys.stdin or _file(config_file)
            except IOError, exc:
                raise ConfigNotFoundError("%s: %s" % (config_file, str(exc)))

        for config_file in self._getDefaultConfigFiles():
            try:
                return _file(config_file)
            except IOError, exc:
                # try next one only if not found
                if exc[0] != errno.ENOENT:
                    raise ConfigNotFoundError("%s: %s" % (
                        config_file, str(exc)
                    ))

        raise ConfigMissingError("No config file found")


    def _applyMaps(self):
        """ Resolves all map definitions

            @TODO: raise an error on unknown options

            @exception ConfigMappingSpecInvalidError: The mapping spec was
                invalid
            @exception ConfigMappingSectionNotFoundError: see L{_getPlainMap}
        """
        section = self.MAPSECTION
        if section is None or not self._config.has_section(section):
            return

        self._maps_ = {}
        remove_sections = [section]
        for option in self._config.options(section):
            if option[:1] in ('_', '-'):
                raise ConfigOptionUnknownError(
                    "Unknown option '%s' in section [%s]" %
                    (option, section)
                )

            value = self._config.get(section, option, raw = True)
            if value[:1] == '[' and value[-1:] == ']':
                this_section = value[1:-1]
                self._maps_[option.replace('-', '_')] = \
                    self._getPlainMap(this_section)
                remove_sections.append(this_section)
            else:
                raise ConfigMappingSpecInvalidError(
                    "Invalid mapping specification %r = %r" % (option, value)
                )

        for name in dict.fromkeys(remove_sections).keys():
            self._config.remove_section(name)


    def _getPlainMap(self, section):
        """ Returns a plain map for a particular section

            @param section: The mapping section
            @type section: C{str}

            @return: The mapping function
            @rtype: C{callable}

            @exception ConfigMappingSectionNotFoundError: The specified
                section was not found
        """
        try:
            mdict = dict([
                (option, self._config.get(section, option, raw = True))
                for option in self._config.options(section)
            ])
        except ConfigParser.NoSectionError, exc:
            raise ConfigMappingSectionNotFoundError(str(exc))

        def mapfunc(value):
            """ Mapping function """
            return mdict.get(value, value)

        return mapfunc


    def _applyIncludes(self, origfile, _file = file):
        """ Applies the includes found in [general]

            @param origfile: original filename
            @type origfile: C{str}

            @param _file: The function to open the file
            @type _file: C{callable}

            @exception ConfigNotFoundError: Error reading an included file
        """
        opt = "include_config"
        try:
            try:
                includes = self._config.get("general", opt, raw = True).strip()
            except ConfigParser.NoOptionError:
                opt = "include-config"
                includes = self._config.get("general", opt, raw = True).strip()
        except ConfigParser.NoOptionError:
            # don't even ignore
            pass
        else:
            self._config.remove_option("general", opt)
            if not len(includes):
                return

            origpath = os.path.dirname(os.path.abspath(origfile))
            includes = [
                util.filename.toLocale(
                    config_file, self._charset_, self.runtime.path_encoding
                )
                for config_file in util.splitCommand(includes) if config_file
            ]

            for config_file in includes:
                try:
                    config_fp = _file(os.path.join(origpath, config_file))
                    self._config.readfp(config_fp, config_fp.name)
                    config_fp.close()
                except IOError, exc:
                    raise ConfigNotFoundError("%s: %s" % (
                        config_file, str(exc)
                    ))
 

    def _applyCharset(self):
        """ Applies the charset found in [general] """
        opt = "config_charset"
        try:
            try:
                charset = self._config.get("general", opt, raw = True).strip()
            except ConfigParser.NoOptionError:
                opt = "config-charset"
                charset = self._config.get("general", opt, raw = True).strip()
        except ConfigParser.NoOptionError:
            # don't even ignore
            pass
        else:
            self._config.remove_option("general", opt)
            if charset:
                self._charset_ = charset


    def _getDefaultConfigFiles(self, _os = os, _sys = sys):
        """ Returns the default config files

            @return: The list
            @rtype: C{list}
        """
        argv0 = util.filename.fromLocale(
            _sys.argv[0], self.runtime.path_encoding
        )
        if isinstance(argv0, unicode):
            candidates = [util.filename.toLocale(
                    name, locale_enc = self.runtime.path_encoding
                ) for name in [
                    _os.path.join(
                        self.runtime.repository, u'conf', u'mailer.conf'
                    ),
                    _os.path.join(_os.path.dirname(argv0), u'mailer.conf'),
                    u'/etc/svn-mailer.conf',
                ]
            ]
        else:
            # --path-encoding=none
            candidates = [
                _os.path.join(self.runtime.repository, 'conf', 'mailer.conf'),
                _os.path.join(_os.path.dirname(argv0), 'mailer.conf'),
                _os.path.join(_os.path.sep, "etc", "svn-mailer.conf"),
            ]

        return candidates
