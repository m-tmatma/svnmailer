# -*- coding: utf-8 -*-
# pylint: disable-msg=W0142
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
======================
 CIA XML-RPC Notifier
======================

This notifier delivers a notification message in XML format
to a `CIA server`_\. The data delivered
contains in particular:

- The timestamp of the revision
- Information about the generator (svnmailer)
- Information about the project (``cia_project_name``,
  ``cia_project_module``, ``cia_project_branch``,
  ``cia_project_submodule``).
- Revision metadata:

  - author
  - revision number
  - log entry
  - summary URL (if ``browser_base_url`` if configured)
  - number of modified lines

- Information about the files modified (``cia_project_path`` is
  stripped). If ``browser_base_url`` is supplied, it is used to
  generate an URI for each file.

The notifier runs only in the post-commit hook. For activation you need
to supply the ``cia_rpc_server`` option in ``[general]`` and at least a
``cia_project_name`` in the group that should be tracked by CIA.

.. _CIA server: http://cia.navi.cx/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['getNotifier']

# global imports
from svnmailer.notifier import _base


def getNotifier(config, groupset):
    """ Returns an initialized notifier or nothing

        :Parameters:
         - `config`: The svnmailer config
         - `groupset`: The groupset to process

        :Types:
         - `config`: `svnmailer.settings._base.BaseSettings`
         - `groupset`: ``list``

        :return: The list of notifiers (containing 0 or 1 member)
        :rtype: ``list``
    """
    if config.general.cia_rpc_server and \
            [group for group in groupset.groups if group.cia_project_name]:
        return [CIAXMLRPCNotifier(config, groupset)]

    return []


class CIAXMLRPCNotifier(_base.BaseNotifier):
    """ The CIA XML-RPC Notifier class

        :IVariables:
         - `config`: The current group configuration
         - `changeset`: The changeset to process
         - `differ`: The differ object

        :Types:
         - `config`: `svnmailer.settings._base.GroupSettingsContainer`
         - `changeset`: ``list``
         - `differ`: ``svnmailer.differ.*``
    """
    __implements__ = [_base.BaseNotifier]


    def __init__(self, config, groupset):
        """ Initialization """
        super(CIAXMLRPCNotifier, self).__init__(config, groupset)
        # we use difflib's opcode output
        self.differ = self.getDiffer(tags = True)
        self.changeset = None
        self.config = None


    def run(self):
        """ Submits notification via XMLRPC to a CIA server """
        import sys
        from svnmailer import settings

        # only work on normal commits
        if not self._settings.runtime.mode == settings.MODES.commit:
            return

        groups, changeset = (self._groupset.groups, self._groupset.changes)
        self.changeset = changeset[:]
        xset = self._groupset.xchanges
        if xset:
            self.changeset.extend(xset)
        for group in [group for group in groups if group.cia_project_name]:
            self.config = group
            doc = self.composeCIAXMLMessage()

            if self._settings.runtime.debug:
                sys.stdout.write(doc.toprettyxml(' ' * 4, encoding = 'utf-8'))
            else:
                self.deliverRPCMessage(doc)


    def deliverRPCMessage(self, doc):
        """ Delivers the supplied message via XML-RPC

            :param doc: The message document
            :type doc: DOM object
        """
        import xmlrpclib
        server = xmlrpclib.ServerProxy(self._settings.general.cia_rpc_server)
        server.hub.deliver(doc.toxml(encoding = 'utf-8'))


    def composeCIAXMLMessage(self):
        """ Composes the XML message to send

            (a commit message according to the `CIA schema`_\)

            .. _CIA schema: http://navi.cx/svn/misc/trunk/cia/xml/schema.xsd

            :return: The message
            :rtype: DOM object
        """
        from xml import dom
        message = dom.getDOMImplementation().createDocument(
            None, 'message', None
        )

        self._addTimeStamp(message)
        self._addGenerator(message)
        self._addSource(message)
        self._addBody(message)

        return message


    def _addTimeStamp(self, doc):
        """ Adds revision timestamp to the message

            :param doc: The message document
            :type doc: DOM object
        """
        stamp = self.getTime()

        if self._settings.runtime.debug:
            import time
            comment = doc.createComment(u" %s " % time.ctime(stamp))
            doc.documentElement.appendChild(comment)

        timestamp = self._getTextElement(doc, u'timestamp', unicode(stamp))
        doc.documentElement.appendChild(timestamp)


    def _addGenerator(self, doc):
        """ Adds the generator info to the message

            :param doc: The message document
            :type doc: DOM object
        """
        from svnmailer import version

        generator = doc.createElement('generator')
        self._addTextElements(generator,
            (u'name', u'svnmailer (cia_xmlrpc notifier)'),
            (u'version', version.string.decode('utf-8')),
            (u'url', u'http://opensource.perlig.de/svnmailer/'),
        )

        doc.documentElement.appendChild(generator)


    def _addSource(self, doc):
        """ Adds the source info to the message

            :param doc: The message document
            :type doc: DOM object
        """
        source = doc.createElement('source')

        self._addTextElements(source,
            (u'project',   self.config.cia_project_name),
            (u'module',    self.config.cia_project_module),
            (u'branch',    self.config.cia_project_branch),
            (u'submodule', self.config.cia_project_submodule),
        )

        doc.documentElement.appendChild(source)


    def _addBody(self, doc):
        """ Adds the actual commit info to the message

            :param doc: The message document
            :type doc: DOM object
        """
        body = doc.createElement(u'body')
        commit = doc.createElement(u'commit')
        body.appendChild(commit)

        self._addTextElements(commit,
            (u'author', self._getAuthorName()),
            (u'revision', unicode(self._settings.runtime.revision)),
            (u'log', self.getLog().decode('utf-8', 'replace')),
            (u'url', self.getUrl(self.config)),
            (u'diffLines', self._getDiffLineCount())
        )

        files = doc.createElement(u'files')
        commit.appendChild(files)
        self._addTextElements(files, *[(
            u'file',
            "%s%s" % (
                self._stripPath(change.path),
                ["", "/"][change.isDirectory()]
            ),
            {
                u'uri'   : self._getFileUri(change),
                u'action': self._getFileAction(change),
                u'type'  : self._getFileType(change),
            },
        ) for change in self.changeset])

        doc.documentElement.appendChild(body)


    def _getDiffLineCount(self):
        """ Returns the number of changed lines

            It counts the number of minus lines and the number of plus lines
            and returns the greater value.

            :return: The diff line count or ``None``
            :rtype: ``unicode``
        """
        count = 0
        for change in self.changeset:
            # content
            if not (change.isDirectory() or change.isBinary()):
                file1, file2 = self.dumpContent(change)[:2]
                diff_out = self.differ.getFileDiff(
                    file1.name, file2.name, '1', '2',
                )
                count += self._getTagCount(diff_out)
                del file1, file2, diff_out

            # properties
            if change.hasPropertyChanges():
                propdict = change.getModifiedProperties()
                for name, values in propdict.items():
                    if not self.isBinaryProperty(values):
                        diff_out = self.differ.getStringDiff(
                            values[0], values[1], name, name
                        )
                        count += self._getTagCount(diff_out)
                        del diff_out

        return count and unicode(count) or None


    def _getTagCount(self, diff_out):
        """ Returns the number of changed lines for a diff

            :param diff_out: The diff output (one opcode per item)
            :type diff_out: iterable

            :return: Number of changed lines
            :rtype: ``int``
        """
        lines = 0
        for tag, a1, a2, b1, b2 in diff_out:
            if tag == 'A':   # added
                lines += b2 - b1
            elif tag == 'D': # deleted
                lines += a2 - a1
            elif tag == 'M': # modified
                lines += max(a2 - a1, b2 - b1)

        return lines


    def _getFileUri(self, change):
        """ Returns an URL associated with the changed file

            :TODO: add the ability to use raw subversion urls?

            :param change: The change to process
            :type change: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The URI or ``None``
            :rtype: ``unicode``
        """
        return self.getContentDiffUrl(self.config, change)


    def _getFileAction(self, change):
        """ Returns the action applied to the changed file

            :TODO: file renaming?

            :param change: The change to process
            :type change: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The action
            :rtype: ``unicode``
        """
        if change.wasDeleted():
            return u"remove"
        elif change.wasCopied() or change.wasAdded():
            return u"add"

        return u"modify"


    def _getFileType(self, change):
        """ Returns the type of the modified file

            :note: currently it only marks directories as x-directory/normal
            :note: This is currently not implemented yet on server side
            :note: What do we do with different types (changed in the
                   revision)?

            :param change: The change to process
            :type change: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The type or ``None``
            :rtype: ``unicode``
        """
        if change.isDirectory():
            return u"x-directory/normal"

        return None


    def _stripPath(self, path):
        """ Returns the stripped path of a change

            :param path: The path to strip
            :type path: ``str``

            :return: The stripped path
            :rtype: ``unicode``
        """
        path = path.decode('utf-8', 'replace')
        tostrip = self.config.cia_project_path
        if tostrip:
            # normalize
            while tostrip.startswith('/'):
                tostrip = tostrip[1:]
            while tostrip.endswith('//'):
                tostrip = tostrip[:-1]
            if not tostrip.endswith('/'):
                tostrip = "%s/" % tostrip
            # strip it
            if path.startswith(tostrip):
                path = path.replace(tostrip, "", 1)

        return path


    def _getAuthorName(self):
        """ Returns the name of the author

            @return: The name
            @rtype: ``unicode``
        """
        if self.config.extract_x509_author:
            from svnmailer import util
            author = util.extractX509User(self.getAuthor())
            if author and author[0]:
                return author[0]

        return (self.getAuthor() or "(no author)").decode('utf-8', 'replace')


    def _addTextElements(self, parent, *elems):
        """ Add multiple text elements

            :Parameters:
             - `parent`: The parent element
             - `elems`: The elements to add (name, value)

            :Types:
             - `parent`: Element Node
             - `elems`: ``list`` of ``tuple``
        """
        for elem in [elem for elem in elems if elem[1]]:
            name, value = elem[:2]
            attr = elem[2:] and elem[2] or {}
            elem = self._getTextElement(parent.ownerDocument,
                name, value, attr
            )
            parent.appendChild(elem)


    def _getTextElement(self, doc, name, value, attr = None):
        """ Returns a new element containing text to the message

            :Parameters:
             - `doc`: The message document
             - `name`: The name of the element
             - `value`: The content of the element
             - `attr`: Attributes

            :Types:
             - `doc`: DOM object
             - `name`: ``unicode``
             - `value`: ``unicode``
             - `attr`: ``dict``
        """
        from svnmailer import util

        elem = doc.createElement(name)
        cont = doc.createTextNode(util.filterForXml(value))
        elem.appendChild(cont)

        if attr:
            for key, value in [item for item in attr.items() if item[1]]:
                elem.setAttribute(key, util.filterForXml(value))

        return elem
