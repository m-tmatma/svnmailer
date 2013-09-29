# -*- coding: utf-8 -*-
# pylint: disable-msg = W0613, W0622, W0704
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
Utilities
=========

This module contains some utility functions and classes used in several
places of the svnmailer. These functions have a quite general character
and can be used easily outside of the svnmailer as well.
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = [
    'TempFile',
    'getPipe4',
    'getSuitableCommandLine',
    'splitCommand',
    'filename',
    'extractX509User',
    'substitute',
    'filterForXml',
    'getParentDirList',
    'getGlobValue',
    'parseQuery',
    'modifyQuery',
    'inherit',
    'commonPaths',
    'ReadOnlyDict',
    'SafeDict',
]

# global imports
import locale, os, sys


class TempFile(object):
    """ Tempfile container class

        The class contains a destructor that removes the created
        file. This differs from the stuff in tempfile, which removes
        the file, when it's closed.

        The mode is fixed to C{w+}; a C{b} is added if the C{text}
        argument is false (see C{__init__})

        @cvar name: C{None}
        @ivar name: The full name of the file
        @type name: C{str}

        @cvar fp: C{None}
        @ivar fp: The file descriptor
        @type fp: file like object

        @cvar _unlink: C{None}
        @ivar _unlink: C{os.unlink}
        @type _unlink: callable
    """
    name = None
    fp = None
    _unlink = None

    def __init__(self, tempdir = None, text = False):
        """ Initialization

            @param tempdir: The temporary directory
            @type tempdir: C{str}

            @param text: want to write text?
            @type text: C{bool}
        """
        import tempfile

        self._unlink = os.unlink # make sure, unlink is available in __del__

        fd, self.name = tempfile.mkstemp(dir = tempdir, text = text)
        self.fp = os.fdopen(fd, "w+%s" % ["b", ""][bool(text)])


    def __del__(self):
        """ Unlink the file name """
        if self.fp:
            try:
                self.fp.close()
            except ValueError:
                # ok
                pass

        if self.name and self._unlink:
            try:
                self._unlink(self.name)
            except OSError:
                # don't even ignore
                pass


    def close(self):
        """ Close the file (but don't delete it)

            @exception ValueError: The file was already closed
        """
        if self.fp:
            self.fp.close()


def getPipe2(command):
    """ Returns a pipe object (C{Popen3} or C{_DummyPopen3} on win32)

        @param command: The command list (the first item is the command
            itself, the rest represents the arguments)
        @type command: C{list}

        @return: The pipe object
        @rtype: C{popen2.Popen3} or C{_DummyPopen3}
    """
    import popen2

    try:
        cls = popen2.Popen3
    except AttributeError:
        cls = _DummyPopen3

    return cls(getSuitableCommandLine(command))


def getPipe4(command):
    """ Returns a pipe object (C{Popen4} or C{_DummyPopen4} on win32)

        @param command: The command list (the first item is the command
            itself, the rest represents the arguments)
        @type command: C{list}

        @return: The pipe object
        @rtype: C{popen2.Popen4} or C{_DummyPopen4}
    """
    import popen2

    try:
        cls = popen2.Popen4
    except AttributeError:
        cls = _DummyPopen4

    return cls(getSuitableCommandLine(command))


class _DummyPopen4(object):
    """ Dummy Popen4 class for platforms which don't provide one in popen2 """

    def __init__(self, cmd, bufsize = -1):
        """ Initialization """
        bufsize = -1 # otherwise error on win32
        self.tochild, self.fromchild = os.popen4(cmd, 'b', bufsize)


    def wait(self):
        """ Dummy wait """
        return 0


class _DummyPopen3(object):
    """ Dummy Popen3 class for platforms which don't provide one in popen2 """

    def __init__(self, cmd, capturestderr = False, bufsize = -1):
        """ Initialization """
        bufsize = -1 # otherwise error on win32
        capturestderr = False # we don't do this on win32
        self.tochild, self.fromchild = os.popen2(cmd, 'b', bufsize)
        self.childerr = None


    def wait(self):
        """ Dummy wait """
        return 0


def getSuitableCommandLine(command, _platform = None):
    """ Return the revised command suitable for being exec'd

        Currently this means, it's escaped and converted to a string
        only for Win32, because on this system the shell is called.
        For other systems the list is just returned.

        @note: This is more or less the same as the stuff in
            svn.fs._escape_msvcrt_shell_command/arg. But it
            belongs somewhere else - e.g. into a util module...

            Perhaps once a day the whole package goes directly
            into the subversion distribution and then it's all
            cool.

        @param command: The command to escape
        @type command: C{list}

        @param _platform: A platform string (for testing purposes only)
        @type _platform: C{str}

        @return: The escaped command string or the original list
        @rtype: C{str} or C{list}
    """
    platform = _platform or sys.platform
    if platform != "win32":
        return command

    try:
        slashre = getSuitableCommandLine._slashre
    except AttributeError:
        import re
        slashre = getSuitableCommandLine._slashre = re.compile(r'(\\+)("|$)')

    # What we do here is:
    # (1) double up slashes, but only before quotes or the string end
    #     (since we surround it by quotes afterwards)
    # (2) Escape " as "^""
    #     This means "string end", "Escaped quote", "string begin" in that
    #     order
    #     (See also http://www.microsoft.com/technet/archive/winntas
    #               /deploy/prodspecs/shellscr.mspx)

    # Original comments from the svn.fs functions:
    # ============================================
    # According cmd's usage notes (cmd /?), it parses the command line by
    # "seeing if the first character is a quote character and if so, stripping
    # the leading character and removing the last quote character."
    # So to prevent the argument string from being changed we add an extra set
    # of quotes around it here.

    # The (very strange) parsing rules used by the C runtime library are
    # described at:
    # http://msdn.microsoft.com/library/en-us/vclang/html
    # /_pluslang_Parsing_C.2b2b_.Command.2d.Line_Arguments.asp

    return '"%s"' % " ".join([
        '"%s"' % slashre.sub(r'\1\1\2', arg).replace('"', '"^""')
        for arg in command
    ])


def splitCommand(command):
    r"""Split a command string with respect to quotes and such

        The command string consists of several tokens:
            - whitespace: Those are separators except inside quoted items
            - unquoted items: every token that doesn't start with
                a double quote (")
            - quoted items: every token that starts with a double quote (").
                Those items must be closed with a double quote and may contain
                whitespaces. The enclosing quotes are stripped. To put a double
                quote character inside such a token, it has to be escaped with
                a backslash (\). Therefore - backslashes themselves have to be
                escaped as well. The escapes are also stripped from the result.

        Here's an example: C{r'foo bar "baz" "zo\"" "\\nk"'} resolves
        to C{['foo', 'bar', 'baz', 'zo"', r'\nk']}

        @param command: The command string
        @type command: C{str}

        @return: The splitted command
        @rtype: C{list}

        @exception ValueError: The command string is not valid
            (unclosed quote or the like)
    """
    try:
        argre, checkre, subre = splitCommand._regexps
    except AttributeError:
        import re
        argre   = r'[^"\s]\S*|"[^\\"]*(?:\\[\\"][^\\"]*)*"'
        checkre = r'\s*(?:%(arg)s)(?:\s+(?:%(arg)s))*\s*$' % {'arg': argre}
        subre   = r'\\([\\"])'

        argre, checkre, subre = splitCommand._regexps = (
            re.compile(argre), re.compile(checkre), re.compile(subre)
        )

    if not checkre.match(command or ''):
        raise ValueError("Command string %r is not valid" % command)

    return [
        (arg.startswith('"') and [subre.sub(r'\1', arg[1:-1])] or [arg])[0]
        for arg in argre.findall(command or '')
    ]


class _LocaleFile(object):
    """ Transform filenames according to locale """
    def __init__(self, _locale = locale, _os = os, _sys = sys):
        """ Initialization """
        self.unicode_system = _os.path.supports_unicode_filenames
        self.from_enc = _locale.getpreferredencoding(False) or "us-ascii"
        self.to_enc = _sys.getfilesystemencoding() or "us-ascii"


    def toLocale(self, name, name_enc = None, locale_enc = None):
        """ Transforms a file name to the locale representation

            @param name: The name to consider
            @type name: C{str} / C{unicode}

            @param name_enc: The source encoding of C{name}, if it's
                not unicode already
            @type name_enc: C{str}

            @param locale_enc: The file system encoding (used only
                if it's not a unicode supporting OS)
            @type locale_enc: C{str}

            @return: The name in locale representation
            @rtype: C{str}/C{unicode}

            @exception UnicodeError: An error happened while recoding
        """
        if locale_enc is None:
            locale_enc = self.to_enc
        if name_enc is None:
            name_enc = self.from_enc

        if self.unicode_system:
            if isinstance(name, unicode):
                return name
            else:
                return name.decode(name_enc, "strict")

        if locale_enc.lower() == "none":
            if isinstance(name, unicode):
                raise RuntimeError("Illegal call")
            else:
                return name

        if not isinstance(name, unicode):
            name = name.decode(name_enc, "strict")

        return name.encode(locale_enc, "strict")


    def fromLocale(self, name, locale_enc = None):
        """ Transform a file name from locale repr to unicode (hopefully)

            @param name: The name to decode
            @type name: C{str}/C{unicode}

            @param locale_enc: The locale encoding
            @type locale_enc: C{str}

            @return: The decoded name
            @rtype: C{unicode}/C{str}

            @exception UnicodeError: An error happend while recoding
        """
        if isinstance(name, unicode):
            return name

        if locale_enc is None:
            locale_enc = self.from_enc

        if locale_enc.lower() == "none":
            return name # no unicode.

        return name.decode(locale_enc, "strict")

filename = _LocaleFile()


def extractX509User(author):
    """ Returns user data extracted from x509 subject string

        @param author: The author string
        @type author: C{str}

        @return: user name, mail address (user name maybe C{None})
        @rtype: C{tuple} or C{None}
    """
    if author:
        try:
            cnre, eare = extractX509User._regexps
        except AttributeError:
            import re
            cnre = re.compile(ur'/CN=([^/]+)', re.I)
            eare = re.compile(ur'/emailAddress=([^/]+)', re.I)
            extractX509User._regexps = (cnre, eare)

        author = author.decode('utf-8', 'replace')
        ea_match = eare.search(author)
        if ea_match:
            cn_match = cnre.search(author)
            return (cn_match and cn_match.group(1), ea_match.group(1))

    return None


def substitute(template, subst):
    """ Returns a filled template

        If the L{template} is C{None}, this function returns C{None}
        as well.

        @param template: The temlate to fill
        @type template: C{unicode}

        @param subst: The substitution parameters
        @type subst: C{dict}

        @return: The filled template (The return type depends on the
            template and the parameters)
        @rtype: C{str} or C{unicode}
    """
    if template is None:
        return None

    return template % SafeDict(subst.items())


def filterForXml(value):
    """ Replaces control characters with replace characters

        @param value: The value to filter
        @type value: C{unicode}

        @return: The filtered value
        @rtype: C{unicode}
    """
    try:
        regex = filterForXml._regex
    except AttributeError:
        import re
        chars = u''.join([chr(num) for num in range(32)
            if num not in (9, 10, 13) # XML 1.0
        ])
        regex = filterForXml._regex = re.compile("[%s]" % chars)

    return regex.sub(u'\ufffd', value)


def getParentDirList(path):
    """ Returns the directories up to a (posix) path

        @param path: The path to process
        @type path: C{str}

        @return: The directory list
        @rtype: C{list}
    """
    import posixpath

    path = posixpath.normpath("/%s" % path)
    if path[:2] == '//':
        path = path[1:]

    dirs = []
    path = posixpath.dirname(path)
    while path != '/':
        dirs.append(path)
        path = posixpath.dirname(path)
    dirs.append('/')

    return dirs


def getGlobValue(globs, path):
    """ Returns the value of the glob, where path matches

        @param globs: The glob list (C{[(glob, associated value)]})
        @type globs: C{list} of C{tuple}

        @param path: The path to match
        @type path: C{str}

        @return: The matched value or C{None}
        @rtype: any
    """
    import fnmatch

    result = None
    for glob in globs:
        if fnmatch.fnmatchcase(path, glob[0]):
            result = glob[1]
            break

    return result


def modifyQuery(query, rem = None, add = None, set = None, delim = '&'):
    """ Returns a modified query string

        @note: set is a convenience parameter, it's actually a combination of
            C{rem} and C{add}. The order of processing is:
                1. append the set parameters to C{rem} and C{add}
                2. apply C{rem}
                3. apply C{add}

        @warning: query parameters containing no C{=} character are silently
            dropped.

        @param query: The query string to modify
        @type query: C{str} or C{dict}

        @param rem: parameters to remove (if present)
        @type rem: C{list} of C{str}

        @param add: parameters to add
        @type add: C{list} of C{tuple}

        @param set: parameters to override
        @type set: C{list} of C{tuple}

        @param delim: Delimiter to use when rebuilding the query string
        @type delim: C{str}
    """
    rem = list(rem or [])
    add = list(add or [])
    set = list(set or [])

    # parse query string
    query_dict = (isinstance(query, dict) and
        [query.copy()] or [parseQuery(query)]
    )[0]

    # append set list to rem and add
    rem.extend([tup[0] for tup in set])
    add.extend(set)

    # apply rem
    for key in rem:
        try:
            del query_dict[key]
        except KeyError:
            # don't even ignore
            pass

    # apply add
    for key, val in add:
        query_dict.setdefault(key, []).append(val)

    # rebuild query and return
    return delim.join([
        delim.join(["%s=%s" % (key, str(val)) for val in vals])
        for key, vals in query_dict.items()
    ])


def parseQuery(query):
    """ Parses a query string

        @warning: query parameters containing no C{=} character are silently
            dropped.

        @param query: The query string to parse
        @type query: C{str}

        @return: The parsed query (C{{key: [values]}})
        @rtype: C{dict}
    """
    try:
        queryre = parseQuery._regex
    except AttributeError:
        import re
        parseQuery._regex = queryre = re.compile(r'[&;]')

    query_dict = {}
    for key, val in [pair.split('=', 1)
            for pair in queryre.split(query) if '=' in pair]:
        query_dict.setdefault(key, []).append(val)

    return query_dict


def commonPaths(paths):
    """ Returns the common component and the stripped paths

        It expects that directories do always end with a trailing slash and
        paths never begin with a slash (except root).

        @param paths: The list of paths (C{[str, str, ...]})
        @type paths: C{list}

        @return: The common component (always a directory) and the stripped
            paths (C{(str, [str, str, ...])})
        @rtype: C{tuple}
    """
    import posixpath

    common = ''
    if len(paths) > 1 and "/" not in paths:
        common = posixpath.commonprefix(paths)
        if common[-1:] != "/":
            common = common[:common.rfind("/") + 1]

        idx = len(common)
        if idx > 0:
            paths = [path[idx:] or "./" for path in paths]
            common = common[:-1] # chop the trailing slash

    return (common, paths)


def inherit(cls, *bases):
    """ Inherits class cls from *bases

        @note: cls needs a __dict__, so __slots__ is tabu

        @param cls: The class to inherit from *bases
        @type cls: C{class}

        @param bases: The base class(es)
        @type bases: C{list}
    """
    newdict = dict([(key, value)
        for key, value in cls.__dict__.items()
        if key != '__module__'
    ])
    cls = type(cls.__name__, tuple(bases), newdict)
    setattr(cls, "_%s__decorator_class" % cls.__name__, cls)

    return cls


def parseContentType(value):
    """ Parses a content type

        (the email module unfortunately doesn't provide a public
        interface for this)

        @warning: comments are not recognized yet

        @param value: The value to parse - must be ascii compatible
        @type value: C{basestring}

        @return: The parsed header (C{(value, {key, [value, value, ...]})})
            or C{None}
        @rtype: C{tuple}
    """
    try:
        if isinstance(value, unicode):
            value.encode('us-ascii')
        else:
            value.decode('us-ascii')
    except (AttributeError, UnicodeError):
        return None

    try:
        typere, pairre, stripre = parseContentType._regexps
    except AttributeError:
        import re
        # a bit more lenient than RFC 2045
        tokenres = r'[^\000-\040()<>@,;:\\"/[\]?=]+'
        qcontent = r'[^\000\\"]'
        qsres    = r'"%(qc)s*(?:\\"%(qc)s*)*"' % {'qc': qcontent}
        valueres = r'(?:%(token)s|%(quoted-string)s)' % {
            'token': tokenres, 'quoted-string': qsres,
        }

        typere = re.compile(
            r'\s*([^;/\s]+/[^;/\s]+)((?:\s*;\s*%(key)s\s*=\s*%(val)s)*)\s*$' %
            {'key': tokenres, 'val': valueres,}
        )
        pairre = re.compile(r'\s*;\s*(%(key)s)\s*=\s*(%(val)s)' % {
            'key': tokenres, 'val': valueres
        })
        stripre = re.compile(r'\r?\n')
        parseContentType._regexps = (typere, pairre, stripre)

    match = typere.match(value)
    if not match:
        return None

    parsed = (match.group(1).lower(), {})
    match = match.group(2)
    if match:
        for key, val in pairre.findall(match):
            if val[:1] == '"':
                val = stripre.sub(r'', val[1:-1]).replace(r'\"', '"')
            parsed[1].setdefault(key.lower(), []).append(val)

    return parsed


class ReadOnlyDict(dict):
    """ Read only dictionary """
    __msg = "The dictionary is read-only"

    def __setitem__(self, key, value):
        """ modifiying is not allowed """
        raise TypeError(self.__msg)


    def __delitem__(self, key):
        """ deleting is not allowed """
        raise TypeError(self.__msg)


    def clear(self):
        """ clearing is not allowed """
        raise TypeError(self.__msg)


    def fromkeys(cls, seq, value = None):
        """ Chokes by default, so work around it """
        return cls(dict.fromkeys(seq, value))
    fromkeys = classmethod(fromkeys)


    def pop(self, key, default = None):
        """ popping is not allowed """
        raise TypeError(self.__msg)


    def popitem(self):
        """ popping is not allowed """
        raise TypeError(self.__msg)


    def setdefault(self, default = None):
        """ modifying is not allowed """
        raise TypeError(self.__msg)


    def update(self, newdict):
        """ updating is not allowed """
        raise TypeError(self.__msg)


class SafeDict(dict):
    """ A dict, which returns '' on unknown keys or false values """

    def __getitem__(self, key):
        """ Returns an empty string on false values or unknown keys """
        return dict.get(self, key) or ''
