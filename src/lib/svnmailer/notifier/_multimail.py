# -*- coding: utf-8 -*-
# pylint: disable-msg = W0201, W0233, W0613
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
email notifier
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['Error', 'InvalidMailOption', 'getNotifier']

# global imports
from svnmailer.notifier import _mail

# exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class InvalidMailOption(Error):
    """ Invalid Multipart mail option """
    pass


def getNotifier(cls, config, groupset):
    """ Returns an initialized notifier or nothing

        @param cls: The notifier base class to use
        @type cls: C{class}

        @param config: The svnmailer config
        @type config: C{svnmailer.settings.Settings}

        @param groupset: The groupset to process
        @type groupset: C{list}

        @return: The list of notifiers (containing 0 or 1 member)
        @rtype: C{list}
    """
    from svnmailer import util

    return [decorateNotifier(
        util.inherit(cls, MultiMailNotifier),
        groupset.groups[0].long_mail_action, config, groupset
    )]


def decorateNotifier(cls, action, config, groupset):
    """ Decorates the notifier class (or not)

        @param cls: The notifier class
        @type cls: C{class}

        @param action: The configured action
        @type action: C{unicode}

        @param config: The svnmailer config
        @type config: C{svnmailer.settings.Settings}

        @param groupset: The groupset to process
        @type groupset: C{list}

        @return: The decorated class or C{None}
        @rtype: C{class}
    """
    if action and action.maxbytes:
        from svnmailer import util

        decorator = None
        generator = cls

        if action.mode == action.TRUNCATE:
            decorator = util.inherit(TruncatingDecorator, generator)

        elif action.mode == action.URLS:
            decorator = util.inherit(URLDecorator, generator)
            if action.truncate:
                decorator = util.inherit(URLTruncatingDecorator, decorator)

        elif action.mode == action.SPLIT:
            decorator = util.inherit(SplittingDecorator, generator)
            if action.truncate:
                decorator = util.inherit(
                    SplittingTruncatingDecorator, decorator
                )

        if decorator:
            return decorator(config, groupset, action.maxbytes, action.drop)

    return cls(config, groupset)


class MultiMailNotifier(_mail.MailNotifier):
    """ Bases class for mail notifiers using attachments for the diffs """
    __implements__ = [_mail.MailNotifier]

    # need this (variable args) for deco classes
    def __init__(self, config, groupset, *args, **kwargs):
        """ Initialization """
        _mail.MailNotifier.__init__(self, config, groupset)
        self.mctype, self.mdispo = self._parseMailType()


    def _parseMailType(self):
        """ Returns the multimail options

            @return: The diff content type and disposition
            @rtype: C{tuple}
        """
        from svnmailer import util

        ctype = 'text/plain'
        dispo = 'inline'
        for option in (self.config.mail_type or '').split()[1:]:
            try:
                name, value = [val.lower() for val in option.split('=')]
                if name == u'type':
                    ctype = util.parseContentType(value)
                    if not ctype:
                        raise ValueError(
                            "invalid multimail type specification %r" % value
                        )
                    ctype = ctype[0]
                elif name == u'disposition':
                    if value not in (u'inline', 'attachment'):
                        raise ValueError(
                            "invalid disposition specification %r" % value
                        )
                    dispo = value
                else:
                    raise ValueError("unknown multimail option %r" % option)
            except ValueError, exc:
                raise InvalidMailOption(str(exc))

        return (ctype, dispo)


    def composeMail(self):
        """ Composes the mail

            @return: The senders, the receivers, the mail(s)
            @rtype: C{tuple}
        """
        import cStringIO

        groups = self._groupset.groups
        sender, to_addrs, headers = self.composeHeaders(groups)

        self.diff_file_list = []
        self.fp = self._getMailWriter(cStringIO.StringIO())
        self.writeNotification()

        # create the mails
        mails = self._getMultiMails()

        for mail in mails:
            mail.update(headers)
            yield (
                sender.encode('utf-8'),
                [addr.encode('utf-8') for addr in to_addrs],
                mail
            )

        self.diff_file_list = []
        self.fp.close()


    def sendMail(self, sender, to_addr, mail):
        """ Sends the mail (abstract method) """
        raise NotImplementedError()


    def _getMultiMails(self):
        """ Returns the multipart mail(s)

            @return: The mail(s)
            @rtype: C{list} of C{_MultiMail}
        """
        parts = [_SinglePart(self.fp.getvalue(), encoding = 'utf-8')]
        diff = None # avoid UnboundLocalError if the loop is not run
        for diff in self.diff_file_list:
            parts.append(diff.toMIMEPart())
        del diff # cleanup

        return [_MultiMail(self.getMailSubject(), parts)]


    def _getMailWriter(self, fp):
        """ Returns a mail writer

            @param fp: The stream to wrap
            @type fp: file like object

            @return: The file object
            @rtype: file like object
        """
        from svnmailer import stream

        return stream.UnicodeStream(fp)


    def writeDiffList(self):
        """ Writes the commit diffs into temp files """
        from svnmailer import stream

        # drop all stuff between diffs
        old_fp, self.fp = (self.fp, stream.DevNullStream())

        super(MultiMailNotifier, self).writeDiffList()

        # restore the descriptor
        self.fp.close()
        self.fp = old_fp


    def writeContentDiff(self, change, raw = False):
        """ Dump the diff into a separate file """
        if change.isDirectory():
            return

        tmpfile = self.getTempFile()
        old_fp, self.fp = (self.fp, self._getDiffStream(tmpfile.fp))

        raw = True
        super(MultiMailNotifier, self).writeContentDiff(change, raw)

        self.fp.close()
        self.diff_file_list.append(DiffDescriptor(self, tmpfile, change))

        self.fp = old_fp


    def writePropertyDiffs(self, diff_tokens, change, raw = False):
        """ Dump the property diff into a separate file """
        tmpfile = self.getTempFile()
        old_fp, self.fp = (self.fp, self._getDiffStream(tmpfile.fp))

        raw = True
        super(MultiMailNotifier, self).writePropertyDiffs(
            diff_tokens, change, raw
        )

        self.fp.close()
        self.diff_file_list.append(DiffDescriptor(self, tmpfile, change, True))

        self.fp = old_fp


    def _getDiffStream(self, fp):
        """ Returns the (possibly decorated) diff stream """
        from svnmailer import stream

        return stream.BinaryOrUnicodeStream(fp)


class SplittingDecorator(object):
    """ Splits the content between diffs if it gets too long

        @ivar max_notification_size: Maximum size of one mail content
        @type max_notification_size: C{int}

        @ivar drop: maximum number of mails
        @type drop: C{int}

        @ivar drop_fp: The alternate summary stream
        @type drop_fp: file like object
    """

    def __init__(self, settings, groupset, maxsize, drop):
        """ Initialization

            @param maxsize: The maximum number of bytes that should be written
                into one mail
            @type maxsize: C{int}

            @param drop: maximum number of mails
            @type drop: C{int}
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(settings, groupset, maxsize, drop)
        self.max_notification_size = maxsize
        self.drop = drop


    def _getMailWriter(self, fp):
        """ inits the drop_fp """
        import cStringIO

        self.drop_fp = self.__super._getMailWriter(cStringIO.StringIO())

        return self.__super._getMailWriter(fp)


    def writeMetaData(self):
        """ write meta data to drop_fp as well """
        old_fp, self.fp = (self.fp, self.drop_fp)
        self.__super.writeMetaData()
        self.fp = old_fp

        self.__super.writeMetaData()


    def _getMultiMails(self):
        """ Returns the multipart mail(s)

            @return: The mail(s)
            @rtype: C{list} of C{_MultiMail}
        """
        parts = [_SinglePart(self.fp.getvalue(), encoding = 'utf-8')]

        diff = None
        asize = parts[0].getSize()
        diffs = [(diff, diff.toMIMEPart().getSize())
            for diff in self.diff_file_list
        ]
        diff_sizes = [diff[1] for diff in diffs]
        maxsize = sum(diff_sizes, asize)

        if maxsize <= self.max_notification_size or not diff_sizes:
            parts.extend([diff.toMIMEPart() for diff in self.diff_file_list])
            yield _MultiMail(self.getMailSubject(), parts)
        else:
            nummails = 1
            tsize = asize
            for size in diff_sizes:
                tsize += size
                if tsize > self.max_notification_size:
                    nummails += 1
                    tsize = size

            if self.drop and nummails > self.drop:
                self.drop_fp.write((
                    u"\n[This commit notification would consist of %d parts, "
                    u"\nwhich exceeds the limit of %d ones, so it was "
                    u"shortened to the summary.]\n" % (nummails, self.drop)
                ).encode("utf-8"))

                yield _MultiMail(self.getMailSubject(), [_SinglePart(
                    self.drop_fp.getvalue(), encoding = 'utf-8'
                )])
            else:
                mcount = 1
                for diff in diffs:
                    asize += diff[1]
                    if asize > self.max_notification_size:
                        yield _MultiMail(
                            self.getMailSubject(u"[%d/%d]" % (mcount, nummails)
                        ), parts)
                        mcount += 1
                        asize = diff[1]
                        parts = [_SinglePart((
                            u"[Part %d/%d]\n" % (mcount, nummails)
                        ).encode('utf-8'), encoding = 'utf-8')]
                    parts.append(diff[0].toMIMEPart())

                if parts:
                    yield _MultiMail(
                        self.getMailSubject(u"[%d/%d]" % (mcount, nummails)
                    ), parts)

        del diff # cleanup


class SplittingTruncatingDecorator(object):
    """ split/truncate decorator """

    def __init__(self, settings, groupset, maxsize, drop):
        """ Initialization

            @param maxsize: The maximum number of bytes that should be written
                into one mail
            @type maxsize: C{int}

            @param drop: maximum number of mails
            @type drop: C{int}
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(settings, groupset, maxsize, drop)


    def _getMailWriter(self, fp):
        """ Returns a truncating mail writer """
        from svnmailer import stream

        fp = stream.TruncatingStream(fp, self.max_notification_size, True)
        return self.__super._getMailWriter(fp)


    def _getDiffStream(self, fp):
        """ Returns the truncating diff stream """
        from svnmailer import stream

        fp = stream.TruncatingFileStream(fp, self.max_notification_size, True)
        return self.__super._getDiffStream(fp)


class TruncatingDecorator(object):
    """ Truncates the mail body after n bytes

        @ivar max_notification_size: Maximum size of one mail content
        @type max_notification_size: C{int}
    """

    def __init__(self, settings, groupset, maxsize, drop):
        """ Initialization

            @param maxsize: The maximum number of bytes that should be written
                into one mail
            @type maxsize: C{int}

            @param drop: maximum number of mails
            @type drop: C{int}
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(settings, groupset, maxsize, drop)
        self.max_notification_size = maxsize


    def _getMailWriter(self, fp):
        """ Returns a truncating mail writer """
        from svnmailer import stream

        fp = stream.TruncatingStream(fp, self.max_notification_size, True)
        return self.__super._getMailWriter(fp)


    def _getMultiMails(self):
        """ Returns the multipart mail(s)

            @return: The mail(s)
            @rtype: C{list} of C{_MultiMail}
        """
        parts = [_SinglePart(self.fp.getvalue(), encoding = 'utf-8')]

        if self.fp.getTruncatedLineCount():
            dlen = len(self.diff_file_list)
            if dlen:
                parts.append(_SinglePart((
                    u"[... %d diffs stripped ...]\n" % dlen
                ).encode('utf-8'), encoding = 'utf-8'))
        else:
            diff = None # avoid UnboundLocalError if the loop is not run
            asize = parts[0].getSize()
            mcount = len(self.diff_file_list)
            for diff in self.diff_file_list:
                thispart = diff.toMIMEPart()
                asize += thispart.getSize()
                if asize > self.max_notification_size:
                    break
                parts.append(thispart)
                mcount -= 1
            del diff # cleanup
            if mcount:
                parts.append(_SinglePart((
                    u"[... %d diffs stripped ...]\n" % mcount
                ).encode('utf-8'), encoding = 'utf-8'))

        return [_MultiMail(self.getMailSubject(), parts)]


class URLDecorator(object):
    """ Shows only the urls, if the mail gets too long

        @ivar url_fp: The alternative stream
        @type url_fp: file like object

        @ivar do_truncate: truncating mode?
        @type do_truncate: C{bool}

        @ivar max_notification_size: Maximum size of one mail content
        @type max_notification_size: C{int}
    """

    def __init__(self, settings, groupset, maxsize, drop):
        """ Initialization

            @param maxsize: The maximum number of bytes that should be written
                into one mail
            @type maxsize: C{int}

            @param drop: maximum number of mails
            @type drop: C{int}
        """
        self.__super = super(self.__decorator_class, self)
        self.__super.__init__(settings, groupset, maxsize, drop)
        self.max_notification_size = maxsize
        self.do_truncate = False


    def _getMailWriter(self, fp):
        """ Returns a "urling" mail writer """
        import cStringIO
        from svnmailer import stream

        if self.do_truncate:
            fp = stream.TruncatingStream(
                self.__super._getMailWriter(fp),
                self.max_notification_size,
                True
            )
 
        self.url_fp = self.__super._getMailWriter(cStringIO.StringIO())
        return fp


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


    def _getMultiMails(self):
        """ Returns the multipart mail(s)

            @return: The mail(s)
            @rtype: C{list} of C{_MultiMail}
        """
        part0 = _SinglePart(self.fp.getvalue(), encoding = 'utf-8')
        if self.do_truncate and self.fp.getTruncatedLineCount():
            return [_MultiMail(self.getMailSubject(), [part0])]

        diff = None
        asize = part0.getSize()
        diff_sizes = [diff.toMIMEPart().getSize()
            for diff in self.diff_file_list
        ]
        maxsize = sum(diff_sizes, asize)
        del diff

        if maxsize <= self.max_notification_size or not diff_sizes:
            # fine.
            self.url_fp.close()
            return self.__super._getMultiMails()

        if not self.getUrl(self.config):
            self.fp.write(
                u"\n[This mail would be too long, it should contain the "
                u"URLs only, but no browser base url was configured...]\n"
            )
            parts = [_SinglePart(self.fp.getvalue(), encoding = 'utf-8')]
        else:
            self.fp.write(
                u"\n[This mail would be too long, it was shortened to "
                u"contain the URLs only.]\n"
            )
            parts = [_SinglePart(self.fp.getvalue(), encoding = 'utf-8')]

            if self.do_truncate:
                import cStringIO
                from svnmailer import stream
                tfp = stream.TruncatingStream(
                    cStringIO.StringIO(),
                    self.max_notification_size - parts[0].getSize(),
                    True
                )
                tfp.write(self.url_fp.getvalue())
                self.url_fp.close()
                self.url_fp = tfp

            parts.append(
                _SinglePart(self.url_fp.getvalue(), encoding = 'utf-8')
            )

        self.url_fp.close()
        return [_MultiMail(self.getMailSubject(), parts)]


class URLTruncatingDecorator(object):
    """ Truncates url-only mails """

    def __init__(self, settings, groupset, maxsize, drop):
        """ Initialization

            @param maxsize: The maximum number of bytes that should be written
                into one mail
            @type maxsize: C{int}

            @param drop: maximum number of mails
            @type drop: C{int}
        """
        super(self.__decorator_class, self).__init__(
            settings, groupset, maxsize, drop
        )
        self.do_truncate = True


class DiffDescriptor(object):
    """ Container class to describe a dumped diff """

    def __init__(self, notifier, tmpfile, change, propdiff = False):
        """ Initialization

            @param tmpfile: The tempfile the diff was dumped to
            @type tmpfile: C{svnmailer.util.TempFile}

            @param change: The change in question
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @param propdiff: is a property diff?
            @type propdiff: C{bool}
        """
        self.tmpfile  = tmpfile
        self.change   = change
        self.propdiff = propdiff
        self.encoding = None
        self.ctype    = notifier.mctype
        self.dispo    = notifier.mdispo

        if not self.propdiff:
            enc1, enc2 = notifier.getContentEncodings(change, None)
            if enc1 and enc1 == enc2:
                self.encoding = enc1


    def getValue(self):
        """ Returns the diff value

            @return: The value
            @rtype: C{str}
        """
        return file(self.tmpfile.name, 'rb').read()


    def getSize(self):
        """ Returns the size of the diff part

            @return: The size
            @rtype: C{int}
        """
        import os
        return os.stat(self.tmpfile.name).st_size


    def toMIMEPart(self):
        """ Returns the diff as MIME part """
        import posixpath
        ext = self.propdiff and 'propchange' or 'diff'
        name = "%s.%s" % (posixpath.basename(self.change.path), ext)
        enc = (self.propdiff and [None] or [self.encoding])[0]

        part = _SinglePart(self.getValue(),
            name = name, encoding = enc, binary = True, ctype = self.ctype,
            dispo = self.dispo
        )

        return part


from email import MIMEMultipart, MIMENonMultipart
class _MultiMail(MIMEMultipart.MIMEMultipart):
    """ A multimail class """

    def __init__(self, subject, parts):
        """ Initialization

            @param subject: The subject to use
            @type subject: C{str}

            @param parts: The body parts
            @type parts: C{list}
        """
        from email import Header

        MIMEMultipart.MIMEMultipart.__init__(self)
        self['Subject'] = Header.Header(subject, 'iso-8859-1')
        for part in parts:
            self.attach(part)


    def dump(self, fp):
        """ Serializes the mail into a descriptor

            @param fp: The file object
            @type fp: file like object
        """
        from email import Generator

        generator = Generator.Generator(fp, mangle_from_ = False)
        generator.flatten(self, unixfrom = False)


    def update(self, headers):
        """ Update the header set of the mail

            @param headers: The new headers
            @type headers: C{dict}
        """
        for name, value in headers.items():
            self[name] = value


class _SinglePart(MIMENonMultipart.MIMENonMultipart):
    """ A single part of a multipart mail """

    def __init__(self, body, name = None, encoding = None, binary = False,
        ctype = 'text/plain', dispo = 'inline'):
        """ Initialization

            @param body: The body
            @type body: C{str}
        """
        tparam = {}
        dparam = {}
        if name is not None:
            # Deal with RFC 2184 encoding
            name = name.decode('utf-8')
            names = self._encodeRfc2184(name, dosplit = False)

            # safe name
            if names[0] == name:
                tparam['name'] = dparam['filename'] = name.encode('utf-8')

            # encoded simple
            elif len(names) == 1:
                tparam['name*'] = dparam['filename*'] = names[0]

            # encoded and splitted (turned off above [dosplit = False])
            else:
                for idx, name in enumerate(names):
                    tparam['name*%d*' % idx] = name
                    dparam['filename*%d*' % idx] = name

        if encoding is not None:
            tparam['charset'] = encoding

        maintype, subtype = ctype.encode('us-ascii').split('/')
        MIMENonMultipart.MIMENonMultipart.__init__(
            self, maintype, subtype, **tparam
        )
        self.set_payload(body)
        self.add_header('Content-Disposition',
            dispo.encode('us-ascii'), **dparam)
        if binary:
            cte = 'binary'
        else:
            cte = '7bit'
            try:
                body.encode('us-ascii')
            except UnicodeError:
                cte = '8bit'
        self['Content-Transfer-Encoding'] = cte
        del self['MIME-Version']


    def _encodeRfc2184(self, value, dosplit = False):
        """ Encode a string (parameter value) according to RFC 2184

            @param value: The value to encode
            @type value: C{unicode}

            @param dosplit: Allow long parameter splitting? (Note that is not
                widely supported...)
            @type dosplit: C{bool}

            @return: The list of encoded values
            @rtype: C{list}
        """
        encode = False
        try:
            value.encode('us-ascii')
        except UnicodeError:
            encode = True
        else:
            if u'"' in value or (len(value) > 78 and dosplit):
                encode = True

        values = []
        if encode:
            import urllib
            value = "utf-8''%s" % urllib.quote(value.encode('utf-8'))
            if dosplit: # doesn't seem to be supported that much ...
                while len(value) > 78:
                    slen = value[77] == '%' and 80 or (
                        value[76] == '%' and 79 or 78
                    )
                    values.append(value[:slen])
                    value = value[slen + 1:]
        values.append(value)

        return values


    def getSize(self):
        """ Serializes the mail into a descriptor

            @return: The size of the serialized object
            @rtype: C{int}
        """
        from email import Generator
        from svnmailer import stream

        fp = stream.CountStream()
        generator = Generator.Generator(fp, mangle_from_ = False)
        generator.flatten(self, unixfrom = False)

        return fp.size
