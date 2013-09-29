# -*- coding: utf-8 -*-
# pylint: disable-msg = W0232, W0613
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
Struct Member Definitions
=========================

This module exactly describes the struct member definitions used by
the svnmailer. All those definitions are pooled in the L{typemap} dict, which
can be supplied as-is to L{typedstruct.members}.

The following types are defined by this module:
    - C{unicode}: see L{UnicodeDescriptor}
    - C{string}: see L{StringDescriptor}
    - C{int}: see L{IntegerDescriptor}
    - C{bool}: see L{BooleanDescriptor}
    - C{humanbool}: see L{HumanBooleanDescriptor}
    - C{regex}: see L{RegexDescriptor}
    - C{token}: see L{TokenDescriptor}
    - C{tokenlist}: see L{TokenlistDescriptor}
    - C{filename}: see L{FilenameDescriptor}
    - C{unicommand}: see L{CommandlineDescriptor}
    - C{quotedstr} : see L{QuotedstringDescriptor}
    - C{stdin}: see L{StdinDescriptor}
    - C{mailaction}: see L{MailactionDescriptor}

@var typemap: The type mapping dict (C{{<name>: <class>}})
@type typemap: C{svnmailer.util.ReadOnlyDict}
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['typemap']

# global imports
from svnmailer import typedstruct, util


# Exceptions
class NotSupportedError(NotImplementedError):
    """ This method is not supported """
    pass


class BaseDescriptor(typedstruct.MemberDescriptor):
    """ Base class for svnmailer descriptors """

    def __init__(self, name, private, param = None):
        """ Initialization """
        super(BaseDescriptor, self).__init__(name, private, param or {})
        self.MAP = bool(self.param.get('map'))
        self.SUBST = bool(self.param.get('subst'))


    def transform(self, value, arg):
        """ Transform if value is not None """
        if value is not None:
            value = self.doTransform(value, arg)

        return value


    def substitute(self, value, subst, arg):
        """ Substitute the value if it's activated """
        if self.SUBST and value is not None:
            value = self.doSubstitute(value, subst, arg)

        return value


    def premap(self, value, mapper, arg):
        """ Premap the value if it's activated """
        if self.MAP and value is not None:
            value = self.doPremap(value, mapper, arg)

        return value


    def postmap(self, value, mapper, arg):
        """ Postmap the value if it's activated """
        if self.MAP and value is not None:
            value = self.doPostmap(value, mapper, arg)

        return value


    def getCharset(self, arg):
        """ Returns the charset """
        return (arg and arg["encoding"]) or 'us-ascii'


    def getFileCharset(self, arg):
        """ Returns the file system charset """
        return arg and arg["path_encoding"]


    def doPremap(self, value, mapper, arg):
        """ abstract method

            @param value: The value to premap
            @type value: any

            @param mapper: The mapper function
            @type mapper: C{function}

            @param arg: The argument used for struct initialization
            @type arg: any
        """
        raise NotSupportedError()


    def doTransform(self, value, arg):
        """ abstract method

            @param value: The value to tranform
            @type value: any

            @param arg: The argument used for struct initialization
            @type arg: any

            @return: The transformed value
            @rtype: any
        """
        raise NotSupportedError()


    def doSubstitute(self, value, subst, arg):
        """ abstract method

            @param value: The value to substitute
            @type value: any

            @param subst: The substitution dictionary
            @type subst: C{dict}

            @param arg: The argument used for struct initialization
            @type arg: any

            @return: The substituted value
            @rtype: any
        """
        raise NotSupportedError()


    def doPostmap(self, value, mapper, arg):
        """ abstract method

            @param value: The value to premap
            @type value: any

            @param mapper: The mapper function
            @type mapper: C{function}

            @param arg: The argument used for struct initialization
            @type arg: any
        """
        raise NotSupportedError()


class BasePremapDescriptor(BaseDescriptor):
    """ Base class for premap only descriptors """

    def doPremap(self, value, mapper, arg):
        """ Maps the value """
        return mapper(value)


    def doPostmap(self, value, mapper, arg):
        """ Passes through """
        return value


class BasePostmapDescriptor(BaseDescriptor):
    """ Base class for postmap only descriptors """

    def doPremap(self, value, mapper, arg):
        """ Passes through """
        return value


class UnicodeDescriptor(BasePostmapDescriptor):
    """ Unicode object storage """

    def doTransform(self, value, arg):
        """ Transforms the value to unicode if it wasn't already

            @exception TypeError: The supplied value is neither C{str} nor
               C{unicode}
            @exception UnicodeError: The supplied value is a string and cannot
                be interpreted as the specified charset
        """
        if isinstance(value, str):
            value = value.decode(self.getCharset(arg))
        elif not isinstance(value, unicode):
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        return value


    def doSubstitute(self, value, subst, arg):
        """ Substitutes the value """
        return util.substitute(value, subst)


    def doPostmap(self, value, mapper, arg):
        """ Maps the value

            @exception TypeError: The mapped value is neither C{str} nor
               C{unicode}
            @exception UnicodeError: The mapped value is a string and cannot
                be interpreted as the specified charset
        """
        return self.transform(mapper(value), arg)


class StringDescriptor(BaseDescriptor):
    """ String storage """

    def doTransform(self, value, arg):
        """ Turns into a string

            @exception TypeError: The supplied value is not convertable
            @exception ValueError: The supplied value is not convertable
        """
        return str(value)


class IntegerDescriptor(BaseDescriptor):
    """ Integer storage """

    def doTransform(self, value, arg):
        """ Turns into an int

            @exception TypeError: The supplied value is not convertable
            @exception ValueError: The supplied value is not convertable
        """
        return int(value)


class BooleanDescriptor(BaseDescriptor):
    """ Boolean storage """

    def doTransform(self, value, arg):
        """ Turns into a boolean """
        return bool(value)


class HumanBooleanDescriptor(BaseDescriptor):
    """ Boolean storage with translater from human readable booleans

        @cvar TRUE: The true words (C{tuple} of C{str})
        @type TRUE: C{tuple}

        @cvar FALSE: The false words (C{tuple} of C{str})
        @type FALSE: C{tuple}

        @ivar HUMAN: The dictionary containing true and false keys
        @type HUMAN: C{dict}
    """
    TRUE = ('1', 'yes', 'on', 'true')
    FALSE = ('', '0', 'no', 'off', 'false', 'none')

    def __init__(self, name, private, param = None):
        """ Initialization """
        super(HumanBooleanDescriptor, self).__init__(name, private, param)

        self.HUMAN = dict.fromkeys(self.TRUE, True)
        self.HUMAN.update(dict.fromkeys(self.FALSE, False))


    def doTransform(self, value, arg):
        """ Turns into boolean

            @exception ValueError: The supplied value was not recognized as
                human boolean
        """
        try:
            return self.HUMAN[str(value).lower()]
        except KeyError:
            raise ValueError(
                "Value %r means neither 'true' nor 'false'" % value
            )


class RegexDescriptor(BasePremapDescriptor):
    """ Regex storage

        @ivar FLAGS: The flags for the regex compiler
        @type FLAGS: C{int}
    """

    def __init__(self, name, private, param = None):
        """ Initialization """
        super(RegexDescriptor, self).__init__(name, private, param)
        self.FLAGS = self.param.get('flags', 0)


    def doTransform(self, value, arg):
        """ Turns into a regex

            @exception TypeError: Invalid type of value or the flags
                are broken
            @exception ValueError: The regex could not be compiled
            @exception UnicodeError: The supplied value was a string and
                could not be converted to unicode
        """
        import re

        if isinstance(value, str):
            value = value.decode(self.getCharset(arg))

        try:
            value = re.compile(value, self.FLAGS)
        except re.error:
            raise ValueError("Regex %r could not be compiled" % value)

        return value


class TokenDescriptor(BasePremapDescriptor):
    """ Unicode token storage """

    def __init__(self, name, private, param = None):
        """ Initialization """
        super(TokenDescriptor, self).__init__(name, private, param)

        allowed = self.param.get('allowed')
        if allowed:
            self.ALLOWED = dict.fromkeys([token.lower() for token in allowed])
        else:
            self.ALLOWED = None


    def doTransform(self, value, arg):
        """ Transforms the value to unicode if it wasn't already

            @exception TypeError: The supplied value is neither C{str} nor
               C{unicode}
            @exception UnicodeError: The supplied value is a string and cannot
                be interpreted as the specified charset
            @exception ValueError: The supplied value is not allowed
        """
        if isinstance(value, str):
            value = value.decode(self.getCharset(arg))
        elif not isinstance(value, unicode):
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        value = value.lower()
        if self.ALLOWED is not None and value and \
                not self.ALLOWED.has_key(value):
            raise ValueError(
                "Supplied token %r is not allowed" % value
            )

        return value


class TokenlistDescriptor(BasePostmapDescriptor):
    """ (Unicode) Tokenlist storage """

    def __init__(self, name, private, param = None):
        """ Initialization """
        super(TokenlistDescriptor, self).__init__(name, private, param)

        allowed = self.param.get('allowed')
        if allowed:
            self.ALLOWED = dict.fromkeys([token.lower() for token in allowed])
        else:
            self.ALLOWED = None


    def doTransform(self, value, arg):
        """ Turns into a token list

            @exception UnicodeError: The supplied value was a string and could
                not be converted to unicode
            @exception TypeError: The input value is neither string nor unicode
                nor a tuple
            @exception ValueError: At least one of the tokens is not allowed
        """
        if isinstance(value, tuple):
            pass
        else:
            if isinstance(value, str):
                value = value.decode(self.getCharset(arg))
            elif not isinstance(value, unicode):
                raise TypeError(
                    "Supplied value must be string or unicode, not %r" %
                    type(value).__name__
                )

            value = tuple(value.split())

        if not self.MAP and self.ALLOWED is not None:
            for token in value:
                if not self.ALLOWED.has_key(token.lower()):
                    raise ValueError(
                        "Supplied token %r is not allowed" % token
                    )

        return value


    def doSubstitute(self, value, subst, arg):
        """ Substitutes the items """
        return tuple([util.substitute(token, subst) for token in value])


    def doPostmap(self, value, mapper, arg):
        """ Maps the items """
        value = tuple([mapper(token) for token in value])

        if self.ALLOWED:
            for token in value:
                if not self.ALLOWED.has_key(token.lower()):
                    raise ValueError(
                        "Supplied token %r is not allowed" % token
                    )

        return value


class FilenameDescriptor(BasePremapDescriptor):
    """ Filename storage """

    def doTransform(self, value, arg):
        """ Stores a file name either as string or unicode (depending on OS)

            @exception TypeError: The supplied value is neither C{str} nor
               C{unicode}
            @exception UnicodeError: The supplied value cannot be recoded
        """
        if hasattr(value, '_already_recoded_filename'):
            pass
        elif isinstance(value, str) or isinstance(value, unicode):
            value = util.filename.toLocale(
                value, self.getCharset(arg), self.getFileCharset(arg)
            )
            class RecodedFilename(type(value)):
                """ Designates the recoded file name """
                _already_recoded_filename = True
            value = RecodedFilename(value)
        else:
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        return value


class CommandlineDescriptor(BasePremapDescriptor):
    """ Commandline storage """

    def doTransform(self, value, arg):
        """ Parses as command line with quoted arguments

            @exception UnicodeError: C{value} could not be en-/decoded
            @exception TypeError: C{value} is neither string nor unicode nor
                tuple
            @exception ValueError: C{value} represents an invalid command
                line
        """
        if value == '':
            value = None
        elif isinstance(value, tuple):
            pass
        elif type(value) in (str, unicode):
            value = util.splitCommand(value)
            coding = self.getCharset(arg)
            if isinstance(value[0], str):
                value[1:] = [item.decode(coding) for item in value[1:]]
            value[0] = util.filename.toLocale(
                value[0], coding, self.getFileCharset(arg)
            )
            value = tuple(value)
        else:
            raise TypeError(
                "Supplied value must be string or unicode, not %r" %
                type(value).__name__
            )

        return value


class _QuotedString(str):
    """ Holds a quoted string """
    import re
    _parsed_quoted_string = (
        re.compile(r'(?:[^"\s]\S*|"[^\\"]*(?:\\[\\"][^\\"]*)*")$'),
        re.compile(r'\\([\\"])')
    )
    del re

    def __new__(cls, value = ''):
        """ Initialization and check

            @param value: The value to initialize the string
            @type value: C{str}

            @exception ValueError: The string did not pass the test
        """
        checkre, subre = cls._parsed_quoted_string
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


class QuotedstringDescriptor(BasePremapDescriptor):
    """ Quoted string storage """

    def doTransform(self, value, arg):
        """ Parses value as quoted string

            @exception ValueError: The value is not parsable as quoted string
        """
        if hasattr(value, '_parsed_quoted_string'):
            pass
        elif isinstance(value, str):
            value = _QuotedString(value)
        else:
            raise TypeError(
                "Supplied value must be a string, not %r" %
                type(value).__name__
            )

        return value


class StdinDescriptor(BaseDescriptor):
    """ Stdin storage """
    _stdin = None

    def substitute(self, value, subst, arg):
        """ Read stdin once and return it as string """
        if StdinDescriptor._stdin is None:
            import sys
            StdinDescriptor._stdin = sys.stdin.read()

        return StdinDescriptor._stdin


class _MailAction(object):
    """ Mailaction container

        @cvar TRUNCATE: C{truncate} token
        @type TRUNCATE: C{str}

        @cvar URLS: C{showurls} token
        @type URLS: C{str}

        @cvar SPLIT: C{split} token
        @type SPLIT: C{str}

        @cvar REVPROP: C{revprop-changes} token
        @type REVPROP: C{str}

        @cvar LOCKS: C{locks} token
        @type LOCKS: C{str}

        @ivar maxbytes: maximum number of bytes
        @type maxbytes: C{int}

        @ivar mode: basic mode (C{truncate}, C{showurls}, C{split})
        @type mode: C{str}

        @ivar truncate: truncate submode
        @type truncate: C{bool}

        @ivar drop: drop submode or C{None}
        @type drop: C{int}

        @ivar scope: additional scopes (C{revprop-changes}, C{locks})
        @type scope: C{tuple}
    """
    maxbytes = 0
    mode     = None
    truncate = False
    drop     = None
    scope    = ()

    TRUNCATE = "truncate"
    URLS     = "showurls"
    SPLIT    = "split"

    REVPROP  = "revprop-changes"
    LOCKS    = "locks"

    def __init__(self, action):
        """ Initialization

            @param action: The action as string
            @type action: C{str}
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

            @return: The representation
            @rtype: C{str}
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


class MailactionDescriptor(BasePremapDescriptor):
    """ Mail action parsing and storage """

    def doTransform(self, value, arg):
        """ Parse the mail action """
        if not value:
            value = None
        elif isinstance(value, _MailAction):
            pass
        elif isinstance(value, str):
            value = _MailAction(value)
        else:
            raise TypeError(
                "Supplied value must be a string, not %r" %
                type(value).__name__
            )

        return value


# Define the typemap
typemap = util.ReadOnlyDict({
    'unicode'   : UnicodeDescriptor,
    'string'    : StringDescriptor,
    'int'       : IntegerDescriptor,
    'bool'      : BooleanDescriptor,
    'humanbool' : HumanBooleanDescriptor,
    'regex'     : RegexDescriptor,
    'token'     : TokenDescriptor,
    'tokenlist' : TokenlistDescriptor,
    'filename'  : FilenameDescriptor,
    'unicommand': CommandlineDescriptor,
    'quotedstr' : QuotedstringDescriptor,
    'stdin'     : StdinDescriptor,
    'mailaction': MailactionDescriptor,
})
