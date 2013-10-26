# -*- coding: utf-8 -*-
# pylint: disable-msg=R0914
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
r"""
===============================
 Simplified Config File Parser
===============================

This parser is derived from the `ConfigParser module`_\, which
unfortunately has some design and documentation flaws. These flaws are
not tolerable for the svnmailer application, so this is a rewrite from the
scratch with some features/bugs missing. It was designed to provide the
ability to re-add these things if desired.

.. _`ConfigParser module`:
    http://docs.python.org/lib/module-ConfigParser.html
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'Error',
    'ParseError',
    'ContinuationError',
    'OptionSyntaxError',
    'FileParser',
    'Section',
    'Option'
]

# global imports
from svnmailer.settings import _base

# Exceptions
class Error(_base.Error):
    """ Base exception for this module """
    pass

class ParseError(Error):
    """ Parse error

        :CVariables:
         - `_MESSAGE`: The message format string

        :IVariables:
         - `filename`: The name of the file where the error occured
         - `lineno`: The line number of the error

        :Types:
         - `_MESSAGE`: ``str``
         - `filename`: ``basestring``
         - `lineno`: ``int``
    """
    _MESSAGE = "Parse error in %(filename)r, line %(lineno)s"

    def __init__(self, filename, lineno):
        """ Initialization

            :Parameters:
             - `filename`: The name of the file, where the error occured
             - `lineno`: The erroneous line number

            :Types:
             - `filename`: ``basestring``
             - `lineno`: ``int``
        """
        Error.__init__(self, filename, lineno)
        self.filename = filename
        self.lineno = lineno


    def __str__(self):
        """ Returns a string representation of the Exception """
        return self._MESSAGE % \
            {'filename': self.filename, 'lineno': self.lineno}


class ContinuationError(ParseError):
    """ A line continuation without a previous option line occured """
    _MESSAGE = "Invalid line continuation in %(filename)r, line %(lineno)s"

class OptionSyntaxError(ParseError):
    """ A option line could not be parsed """
    _MESSAGE = "Option syntax error in %(filename)r, line %(lineno)s"


class FileParser(object):
    """ Simplified config file parser

        The ``ConfigParser`` module does too much magic (partially
        not even documented). Further we don't need all the set and
        save stuff here, so we write our own - clean - variant.
        This variant just reads the stuff and does not apply any
        typing or transformation. It also uses a better design...

        :ivar `_sections`: The parsed sections
        :type `_sections`: ``dict``
    """

    def __init__(self):
        """ Initialization """
        self._sections = {}


    def __contains__(self, section):
        """ Decides if `section` is a parsed section name

            :param `section`: The section name to process
            :type `section`: ``str``

            :return: Is `section` available?
            :rtype: ``bool``
        """
        return bool(section in self._sections)


    def __iter__(self):
        """ Returns a section iterator

            :return: iterator object
            :rtype: ``iter``
        """
        return iter([section
            for name, section in self._sections.items() if name is not None
        ])


    def __getitem__(self, name):
        """ Returns the section specified by `name`

            :param `name`: The name of the section. May be ``None`` to specify
                           the presection section
            :type name: ``str``

            :return: The specified section
            :rtype: `Section`

            :exception KeyError: The requested section does not exist
        """
        return self._sections[name]


    def __delitem__(self, name):
        """ Removes the section specified by `name`

            :param `name`: The name of the section to remove (or ``None`` to
                           specifiy the presection section)
            :type name: ``str``

            :exception KeyError: The option does not exist
        """
        del self._sections[name]


    def slurp(self, fp, filename):
        """ Reads from `fp` until EOF and parses line by line

            :Parameters:
             - `fp`: The stream to read from
             - `filename`: The filename used for error messages

            :Types:
             - `fp`: ``file``
             - `filename`: ``basestring``

            :Exceptions:
             - `ContinuationError`: An invalid line continuation occured
             - `OptionSyntaxError`: An option line could not be parsed
             - `IOError`: An I/O error occured while reading the stream
        """
        lineno = 0
        section = None
        option = None

        # speed enhancements
        sections = self._sections
        readline = fp.readline
        is_comment = self._isComment
        try_section = self._trySectionHeader
        parse = self._parseOption
        create_section = self._createSection
        create_option = self._createOption

        while True:
            line = readline()
            if not line:
                break
            lineno += 1

            # skip blank lines and comments
            if line.strip() and not is_comment(line):
                # section header?
                header = try_section(line)
                if header is not None:
                    option = None # reset for the next continuation line
                    section = sections.get(header)
                    if section is None:
                        section = create_section(header)
                        sections[header] = section

                # line continuation?
                elif line[0].isspace():
                    try:
                        option.addLine(line)
                    except AttributeError:
                        raise ContinuationError(filename, lineno)

                # must be a new option
                else:
                    name, value = parse(line)
                    if name is None:
                        raise OptionSyntaxError(filename, lineno)
                    option = create_option(name, value)
                    if section is None:
                        section = create_section()
                        sections[None] = section
                    section.add(option)


    def _isComment(self, line):
        """ Decides if `line` is comment

            :param `line`: The line to inspect
            :type `line`: ``str``

            :return: Is `line` is comment line?
            :rtype: ``bool``
        """
        return bool(line.startswith('#') or line.startswith(';'))


    def _trySectionHeader(self, line):
        """ Tries to extract a section header from `line`

            :param `line`: The line to process
            :type `line`: ``str``

            :return: The section header name or ``None``
            :rtype: ``str``
        """
        if line.startswith('['):
            pos = line.find(']')
            if pos > 1: # one name char minimum
                return line[1:pos]

        return None


    def _parseOption(self, line):
        """ Parses `line` as option (``name [:=] value``)

            :param `line`: The line to process
            :type `line`: ``str``

            :return: The name and the value (both ``None`` if an error occured)
            :rtype: ``tuple``
        """
        pose = line.find('=')
        posc = line.find(':')
        pos = min(pose, posc)
        if pos < 0:
            if pose >= 0:
                pos = pose
            elif posc >= 0:
                pos = posc
            else:
                return (None, None)

        if pos > 0: # name must not be empty
            return (line[:pos], line[pos + 1:])

        return (None, None)


    def _createSection(self, name = None):
        """ Returns a new `Section` instance

            :return: The new `Section` instance
            :rtype: `Section`
        """
        return Section(name)


    def _createOption(self, name, value):
        """ Returns a new `Option` instance

            :Parameters:
             - `name`: The option name
             - `value`: The option value

            :Types:
             - `name`: ``str``
             - `value`: ``str``

            :return: The new `Option` instance
            :rtype: `Option`
        """
        return Option(name, value)


class Section(object):
    """ Represents a config section

        :IVariables:
         - `name`: The section name
         - `_options`: The parsed options

        :Types:
         - `name`: ``str``
         - `_options`: ``dict``
    """

    def __init__(self, name):
        """ Initialization

            :param `name`: The section name
            :type `name`: ``str``
        """
        self.name = name
        self._options = {}


    def __iter__(self):
        """ Returns an option iterator

            :return: iterator object
            :rtype: ``iter``
        """
        return iter(self._options.values())


    def __delitem__(self, name):
        """ Removes the option specified by `name`

            :param `name`: The name of the option to remove
            :type `name`: ``str``

            :exception KeyError: The option does not exist
        """
        del self._options[name]


    def __len__(self):
        """ Determines the number of stored options

            :return: The number of stored options
            :rtype: ``int``
        """
        return len(self._options)


    def add(self, option):
        """ Adds a new option to the section

            :param `option`: The option to add
            :type `option`: `Option`
        """
        self._options[option.name] = option


class Option(object):
    """ Represents a config option

        :IVariables:
         - `name`: The name of the option
         - `value`: The value of the option

        :Types:
         - `name`: ``str``
         - `value`: ``str``
    """

    def __init__(self, name, value):
        """ Initialization

            :Parameters:
             - `name`: The name of the option
             - `value`: The value of the option

            :Types:
             - `name`: ``str``
             - `value`: ``str``
        """
        self.name = name.rstrip()
        value = value.strip()
        if value == '""': # compat
            value = ''
        self.value = value


    def addLine(self, line):
        """ Adds a line to the option value

            `line` is appended to the current value with one space
            character as delimiter.

            :param `line`: The line to add
            :type `line`: ``str``
        """
        self.value = ' '.join((self.value, line.strip()))
