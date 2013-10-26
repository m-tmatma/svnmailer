# -*- coding: utf-8 -*-
# pylint: disable-msg=W0611
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
Utilities
=========

This module contains some utility functions and classes used in several
places of the svnmailer. These functions have a quite general character
and can be used easily outside of the svnmailer as well.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'TempFile',
    'splitCommand',
    'filename',
    'extractX509User',
    'substitute',
    'filterForXml',
    'getParentDirList',
    'getGlobValue',
    'inherit',
    'commonPaths',
    'ReadOnlyDict',
    'SafeDict',
    'Singleton',
    'loadDotted',
]

# global imports
import errno, locale, os, sys


class TempFile(object):
    """ Tempfile container class

        The class contains a destructor that removes the created
        file. This differs from the stuff in tempfile, which removes
        the file, when it's closed.

        The mode is fixed to ``w+``; a ``b`` is added if the ``text``
        argument is false (see `__init__`)

        :IVariables:
         - `name`: The full name of the file
         - `fp`: The file descriptor
         - `_unlink`: ``os.unlink``

        :Types:
         - `name`: ``str``
         - `fp`: ``file``
         - `_unlink`: ``callable``
    """
    name = None
    fp = None
    _unlink = None

    def __init__(self, tempdir = None, text = False):
        """ Initialization

            :Parameters:
             - `tempdir`: The temporary directory
             - `text`: want to write text?

            :Types:
             - `tempdir`: ``str``
             - `text`: ``bool``
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
                """ ok """
                pass

        if self.name and self._unlink:
            try:
                self._unlink(self.name)
            except OSError:
                """ don't even ignore """
                pass


    def close(self):
        """ Close the file (but don't delete it)

            :exception ValueError: The file was already closed
        """
        if self.fp:
            self.fp.close()


def splitCommand(command):
    r"""Split a command string with respect to quotes and such

        The command string consists of several tokens:

        * whitespace: Those are separators except inside quoted items
        * unquoted items: every token that doesn't start with
          a double quote (``"``)
        * quoted items: every token that starts with a double quote (``"``).
          Those items must be closed with a double quote and may contain
          whitespaces. The enclosing quotes are stripped. To put a double
          quote character inside such a token, it has to be escaped with
          a backslash (``\``). Therefore - backslashes themselves have to be
          escaped as well. The escapes are also stripped from the result.

        Here's an example: ``r'foo bar "baz" "zo\"" "\\nk"'`` resolves
        to ``['foo', 'bar', 'baz', 'zo"', r'\nk']``

        :param command: The command string
        :type command: ``str``

        :return: The splitted command
        :rtype: ``list``

        :exception ValueError: The command string is not valid
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
    """ Transform filenames according to locale

        :IVariables:
         - `unicode_system`: Does the system support unicode file names?
         - `from_enc`: The default encoding of filenames coming from
           the environment
         - `to_enc`: The default encoding of filenames written to disk

        :Types:
         - `unicode_system`: ``bool``
         - `from_enc`: ``str``
         - `to_enc`: ``str``
    """

    def __init__(self, _locale = locale, _os = os, _sys = sys):
        """ Initialization """
        self.unicode_system = _os.path.supports_unicode_filenames
        self.from_enc = _locale.getpreferredencoding(False) or "us-ascii"
        self.to_enc = _sys.getfilesystemencoding() or "us-ascii"


    def toLocale(self, name, name_enc = None, locale_enc = None, force = False):
        """ Transforms a file name to the locale representation

            :Parameters:
             - `name`: The name to consider
             - `name_enc`: The source encoding of ``name``, if it's
               not unicode already
             - `locale_enc`: The file system encoding (used only if it's
               not a unicode supporting OS)
             - `force`: force transcoding even if unicode system?

            :Types:
             - `name`: ``basestring``
             - `name_enc`: ``str``
             - `locale_enc`: ``str``
             - `force`: ``bool``

            :return: The name in locale representation
            :rtype: ``basestring``

            :exception UnicodeError: An error happened while recoding
        """
        if locale_enc is None:
            locale_enc = self.to_enc
        if name_enc is None:
            name_enc = self.from_enc

        if self.unicode_system and not force:
            if isinstance(name, unicode):
                return name
            else:
                return name.decode(name_enc, "strict")

        if locale_enc.lower() == "none":
            if isinstance(name, unicode):
                raise AssertionError("Illegal call")
            else:
                return name

        if not isinstance(name, unicode):
            name = name.decode(name_enc, "strict")

        return name.encode(locale_enc, "strict")


    def fromLocale(self, name, locale_enc = None):
        """ Transform a file name from locale repr to unicode (hopefully)

            :Parameters:
             - `name`: The name to decode
             - `locale_enc`: The locale encoding

            :Types:
             - `name`: ``basestring``
             - `locale_enc`: ``str``

            :return: The decoded name
            :rtype: ``basestring``

            :exception UnicodeError: An error happend while recoding
        """
        if isinstance(name, unicode):
            return name

        if locale_enc is None:
            locale_enc = self.from_enc

        if locale_enc.lower() == "none":
            return name # no unicode.

        return name.decode(locale_enc, "strict")

filename = _LocaleFile()


class _Terminal(object):
    """ Deal with terminal properties """

    def __init__(self):
        """ Initialization """
        fd = None
        for fp in (sys.stdout, sys.stdin):
            try:
                _fd = fp.fileno()
            except (AttributeError, ValueError):
                continue
            else:
                if self.isatty(_fd):
                    fd = _fd
                    break

        self._fd = fd


    def isatty(self, fd):
        """ Returns whether the given descriptor is connected to a terminal

            If the ``os`` module doesn't provide an ``isatty`` function,
            we return ``False`` instead of raising an exception

            :param fd: The file descriptor to inspect
            :type fd: ``int``

            :return: Is `fd` connected to a terminal?
            :rtype: ``bool``
        """
        try:
            _isatty = bool(os.isatty(fd))
        except AttributeError:
            _isatty = False

        return _isatty


    def getWidth(self):
        """ Returns terminal width if determined, None otherwise

            :return: The width
            :rtype: ``int``
        """
        if self._fd is None:
            return None

        try:
            import fcntl, struct, termios

            # struct winsize { /* on linux in asm/termios.h */
            #     unsigned short ws_row;
            #     unsigned short ws_col;
            #     unsigned short ws_xpixel;
            #     unsigned short ws_ypixel;
            # }
            return struct.unpack("4H", fcntl.ioctl(
                self._fd, termios.TIOCGWINSZ, struct.pack("4H", 0, 0, 0, 0)
            ))[1]

        except (SystemExit, KeyboardInterrupt):
            raise

        except:
            """ don't even ignore """
            pass

        return None

terminal = _Terminal()


def extractX509User(author):
    """ Returns user data extracted from x509 subject string

        :param author: The author string
        :type author: ``basestring``

        :return: user name, mail address (user name maybe ``None``)
        :rtype: ``tuple`` or ``None``
    """
    if author:
        try:
            cnre, eare = extractX509User._regexps
        except AttributeError:
            import re
            cnre = re.compile(ur'/CN=([^/]+)', re.I)
            eare = re.compile(ur'/emailAddress=([^/]+)', re.I)
            extractX509User._regexps = (cnre, eare)

        if not isinstance(author, unicode):
            author = author.decode('utf-8', 'replace')

        ea_match = eare.search(author)
        if ea_match:
            cn_match = cnre.search(author)
            return (cn_match and cn_match.group(1), ea_match.group(1))

    return None


def substitute(template, subst):
    """ Returns a filled template

        If the `template` is ``None``, this function returns ``None``
        as well.

        :param template: The temlate to fill
        :type template: ``basestring``

        :param subst: The substitution parameters
        :type subst: ``dict``

        :return: The filled template (The return type depends on the
            template and the parameters)
        :rtype: ``basestring``
    """
    if template is None:
        return None

    return template % SafeDict(subst)


def filterForXml(value):
    """ Replaces control characters with replace characters

        :param value: The value to filter
        :type value: ``unicode``

        :return: The filtered value
        :rtype: ``unicode``
    """
    try:
        regex = filterForXml._regex
    except AttributeError:
        import re
        chars = u''.join([chr(num) for num in range(32)
            if num not in (9, 10, 13) # XML 1.0
        ])
        regex = filterForXml._regex = re.compile(u"[%s]" % chars)

    return regex.sub(u'\ufffd', value)


def getParentDirList(path):
    """ Returns the directories up to a (posix) path

        :param path: The path to process
        :type path: ``str``

        :return: The directory list
        :rtype: ``list``
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

        :Parameters:
         - `globs`: The glob list (``[(glob, associated value)]``)
         - `path`: The path to match

        :Types:
         - `globs`: sequence
         - `path`: ``str``

        :return: The matched value or ``None``
        :rtype: any
    """
    import fnmatch

    result = None
    for glob in globs:
        if fnmatch.fnmatchcase(path, glob[0]):
            result = glob[1]
            break

    return result


def commonPaths(paths):
    """ Returns the common component and the stripped paths

        It expects that directories do always end with a trailing slash and
        paths never begin with a slash (except root).

        :param paths: The list of paths (``[str, str, ...]``)
        :type paths: ``list``

        :return: The common component (always a directory) and the stripped
                 paths (``(str, [str, str, ...])``)
        :rtype: ``tuple``
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
    r"""Inherits class cls from \*bases

        :note: `cls` needs a ``__dict__``\, so ``__slots__`` is a nono

        :Parameters:
         - `cls`: The class to inherit from `bases`
         - `bases`: The base class(es)

        :Types:
         - `cls`: ``class``
         - `bases`: ``tuple``
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

        :warning: comments are not recognized (yet?)

        :param value: The value to parse - must be ascii compatible
        :type value: ``basestring``

        :return: The parsed header (``(value, {key, [value, value, ...]})``)
                 or ``None``
        :rtype: ``tuple``
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


class Singleton(object):
    """ Singleton base class """
    __singletoninstance__ = None

    def __new__(cls):
        """ Returns the one and only instance """
        self = cls.__singletoninstance__
        if self is None:
            self = object.__new__(cls)
            cls.__singletoninstance__ = self

        return self


    def __init__(self):
        """ Non-initialization """
        pass


def loadDotted(name):
    """ Loads a dotted name

        The dotted name can be anything, which is passively resolvable
        (i.e. without the invocation of a class to get their attributes or
        the like). For example, `name` could be 'svnmailer.util.loadDotted'
        and would return this very function. It's assumed that the first
        part of the `name` is always is a module.

        If a dotted name was loaded successfully, the object will be cached
        and delivered from there the next time.

        :param name: The dotted name to load
        :type name: ``str``

        :return: The loaded object
        :rtype: any

        :exception ImportError: A module in the path could not be loaded
    """
    try:
        return loadDotted._cache[name]
    except AttributeError:
        """ create cache """
        loadDotted._cache = {}
    except KeyError:
        """ cache MISS """
        pass

    components = name.split('.')
    path = [components.pop(0)]
    obj = __import__(path[0])
    while components:
        comp = components.pop(0)
        path.append(comp)
        try:
            obj = getattr(obj, comp)
        except AttributeError:
            __import__('.'.join(path))
            obj = getattr(obj, comp)

    loadDotted._cache[name] = obj
    return obj
