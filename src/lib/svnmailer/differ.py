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
Differ classes
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ["InternalDiffer", "ExternalDiffer"]


class InternalDiffer(object):
    """ Differ without an external program call (uses difflib) """

    def __init__(self):
        """ Initialization """
        pass


    def getStringDiff(self, string1, string2, label1, label2 = None,
                      date1 = "", date2 = ""):
        """ creates a diff of two line based strings

            If a string is C{None}, it's treated as ""

            @param string1: First string
            @type string1: C{str}

            @param string2: Second string
            @type string2: C{str}

            @param label1: Label for first data
            @type label1: C{str}

            @param label2: Label for second data
            @type label2: C{str}

            @param date1: Date description for first data
            @type date1: C{str}

            @param date2: Date description for second data
            @type date2: C{str}

            @return: unified diff lines (maybe a generator)
            @rtype: iterable
        """
        import difflib

        list1 = (string1 or "").splitlines(True)
        list2 = (string2 or "").splitlines(True)
        if not (list1 or list2):
            list1 = list2 = [""]

        return difflib.unified_diff(
            list1, list2, label1, label2 or label1, date1, date2,
        )


    def getFileDiff(self, name1, name2, label1, label2 = None,
                    date1 = "", date2 = ""):
        """ creates a diff of two line based files

            @param name1: First file name
            @type name1: C{str}

            @param name2: Second file name
            @type name2: C{str}

            @param label1: Label for first data
            @type label1: C{str}

            @param label2: Label for second data
            @type label2: C{str}

            @param date1: Date description for first data
            @type date1: C{str}

            @param date2: Date description for second data
            @type date2: C{str}

            @return: unified diff lines (maybe a generator)
            @rtype: iterable
        """
        import difflib

        list1 = file(name1, "rb").readlines()
        list2 = file(name2, "rb").readlines()
        if not (list1 or list2):
            list1 = list2 = [""]

        return difflib.unified_diff(
            list1, list2, label1, label2 or label1, date1, date2,
        )


class ExternalDiffer(object):
    """ Differ which calls an external program (e.g. diff)

        @ivar _diff_command: The diff command line
        @type _diff_command: C{list}

        @ivar _tempdir: The tempdir to use for string diffs
        @type _tempdir: C{str}
    """

    def __init__(self, diff_command, tempdir = None):
        """ Initialization

            @param diff_command: The diff command to call
            @type diff_command: C{list}

            @param tempdir: The tempdir to use for string diffs
            @type tempdir: C{str}
        """
        self._diff_command = diff_command
        self._tempdir = tempdir


    def getStringDiff(self, string1, string2, label1, label2 = None,
                      date1 = "", date2 = ""):
        """ creates a diff of two line based strings

            If a string is C{None}, it's treated as ""

            @param string1: First string
            @type string1: C{str}

            @param string2: Second string
            @type string2: C{str}

            @param label1: Label for first data
            @type label1: C{str}

            @param label2: Label for second data
            @type label2: C{str}

            @param date1: Date description for first data
            @type date1: C{str}

            @param date2: Date description for second data
            @type date2: C{str}

            @return: unified diff lines (maybe a generator)
            @rtype: iterable
        """
        from svnmailer import util

        string1 = string1 or ""
        string2 = string2 or ""

        file1 = util.TempFile(self._tempdir)
        file1.fp.write(string1)
        file1.close()

        file2 = util.TempFile(self._tempdir)
        file2.fp.write(string2)
        file2.close()

        pipe = self._getPipe(
            file1.name, file2.name, label1, label2, date1, date2
        )

        # yield line by line
        line = pipe.fromchild.readline()
        while line:
            yield line
            line = pipe.fromchild.readline()

        pipe.fromchild.close()
        pipe.wait()


    def getFileDiff(self, name1, name2, label1, label2 = None,
                    date1 = "", date2 = ""):
        """ creates a diff of two line based files

            @param name1: First file name
            @type name1: C{str}

            @param name2: Second file name
            @type name2: C{str}

            @param label1: Label for first data
            @type label1: C{str}

            @param label2: Label for second data
            @type label2: C{str}

            @param date1: Date description for first data
            @type date1: C{str}

            @param date2: Date description for second data
            @type date2: C{str}

            @return: unified diff lines (maybe a generator)
            @rtype: iterable
        """
        pipe = self._getPipe(name1, name2, label1, label2, date1, date2)

        # yield line by line
        line = pipe.fromchild.readline()
        while line:
            yield line
            line = pipe.fromchild.readline()

        pipe.fromchild.close()
        pipe.wait()


    def _getPipe(self, name1, name2, label1, label2, date1, date2):
        """ Returns a pipe from the diff program

            @param name1: First file name
            @type name1: C{str}

            @param name2: Second file name
            @type name2: C{str}

            @param label1: Label for first data
            @type label1: C{str}

            @param label2: Label for second data
            @type label2: C{str}

            @param date1: Date description for first data
            @type date1: C{str}

            @param date2: Date description for second data
            @type date2: C{str}

            @return: The pipe object
            @rtype: see: C{util.getPipe4}
        """
        from svnmailer import util

        params = {
            "label_from": "%s %s" % (label1, date1 or ""),
            "label_to"  : "%s %s" % (label2 or label1, date2 or ""),
            "from"      : name1,
            "to"        : name2,
        }

        # check for sanity
        for key, value in params.items():
            if isinstance(value, unicode):
                params[key] = value.encode("utf-8")

        cmd = list(self._diff_command)
        cmd[1:] = [(isinstance(arg, unicode) and
            [arg.encode("utf-8")] or [arg])[0] % params for arg in cmd[1:]
        ]

        pipe = util.getPipe4(cmd)
        pipe.tochild.close()

        return pipe
