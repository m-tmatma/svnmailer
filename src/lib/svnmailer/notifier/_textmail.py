# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201,W0232,W0233,C0103,E0201,R0921
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
text based email notifier
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['getNotifier']

# global imports
from svnmailer.notifier import _mail


def getNotifier(cls, config, groupset):
    """ Returns an initialized notifier or nothing

        :Parameters:
         - `cls`: The notifier base class to use
         - `config`: The svnmailer config
         - `groupset`: The groupset to process

        :Types:
         - `cls`: ``class``
         - `config`: `svnmailer.settings._base.BaseSettings`
         - `groupset`: ``list``

        :return: The list of notifiers (containing 0 or 1 member)
        :rtype: ``list``
    """
    from svnmailer import util

    return [decorateNotifier(
        util.inherit(cls, TextMailNotifier),
        groupset.groups[0].long_mail_action, config, groupset
    )]


def decorateNotifier(cls, action, config, groupset):
    """ Decorates the notifier class (or not)

        :Parameters:
         - `cls`: The notifier class
         - `action`: The configured action
         - `config`: The svnmailer config
         - `groupset`: The groupset to process

        :Types:
         - `cls`: ``class``
         - `action`: ``unicode``
         - `config`: `svnmailer.settings._base.BaseSettings`
         - `groupset`: ``list``

        :return: The decorated class or ``None``
        :rtype: ``class``
    """
    if action:
        from svnmailer.settings import MODES
        runtime = config.runtime

        is_commit = bool(runtime.mode == MODES.commit)
        other = bool(
            (    action.REVPROP in action.scope
            and runtime.mode == MODES.propchange)
                            or
            (    action.LOCKS in action.scope
            and runtime.mode in (MODES.lock, MODES.unlock))
        )

        if action.maxbytes and (is_commit or other):
            from svnmailer import util

            decorator = None
            generator = cls

            if action.mode == action.TRUNCATE:
                decorator = util.inherit(TruncatingDecorator, generator)

            elif action.mode == action.URLS:
                if is_commit:
                    decorator = util.inherit(URLDecorator, generator)
                if action.truncate:
                    decorator = util.inherit(
                        is_commit and 
                            URLTruncatingDecorator or TruncatingDecorator,
                        decorator or generator
                    )

            elif action.mode == action.SPLIT:
                if action.truncate:
                    decorator = util.inherit(TruncatingDecorator, generator)
                if is_commit:
                    decorator = util.inherit(
                        SplittingDecorator, decorator or generator
                    )

            if decorator:
                return decorator(config, groupset, action.maxbytes, action.drop)

    return cls(config, groupset)


class TextMailNotifier(_mail.MailNotifier):
    """ Bases class for textual mail notifiers """
    __implements__ = [_mail.MailNotifier]

    def composeMail(self):
        """ Composes the mail

            :return: The senders, the receivers, the mail(s)
            :rtype: ``tuple``
        """
        import cStringIO

        groups = self._groupset.groups
        sender, to_addrs, headers = self.composeHeaders(groups)

        fp = self.fp = self._getMailWriter(cStringIO.StringIO())
        self.writeNotification()
        mails = self._getTextMails('utf-8', {
            u"quoted-printable": "Q",
            u"qp"      : "Q",
            u"base64"  : "B",
            u"base 64" : "B",
            u"8bit"    : "8",
            u"8 bit"   : "8",
        }.get((self.getTransferEncoding() or u'').lower(), 'Q'))

        for mail in mails:
            mail.update(headers)
            yield (
                sender.encode('utf-8'),
                [addr.encode('utf-8') for addr in to_addrs],
                mail
            )

        fp.close()


    def sendMail(self, sender, to_addr, mail):
        """ Sends the mail (abstract method) """
        raise NotImplementedError()


    def _getTextMails(self, charset, enc):
        """ Returns the text mail(s)

            :Parameters:
             - `charset`: The mail charset
             - `enc`: transfer encoding token

            :Types:
             - `charset`: ``str``
             - `enc`: ``str``

            :return: The mail(s)
            :rtype: ``list`` of ``_TextMail``
        """
        return [_TextMail(
            self.getMailSubject(), self.fp.getvalue(), charset, enc
        )]


    def _getMailWriter(self, fp):
        """ Returns a mail writer

            :param fp: The stream to wrap
            :type fp: ``file``

            :return: The file object
            :rtype: ``file``
        """
        from svnmailer import stream

        return stream.UnicodeStream(fp)


class SplittingDecorator(object):
    """ Splits the content between diffs, if it gets loo long

        :IVariables:
         - `final_fp`: Actual stream object containg all data
         - `max_notification_size`: Maximum size of one mail content
         - `drop`: maximum number of mails
         - `drop_fp`: The alternate summary stream

        :Types:
         - `final_fp`: ``file``
         - `max_notification_size`: ``int``
         - `drop`: ``int``
         - `drop_fp`: ``file``
    """

    def __init__(self, config, groupset, maxsize, drop):
        """ Initialization

            :Parameters:
             - `maxsize`: The maximum number of bytes that should be written
               into one mail
             - `drop`: maximum number of mails

            :Types:
             - `maxsize`: ``int``
             - `drop`: ``int``
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(config, groupset, maxsize, drop)
        self.max_notification_size = maxsize
        self.drop = drop


    def _getTextMails(self, charset, enc):
        """ Returns the text mail(s) """
        self._flushToFinalStream(split = True)
        stream = self.final_fp

        nummails = stream.getPartCount()
        if nummails == 1:
            yield _TextMail(
                self.getMailSubject(), stream.getPart(0), charset, enc
            )
        elif self.drop and nummails > self.drop:
            self.drop_fp.write((
                u"\n[This commit notification would consist of %d parts, "
                u"\nwhich exceeds the limit of %d ones, so it was shortened "
                u"to the summary.]\n" % (nummails, self.drop)
            ).encode("utf-8"))

            yield _TextMail(
                self.getMailSubject(), self.drop_fp.getvalue(), charset, enc
            )
        else:
            for idx in range(nummails):
                yield _TextMail(
                    self.getMailSubject(u"[%d/%d]" % (idx + 1, nummails)),
                    stream.getPart(idx), charset, enc
                )

        self.drop_fp.close()
        self.final_fp.close()


    def _getMailWriter(self, fp):
        """ Returns a splitting mail writer """
        from svnmailer import stream
        import cStringIO

        self.final_fp = stream.SplittingStream(tempdir = self.getTempDir())
        self.drop_fp = self.__super._getMailWriter(cStringIO.StringIO())

        return self.__super._getMailWriter(fp)


    def writeMetaData(self):
        """ write meta data to drop_fp as well """
        old_fp, self.fp = (self.fp, self.drop_fp)
        self.__super.writeMetaData()
        self.fp = old_fp

        self.__super.writeMetaData()


    def writePathList(self):
        """ write the stuff to the real stream """
        self.__super.writePathList()
        self.final_fp.write(self.fp.getvalue())
        self.fp.seek(0) # don't use reset on possible codec StreamWriters...
        self.fp.truncate()

        if self.final_fp.current > self.max_notification_size:
            self.final_fp.write("\n")
            self.final_fp.split()


    def _flushToFinalStream(self, split = False):
        """ Flushes the current content to the final stream

            :param split: Should split regardless of the current size?
            :type split: ``bool``
        """
        value = self.fp.getvalue()
        self.fp.seek(0)
        self.fp.truncate()

        supposed = self.final_fp.current + len(value)
        if split or supposed > self.max_notification_size:
            self.final_fp.write("\n")
            self.final_fp.split()

        self.final_fp.write(value)


    def writeContentDiff(self, change):
        """ write the stuff to the real stream """
        self.__super.writeContentDiff(change)
        self._flushToFinalStream()


    def writePropertyDiffs(self, diff_tokens, change):
        """ write the stuff to the real stream """
        self.__super.writePropertyDiffs(diff_tokens, change)
        self._flushToFinalStream()


class TruncatingDecorator(object):
    """ Truncates the mail body after n bytes """

    def __init__(self, config, groupset, maxsize, drop):
        """ Initialization

            :Parameters:
             - `maxsize`: The maximum number of bytes that should be written
               into one mail
             - `drop`: maximum number of mails
            
            :Types:
             - `maxsize`: ``int``
             - `drop`: `int`
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(config, groupset, maxsize, drop)
        self.max_notification_size = maxsize


    def _getMailWriter(self, fp):
        """ Returns a truncating mail writer """
        from svnmailer import stream

        fp = stream.TruncatingStream(fp, self.max_notification_size, True)
        return self.__super._getMailWriter(fp)


class URLDecorator(object):
    """ Shows only the urls, if the mail gets too long

        :ivar url_fp: The alternative stream
        :type url_fp: ``file``
    """

    def __init__(self, config, groupset, maxsize, drop):
        """ Initialization

            :Parameters:
             - `maxsize`: The maximum number of bytes that should be written
               into one mail
             - `drop`: maximum number of mails

            :Types:
             - `maxsize`: ``int``
             - `drop`: ``int``
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(config, groupset, maxsize, drop)
        self.max_notification_size = maxsize


    def _getMailWriter(self, fp):
        """ Returns a "urling" mail writer """
        import cStringIO
        from svnmailer import stream

        fp = stream.TruncatingStream(
            self.__super._getMailWriter(fp),
            self.max_notification_size
        )
        self.url_fp = self.__super._getMailWriter(
            cStringIO.StringIO()
        )

        return stream.CuckooStream(fp)


    def writeNotification(self):
        """ Writes the notification body """
        self.__super.writeNotification()

        if self.fp.getTruncatedLineCount():
            self.fp.replaceStream(self.url_fp)


    def writeMetaData(self):
        """ Writes the commit metadata output """
        self.__super.writeMetaData()
        old_fp, self.fp = (self.fp, self.url_fp)
        self.__super.writeMetaData()
        self.fp = old_fp


    def writePathList(self):
        """ Writes the commit path list """
        self.__super.writePathList()
        old_fp, self.fp = (self.fp, self.url_fp)
        self.__super.writePathList()
        self.fp = old_fp


    def writeDiffList(self):
        """ Writes the commit diffs """
        if self.getBrowserGenerator(self.config):
            self.url_fp.write(
                u"\n[This mail would be too long, it was shortened to "
                u"contain the URLs only.]\n\n"
            )
        else:
            self.url_fp.write(
                u"\n[This mail would be too long, it should contain the "
                u"URLs only, but no browser base url was configured...]\n"
            )

        self.__super.writeDiffList()


    def writeContentDiff(self, change):
        """ Writes the content diff for a particular change """
        self.__super.writeContentDiff(change)

        url = self.getContentDiffUrl(self.config, change)
        if url is not None:
            old_fp, self.fp = (self.fp, self.url_fp)
            self.__super.writeContentDiffAction(change)
            self.fp = old_fp
            self.url_fp.write("URL: %s\n" % url)
            self.url_fp.write("\n")


class URLTruncatingDecorator(object):
    """ Truncates the mail body after n bytes """

    def __init__(self, config, groupset, maxsize, drop):
        """ Initialization

            :Parameters:
             - `maxsize`: The maximum number of bytes that should be written
               into one mail
             - `drop`: maximum number of mails

            :Types:
             - `maxsize`: ``int``
             - `drop`: ``int``
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(config, groupset, maxsize, drop)
        self.max_notification_size = maxsize


    def _getMailWriter(self, fp):
        """ Returns a truncating mail writer """
        from svnmailer import stream

        fp = self.__super._getMailWriter(fp)
        self.url_fp = stream.TruncatingStream(
            self.url_fp, self.max_notification_size, True
        )

        return fp


from email import MIMENonMultipart
class _TextMail(MIMENonMultipart.MIMENonMultipart):
    """ A text mail class (email.MIMEText produces undesired results) """

    def __init__(self, subject, body, charset, enc = 'Q'):
        """ Initialization

            :Parameters:
             - `subject`: The subject to use
             - `body`: The mail body
             - `charset`: The charset, the body is encoded
             - `enc`: transfer encoding token (``Q``, ``B`` or ``8``)

            :Types:
             - `subject`: ``str``
             - `body`: ``str``
             - `charset`: ``str``
             - `enc`: ``str``
        """
        from email import Charset, Header

        _charset = Charset.Charset(charset)
        _charset.body_encoding = {
            'Q': Charset.QP, 'B': Charset.BASE64, '8': None
        }.get(str(enc), Charset.QP)
        _charset.header_encoding = Charset.QP
        MIMENonMultipart.MIMENonMultipart.__init__(
            self, 'text', 'plain', charset = charset
        )
        self.set_payload(body, _charset)
        self['Subject'] = Header.Header(subject, 'iso-8859-1')


    def dump(self, fp):
        """ Serializes the mail into a descriptor

            :param fp: The file object
            :type fp: ``file``
        """
        from email import Generator

        class MyGenerator(Generator.Generator):
            """ Derived generator to handle the payload """

            def _handle_text_plain(self, msg):
                """ handle the payload """
                payload = msg.get_payload()
                cset = msg.get_charset()
                if cset:
                    enc = cset.get_body_encoding()
                    if enc == 'quoted-printable':
                        import binascii
                        payload = binascii.b2a_qp(payload, istext = True)
                    elif enc == 'base64':
                        payload = payload.encode('base64')
                self.write(payload)

        generator = MyGenerator(fp, mangle_from_ = False)
        generator.flatten(self, unixfrom = False)


    def update(self, headers):
        """ Update the header set of the mail

            :param headers: The new headers
            :type headers: ``dict``
        """
        for name, value in headers.items():
            self[name] = value
