# -*- coding: iso-8859-1 -*-
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
Text based news notifier
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['TextNewsNotifier']

# global imports
from svnmailer.notifier import _textmail, _mail


def getNotifier(cls, settings, groupset):
    """ Returns an initialized notifier or nothing

        :Parameters:
         - `cls`: The notifier base class to use
         - `settings`: The svnmailer settings
         - `groupset`: The groupset to process

        :Types:
         - `cls`: ``class``
         - `settings`: `svnmailer.settings._base.BaseSettings`
         - `groupset`: ``list``

        :return: The list of notifiers (containing 0 or 1 member)
        :rtype: ``list``
    """
    from svnmailer import util

    return [_textmail.decorateNotifier(
        util.inherit(cls, TextNewsNotifier),
        groupset.groups[0].long_news_action, settings, groupset
    )]


class TextNewsNotifier(_textmail.TextMailNotifier):
    """ Bases class for news notifiers """
    __implements__ = [_textmail.TextMailNotifier]

    def sendMail(self, sender, to_addr, mail):
        """ Sends the news

            :Parameters:
             - `sender`: The mail sender (envelope from)
             - `to_addr`: The receivers
             - `mail`: The mail object

            :Types:
             - `sender`: ``str``
             - `to_addr`: ``list``
             - `mail`: ``_TextMail``
        """
        (to_addr, sender) # pylint
        self.sendNews(mail)


    def sendNews(self, posting):
        """ Sends the news

            :param posting: The posting object
            :type posting: ``_textmail._TextMail``
        """
        raise NotImplementedError()


    def getTransferEncoding(self):
        """ Returns the news transfer encoding """
        return self.config.news_transfer_encoding


    def composeHeaders(self, groups):
        """ Compose the informational headers of the mail

            :param groups: The groups to process
            :type groups: ``list``

            :return: sender (``unicode``), recipients (``list``), headers
                (``dict``)
            :rtype: ``tuple``
        """
        from email import Header

        sender, from_addrs, to_newsgroups, reply_to = \
            self.getNewsAddresses(groups)
        if not to_newsgroups:
            raise _mail.NoRecipientsError()

        headers = self.getBasicHeaders()
        headers['From'] = from_addrs[0]
        headers['Newsgroups'] = Header.Header(','.join(to_newsgroups))

        if reply_to:
            headers['Reply-To'] = Header.Header(', '.join(reply_to))
        if len(from_addrs) > 1:
            # TODO: make Sender configurable?
            headers['Sender'] = Header.Header(from_addrs[0])

        # TODO: generate message-id (using configured format string)?

        if self._settings.runtime.debug:
            headers['X-Config-Groups'] = Header.Header(', '.join([
                "[%s]" % group._name for group in groups
            ]), 'iso-8859-1')

        return (sender, to_newsgroups, headers)


    def getNewsAddresses(self, groups):
        """ Returns the substituted mail addresses (from/to/reply-to)

            :param groups: The groups to process
            :type groups: ``list``

            :return: The address lists (sender, from, to, reply-to)
            :rtype: ``tuple``
        """
        from_addrs = []
        to_newsgroups = []
        reply_to = []

        sender = None
        for group in groups:
            from_addrs.extend(group.from_addr or [])
            to_newsgroups.extend(group.to_newsgroup or [])
            reply_to.extend(
                group.reply_to_addr and [group.reply_to_addr] or []
            )

        from_addrs = dict.fromkeys(from_addrs).keys() or [
            (self.getAuthor() and self.getAuthor().decode('utf-8', 'replace'))
            or u'no_author'
        ]
        to_newsgroups = dict.fromkeys(to_newsgroups).keys()
        reply_to = dict.fromkeys(reply_to).keys()

        return (sender or from_addrs[0], from_addrs, to_newsgroups, reply_to)
