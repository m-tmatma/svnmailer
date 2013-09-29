# -*- coding: utf-8 -*-
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
Runtime settings for the svnmailer
==================================

This module defines one public class, called L{Settings}. This class is the
storage container for all settings used by the svnmailer. L{Settings} is an
abstract class. There is just one method that must be implemented --
L{Settings.init}. This method is responsible for filling the container
properly. An implementor of the L{Settings} class can be found in the
L{svnmailer.config} module.

This module further defines the Settings subcontainers
L{GroupSettingsContainer}, L{GeneralSettingsContainer} and
L{RuntimeSettingsContainer}, but you should not instantiate them directly --
L{Settings} provides methods that return instances of these containers.
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['Settings', 'modes']

# global imports
from svnmailer import typedstruct, struct_accessors


class _Tokens(object):
    """ Generic token container

        @ivar valid_tokens: The valid mode tokens (str, str, ...)
        @type valid_tokens: C{tuple}
    """
    valid_tokens = ()

    def __init__(self, *args):
        """ Initialization """
        self.valid_tokens = args
        for token in self.valid_tokens:
            setattr(self, token.encode('us-ascii'), token)

modes = _Tokens('commit', 'propchange', 'lock', 'unlock')
xpath = _Tokens(u'yes', u'no', u'ignore')
showenc = _Tokens(u'yes', u'no', u'nondefault')


def groupMembers(space):
    """ Define the members of the group settings

        The following members are defined:
            - C{_name}: Name of the group
            - C{_def_for_repos}: default for_repos regex
            - C{_def_for_paths}: default for_paths regex
            - C{for_repos}: Repository regex
            - C{for_paths}: Path regex (inside the repos)
            - C{exclude_paths}: Exclude path regex to prevent for_paths from
                being applied
            - C{ignore_if_other_matches}: this group will be ignored if there
                are any other groups selected for a particular path
            - C{show_nonmatching_paths}: How to deal with paths that are not
                matched by the group
            - C{commit_subject_template}: Subject template for commit mail
            - C{propchange_subject_template}: Subject template for revpropchanges
            - C{lock_subject_template}: Subject template for locks
            - C{unlock_subject_template}: Subject template for unlocks
            - C{commit_subject_prefix}: Subject prefix for commit mail
            - C{propchange_subject_prefix}: Subject prefix for revpropchanges
            - C{lock_subject_prefix}: Subject prefix for locks
            - C{unlock_subject_prefix}: Subject prefix for unlocks
            - C{max_subject_length}: Maximum subject length
            - C{from_addr}: C{From:} address format string
            - C{to_addr}: C{To:} address format string
            - C{to_fake}: C{To:} non-address format string
            - C{bcc_addr}: C{Bcc:} address format string
            - C{reply_to_addr}: C{Reply-To:} address format string
            - C{diff_command}: The diff command to use
            - C{generate_diffs}: List of actions for which diffs are generated
            - C{browser_base_url}: type and format string of the repository
                browser base url
            - C{custom_header}: custom header name and format template
            - C{to_newsgroup}: The newsgroup where the notification should be
                posted to
            - C{long_news_action}: The action to take on huge commit postings
            - C{long_mail_action}: The action to take on huge commit mails
            - C{mail_transfer_encoding}: Content-Transfer-Encoding for mails
            - C{news_transfer_encoding}: Content-Transfer-Encoding for news
            - C{mail_type}: The mail construction type
            - C{extract_x509_author}: Treat author as x509 subject and try to
                extract author's real name and email address
            - C{cia_project_name}: The project name used for CIA notifications
            - C{cia_project_module}: The project module used for CIA
                notifications
            - C{cia_project_branch}: The project branch used for CIA
                notifications
            - C{cia_project_submodule}: The project submodule used for CIA
                notifications
            - C{cia_project_path}: The project path, which will be stripped from
                the absolute node path
            - C{apply_charset_property}: Should svnmailer:content-charset
                properties be recognized?
            - C{show_applied_charset}: Show the encoding of the files in the
                diff?
            - C{viewcvs_base_url}: (I{deprecated}, use C{browser_base_url}
                instead) format string for the viewcvs URL

        @param space: The namespace to pollute
        @type space: C{dict}

        @return: The members definition
        @rtype: C{dict}
    """
    args = {
        'space'      : space,
        'typemap'    : struct_accessors.typemap,
        'the_members': {
            '_name'                      : 'unicode',
            '_def_for_repos'             : 'regex',
            '_def_for_paths'             : 'regex',
            'for_repos'                  : ('regex',      {'map': True}),
            'for_paths'                  : ('regex',      {'map': True}),
            'exclude_paths'              : ('regex',      {'map': True}),
            'ignore_if_other_matches'    : 'humanbool',
            'show_nonmatching_paths'     : ('token',
                                           {'map': True,
                                            'allowed': xpath.valid_tokens}),
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
            'to_fake'                    : ('unicode',
                                           {'subst': True, 'map': True}),
            'bcc_addr'                   : ('tokenlist',
                                           {'subst': True, 'map': True}),
            'reply_to_addr'              : ('unicode',
                                           {'subst': True, 'map': True}),
            'to_newsgroup'               : ('tokenlist',
                                           {'subst': True, 'map': True}),
            'diff_command'               : ('unicommand', {'map': True}),
            'generate_diffs'             : 'tokenlist',
            'browser_base_url'           : ('unicode',
                                           {'subst': True, 'map': True}),
            'long_mail_action'           : ('mailaction', {'map': True}),
            'long_news_action'           : ('mailaction', {'map': True}),
            'mail_type'                  : ('unicode',    {'map': True}),
            'mail_transfer_encoding'     : 'unicode',
            'news_transfer_encoding'     : 'unicode',
            'custom_header'              : ('unicode',
                                           {'subst': True, 'map': True}),
            'extract_x509_author'        : 'humanbool',
            'cia_rpc_server'             : ('unicode',    {'map': True}),
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
                                           {'allowed': showenc.valid_tokens}),

            # deprecated
            'viewcvs_base_url'           : ('unicode',
                                           {'subst': True, 'map': True}),
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
    }

    return typedstruct.members(**args)


def generalMembers(space):
    """ Define the members of the general settings

        The following members are defined:
            - C{diff_command}: The diff command
            - C{sendmail_command}: The sendmail compatible command
            - C{smtp_host}: The smtp host (C{host[:port]})
            - C{smtp_user}: The smtp auth. user
            - C{smtp_pass}: The smtp auth. password
            - C{debug_all_mails_to}: All mails are sent to these addresses
                (for debugging purposes)
            - C{cia_rpc_server}: The XML-RPC server running the CIA tracker
            - C{tempdir}: The directory to use for temporary files

        @param space: The namespace to pollute
        @type space: C{dict}

        @return: The members definition
        @rtype: C{dict}
    """
    args = {
        'space'      : space,
        'typemap'    : struct_accessors.typemap,
        'the_members': {
            'sendmail_command'  : ('unicommand', {'map': True}),
            'smtp_host'         : ('unicode',    {'map': True}),
            'smtp_user'         : ('quotedstr',  {'map': True}),
            'smtp_pass'         : ('quotedstr',  {'map': True}),
            'nntp_host'         : ('unicode',    {'map': True}),
            'nntp_user'         : ('quotedstr',  {'map': True}),
            'nntp_pass'         : ('quotedstr',  {'map': True}),
            'debug_all_mails_to': ('tokenlist',  {'map': True}),
            'tempdir'           : ('filename',   {'map': True}),

            # deprecated
            'cia_rpc_server'    : ('unicode',    {'map': True}),
            'diff_command'      : ('unicommand', {'map': True}),
        },
        'aliases'    : {
            'mail_command' : 'sendmail_command',
            'smtp_hostname': 'smtp_host',
            'diff'         : 'diff_command',
        },
    }

    return typedstruct.members(**args)


def runtimeMembers(space):
    """ Define the members of the runtime settings

        The following members are defined:
            - C{_repos}: The repository object
            - C{stdin}: The stdin, read once
            - C{path_encoding}: The path-encoding parameter
            - C{debug}: debug mode (True/False)
            - C{revision}: committed revision number
            - C{repository}: path to the repository
            - C{config}: supplied config file name
            - C{mode}: running mode (see L{modes})
            - C{author}: Author of the commit or revpropchange
            - C{propname}: Property changed (in revpropchange)
            - C{action}: The revprop action (M, A, D)

        @param space: The namespace to pollute
        @type space: C{dict}

        @return: The members definition
        @rtype: C{dict}
    """
    args = {
        'space'      : space,
        'typemap'    : struct_accessors.typemap,
        'the_members': {
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
        'aliases'    : None,
    }

    return typedstruct.members(**args)


class GroupSettingsContainer(typedstruct.Struct):
    """ Container for group settings

        @see: L{groupMembers} for the actual member list
    """
    __slots__ = groupMembers(locals())

    def _compare(self, other):
        """ compare some of the attributes

            @note: It uses a list of attributes that are compared if two
                of these types are tested for equality. Keep in mind that
                this comparision takes place, when the decision is made
                whether a mail for more than one group should be sent more
                than once (if the groups are not equal). All attributes, but
                the ones returned by L{_getIgnorableMembers} are compared.

            @see: L{_getIgnorableMembers}

            @param other: The object compared to
            @type other: C{GroupSettingsContainer}

            @return: Are the objects equal?
            @rtype: C{bool}
        """
        if type(self) != type(other):
            return False

        attrs = [name for name in self._members_
            if name not in self._getIgnorableMembers()
        ]

        for name in attrs:
            if getattr(self, name) != getattr(other, name):
                return False

        return True


    def _getIgnorableMembers(self):
        """ Returns the list of member names that be ignored in comparisons

            This method called by L{_compare}. Override this method to modify
            the list.

            @return: The list
            @rtype: C{list}
        """
        return [
            '_name', '_def_for_repos', '_def_for_paths',
            'for_repos', 'for_paths', 'exclude_paths',
            'ignore_if_other_matches', 'to_addr', 'from_addr',
            'to_newsgroup', 'custom_header', 'cia_rpc_server',
            'cia_project_name', 'cia_project_module', 'cia_project_branch',
            'cia_project_submodule', 'cia_project_path',
        ]


class GeneralSettingsContainer(typedstruct.Struct):
    """ Container for general settings

        @see: L{generalMembers} for the actual member list
    """
    __slots__ = generalMembers(locals())


class RuntimeSettingsContainer(typedstruct.Struct):
    """ Container for runtime settings

        @see: L{runtimeMembers} for the actual member list
    """
    __slots__ = runtimeMembers(locals())


class Settings(object):
    """ Settings management

        @note: The C{init} method must be overridden to do the actual
        initialization.

        @ivar groups: group settings list
        @type groups: C{list} of C{GroupSettingsContainer}

        @ivar general: General settings
        @type general: C{GeneralSettingsContainer}

        @ivar runtime: Runtime settigs
        @type runtime: C{RuntimeSettingsContainer}

        @ivar debug: Debug state
        @type debug: C{bool}

        @ivar _charset_: The charset used for settings recoding
        @type _charset_: C{str}

        @ivar _maps_: The value mappers to use or C{None}
        @type _maps_: C{dict}
    """

    def __init__(self, *args, **kwargs):
        """ Constructor

            Don't override this one. Override C{init()} instead.
        """
        # supply default values
        self._charset_  = 'us-ascii'
        self._fcharset_ = None
        self._maps_     = None

        self.groups = []
        self.general  = None
        self.runtime  = None

        # parameter initialization
        self.init(*args, **kwargs)

        # sanity check
        self._checkInitialization()


    def _checkInitialization(self):
        """ Checks if all containers are filled """
        if not(self.general and self.runtime and self.groups):
            raise RuntimeError("Settings are not completely initialized")


    def init(self, *args, **kwargs):
        """ Abstract initialization method """
        raise NotImplementedError()


    def _getArgs(self):
        """ Returns the basic arguments for container initialization

            @return: The args
            @rtype: C{list}
        """
        return [
            self._maps_,
            {'encoding': self._charset_, 'path_encoding': self._fcharset_}
        ]


    def getGroupContainer(self, **kwargs):
        """ Returns an initialized group settings container

            @return: The container object
            @rtype: C{GroupSettingsContainer}
        """
        return GroupSettingsContainer(*self._getArgs(), **kwargs)


    def getDefaultGroupContainer(self, **kwargs):
        """ Returns an initialized default group settings container

            @return: The container object
            @rtype: C{GroupSettingsContainer}
        """
        args = self._getArgs()
        args[0] = None # no maps
        return GroupSettingsContainer(*args, **kwargs)


    def getGeneralContainer(self, **kwargs):
        """ Returns an initialized general settings container

            @return: The container object
            @rtype: C{GeneralSettingsContainer}
        """
        return GeneralSettingsContainer(*self._getArgs(), **kwargs)


    def getRuntimeContainer(self, **kwargs):
        """ Returns an initialized runtime settings container

            Note that the runtime settings (from commandline)
            are always assumed to be utf-8 encoded.

            @return: The container object
            @rtype: C{RuntimeSettingsContainer}
        """
        args = self._getArgs()
        args[0] = None
        args[1]["encoding"] = "utf-8"
        return RuntimeSettingsContainer(*args, **kwargs)
