# -*- coding: utf-8 -*-
# pylint: disable-msg=R0921
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
Plain text notifier base
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['TextNotifier']

# global imports
from svnmailer.notifier import _base


class TextNotifier(_base.BaseNotifier):
    """ Base class for plain text notifications

        The derived class must implement the run method.

        :CVariables:
         - `OUTPUT_SEPARATOR`: the separator between headline and diff
         - `OUTPUT_SEPARATOR_LIGHT`: the separator between headline and
           property diff

        :IVariables:
         - `fp`: The file to write to
         - `config`: The group config
         - `changeset`: The list of changes to process
         - `differ`: The differ object

        :Types:
         - `OUTPUT_SEPARATOR`: ``str``
         - `OUTPUT_SEPARATOR_LIGHT`: ``str``

         - `fp`: file like object
         - `config`: `svnmailer.settings._base.GroupSettingsContainer`
         - `changeset`: ``list``
         - `differ`: ``svnmailer.differ.*``
    """
    __implements__ = [_base.BaseNotifier]

    OUTPUT_SEPARATOR = "=" * 78 + "\n"
    OUTPUT_SEPARATOR_LIGHT = "-" * 78 + "\n"
    fp = None


    def __init__(self, settings, groupset):
        """ Initialization """
        _base.BaseNotifier.__init__(self, settings, groupset)
        groups, self.changeset = (groupset.groups, groupset.changes)
        self.config = groups[0]
        self.differ = self.getDiffer(self.config.diff_command)


    def run(self):
        """ Runs the notifier (abstract method) """
        raise NotImplementedError()


    def getDate(self, oftime = None):
        """ Returns the revision date in a human readable format

            :return: The date
            :rtype: ``str``
        """
        import time

        # TODO: make timeformat configurable? (keep locale issues in mind!)
        return time.ctime(oftime or self.getTime())


    def writeRevPropData(self, raw = False):
        """ Writes the revision property change data

            :param `raw`: Don't recode the property?
            :type `raw`: ``bool``
        """
        runtime  = self._settings.runtime

        name     = runtime.propname.encode('utf-8')
        revision = runtime.revision
        action = {
            u'A': self.ADD,
            u'M': self.MODIFY,
            u'D': self.DELETE,
        }.get(runtime.action, None)

        desc = {
            self.ADD:    "Added",
            self.MODIFY: "Modified",
            self.DELETE: "Deleted",
        }.get(action, "Modified")

        self.fp.write(
            "Author: %s\nRevision: %d\n%s property: %s\n\n" % (
            self.getAuthor() or "(unknown)", revision, desc, name
        ))

        value2 = runtime._repos.getRevisionProperty(revision, name)

        # svn 1.2 vs. 1.1
        if action:
            import time
            value1 = (action == self.ADD and [''] or [runtime.stdin])[0]
            value2 = value2 or ''
            oftime = int(time.time())
            self.fp.write("%s: %s at %s\n" % (
                desc, name, self.getDate(oftime)
            ))
            self.writePropertyDiff(
                action, name, value1, value2, time = oftime, raw = raw
            )
        else:
            self.fp.write("New value:")
            if value2 is None:
                self.fp.write(" (removed)\n")
            else:
                self.fp.write("\n")
                # TODO: make revision property charset configurable?
                # iso-8859-1 for now (translates 1:1 to unicode)
                if not self.isUTF8Property(name) and not raw:
                    value2 = value2.decode('iso-8859-1').encode('utf-8')
                self.fp.write(value2)

        self.fp.write("\n")


    def writeLockData(self):
        """ Writes the locking metadata """
        from svnmailer.settings import MODES
        runtime  = self._settings.runtime
        is_locked = bool(runtime.mode == MODES.lock)

        self.fp.write("Author: %s" % (
            self.getAuthor() or "(unknown)",)
        )

        if is_locked:
            self.fp.write("\nComment:")
            comment = self.changeset[0].getComment().strip()
            if comment:
                self.fp.write("\n%s\n" % comment)
            else:
                self.fp.write(" (empty)")

        self.fp.write("\n%s paths:\n" % (is_locked and "Locked" or "Unlocked",))

        for change in self.changeset:
            self.fp.write("   %s\n" % change.path)

        self.fp.write("\n")


    def writeDiffList(self):
        """ Writes the commit diffs """
        diff_tokens, diff_tests = self.getDiffTokens(self.config)

        self.fp.write("\n")

        set = self.changeset[:]
        xset = self._groupset.xchanges
        if xset:
            set.extend(xset)

        for change in set:
            for test in diff_tests:
                if test(change):
                    if change.hasContentChanges():
                        self.writeContentDiff(change)

                    if change.hasPropertyChanges() and \
                            self.PROPCHANGE in diff_tokens:
                        self.writePropertyDiffs(diff_tokens, change)
                    # one diff per change is enough
                    break


    def writePropertyDiffs(self, diff_tokens, change, raw = False):
        """ Writes the property diffs for a particular change

            :Parameters:
             - `diff_tokens`: The valid diff tokens
             - `change`: The particular change to process
             - `raw`: Don't recode the properties?

            :Types:
             - `diff_tokens`: ``list``
             - `change`: `svnmailer.subversion.VersionedPathDescriptor`
             - `raw`: ``bool``
        """
        if change.wasDeleted():
            return # don't bother

        propdict = change.getModifiedProperties()
        propnames = propdict.keys()
        propnames.sort()

        for name in propnames:
            values = propdict[name]
            token = self.writePropertyDiffAction(
                change, name, values, diff_tokens
            )

            if token in diff_tokens:
                self.writePropertyDiff(
                    token, name, values[0], values[1], raw = raw
                )

            self.fp.write("\n")


    def writePropertyDiff(self, token, name, value1, value2, time = None,
                          raw = False):
        """ Writes a property diff

            :Parameters:
             - `token`: The diff token
             - `name`: The name of the property
             - `value1`: The raw old value
             - `value2`: The raw new value
             - `time`: Time to display in the diff description
               in seconds since epoch
             - `raw`: Don't recode the properties?

            :Types:
             - `token`: ``unicode``
             - `name`: ``str``
             - `value1`: ``str``
             - `value2`: ``str``
             - `time`: ``int``
             - `raw`: ``bool``
        """
        self.fp.write(self.OUTPUT_SEPARATOR_LIGHT)

        # TODO: make property charset configurable?
        # (iso-8859-1 was chosen for now, because it
        # translates 1:1 to unicode)
        if not self.isUTF8Property(name) and not raw:
            if value1:
                value1 = value1.decode('iso-8859-1').encode('utf-8')
            if value2:
                value2 = value2.decode('iso-8859-1').encode('utf-8')

        # now throw something out
        if not self.isUTF8Property(name) and \
                self.isBinaryProperty((value1, value2)):
            self.fp.write(
                "Binary property '%s' - no diff available.\n" % name
            )

        elif token == self.ADD and self.isOneLineProperty(name, value2):
            self.fp.write("    %s = %s\n" % (name, value2))

        else:
            # avoid "no newline at end of file" for props
            if value1 and not value1.endswith("\n"):
                value1 = "%s\n" % value1
            if value2 and not value2.endswith("\n"):
                value2 = "%s\n" % value2
            self.writeDiff(token, name, name, value1, value2, time = time)


    def writePropertyDiffAction(self, change, name, values, diff_tokens):
        """ Writes the property diff action for a particular change

            :Parameters:
             - `change`: The particular change to process
             - `name`: The property name
             - `values`: The values of the property
             - `diff_tokens`: Valid diff tokens

            :Types:
             - `change`: `svnmailer.subversion.VersionedPathDescriptor`
             - `name`: ``str``
             - `values`: ``tuple``
             - `diff_tokens`: ``list``

            :return: diff token that should be applied
            :rtype: ``str``
        """
        token = self.getPropertyDiffAction(values)
        desc = {
            self.ADD   : "added",
            self.DELETE: "removed",
            self.MODIFY: "modified",
        }[token]

        self.fp.write("Propchange: %s%s\n" % (
            change.path, ["", "/"][change.isDirectory()]
        ))
        if token not in diff_tokens:
            self.fp.write("            ('%s' %s)\n" % (name, desc))

        return token


    def writeContentDiff(self, change, raw = False):
        """ Writes the content diff for a particular change

            :Parameters:
             - `change`: The particular change to process
             - `raw`: Prefer no recoding?

            :Types:
             - `change`: `svnmailer.subversion.VersionedPathDescriptor`
             - `raw`: ``bool``
        """
        if change.isDirectory():
            # 'nuff said already
            return

        token = self.writeContentDiffAction(change)
        if token is None:
            # nothing more to say
            return

        config = self.config
        url = self.getContentDiffUrl(config, change)
        if url is not None:
            self.fp.write("URL: %s\n" % url)

        self.fp.write(self.OUTPUT_SEPARATOR)

        if (change.isBinary()):
            self.fp.write(
                "Binary file%s - no diff available.\n" % ["s", ""][
                    (change.wasAdded() and not change.wasCopied()) or
                    change.wasDeleted()
                ]
            )
        else:
            from svnmailer.settings import SHOWENC

            if raw:
                default = False
                enc = None
            else:
                enc = config.apply_charset_property and \
                    self.ENC_CONFIG or self.ENC_DEFAULT
                default = bool(config.show_applied_charset == SHOWENC.yes)
            show_applied_charset = bool(config.show_applied_charset == SHOWENC.yes)

            default_charsets = None
            if config.default_charsets:
                default_charsets = config.default_charsets
            file1, file2, rec1, rec2 = self.dumpContent(
                change, enc = enc, default = default, default_charsets = default_charsets, show_applied_charset = show_applied_charset
            )
            if config.show_applied_charset == SHOWENC.no:
                rec1 = rec2 = None

            self.writeDiff(token,
                (change.wasCopied() and
                    [change.getBasePath()] or [change.path])[0],
                change.path, file1.name, file2.name, isfile = True,
                rec1 = rec1, rec2 = rec2
            )

        self.fp.write("\n")


    def writeContentDiffAction(self, change):
        """ Writes the content diff action for a particular change

            :param change: The particular change to process
            :type change: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The diff token (maybe ``None``)
            :rtype: ``str``
        """
        token = self.getContentDiffAction(change)

        if token == self.MODIFY:
            self.fp.write("Modified: %s\n" % change.path)
        elif token == self.ADD:
            self.fp.write("Added: %s\n" % change.path)
        elif token == self.DELETE:
            self.fp.write("Removed: %s\n" % change.path)
        elif token == self.COPY:
            self.fp.write("Copied: %s (from r%d, %s)\n" % (
                change.path,
                change.getBaseRevision(),
                change.getBasePath(),
            ))

        return token


    def writeDiff(self, token, name1, name2, value1, value2, isfile = False,
                  rec1 = None, rec2 = None, time = None):
        """ Writes a diff

            By default `value1` and `value2` are strings to diff,
            but if `isfile` is set and ``True``, these are treated as names
            of files to diff.

            :Parameters:
             - `token`: The diff token
             - `name1`: The (faked) first filename
             - `name2`: The (faked) second filename
             - `value1`: The first value
             - `value2`: The second value
             - `isfile`: are the values file names?

            :Types:
             - `token`: ``unicode``
             - `name1`: ``str``
             - `name2`: ``str``
             - `value1`: ``str``
             - `value2`: ``str``
             - `isfile`: ``bool``
        """
        date1 = ["(original)", "(added)"][token == self.ADD]
        date2 = [self.getDate(time), "(removed)"][token == self.DELETE]

        if rec1 and token != self.ADD:
            date1 = "[%s] %s" % (rec1, date1)
        if rec2 and token != self.DELETE:
            date2 = "[%s] %s" % (rec2, date2)

        meth = [
            self.differ.getStringDiff, self.differ.getFileDiff
        ][bool(isfile)]

        diff_empty = True
        for line in meth(value1, value2, name1, name2, date1, date2):
            diff_empty = False
            self.fp.write(line)
            if not line.endswith("\n"):
                self.fp.write("\n")

        if diff_empty:
            if rec1 != None and rec2 != None and rec1 != rec2:
                self.fp.write("--- ")
                self.fp.write(name1)
                self.fp.write("\t")
                self.fp.write(date1)
                self.fp.write("\n")

                self.fp.write("+++ ")
                self.fp.write(name2)
                self.fp.write("\t")
                self.fp.write(date2)
                self.fp.write("\n")
            self.fp.write("    (empty)\n")


    def writePathList(self):
        """ Writes the commit path list """
        self._doWritePathList(self.changeset)

        xset = self._groupset.xchanges
        if xset is not None:
            from svnmailer.settings import XPATH

            if xset:
                self.fp.write(
                    "\nChanges in other areas also in this revision:\n"
                )
                self._doWritePathList(xset)
            elif self._groupset.groups[0].show_nonmatching_paths == XPATH.no:
                self.fp.write(
                    "\n(There are changes in other areas, but they are not "
                    "listed here.)\n"
                )


    def _doWritePathList(self, set):
        """ Write the path list of a particular changeset

            :param set: The changeset to process
            :type set: ``list``
        """
        for title, changes in [(title, changes) for title, changes in (
            ("Added",    [chg for chg in set if chg.wasAdded()]),
            ("Removed",  [chg for chg in set if chg.wasDeleted()]),
            ("Modified", [chg for chg in set if chg.wasModified()]),
        ) if changes]:
            self.fp.write("%s:\n" % title)
            for change in changes:
                self.writePathInfo(change)


    def writePathInfo(self, change):
        """ Writes a short info about the kind of change

            :param change: The change info
            :type change: `svnmailer.subversion.VersionedPathDescriptor`
        """
        slash = ["", "/"][change.isDirectory()]

        self.fp.write("    %s%s" % (change.path, slash))
        if change.hasPropertyChanges():
            self.fp.write("   (")
            if not change.wasAdded() or change.wasCopied():
                self.fp.write("%sprops changed)" %
                    ["", "contents, "][change.hasContentChanges()]
                )
            else:
                self.fp.write("with props)")

        if change.wasCopied():
            self.fp.write("\n      - copied")
            if not change.isDirectory():
                self.fp.write(
                    [" unchanged", ", changed"][change.hasContentChanges()]
                )
            self.fp.write(" from r%d, %s%s" % (
                change.getBaseRevision(),
                change.getBasePath(),
                slash
            ))

        self.fp.write("\n")


    def writeMetaData(self):
        """ Writes the commit metadata output """
        author = self.getAuthor() or "(unknown)"
        if self.config.extract_x509_author:
            from svnmailer import util
            x509 = util.extractX509User(author)
            if x509 and x509[0]:
                author = x509[0]

        self.fp.write("Author: %s\n" % author)
        self.fp.write("Date: %s\n" % self.getDate())
        self.fp.write("New Revision: %d\n" % self._settings.runtime.revision)

        self.fp.write("\n")

        url = self.getUrl(self.config)
        if url is not None:
            self.fp.write('URL: %s\n' % url)

        log_entry = self.getLog() or ''
        self.fp.write(
            "Log:%s" % [" (empty)", "\n%s" % log_entry][bool(log_entry)]
        )
        if not log_entry.endswith("\n"):
            self.fp.write("\n")

        self.fp.write("\n")
