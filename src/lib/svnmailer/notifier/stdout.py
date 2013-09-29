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
Stdout notifier - mostly for debugging purposes
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['getNotifier']

# global imports
import sys
from svnmailer.notifier import _text


def getNotifier(config, groupset):
    """ Returns an initialized notifier or nothing

        @param config: The svnmailer config
        @type config: C{svnmailer.settings.Settings}

        @param groupset: The groupset to process
        @type groupset: C{list}

        @return: The list of notifiers (containing 0 or 1 member)
        @rtype: C{list}
    """
    return [StdoutNotifier(config, groupset)]


class StdoutNotifier(_text.TextNotifier):
    """ Writes all stuff to sys.stdout

        @cvar _fp: C{None}
        @ivar _fp: alternate file like object (for testing purposes)
        @type _fp: file like object
    """
    __implements__ = [_text.TextNotifier]
    _fp = None


    def run(self):
        """ Print the notification to stdout """
        from svnmailer import stream

        fp = self._fp or sys.stdout
        fp = stream.UnicodeStream(fp, out_enc = self._getOutputEnc(fp))
        groups = self._groupset.groups
        self.fp = fp

        self._writePreamble(groups)
        self._writeNotification()


    def _writeNotification(self):
        """ Writes the whole diff notification body """
        from svnmailer.settings import modes

        mode = self._settings.runtime.mode

        if mode == modes.commit:
            self.writeMetaData()
            self.writePathList()
            self.writeDiffList()
        elif mode == modes.propchange:
            self.writeRevPropData()
        elif mode in (modes.lock, modes.unlock):
            self.writeLockData()
        else:
            raise AssertionError("Unknown runtime.mode %r" % (mode,))


    def _writePreamble(self, groups):
        """ Writes the stdout preamble for the selected groups

            @param groups: The groups that are notified
            @type groups: C{list}
        """
        self.fp.write(
            ">>> Notification for the following group%s:\n  %s\n\n" %
            (["", "s"][len(groups) > 1],
            ",\n  ".join(["[%s]" % group._name for group in groups]))
        )


    def _getOutputEnc(self, fp):
        """ Returns the "proper" output encoding

            If the output goes to a terminal, the method tries to get
            the current locale encoding. UTF-8 is default and fallback
            if anything fails.

            @param fp: The file object written to
            @type fp: file like object

            @return: The chosen encoding
            @rtype: C{str}
        """
        import os

        enc = "utf-8"
        try:
            isatty = os.isatty(fp.fileno())
        except AttributeError:
            isatty = False

        if isatty:
            import locale
            enc = locale.getpreferredencoding() or enc

        return enc
