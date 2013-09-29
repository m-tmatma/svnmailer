# -*- coding: iso-8859-1 -*-
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
=====================
 Settings Management
=====================

This package is responsible for all settings logic. Here are all possible
configuration specified in detail. The application code relies on proper
type and constraints checking, which happens here.

Extension modules can register new options by using the proper methods of
the `Manager` class.

:Variables:
 - `MODES`: The different behaviour modes
 - `XPATH`: The option values for the ``show_nonmatching_paths`` option
 - `SHOWENC`: The option values for the ``show_applied_charset`` option

:Types:
 - `MODES`: `Tokens`
 - `XPATH`: `Tokens`
 - `SHOWENC`: `Tokens`
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Error', 'Tokens', 'MODES', 'XPATH', 'SHOWENC', 'Manager']

# global imports
from svnmailer import util

# exceptions
class Error(Exception):
    """ Base exception for this package """
    pass


class Tokens(object):
    """ Generic token container

        The purpose of the container is to avoid typos when using literal
        constants and nasty hidden bugs because of them. If we mistype
        <instance>.<token> we get an AttributeError. When using plain
        literals we may just get misbehaviour instead.

        Additionally `valid_tokens` provides the set of valid tokens
        for checks.

        :ivar `valid_tokens`: The valid tokens (``('t1', 't2', ...)``)
        :type `valid_tokens`: ``tuple``
    """
    valid_tokens = ()

    def __init__(self, *args):
        """ Initialization

            :param args: The tokens to provide

            :exception UnicodeError: A token could not be encoded as ascii
        """
        self.valid_tokens = args
        for token in self.valid_tokens:
            setattr(self, token.encode('us-ascii'), token)


    def __repr__(self):
        """ Returns a string representation of the instance """
        return "%s(%s)" % (self.__class__.__name__, ", ".join([
            repr(item) for item in self.valid_tokens
        ]))


MODES   = Tokens('commit', 'propchange', 'lock', 'unlock')
XPATH   = Tokens(u'yes', u'no', u'ignore')
SHOWENC = Tokens(u'yes', u'no', u'nondefault')


group_members = {
    'members': {
        '_name'                      : 'unicode',
        '_def_for_repos'             : 'regex',
        '_def_for_paths'             : 'regex',
        'for_repos'                  : ('regex',      {'map': True}),
        'for_paths'                  : ('regex',      {'map': True}),
        'exclude_paths'              : ('regex',      {'map': True}),
        'ignore_if_other_matches'    : 'humanbool',
        'show_nonmatching_paths'     : ('token',
                                       {'map': True,
                                        'allowed': XPATH.valid_tokens}),
        'commit_subject_template'    : ('unicode',    {'map': True}),
        'propchange_subject_template': ('unicode',    {'map': True}),
        'lock_subject_template'      : ('unicode',    {'map': True}),
        'unlock_subject_template'    : ('unicode',    {'map': True}),
        'commit_subject_prefix'      : ('unicode',
                                       {'subst': True, 'map': True}),
        'propchange_subject_prefix'  : ('unicode',
                                       {'subst': True, 'map': True}),
        'lock_subject_prefix'        : ('unicode',
                                       {'subst': True, 'map': True}),
        'unlock_subject_prefix'      : ('unicode',
                                       {'subst': True, 'map': True}),
        'max_subject_length'         : 'int',
        'from_addr'                  : ('tokenlist',
                                       {'subst': True, 'map': True}),
        'to_addr'                    : ('tokenlist',
                                       {'subst': True, 'map': True}),
        'reply_to_addr'              : ('unicode',
                                       {'subst': True, 'map': True}),
        'to_newsgroup'               : ('tokenlist',
                                       {'subst': True, 'map': True}),
        'diff_command'               : ('unicommand', {'map': True}),
        'generate_diffs'             : 'tokenlist',
        'browser_base_url'           : ('unicode',    {'map': True}),
        'revision_url'               : ('unicode',    {'map': True}),
        'diff_add_url'               : ('unicode',    {'map': True}),
        'diff_copy_url'              : ('unicode',    {'map': True}),
        'diff_delete_url'            : ('unicode',    {'map': True}),
        'diff_modify_url'            : ('unicode',    {'map': True}),
        'long_mail_action'           : ('mailaction', {'map': True}),
        'long_news_action'           : ('mailaction', {'map': True}),
        'mail_type'                  : ('unicode',    {'map': True}),
        'mail_transfer_encoding'     : 'unicode',
        'news_transfer_encoding'     : 'unicode',
        'custom_header'              : ('unicode',
                                       {'subst': True, 'map': True}),
        'extract_x509_author'        : 'humanbool',
        'cia_project_name'           : ('unicode',
                                       {'subst': True, 'map': True}),
        'cia_project_module'         : ('unicode',
                                       {'subst': True, 'map': True}),
        'cia_project_branch'         : ('unicode',
                                       {'subst': True, 'map': True}),
        'cia_project_submodule'      : ('unicode',
                                       {'subst': True, 'map': True}),
        'cia_project_path'           : ('unicode',
                                       {'subst': True, 'map': True}),
        'apply_charset_property'     : 'humanbool',
        'show_applied_charset'       : ('token',
                                       {'allowed': SHOWENC.valid_tokens}),
        'default_charsets'           : 'tokenlist',

        # deprecated
        'viewcvs_base_url'           : ('unicode',    {'map': True}),
    },
    'aliases': {
        'suppress_if_match'  : 'ignore_if_other_matches',
        'fallback'           : 'ignore_if_other_matches',
        'reply_to'           : 'reply_to_addr',
        'x509_author'        : 'extract_x509_author',
        'charset_property'   : 'apply_charset_property',
        'truncate_subject'   : 'max_subject_length',
        'subject_length'     : 'max_subject_length',
        'diff'               : 'diff_command',
        'nonmatching_paths'  : 'show_nonmatching_paths',
        'nongroup_paths'     : 'show_nonmatching_paths',
        'show_nongroup_paths': 'show_nonmatching_paths',
    },
    'eqignore': [
        '_name',
        '_def_for_repos', '_def_for_paths',
        'for_repos', 'for_paths', 'exclude_paths', 'ignore_if_other_matches',
        'to_addr', 'from_addr', 'to_newsgroup',
        'custom_header',
        'cia_project_name', 'cia_project_module', 'cia_project_branch',
        'cia_project_submodule', 'cia_project_path',
    ],
}

general_members = {
    'members': {
        'sendmail_command'  : ('unicommand', {'map': True}),
        'smtp_host'         : ('unicode',    {'map': True}),
        'smtp_user'         : ('quotedstr',  {'map': True}),
        'smtp_pass'         : ('quotedstr',  {'map': True}),
        'nntp_host'         : ('unicode',    {'map': True}),
        'nntp_user'         : ('quotedstr',  {'map': True}),
        'nntp_pass'         : ('quotedstr',  {'map': True}),
        'debug_all_mails_to': ('tokenlist',  {'map': True}),
        'cia_rpc_server'    : ('unicode',    {'map': True}),
        'tempdir'           : ('filename',   {'map': True}),

        # deprecated
        'diff_command'      : 'unicommand', # no map, because it's treated as
                                            # [defaults] default and should
                                            # not be mapped twice
    },
    'aliases': {
        'mail_command' : 'sendmail_command',
        'smtp_hostname': 'smtp_host',
        'diff'         : 'diff_command',
    },
}

runtime_members = {
    'members': {
        '_repos'       : None,       # internal usage (Repository object)
        'stdin'        : 'stdin',
        'path_encoding': 'string',
        'debug'        : 'bool',
        'revision'     : 'int',
        'repository'   : 'filename',
        'config'       : 'filename',
        'mode'         : 'string',
        'author'       : 'unicode',
        'propname'     : 'unicode',
        'action'       : 'unicode',  # >= svn 1.2
    },
    'aliases': {},
}


class Manager(util.Singleton):
    """ Svnmailer settings manager

        :CVariables:
         - `_TYPEMAP`: The mapping of all available type names to their
           actual implementation classes. It should be modified by the
           `registerType` method only. The classes are expressed by their
           fully qualified names in string form (like
           ``'svnmailer.settings._accessors.UnicodeMember'``). The dict
           is initially filled with builtin descriptor classes.

         - `_LOADER`: The settings loader. It should be modified by the
           `registerLoader` method only and is also a fully qualified
           class name. Note that each `registerLoader` call overrides the
           previous one.

         - `_MEMBERS`: The member definitions of the configuration sections.
           Use `registerOption` to modifiy it.

         - `_MAPPERS`: The list of mapper classes. It should be modified by
           the `registerMapper` method only. The classes are expressed by
           their fully qualified names in string form (like
           ``'svnmailer.settings.mappers.PlainMapper'``). The list is
           initially filled with the builtin mapper classes.

         - `_util`: The util module

        :Types:
         - `_TYPEMAP`: ``dict``
         - `_LOADER`: ``str``
         - `_MEMBERS`: ``dict``
         - `_MAPPERS`: ``list``
         - `_util`: ``module``
    """
    _util = util
    _LOADER = 'svnmailer.settings.configfile.ConfigFileSettings'
    _TYPEMAP = {
        'unicode'   : 'svnmailer.settings._accessors.UnicodeMember',
        'string'    : 'svnmailer.settings._accessors.StringMember',
        'int'       : 'svnmailer.settings._accessors.IntegerMember',
        'bool'      : 'svnmailer.settings._accessors.BooleanMember',
        'humanbool' : 'svnmailer.settings._accessors.HumanBooleanMember',
        'regex'     : 'svnmailer.settings._accessors.RegexMember',
        'token'     : 'svnmailer.settings._accessors.TokenMember',
        'tokenlist' : 'svnmailer.settings._accessors.TokenlistMember',
        'filename'  : 'svnmailer.settings._accessors.FilenameMember',
        'unicommand': 'svnmailer.settings._accessors.CommandlineMember',
        'quotedstr' : 'svnmailer.settings._accessors.QuotedstringMember',
        'stdin'     : 'svnmailer.settings._accessors.StdinMember',
        'mailaction': 'svnmailer.settings._accessors.MailactionMember',
    }
    _MEMBERS = {
        'general': general_members,
        'group'  : group_members,
        'runtime': runtime_members,
    }
    _MAPPERS = [
        'svnmailer.settings.mappers.PlainMapper',
    ]


    def registerType(self, name, classname):
        """ Registers a new member type

            :Parameters:
             - `name`: The name of the type. It is case sensitive.
             - `classname`: The fully qualified class name (e.g.
               ``'svnmailer.settings._accessors.UnicodeMember'``)

            :Types:
             - `name`: ``str``
             - `classname`: ``str``
        """
        self._TYPEMAP[name] = classname


    def registerLoader(self, classname):
        """ Registers a new settings loader

            :param `classname`:
                The fully qualified class name (e.g.
                ``'svnmailer.settings.configfile.ConfigFileSettings'``)
            :type classname: ``str``
        """
        self._LOADER = classname


    def registerOption(self, category, name, spec = None, aliases = None,
            compare = True):
        """ Registers a new configuration option

            :Parameters:
             - `category`: The configuration category where the option
               should be recognized. Valid values are ``general``, ``group``
               and ``runtime``. Modifying the latter is not so useful though.

             - `name`: The name of the option (like ``'cia_project_path'``)

             - `spec`: The member specification. Generally this is a tuple,
               with two items: ``('descriptor', {specdict})``. If ``specdict``
               is empty, the descriptor string is sufficient. If no
               specific descriptor is needed, ``None`` may be used.

             - `aliases`: Alias names for this member (``('alias', ...)``)

             - `compare`: Does the option needs to be included in the
               comparison of different group sections (while compressing
               notification groups) (In other words -- does it affect the
               mail/news subject or body in any way)? Setting to ``False``
               is only valid if `category` is ``group``.

            :Types:
             - `category`: ``str``
             - `name`: ``str``
             - `spec`: ``tuple`` or ``str``
             - `aliases`: sequence
             - `compare`: ``bool``

            :exception KeyError: The category was invalid
        """
        cat = self._MEMBERS[category]
        cat['members'][name] = spec

        if aliases:
            for alias in aliases:
                cat['aliases'][alias] = name

        if not compare:
            cat['eqignore'].append(name)


    def registerMapper(self, classname):
        """ Registers a new mapper class

            :param classname:
                The fully qualified class name (e.g.
                ``'svnmailer.settings.mappers.PlainMapper'``)
            :type classname: ``str``
        """
        self._MAPPERS.append(classname)


    def loadSettings(self, options):
        """ Loads the settings using the registered loader

            :param options: runtime options
            :type options: ``optparse.OptionContainer``

            :return: A new `_base.BaseSettings` instance
            :rtype: `_base.BaseSettings`

            :Exceptions:
             - `Error`: A settings error occured
             - `ImportError`: A class could not be loaded
        """
        loader = self._load(self._LOADER)
        members = self._MEMBERS
        typemap = self._util.ReadOnlyDict([
            (key, self._load(val))
            for key, val in self._TYPEMAP.items()
        ])
        mappers = tuple([self._load(cls) for cls in self._MAPPERS])

        return loader(options, members, typemap, mappers)


    def _load(self, classname):
        """ Loads the class specified by `classname`

            :param `classname`: The classname to load
            :type `classname`: ``str``

            :exception ImportError: The import of the class failed
        """
        if '.' not in classname:
            raise ImportError("%r is not a qualified name" % classname)

        return self._util.loadDotted(classname)


del util, general_members, group_members, runtime_members
