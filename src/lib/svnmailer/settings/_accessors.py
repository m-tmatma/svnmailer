# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201,W0232,W0613
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
====================
 Member Descriptors
====================

This module defines the settings member descriptors used by the svnmailer.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'UnicodeMember',
    'StringMember',
    'IntegerMember',
    'BooleanMember',
    'HumanBooleanMember',
    'RegexMember',
    'TokenMember',
    'TokenlistMember',
    'FilenameMember',
    'CommandlineMember',
    'QuotedstringMember',
    'StdinMember',
    'MailactionMember',
]

# global imports
import re, sys
from svnmailer import util
from svnmailer.settings import _base


class UnicodeMember(_base.BasePostmapMember):
    """ Unicode object storage """

    def doTransform(self, value):
        """ Transforms the value to unicode if it wasn't already

            :Exceptions:
             - `TypeError`: The supplied value is neither ``str`` nor
               ``unicode``

             - `UnicodeError`: The supplied value is a string and cannot
               be interpreted as the specified charset
        """
        if isinstance(value, str):
            value = unicode(value, self.CHARSET)
        elif not isinstance(value, unicode):
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        return value


    def doSubstitute(self, value, subst):
        """ Substitutes the value """
        return util.substitute(value, subst)


    def doPostmap(self, value):
        """ Maps the value

            :Exceptions:
             - `TypeError`: The mapped value is neither ``str`` nor
               ``unicode``

             - `UnicodeError`: The mapped value is a string and cannot
               be interpreted as the specified charset
        """
        return self.transform(self.mapper(value))


class StringMember(_base.BaseMember):
    """ String storage """

    def doTransform(self, value):
        """ Turns into a string """
        return str(value)


class IntegerMember(_base.BaseMember):
    """ Integer storage """

    def doTransform(self, value):
        """ Turns into an int

            :Exceptions:
             - `TypeError`: The supplied value is not convertable
             - `ValueError`: The supplied value is not convertable
        """
        return int(value)


class BooleanMember(_base.BaseMember):
    """ Boolean storage """

    def doTransform(self, value):
        """ Turns into a boolean """
        return bool(value)


class HumanBooleanMember(_base.BaseMember):
    """ Boolean storage with translater from human readable booleans

        :CVariables:
         - `_TRUE`: The true words (``('word', ...)``)
         - `_FALSE`: The false words (``('word', ...)``)

        :IVariables:
         - `_human`: The dictionary containing true and false keys

        :Types:
         - `_TRUE`: ``tuple``
         - `_FALSE`: ``tuple``
         - `_human`: ``dict``
    """
    _TRUE = ('1', 'yes', 'on', 'true')
    _FALSE = ('', '0', 'no', 'off', 'false', 'none')

    def init(self):
        """ Custom initialization """
        super(HumanBooleanMember, self).init()
        self._human = dict.fromkeys(self._TRUE, True)
        self._human.update(dict.fromkeys(self._FALSE, False))


    def doTransform(self, value):
        """ Turns into boolean

            :exception ValueError: The supplied value was not recognized as
                                   human boolean
        """
        try:
            return self._human[str(value).lower()]
        except KeyError:
            raise ValueError(
                "Value %r means neither 'true' nor 'false'" % value
            )


class RegexMember(_base.BasePremapMember):
    """ Regex storage

        :ivar _flags: The flags for the regex compiler
        :type _flags: ``int``
    """

    def init(self):
        """ Custom initialization """
        super(RegexMember, self).init()
        self._flags = self.param.get('flags', 0)


    def doTransform(self, value):
        """ Turns into a regex

            :Exceptions:
             - `TypeError`: Invalid type of value or the flags are broken
             - `UnicodeError`: The supplied value was a ``str`` and
               could not be converted to ``unicode``
             - `ValueError`: The regex could not be compiled
        """
        if isinstance(value, str):
            value = unicode(value, self.CHARSET)

        try:
            value = re.compile(value, self._flags)
        except re.error:
            raise ValueError("Regex %r could not be compiled" % value)

        return value


class TokenMember(_base.BasePremapMember):
    """ Unicode token storage

        :ivar `_allowed`: List of allowed tokens (or ``None``) - saved in a
                          dict for faster lookup
        :type `_allowed`: ``dict``
    """

    def init(self):
        """ Custom initialization """
        super(TokenMember, self).init()

        allowed = self.param.get('allowed')
        if allowed:
            self._allowed = dict.fromkeys([token.lower() for token in allowed])
        else:
            self._allowed = None


    def doTransform(self, value):
        """ Transforms the value to unicode if it wasn't already

            :Exceptions:
             - `TypeError`: The supplied value is neither ``str`` nor
               ``unicode``

             - `UnicodeError`: The supplied value is a string and cannot
               be interpreted as the specified charset

             - `ValueError`: The supplied value is not allowed
        """
        if isinstance(value, str):
            value = unicode(value, self.CHARSET)
        elif not isinstance(value, unicode):
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        value = value.lower()
        if self._allowed is not None and value and \
                not self._allowed.has_key(value):
            raise ValueError(
                "Supplied token %r is not allowed" % value
            )

        return value


class TokenList(tuple):
    """ represents a token list """
    pass


class TokenlistMember(_base.BasePostmapMember):
    """ Unicode token list storage

        :ivar `_allowed`: List of allowed tokens (or ``None``) - saved in a
                          dict for faster lookup
        :type _allowed: ``dict``
    """

    def init(self):
        """ Custom initialization """
        super(TokenlistMember, self).init()

        allowed = self.param.get('allowed')
        if allowed:
            self._allowed = dict.fromkeys([token.lower() for token in allowed])
        else:
            self._allowed = None


    def doTransform(self, value):
        """ Turns into a token list

            :Exceptions:
             - `UnicodeError`: The supplied value was a ``str`` and could
               not be converted to ``unicode``
             - `TypeError`: The input value is neither ``str`` nor ``unicode``
               nor a `TokenList`
             - `ValueError`: At least one of the tokens is not allowed
        """
        if not isinstance(value, TokenList):
            if isinstance(value, str):
                value = unicode(value, self.CHARSET)
            elif not isinstance(value, unicode):
                raise TypeError(
                    "Supplied value must be string or unicode, not %r" %
                    type(value).__name__
                )

            value = TokenList(value.split())

        if self._allowed is not None and (not self.MAP or self.mapper is None):
            self._checkallowed(value)

        return value


    def doSubstitute(self, value, subst):
        """ Substitutes the items """
        return TokenList([util.substitute(token, subst) for token in value])


    def doPostmap(self, value):
        """ Maps the items """
        result = []
        for token in value:
            token = self.mapper(token)
            if isinstance(token, str):
                token = unicode(token, self.CHARSET)
            result.append(token)
        value = TokenList(result)

        if self._allowed is not None:
            self._checkallowed(value)

        return value


    def _checkallowed(self, value):
        """ Checks if the tokens are allowed

            :param value: The token list
            :type value: `TokenList`

            :exception ValueError: A token was invalid
        """
        for token in value:
            if not self._allowed.has_key(token.lower()):
                raise ValueError(
                    "Supplied token %r is not allowed" % token
                )


class FilenameMember(_base.BasePremapMember):
    """ Filename storage """

    def doTransform(self, value):
        """ Stores a file name either as ``str`` or ``unicode`` (depends on OS)

            :Exceptions:
             - `TypeError`: The supplied value is neither ``str`` nor
               ``unicode``
             - `UnicodeError`: The supplied value cannot be recoded
        """
        if not hasattr(value, '_already_recoded_filename'):
            if isinstance(value, basestring):
                value = util.filename.toLocale(
                    value, self.CHARSET, self.FILECHARSET
                )
                class Filename(type(value)):
                    """ Designates the recoded file name """
                    _already_recoded_filename = True
                value = Filename(value)
            else:
                raise TypeError(
                    "Supplied value must be string or unicode, not %r" %
                    type(value).__name__
                )

        return value


class Commandline(tuple):
    """ Represents a command line """

    def __new__(cls, command, charset, filecharset):
        """ Constructor

            :Parameters:
             - `command`: The command to parse
             - `charset`: The charset to apply on strings
             - `filecharset`: The charset to apply on the command

            :Types:
             - `command`: ``basestring``
             - `charset`: ``str``
             - `filecharset`: ``str``

            :return: A new `Commandline` instance
            :rtype: `Commandline`

            :Exceptions:
             - `UnicodeError`: Error while recoding the command
             - `ValueError`: Invalid command line
        """
        if not command:
            return None

        command = util.splitCommand(command)
        if isinstance(command[0], str):
            command[1:] = [unicode(item, charset) for item in command[1:]]
        command[0] = util.filename.toLocale(command[0], charset, filecharset)

        return tuple.__new__(cls, command)


class CommandlineMember(_base.BasePremapMember):
    """ Commandline storage """

    def doTransform(self, value):
        """ Parses as command line with quoted arguments

            :Exceptions:
             - `UnicodeError`: `value` could not be en-/decoded
             - `TypeError`: `value` is neither ``str`` nor ``unicode`` nor
               `Commandline`
             - `ValueError`: `value` represents an invalid command line
        """
        if isinstance(value, basestring):
            value = Commandline(value, self.CHARSET, self.FILECHARSET)
        elif not isinstance(value, Commandline):
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        return value


class QuotedString(str):
    """ Holds a quoted string """
    _quoterex = (
        re.compile(r'(?:[^"\s]\S*|"[^\\"]*(?:\\[\\"][^\\"]*)*")$'),
        re.compile(r'\\([\\"])')
    )

    def __new__(cls, value = ''):
        """ Initialization and check

            :param value: The value to initialize the string
            :type value: ``str``

            :exception ValueError: The string did not pass the test
        """
        checkre, subre = cls._quoterex
        if value and not checkre.match(value):
            raise ValueError("Could not parse quoted string %r" % value)

        if value.startswith('"'):
            value = subre.sub(r'\1', value[1:-1])

        return str.__new__(cls, value)


    def __repr__(self):
        """ Returns the representation of the quoted string """
        return repr(
            '"%s"' % str(self).replace('\\', r'\\').replace('"', r'\"')
        )


class QuotedstringMember(_base.BasePremapMember):
    """ Quoted string storage """

    def doTransform(self, value):
        """ Parses value as quoted string

            :exception ValueError: The value is not parsable as quoted string
        """
        if not isinstance(value, QuotedString):
            if isinstance(value, str):
                value = QuotedString(value)
            else:
                raise TypeError(
                    "Supplied value must be a string, not %r" %
                    type(value).__name__
                )

        return value


class StdinMember(_base.BaseMember):
    """ Stdin storage """
    _stdin = None

    def substitute(self, value, subst):
        """ Reads stdin once and returns it as string """
        if StdinMember._stdin is None:
            StdinMember._stdin = sys.stdin.read()

        return StdinMember._stdin


class MailAction(object):
    """ Mailaction container

        :Groups:
         - `Basic Modes`: `TRUNCATE`, `URLS`, `SPLIT`
         - `Scopes`: `REVPROP`, `LOCKS`

        :CVariables:
         - `TRUNCATE`: ``truncate`` token
         - `URLS`: ``showurls`` token
         - `SPLIT`: ``split`` token
         - `REVPROP`: ``revprop-changes`` token
         - `LOCKS`: ``locks`` token

        :IVariables:
         - `maxbytes`: maximum number of bytes
         - `mode`: basic mode (``truncate``, ``showurls``, ``split``)
         - `truncate`: truncation submode
         - `drop`: dropping submode or ``None``
         - `scope`: additional scopes (``revprop-changes``, ``locks``)

        :Types:
         - `TRUNCATE`: ``unicode``
         - `URLS`: ``unicode``
         - `SPLIT`: ``unicode``
         - `REVPROP`: ``unicode``
         - `LOCKS`: ``unicode``

         - `maxbytes`: ``int``
         - `mode`: ``unicode``
         - `truncate`: ``bool``
         - `drop`: ``int``
         - `scope`: ``tuple``
    """
    maxbytes = 0
    mode     = None
    truncate = False
    drop     = None
    scope    = ()

    TRUNCATE = u"truncate"
    URLS     = u"showurls"
    SPLIT    = u"split"

    REVPROP  = u"revprop-changes"
    LOCKS    = u"locks"

    def __new__(cls, action):
        """ Constructor

            :param action: The action as string
            :type action: ``basestring``

            :return: A new `MailAction` instance or ``None`` if `action` is
                     empty or `None`
            :rtype: `MailAction`
        """
        if not action:
            return None

        return object.__new__(cls)


    def __init__(self, action):
        """ Initialization

            :param action: The action as string
            :type action: ``basestring``

            :exception ValueError: The supplied `action` is invalid
        """
        _msg = "Can't parse action string %r" % (action,)

        action = action.split()
        if len(action) < 2:
            raise ValueError(_msg)

        self.maxbytes = int(action[0])
        tokens = action[1].lower().split('/')

        self.mode = tokens.pop(0).lower()
        if self.mode not in (self.TRUNCATE, self.URLS, self.SPLIT):
            raise ValueError(_msg)

        if tokens and tokens[0].lower() == self.TRUNCATE:
            if self.mode not in (self.URLS, self.SPLIT):
                raise ValueError(_msg)
            self.truncate = True
            tokens.pop(0)

        if tokens:
            if self.mode != self.SPLIT:
                raise ValueError(_msg)
            self.drop = int(tokens.pop(0))

        if tokens:
            raise ValueError(_msg)

        sdict = {}
        for token in action[2:]:
            if token.lower() not in (self.REVPROP, self.LOCKS):
                raise ValueError(_msg)
            sdict[token.lower()] = None
        self.scope = tuple(sdict.keys())


    def __repr__(self):
        """ String representation of the object

            :return: The representation
            :rtype: ``str``
        """
        result = "%d %s" % (self.maxbytes, self.mode)
        if self.truncate:
            result = "%s/truncate" % result
        if self.drop:
            result = "%s/%d" % (result, self.drop)
        if self.scope:
            scopes = list(self.scope)
            scopes.sort()
            result = " ".join([result] + scopes)

        return result


class MailactionMember(_base.BasePremapMember):
    """ Mail action parsing and storage """

    def doTransform(self, value):
        """ Parse the mail action

            :Exceptions:
             - `TypeError`: `value` has the wrong type
             - `UnicodeError`: `value` could not be decoded
             - `ValueError`: `value` has syntax errors
        """
        if isinstance(value, basestring):
            if isinstance(value, str):
                value = unicode(value, self.CHARSET)
            value = MailAction(value)
        elif not isinstance(value, MailAction):
            raise TypeError(
                "Supplied value must be a string or unicode, not %r" %
                type(value).__name__
            )

        return value
