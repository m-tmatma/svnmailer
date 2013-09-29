# -*- coding: utf-8 -*-
# pylint: disable-msg = W0613
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
Email notifier base module
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ["MailNotifier"]

# global imports
from svnmailer.notifier import _text

# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class NoRecipientsError(Error):
    """ No recipients found """
    pass


class MailNotifier(_text.TextNotifier):
    """ Bases class for mail (like) notifiers

        @ivar _header_re: Pattern for header name checking
        @type _header_re: sre pattern or C{None}
    """
    __implements__ = [_text.TextNotifier]

    COMMIT_SUBJECT  = u"%(prefix)s r%(revision)s %(part)s - %(files/dirs)s"
    REVPROP_SUBJECT = u"%(prefix)s r%(revision)s - %(property)s"
    LOCK_SUBJECT    = u"%(prefix)s %(files/dirs)s"
    UNLOCK_SUBJECT  = u"%(prefix)s %(files/dirs)s"

    # need this (variable args) for deco classes
    def __init__(self, config, groupset, *args, **kwargs):
        """ Initialization """
        _text.TextNotifier.__init__(self, config, groupset)
        self._header_re = None


    def run(self):
        """ Send notification as mail """
        import sys

        try:
            for mail in self.getMails():
                if self._settings.runtime.debug:
                    mail[2].dump(sys.stdout)
                else:
                    self.sendMail(mail[0], mail[1], mail[2])
        except NoRecipientsError:
            if self._settings.runtime.debug:
                sys.stdout.write("No recipients found for %s\n" %
                    ', '.join([
                        "[%s]" % group._name.encode('utf-8')
                        for group in self._groupset.groups
                    ])
                )


    def getMails(self):
        """ Returns the composed mail(s)

            @return: The mails
            @rtype: generator
        """
        for mail in self.composeMail():
            yield mail


    def writeNotification(self):
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


    def getTransferEncoding(self):
        """ Returns the transfer encoding to use

            @return: The configured value
            @rtype: C{unicode}
        """
        return self.config.mail_transfer_encoding


    def sendMail(self, sender, to_addr, mail):
        """ Sends the mail

            @param sender: The mail sender (envelope from)
            @type sender: C{str}

            @param to_addr: The receivers
            @type to_addr: C{list}

            @param mail: The mail object
            @type mail: C{_TextMail}
        """
        raise NotImplementedError()


    def composeMail(self):
        """ Composes the mail

            @return: The senders, the receivers, the mail(s)
            @rtype: C{tuple}
        """
        raise NotImplementedError()


    def getBasicHeaders(self):
        """ Returns the basic headers

            @return: The headers
            @rtype: C{dict}
        """
        from email import Utils, Header
        from svnmailer import version

        return {
            'X-Mailer': Header.Header(
                ("svnmailer-%s" % version).decode('utf-8'), 'iso-8859-1'
            ),
            'Date': Utils.formatdate(),
        }


    def composeHeaders(self, groups):
        """ Compose the informational headers of the mail

            @param groups: The groups to process
            @type groups: C{list}

            @return: sender (C{unicode}), recipients (C{list}), headers
                (C{dict})
            @rtype: C{tuple}
        """
        from email import Header

        sender, from_addrs, reply_to, to_addrs, to_fakes, bcc_addrs = \
            self.getMailAddresses(groups)
        recipients = to_addrs + bcc_addrs
        if not recipients:
            raise NoRecipientsError()

        headers = self.getBasicHeaders()
        headers['From'] = ', '.join(from_addrs)

        if self._settings.general.debug_all_mails_to:
            headers['X-Supposed-Recipients'] = \
                Header.Header(', '.join(recipients))
            recipients = self._settings.general.debug_all_mails_to
        if to_addrs:
            headers['To'] = Header.Header(', '.join(to_addrs))
        elif to_fakes:
            headers['To'] = Header.Header(', '.join(to_fakes))

        if reply_to:
            headers['Reply-To'] = Header.Header(', '.join(reply_to))
        if len(from_addrs) > 1:
            # TODO: make Sender configurable?
            headers['Sender'] = Header.Header(from_addrs[0])

        headers.update(self.getCustomHeaders(groups))

        # TODO: generate message-id (using configured format string)?

        if self._settings.runtime.debug:
            headers['X-Config-Groups'] = Header.Header(', '.join([
                "[%s]" % group._name for group in groups
            ]), 'iso-8859-1')

        return (sender, recipients, headers)


    def getCustomHeaders(self, groups):
        """ Returns the custom headers

            @param groups: The groups to process
            @type groups: C{list}

            @return: The custom headers
            @rtype: C{dict}
        """
        import re
        from email import Header

        header_re = self._header_re
        if not header_re:
            header_re = self._header_re = re.compile("[^%s]" %
                re.escape(u''.join([
                    # RFC 2822, 3.6.8.
                    chr(num) for num in range(33,127) if num != 58
                ]))
            )

        custom = {}
        for group in [group for group in groups if group.custom_header]:
            tup = group.custom_header.split(None, 1)
            custom.setdefault(
                'X-%s' % header_re.sub("", tup[0]), []
            ).extend(tup[1:])

        return dict([(name,
            Header.Header(', '.join(values), 'iso-8859-1')
        ) for name, values in custom.items()])


    def getMailAddresses(self, groups):
        """ Returns the substituted mail addresses (from/to/reply-to)

            @param groups: The groups to process
            @type groups: C{list}

            @return: The address lists (sender, from, reply-to, to, to-fake,
                     bcc)
            @rtype: C{tuple}
        """
        from_addrs = []
        to_addrs = []
        to_fakes = []
        bcc_addrs = []
        reply_to = []

        sender = None
        for group in groups:
            from_addrs.extend(group.from_addr or [])
            to_addrs.extend(group.to_addr or [])
            bcc_addrs.extend(group.bcc_addr or [])
            to_fakes.extend(group.to_fake and [group.to_fake] or [])
            reply_to.extend(
                group.reply_to_addr and [group.reply_to_addr] or []
            )

        from_addrs = dict.fromkeys(from_addrs).keys() or [
            (self.getAuthor() and self.getAuthor().decode('utf-8', 'replace'))
            or u'no_author'
        ]
        to_addrs = dict.fromkeys(to_addrs).keys()
        bcc_addrs = dict.fromkeys(bcc_addrs).keys()
        reply_to = dict.fromkeys(reply_to).keys()
        if to_addrs:
            to_fakes = []
        else:
            to_fakes = dict.fromkeys(to_fakes).keys()

        return (
            sender or from_addrs[0], from_addrs, reply_to,
            to_addrs, to_fakes, bcc_addrs
        )


    def getMailSubject(self, countprefix = None):
        """ Returns the subject

            @param countprefix: Optional countprefix (inserted after the rev
                number)
            @type countprefix: C{unicode}

            @return: The subject line
            @rtype: C{unicode}
        """
        from svnmailer import util
        from svnmailer.settings import modes

        runtime = self._settings.runtime
        groups, changeset = (self._groupset.groups, self._groupset.changes[:])
        xset = self._groupset.xchanges
        if xset:
            changeset.extend(xset)

        max_length   = max(0, groups[0].max_subject_length)
        short_length = max_length or 255 # for files/dirs

        template, mode = {
            modes.commit:     (self.COMMIT_SUBJECT,  'commit',   ),
            modes.propchange: (self.REVPROP_SUBJECT, 'propchange'),
            modes.lock:       (self.LOCK_SUBJECT,    'lock',     ),
            modes.unlock:     (self.UNLOCK_SUBJECT,  'unlock',   ),
        }[runtime.mode]

        template = getattr(groups[0], "%s_subject_template" % mode) \
            or template

        params = {
            'prefix'  : getattr(groups[0], "%s_subject_prefix" % mode),
            'part'    : countprefix,
            'files'   : self._getPrefixedFiles(changeset),
            'dirs'    : self._getPrefixedDirectories(changeset),
        }

        # We may try twice, first with files/dirs = files
        # If the result is too long, we do again with files/dirs = dirs
        def dosubject(param):
            """ Returns the subject """
            # set files/dirs, substitute, normalize WS
            params['files/dirs'] = params[param]
            cparams = params.copy()
            cparams.update(groups[0]._sub_.dict())
            return " ".join(util.substitute(template, cparams).split())

        subject = dosubject('files')
        if len(subject) > short_length:
            subject = dosubject('dirs')

        # reduce to the max ...
        if max_length and len(subject) > max_length:
            subject = "%s..." % subject[:max_length - 3]

        return subject


    def _getPrefixedDirectories(self, changeset):
        """ Returns the longest common directory prefix

            @param changeset: The change set
            @type changeset: list

            @return: The common dir and the path list, human readable
            @rtype: C{unicode}
        """
        import posixpath
        from svnmailer import util

        dirs = dict.fromkeys([
            "%s/" % (change.isDirectory() and
                [change.path] or [posixpath.dirname(change.path)])[0]
            for change in changeset
        ]).keys()

        common, dirs = util.commonPaths(dirs)
        dirs.sort()

        return self._getPathString(common, dirs)


    def _getPrefixedFiles(self, changeset):
        """ Returns the longest common path prefix

            @param changeset: The change set
            @type changeset: list

            @return: The common dir and the path list, human readable
            @rtype: C{unicode}
        """
        from svnmailer import util

        paths = dict.fromkeys([
            change.isDirectory() and "%s/" % change.path or change.path
            for change in changeset
        ]).keys()

        common, paths = util.commonPaths(paths)
        paths.sort()

        return self._getPathString(common, paths)
 

    def _getPathString(self, prefix, paths):
        """ Returns the (possibly) prefixed paths as string

            All parameters are expected to be UTF-8 encoded

            @param prefix: The prefix (may be empty)
            @type prefix: C{str}

            @param paths: List of paths (C{[str, str, ...]})
            @type paths: C{list}

            @return: The prefixed paths as unicode
            @rtype: C{unicode}
        """
        slash = [u"/", u""][bool(prefix)]
        paths = u" ".join([
            u"%s%s" % (slash, path.decode("utf-8"))
            for path in paths
        ])

        return (prefix and
            u"in /%s: %s" % (prefix.decode("utf-8"), paths) or paths
        )
