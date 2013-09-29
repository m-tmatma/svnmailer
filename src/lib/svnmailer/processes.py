# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=F0203,E0201,W0231,W0131
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
Process Handling
================

This module contains a portable class (`Process`) for process creation
with pipes. It has a a quite general character and can be easily used
outside of the svnmailer as well.

The `Process` class uses an implementation which depends on the runtime.
Which implementation is chosen can be determined via the
`Process.IMPLEMENTATION` class variable. These are the possibilities (and
they are tried in this order):

``subprocess``
    The ``subprocess`` module is used. This is available in python 2.4 and
    later by default.

``popen``
    The ``popen2.Popen3`` class is used. This is available in python 2.3 on
    supported platforms (notably Win32 isn't one of them)

``win32api``
    Processes are created using the Win32 API (``CreateProcess`` etc). The
    utilized package is PyWin32_, which is included in *ActivePython* by
    default.

``dumb``
    If none of the above possibilities is available, the ``dumb``
    implementation is chosen. This uses the ``popen*`` functions from the
    ``os`` module. Various combinations of pipe parameter combinations are
    not available in this implementation. ``NotImplementedError`` is
    raised in this case.

.. _PyWin32: http://pywin32.sourceforge.net/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Process']

# global imports
import os, sys

# Choose an implementation based on the runtime
try:
    import subprocess # python >= 2.4
    _implementation = 'subprocess'
except ImportError:
    try:
        import popen2
        if popen2.Popen3:
            if sys.platform == 'win32':
                raise AssertionError("Windows should not have Popen* classes")
            _implementation = 'popen'
    except AttributeError:
        try:
            import win32api, win32con, win32pipe, win32process, win32event, \
                win32file, msvcrt
            if sys.platform != 'win32':
                raise AssertionError("Only Windows should have win32api")
            _implementation = 'win32api'
        except ImportError:
            _implementation = 'dumb'


# Implement the Process class in the chosen way
if _implementation == 'subprocess':
    class ProcessImpl(subprocess.Popen):
        """ Spawn a child with certain attributes

            :CVariables:
             - `WINSHELL`: Does the implementation use a shell on Win32?

            :IVariables:
             - `tochild`: pipe to the child
             - `fromchild`: pipe from the child

            :Types:
             - `WINSHELL`: ``bool``
             - `tochild`: ``file``
             - `fromchild`: ``file``
        """
        WINSHELL = False

        def __init__(self, cmd, pstdin, pstdout, pstderr, detach):
            """ Initialization

                :Parameters:
                 - `cmd`: The command to execute (type must be suitable for
                   the platform)
                 - `pstdin`: Pipe to stdin?
                 - `pstdout`: Pipe from stdout?
                 - `pstderr`: Pipe from stderr (on stdout channel)
                 - `detach`: Detach the process? (evauluated on Win32 only)

                :Types:
                 - `cmd`: ``list`` or ``basestring``
                 - `pstdin`: ``bool``
                 - `pstdout`: ``bool``
                 - `pstderr`: ``bool``
                 - `detach`: ``bool``

                :exception NotImplementedError: not implemented functions
                                                were activated
            """
            if sys.platform == 'win32':
                from svnmailer import util
                cmd = util.filename.toLocale(cmd, force = True)
                # (from http://sourceforge.net/projects/pywin32/)
                # DETACHED_PROCESS = 8
                flags = [0, 8][bool(detach)]
            else:
                flags = 0

            stdin = (pstdin and
                [subprocess.PIPE] or [os.dup(sys.stdin.fileno())])[0]
            stdout = (pstdout and
                [subprocess.PIPE] or [os.dup(sys.stdout.fileno())])[0]
            stderr = (pstderr and
                [subprocess.STDOUT] or [os.dup(sys.stderr.fileno())])[0]

            super(ProcessImpl, self).__init__(cmd,
                stdin  = stdin,
                stdout = stdout,
                stderr = stderr,
                creationflags = flags,
            )

            if not pstdin:
                os.close(stdin)
            if not pstdout:
                os.close(stdout)
            if not pstderr:
                os.close(stderr)

            self.tochild = pstdin and self.stdin or None
            self.fromchild = pstdout and self.stdout or None


        def wait(self):
            """ Waits for child process to terminate.

                The actual ``wait()`` call may happen when the last pipe
                handle is closed (in the dumb implementation).
    
                :return: The exit status
                :rtype: ``int``
            """
            return super(ProcessImpl, self).wait()


elif _implementation == 'popen':
    class ProcessImpl(popen2.Popen3):
        """ Spawn a child with certain attributes

            :CVariables:
             - `WINSHELL`: Does the implementation use a shell on Win32?

            :IVariables:
             - `tochild`: pipe to the child
             - `fromchild`: pipe from the child

            :Types:
             - `WINSHELL`: ``bool``
             - `tochild`: ``file``
             - `fromchild`: ``file``
        """
        WINSHELL = False

        def __init__(self, cmd, pstdin, pstdout, pstderr, detach):
            """ Initialization

                :Parameters:
                 - `cmd`: The command to execute (type must be suitable for
                   the platform)
                 - `pstdin`: Pipe to stdin?
                 - `pstdout`: Pipe from stdout?
                 - `pstderr`: Pipe from stderr (on stdout channel)
                 - `detach`: Detach the process? (evauluated on Win32 only)

                :Types:
                 - `cmd`: ``list`` or ``basestring``
                 - `pstdin`: ``bool``
                 - `pstdout`: ``bool``
                 - `pstderr`: ``bool``
                 - `detach`: ``bool``

                :exception NotImplementedError: not implemented functions
                                                were activated
            """
            detach # pylint. This parameter is ignored
            popen2._cleanup()

            if pstdin:
                p2cread, p2cwrite = os.pipe()
            if pstdout:
                c2pread, c2pwrite = os.pipe()
            self.pid = os.fork()

            # Child
            if self.pid == 0:
                if pstdin:
                    os.dup2(p2cread, 0)
                if pstdout:
                    os.dup2(c2pwrite, 1)
                if pstderr and pstdout:
                    os.dup2(c2pwrite, 2)
                self._run_child(cmd)

            # Parent
            else:
                self.tochild = self.fromchild = None
                if pstdin:
                    os.close(p2cread)
                    self.tochild = os.fdopen(p2cwrite, 'wb', -1)
                if pstdout:
                    os.close(c2pwrite)
                    self.fromchild = os.fdopen(c2pread, 'rb', -1)

                popen2._active.append(self)


        def wait(self):
            """ Waits for child process to terminate.

                The actual ``wait()`` call may happen when the last pipe
                handle is closed (in the dumb implementation).
    
                :return: The exit status
                :rtype: ``int``
            """
            return popen2.Popen3.wait(self)


elif _implementation == 'win32api':
    # This implementation is derived from subprocess.py
    # (python 2.4) and should be used in Python 2.3
    # together with pywin32 (ActivePython should just be fine)

    class ProcessImpl(object):
        """ Spawn a child with certain attributes

            :CVariables:
             - `WINSHELL`: Does the implementation use a shell on Win32?

            :IVariables:
             - `tochild`: pipe to the child
             - `fromchild`: pipe from the child

            :Types:
             - `WINSHELL`: ``bool``
             - `tochild`: ``file``
             - `fromchild`: ``file``
        """
        WINSHELL = False

        def __init__(self, cmd, pstdin = False, pstdout = False,
                     pstderr = False, detach = False):
            """ Initialization

                :Parameters:
                 - `cmd`: The command to execute (type must be suitable for
                   the platform)
                 - `pstdin`: Pipe to stdin?
                 - `pstdout`: Pipe from stdout?
                 - `pstderr`: Pipe from stderr (on stdout channel)
                 - `detach`: Detach the process? (evauluated on Win32 only)

                :Types:
                 - `cmd`: ``list`` or ``basestring``
                 - `pstdin`: ``bool``
                 - `pstdout`: ``bool``
                 - `pstderr`: ``bool``
                 - `detach`: ``bool``

                :exception NotImplementedError: not implemented functions
                                                were activated
            """
            self.tochild = self.fromchild = None
            if pstdin:
                p2cread, p2cwrite = win32pipe.CreatePipe(None, 0)
                self.tochild = os.fdopen(
                    msvcrt.open_osfhandle(p2cwrite.Detach(), 0), 'wb', -1
                )
            else:
                p2cread = win32api.GetStdHandle(win32api.STD_INPUT_HANDLE)
            p2cread = self._dup(p2cread)

            if pstdout:
                c2pread, c2pwrite = win32pipe.CreatePipe(None, 0)
                self.fromchild = os.fdopen(
                    msvcrt.open_osfhandle(c2pread.Detach(), 0), 'rb', -1
                )
            else:
                c2pwrite = win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE)
            c2pwrite = self._dup(c2pwrite)

            errwrite = ((pstderr and pstdout) and [c2pwrite] or
                [win32api.GetStdHandle(win32api.STD_ERROR_HANDLE)])[0]
            errwrite = self._dup(errwrite)

            # start the child
            startupinfo = win32process.STARTUPINFO()
            startupinfo.dwFlags   |= win32process.STARTF_USESTDHANDLES
            startupinfo.hStdInput  = p2cread
            startupinfo.hStdOutput = c2pwrite
            startupinfo.hStdError  = errwrite

            phandle, thandle = win32process.CreateProcess(
                None, cmd, None, None, 1,
                [0, win32con.DETACHED_PROCESS][bool(detach)],
                None, None, startupinfo
            )[:2]

            if detach:
                self._handle = None
                phandle.Close()
            else:
                self._handle = phandle
            thandle.Close()
            win32file.CloseHandle(p2cread)
            win32file.CloseHandle(c2pwrite)
            win32file.CloseHandle(errwrite)


        def wait(self):
            """ Waits for child process to terminate.

                The actual ``wait()`` call may happen when the last pipe
                handle is closed (in the dumb implementation).
    
                :return: The exit status
                :rtype: ``int``
            """
            if self._handle is None:
                return 0

            win32event.WaitForSingleObject(
                self._handle, win32event.INFINITE
            )
            rcode = win32process.GetExitCodeProcess(self._handle)
            self._handle.Close()
            self._handle = None

            return rcode


        def _dup(self, handle):
            """ Returns an inheritable duplicate of handle

                :param handle: The handle to duplicate
                :type handle: handle

                :return: The duplicated handle
                :rtype: handle
            """
            thisprocess = win32api.GetCurrentProcess()
            return win32api.DuplicateHandle(
                thisprocess, handle, thisprocess, 0, 1,
                win32con.DUPLICATE_SAME_ACCESS
            )


else: # _implementation = 'dumb'
    class ProcessImpl(object):
        """ Spawn a child with certain attributes

            :CVariables:
             - `WINSHELL`: Does the implementation use a shell on Win32?

            :IVariables:
             - `tochild`: pipe to the child
             - `fromchild`: pipe from the child

            :Types:
             - `WINSHELL`: ``bool``
             - `tochild`: ``file``
             - `fromchild`: ``file``
        """
        WINSHELL = True

        def __init__(self, cmd, pstdin, pstdout, pstderr, detach):
            """ Initialization

                :Parameters:
                 - `cmd`: The command to execute (type must be suitable for
                   the platform)
                 - `pstdin`: Pipe to stdin?
                 - `pstdout`: Pipe from stdout?
                 - `pstderr`: Pipe from stderr (on stdout channel)
                 - `detach`: Detach the process? (evauluated on Win32 only)

                :Types:
                 - `cmd`: ``list`` or ``basestring``
                 - `pstdin`: ``bool``
                 - `pstdout`: ``bool``
                 - `pstderr`: ``bool``
                 - `detach`: ``bool``

                :exception NotImplementedError: not implemented functions
                                                were activated
            """
            if not pstdin or not pstdout or detach:
                raise NotImplementedError()

            if pstderr:
                self.tochild, self.fromchild = os.popen4(cmd, 'b', -1)
            else:
                self.tochild, self.fromchild = os.popen2(cmd, 'b', -1)


        def wait(self):
            """ Waits for child process to terminate.

                The actual ``wait()`` call may happen when the last pipe
                handle is closed (in the dumb implementation).
    
                :return: The exit status
                :rtype: ``int``
            """
            return 0


class Process(object):
    """ Spawn a child with certain attributes

        :CVariables:
         - `IMPLEMENTATION`: A token describing the chosen implementation.
           Possible tokens are: ``subprocess``, ``popen``, ``win32api``,
           ``dumb``

         - `_IMPLEMENTATION_CLASS`: The class object of the implementation

         - `_SLASHRE`: The substitution regex for backslashes (Win32 only)

         - `_TOKENRE`: The search regex for quotable tokens (Win32 only)

        :IVariables:
         - `tochild`: pipe to the child
         - `fromchild`: pipe from the child
         - `_impl`: The `ProcessImpl` instance

        :Types:
         - `IMPLEMENTATION`: ``str``
         - `_IMPLEMENTATION_CLASS`: ``type`` or ``ClassType``
         - `_SLASHRE`: ``_sre.SRE_Pattern``
         - `_TOKENRE`: ``_sre.SRE_Pattern``
         - `tochild`: ``file``
         - `fromchild`: ``file``
         - `_impl`: `ProcessImpl`
    """
    IMPLEMENTATION = _implementation
    _IMPLEMENTATION_CLASS = ProcessImpl

    def __init__(self, cmd, pstdin = False, pstdout = False, pstderr = False,
                 detach = False):
        """ Initialization

            :Parameters:
             - `cmd`: The command to execute (type must be suitable for
               the platform)
             - `pstdin`: Pipe to stdin?
             - `pstdout`: Pipe from stdout?
             - `pstderr`: Pipe from stderr (on stdout channel)
             - `detach`: Detach the process? (evauluated on Win32 only)

            :Types:
             - `cmd`: ``list`` or ``basestring``
             - `pstdin`: ``bool``
             - `pstdout`: ``bool``
             - `pstderr`: ``bool``
             - `detach`: ``bool``

            :exception NotImplementedError: not implemented functions
                                            were activated
        """
        cls = self._IMPLEMENTATION_CLASS
        cmd = self._escapecmd(cmd, winshell = cls.WINSHELL)

        impl = cls(cmd, pstdin, pstdout, pstderr, detach)
        self.tochild = impl.tochild
        self.fromchild = impl.fromchild
        self._impl = impl


    def pipe2(cls, command):
        """ Returns the process object of a piped process

            The function spawns a command and opens two pipes. One pipe
            is for writing to command's stdin and the other one is for
            reading stdout. stderr is inherited from the caller.

            :param command: The command list (the first item is the command
                itself, the rest represents the arguments)
            :type command: ``list``

            :return: The process object
            :rtype: `Process`
        """
        return cls(command, pstdin = True, pstdout = True)

    pipe2 = classmethod(pipe2)


    def pipe4(cls, command):
        """ Returns the process object of a piped process

            The function spawns a command and opens two pipes. One pipe
            is for writing to command's stdin and the other one is for
            reading stdout + stderr (together)

            :param command: The command list (the first item is the command
                itself, the rest represents the arguments)
            :type command: ``list``

            :return: The process object
            :rtype: `Process`
        """
        return cls(command, pstdin = True, pstdout = True, pstderr = True)

    pipe4 = classmethod(pipe4)


    def detach(cls, command):
        """ Returns the process object of a detached process

            The function spawns a command detached from the current one.
            All std-handles are inherited (no pipe is opened).

            :param command: The command list (the first item is the command
                itself, the rest represents the arguments)
            :type command: ``list``

            :return: The process object
            :rtype: `Process`

            :exception NotImplementedError: Detaching this way is not
                                            implemented on this platform
        """
        return cls(command, detach = True)

    detach = classmethod(detach)


    def wait(self):
        """ Waits for the process to end

            :note: The implementation may define a dummy wait call.
                   The actual waiting happens when the last pipe handle is
                   closed then. This happens if the dumb implementation is
                   used.

            :return: The exit status of the process
            :rtype: ``int``
        """
        return self._impl.wait()


    if sys.platform != 'win32':
        def _escapecmd(self, command, winshell = True):
            winshell # pylint
            return command
    else:
        import re
        _SLASHRE = re.compile(r'(\\+)("|$)')
        _TOKENRE = re.compile(r'["\s]')
        del re

        def _escapecmd(self, command, winshell = True):
            # What we do here is:
            # (1) double up backslashes, but only before quotes or the string
            # end (since we surround it by quotes afterwards)
            # (2) Escape " as "^"" (winshell) or \" (no winshell)
            #     "^"" means "string end", "Escaped quote", "string begin" in
            #     that order
            #     (See also http://www.microsoft.com/technet/archive/winntas
            #               /deploy/prodspecs/shellscr.mspx)

            # Original comments from the svn.fs functions (apply to winshell):
            # ================================================================
            # According cmd's usage notes (cmd /?), it parses the command line
            # by "seeing if the first character is a quote character and if so,
            # stripping the leading character and removing the last quote
            # character." So to prevent the argument string from being changed
            # we add an extra set of quotes around it here.
            #
            # The (very strange) parsing rules used by the C runtime library
            # are described at:
            # http://msdn.microsoft.com/library/en-us/vclang/html
            # /_pluslang_Parsing_C.2b2b_.Command.2d.Line_Arguments.asp

            if winshell:
                cline = '"%s"' % " ".join([
                    '"%s"' % self._SLASHRE.sub(
                        r'\1\1\2', arg
                    ).replace('"', '"^""')
                    for arg in command
                ])
            else:
                cline = " ".join([
                    self._TOKENRE.search(arg)
                        and '"%s"' % self._SLASHRE.sub(
                            r'\1\1\2', arg
                        ).replace('"', '\\"')
                        or  arg
                    for arg in command
                ])

            return cline

    _escapecmd.__doc__ = \
        """ Return the revised command suitable for being exec'd

            Currently this means, it's escaped and converted to a string
            only for Win32, because on this system no list based exec is
            available. For other systems the list is just returned.

            :Parameters:
             - `command`: The command to escape
             - `winshell`: Use shell on windows (cmd.exe)?

            :Types:
             - `command`: ``list``
             - `winshell`: ``bool``

            :return: The escaped command string or the original list
            :rtype: ``str`` or ``list``
        """

del _implementation
