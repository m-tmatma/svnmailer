# -*- coding: utf-8 -*-
# pylint-version = 0.7.0
#
# Copyright 2005 André Malo or his licensors, as applicable
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
===============================
 Repository Browser Generators
===============================

This package contains the different browser URL generator classes.
A particular generator is selected by using the `Manager` class, which
is the only public object (well, except ``Exception``\s) in this package.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Error', 'InvalidGeneratorError', 'Manager']

# global imports
from svnmailer import util

# exceptions
class Error(Exception):
    """ Base exception for this package """
    pass

class InvalidGeneratorError(Error):
    """ The generator name was not recognized """
    pass


class Manager(util.Singleton):
    """ Repository browser manager

        :CVariables:
         - `_GENERATORS`: The mapping of all available generator names
           to their actual implementation classes. It should be modified by
           the `registerGenerator` method only. The classes are expressed
           by their fully qualified names in string form (like
           ``'svnmailer.browser.generic.Generator'``). The dict
           is initially filled with the builtin browser generator classes.
           (``{'name': 'classname', ...}``)

         - `_util`: The `svnmailer.util` module

        :Types:
         - `_GENERATORS`: ``dict``
         - `_util`: ``module``
    """
    _GENERATORS = {
        u"viewcvs" : 'svnmailer.browser.viewcvs.Generator',
        u"websvn"  : 'svnmailer.browser.websvn.Generator',
        u"svn::web": 'svnmailer.browser.svnweb.Generator',
        u"chora"   : 'svnmailer.browser.chora.Generator',
        u"trac"    : 'svnmailer.browser.trac.Generator',

        u"generic" : 'svnmailer.browser.generic.Generator',
    }
    _util = util


    def registerGenerator(self, name, classname):
        """ Registers a new browser generator

            :Parameters:
             - `name`: The name of the generator. This is the name that
               appears in the configuration. It's lowercased by the
               `registerGenerator` method.

             - `classname`: The fully qualified class name (e.g.
               ``'svnmailer.browser.generic.Generator'``)

            :Types:
             - `name`: ``unicode``
             - `classname`: ``str``
        """
        self._GENERATORS[unicode(name).lower()] = classname


    def select(self, config):
        """ Returns an initialized repository browser generator

            :param `config`: The group configuration
            :type `config`: `svnmailer.settings._base.GroupSettingsContainer`

            :return: The generator object or ``None`` if no generator was
                configured
            :rtype: `_base.BaseGenerator`

            :exception InvalidGeneratorError: The configured generator could
                                              not be recognized
            :exception ImportError: The registered generator could not be
                                    loaded
        """
        generator = None

        if config.browser_base_url:
            b_type, base_url = self._parseBrowserBase(config.browser_base_url)

            try:
                genclass = self._load(b_type)
            except KeyError:
                raise InvalidGeneratorError(
                    "Can't parse browser_base_url %r" %
                    config.browser_base_url
                )
            generator = genclass(base_url, config)

        # legacy...
        elif config.viewcvs_base_url and config.browser_base_url is None:
            generator = self._load(u"viewcvs")(config.viewcvs_base_url, config)

        # compat...
        elif config.browser_base_url is None: # not specified
            generator = self._load(u"generic")(None, config)

        if generator and not generator.hasTemplates():
            generator = None

        return generator


    def _parseBrowserBase(self, base_config):
        """ Parses the given option value into type and base url

            :param base_config: The option value
            :type base_config: ``str``

            :return: The type and the base url
            :rtype: ``tuple``
        """
        if base_config:
            tokens = base_config.split(None, 1)
            if len(tokens) == 2:
                return (tokens[0].lower(), tokens[1])
            elif len(tokens) == 1:
                return (tokens[0].lower(), None)

        return (None, None)


    def _load(self, name):
        """ Loads the class indexed by `name`

            :param `name`: The name that is looked up in the internal
                registry for the fully qualified class name
            :type `name`: ``unicode``

            :exception KeyError: `name` was not found in the registry
            :exception ImportError: The import of the class failed
        """
        name = self._GENERATORS[name]

        if '.' not in name:
            raise ImportError("%r is not a qualified name" % name)

        return self._util.loadDotted(name)

# cleanup
del util
