# -*- coding: iso-8859-1 -*-
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
Differ classes
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ["InternalDiffer", "ExternalDiffer"]


class InternalDiffer(object):
    """ Differ without an external program call (uses difflib) """

    def __init__(self, tags = False):
        """ Initialization

            :param tags: Return diff opcodes instead of unified format?
            :type tags: ``bool``
        """
        self._want_tags = tags


    def _tags(self, list1, list2):
        """ Returns diff tags

            :Parameters:
             - `list1`: The first sequence
             - `list2`: The second sequence

            :Types:
             - `list1`: ``list``
             - `list2`: ``list``

            :return: iterable of tags (``(code, a1, a2, b1, b2), ...``)
            :rtype: generator
        """
        import difflib

        codes = {
            'equal':   'E',
            'insert':  'A',
            'delete':  'D',
            'replace': 'M',
        }
        matcher = difflib.SequenceMatcher(a = list1, b = list2)
        for tag, a1, a2, b1, b2 in matcher.get_opcodes():
            yield (codes.get(tag, 'U'), a1, a2, b1, b2)


    def getStringDiff(self, string1, string2, label1, label2 = None,
                      date1 = "", date2 = ""):
        """ creates a diff of two line based strings

            If a string is ``None``, it's treated empty

            :Parameters:
             - `string1`: First string
             - `string2`: Second string
             - `label1`: Label for first data
             - `label2`: Label for second data
             - `date1`: Date description for first data
             - `date2`: Date description for second data

            :Types:
             - `string1`: ``str``
             - `string2`: ``str``
             - `label1`: ``str``
             - `label2`: ``str``
             - `date1`: ``str``
             - `date2`: ``str``

            :return: unified diff lines (maybe a generator)
            :rtype: iterable
        """
        import difflib

        list1 = (string1 or "").splitlines(True)
        list2 = (string2 or "").splitlines(True)
        if not (list1 or list2):
            list1 = list2 = [""]

        if self._want_tags:
            return self._tags(list1, list2)

        return difflib.unified_diff(
            list1, list2, label1, label2 or label1, date1, date2,
        )


    def getFileDiff(self, name1, name2, label1, label2 = None,
                    date1 = "", date2 = ""):
        """ creates a diff of two line based files

            :Parameters:
             - `name1`: First file name
             - `name2`: Second file name
             - `label1`: Label for first data
             - `label2`: Label for second data
             - `date1`: Date description for first data
             - `date2`: Date description for second data

            :Types:
             - `name1`: ``str``
             - `name2`: ``str``
             - `label1`: ``str``
             - `label2`: ``str``
             - `date1`: ``str``
             - `date2`: ``str``

            :return: unified diff lines (maybe a generator)
            :rtype: iterable
        """
        import difflib

        list1 = file(name1, "rb").readlines()
        list2 = file(name2, "rb").readlines()
        if not (list1 or list2):
            list1 = list2 = [""]

        if self._want_tags:
            return self._tags(list1, list2)

        return difflib.unified_diff(
            list1, list2, label1, label2 or label1, date1, date2,
        )


class ExternalDiffer(object):
    """ Differ which calls an external program (e.g. diff)

        :IVariables:
         - `_diff_command`: The diff command line
         - `_tempdir`: The tempdir to use for string diffs

        :Types:
         - `_diff_command`: ``list``
         - `_tempdir`: ``str``
    """

    def __init__(self, diff_command, tempdir = None):
        """ Initialization

            :Parameters:
             - `diff_command`: The diff command to call
             - `tempdir`: The tempdir to use for string diffs

            :Types:
             - `diff_command`: ``list``
             - `tempdir`: ``str``
        """
        self._diff_command = diff_command
        self._tempdir = tempdir


    def getStringDiff(self, string1, string2, label1, label2 = None,
                      date1 = "", date2 = ""):
        """ creates a diff of two line based strings

            If a string is ``None``, it's treated empty

            :Parameters:
             - `string1`: First string
             - `string2`: Second string
             - `label1`: Label for first data
             - `label2`: Label for second data
             - `date1`: Date description for first data
             - `date2`: Date description for second data

            :Types:
             - `string1`: ``str``
             - `string2`: ``str``
             - `label1`: ``str``
             - `label2`: ``str``
             - `date1`: ``str``
             - `date2`: ``str``

            :return: unified diff lines (maybe a generator)
            :rtype: iterable
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

            :Parameters:
             - `name1`: First file name
             - `name2`: Second file name
             - `label1`: Label for first data
             - `label2`: Label for second data
             - `date1`: Date description for first data
             - `date2`: Date description for second data

            :Types:
             - `name1`: ``str``
             - `name2`: ``str``
             - `label1`: ``str``
             - `label2`: ``str``
             - `date1`: ``str``
             - `date2`: ``str``

            :return: unified diff lines (maybe a generator)
            :rtype: iterable
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

            :Parameters:
             - `name1`: First file name
             - `name2`: Second file name
             - `label1`: Label for first data
             - `label2`: Label for second data
             - `date1`: Date description for first data
             - `date2`: Date description for second data

            :Types:
             - `name1`: ``str``
             - `name2`: ``str``
             - `label1`: ``str``
             - `label2`: ``str``
             - `date1`: ``str``
             - `date2`: ``str``

            :return: The Process object
            :rtype: `svnmailer.processes.Process`
        """
        from svnmailer import processes

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

        pipe = processes.Process.pipe4(cmd)
        pipe.tochild.close()

        return pipe
