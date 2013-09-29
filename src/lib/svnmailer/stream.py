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
svnmailer stream objects
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = [
    'UnicodeStream', 'TruncatingStream', 'CuckooStream', 'SplittingStream',
    'DevNullStream', 'BinaryOrUnicodeStream', 'CountStream'
]


class _BaseStream(object):
    """ Base stream wrapper

        @ivar stream: The wrapped stream
        @type stream: file like object
    """

    def __init__(self, stream):
        """ Initialization

            @param stream: The stream to wrap
            @type stream: file like object
        """
        self.stream = stream


    def write(self, towrite):
        """ Writes the data to the stream

            @param towrite: stuff to write
            @type towrite: C{str}
        """
        self.stream.write(towrite)


    def writelines(self, lines):
        r"""Write a list of strings

            @param lines: The lines to write (including \n)
            @type lines: C{list}
        """
        for line in lines:
            self.write(line)


    def close(self):
        """ Closes the stream """
        self.stream.close()


    def __getattr__(self, name):
        """ Delegates all undefined attributes to the stream """
        return getattr(self.stream, name)


class UnicodeStream(_BaseStream):
    """ Stream wrapper, which accepts unicode and a specified charset

        @ivar decode: Decoder function for the input encoding
        @type decode: callable

        @ivar err: error handling advise
        @type err: C{str}
    """

    def __init__(self, stream, in_enc = 'utf-8', out_enc = 'utf-8',
                 errors = "replace"):
        """ Initialization

            @param stream: The stream to wrap
            @type stream: file like object

            @param in_enc: The input encoding, that should be assumed, if a
                pure string is written
            @type in_enc: C{str}

            @param out_enc: The output encoding
            @type out_enc: C{str}

            @param errors: The error handling indicator, when an unicode error
                occurs. (The default is quite lenient and writes replace
                characters on errors)
            @type errors: C{str}
        """
        import codecs

        writer = codecs.lookup(out_enc)[3]
        super(UnicodeStream, self).__init__(writer(stream, errors))

        self.decode = codecs.lookup(in_enc)[1]
        self.err    = errors


    def write(self, towrite):
        """ Write a string or unicode """
        if isinstance(towrite, str):
            super(UnicodeStream, self).write(self.decode(towrite, self.err)[0])
        else:
            super(UnicodeStream, self).write(towrite)


class BinaryOrUnicodeStream(_BaseStream):
    """ Stream wrapper, which accepts unicode or binary data

        Unicode data is converted to UTF-8
    """

    def write(self, towrite):
        """ Write a string or unicode """
        if isinstance(towrite, unicode):
            towrite = towrite.encode('utf-8')

        super(BinaryOrUnicodeStream, self).write(towrite)


class TruncatingStream(_BaseStream):
    """ stream wrapper, which truncates after a limit

        @ivar maxsize: The maximum size in bytes
        @type maxsize: C{int}

        @ivar current: The number of bytes received
        @type current: C{int}

        @ivar trunced: The number of lines truncated (maybe actual-1)
        @type trunced: C{int}

        @ivar lastchar: The last character written
        @type lastchar: C{str}
    """

    def __init__(self, stream, maxsize, add_note = False):
        """ Initialization

            @param stream: The stream to wrap
            @type stream: file like object

            @param maxsize: The maximum size in bytes
            @type maxsize: C{int}
        """
        super(TruncatingStream, self).__init__(stream)

        self.maxsize = maxsize
        self.current = 0
        self.trunced = 0
        self.lastchar = "\n"
        self.add_note = add_note


    def write(self, towrite):
        """ Writes a string up to the limit """
        if self.current <= self.maxsize:
            written = 0
            for line in towrite.splitlines(True):
                self.current += len(line)
                if self.current <= self.maxsize:
                    super(TruncatingStream, self).write(line)
                    written += len(line)
                else:
                    towrite = towrite[written:]
                    break

        if self.current > self.maxsize:
            self.trunced += towrite.count('\n')
            self.lastchar = towrite[-1:]


    def getTruncatedLineCount(self):
        """ Returns the number of truncated lines

            @return: The line count
            @rtype: C{int}
        """
        return self.trunced + (self.lastchar != "\n")


    def writeWithoutTruncation(self, towrite):
        """ Writes without truncation

            @param towrite: The data to write
            @type towrite: C{str}
        """
        super(TruncatingStream, self).write(towrite)


    def seek(self, position, mode = 0):
        """ Sets the file position """
        if mode != 0 or position != 0:
            raise NotImplementedError()

        self.current = 0
        self.trunced = 0
        self.lastchar = "\n"
        self.stream.seek(position, mode)


    def getvalue(self):
        """ Returns the content """
        cont = self.stream.getvalue()
        if self.add_note:
            num = self.getTruncatedLineCount()
            if num:
                cont = "%s\n[... %d lines stripped ...]\n" % (
                    cont, num
                )

        return cont


class TruncatingFileStream(TruncatingStream):
    """ Truncating stream, which writes the truncating note on close """

    def close(self):
        """ Closes the stream """
        if self.add_note:
            num = self.getTruncatedLineCount()
            if num:
                self.writeWithoutTruncation(
                    "\n[... %d lines stripped ...]\n" % num
                )
        super(TruncatingFileStream, self).close()


class CuckooStream(_BaseStream):
    """ Stream wrapper, which provides a method to replace the stream """

    def replaceStream(self, stream):
        """ Replaces the stream with another

            @param stream: The new stream
            @type stream: file like object
        """
        self.stream.close()
        self.stream = stream


class SplittingStream(_BaseStream):
    """ Stream wrapper, which provides the ability to split the stream

        @ivar current: The current byte counter
        @type current: C{int}
    """

    def __init__(self, tempdir = None):
        """ Initialization

            @param tempdir: specific temporary directory
            @type tempdir: C{str}
        """
        import cStringIO
        stream = cStringIO.StringIO()

        super(SplittingStream, self).__init__(stream)

        self.current = 0
        self.tempfiles = []
        self.tempdir = tempdir


    def write(self, towrite):
        """ Writes to the current stream and counts the number of bytes """
        self.current += len(towrite)
        super(SplittingStream, self).write(towrite)


    def split(self):
        """ Splits the stream

            This dumps the current content into a tempfile clears
            the old stream.
        """
        if not self.current:
            return

        from svnmailer import util

        tmpfile = util.TempFile(self.tempdir)
        tmpfile.fp.write(self.getvalue())
        tmpfile.close()
        self.tempfiles.append(tmpfile)
        # begin fresh
        self.current = 0
        self.seek(0)
        self.truncate()


    def close(self):
        """ Closes the stream and removes all tempfiles """
        self.tempfiles = []
        super(SplittingStream, self).close()


    def getPartCount(self):
        """ Returns the number of splitted parts

            @return: The number
            @rtype: C{int}
        """
        return len(self.tempfiles)


    def getPart(self, idx):
        """ Returns the value of part C{idx}

            @param idx: The part number
            @type idx: C{int}

            @return: The content of the particular part
            @rtype: C{str}
        """
        try:
            tmpfile = self.tempfiles[idx]
        except IndexError:
            return ''

        return file(tmpfile.name, 'rb').read()


class DevNullStream(_BaseStream):
    """ Dummy stream, which throws away all data """

    def __init__(self):
        """ Initialization """
        import cStringIO
        super(DevNullStream, self).__init__(cStringIO.StringIO())


    def write(self, towrite):
        """ throw away stuff """
        pass


    def writelines(self, lines):
        """ throw away stuff """
        pass


class CountStream(_BaseStream):
    """ Dummy stream, which throws away all data """

    def __init__(self):
        """ Initialization """
        self.size = 0
        import cStringIO
        super(CountStream, self).__init__(cStringIO.StringIO())


    def write(self, towrite):
        """ throw away stuff and count the number of octets """
        self.size += len(towrite)


    def writelines(self, lines):
        """ write lines """
        for line in lines:
            self.write(line)
