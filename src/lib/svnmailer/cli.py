# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
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
========================
 Command line interface
========================

The svnmailer provides two different command line interfaces. On the one hand
there's the compatibility command line to the `mailer.py script`_, which has
some limitations and problems because of its unflexibility. On the other hand
you'll find the new-style command line, which contains no subcommands and
fixed parameters at all.

.. _mailer.py script:
   http://svn.collab.net/viewcvs/svn/trunk/tools/hook-scripts/mailer/mailer.py

The CLI simply transforms old-style command lines to the new format internally
and processes these further using the optparse module::

    svn-mailer commit <rep> <rev> [<config>]
 -> svn-mailer --commit --repository <rep> --revision <rev>
              [--config <config>]

    svn-mailer propchange <rep> <rev> <author> <prop> [<conf>]
 -> svn-mailer --propchange --repository <rep> --revision <rev>
               --author <author> --propname <prop>
              [--config <conf>]

    # (available with svn 1.2 and later)
    svn-mailer propchange2 <rep> <rev> <author> <prop> <action> [<conf>]
 -> svn-mailer --propchange --repository <rep> --revision <rev>
               --author <author> --propname <prop> --action <action>
              [--config <conf>]

    svn-mailer lock <rep> <author> [<conf>]
 -> svn-mailer --lock --repository <rep> --author <author>
              [--config <conf>]

    svn-mailer unlock <rep> <author> [<conf>]
 -> svn-mailer --unlock --repository <rep> --author <author>
              [--config <conf>]
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Error', 'CommandlineError', 'OptionParser']

# global imports
import optparse, os, sys, warnings
from svnmailer import util, settings, subversion

# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class CommandlineError(Error):
    """ Error in commandline """
    pass


class OptionParser(optparse.OptionParser): # old style
    """ Fully initialized option parser

        :ivar `_svnmailer_helper`: The option parser helper instance
        :type `_svnmailer_helper`: ``OptionHelper``
    """

    def __init__(self, background = True):
        """ Initialization

            :param `background`: Is daemonizing of the process allowed?
            :type `background`: ``bool``

            @exception CommandlineError: The argument list was empty
        """
        optparse.OptionParser.__init__(self,
            prog = "<prog>", usage = "1", version = "2"
        )
        self._svnmailer_helper = self._createSvnmailerOptionHelper(background)


    def parseArgs(self, *args, **kwargs):
        """ Parses the argument list

            :param `args`: Additional arguments for the parser
            :param `kwargs`: Additional arguments for the parser

            :return: The ``OptionContainer`` instance
            :rtype: ``optparse.OptionContainer``

            :exception CommandlineError: The argument list was invalid
        """
        helper = self._svnmailer_helper

        return helper.fixUp(optparse.OptionParser.parse_args(self,
            helper.args, *args, **kwargs
        ))


    def error(self, msg):
        """ We raise an exception instead of calling ``sys.exit``

            :param msg: The error message
            :type msg: ``str``

            :exception CommandlineError: command line error
        """
        raise CommandlineError(str(msg))


    def get_version(self):
        """ Returns the version string

            The string consists of two lines. The first line contains the
            svnmailer version (like ``svnmailer-1.2.3``) and the second line
            contains the svn version propagated by the bindings (like
            ``with svn 4.5.6 (revision 7)``)

            :return: The version string
            :rtype: ``str``
        """
        from svnmailer import version

        svn = subversion.version
        return "svnmailer-%s\nwith svn %d.%d.%d%s" % (
            version.string, svn.major, svn.minor, svn.patch, svn.tag
        )


    def get_usage(self):
        """ Returns the usage string

            :return: The usage string
            :rtype: ``str``
        """
        return "Usage: %s <options>\n" % self.get_prog_name()


    def get_prog_name(self):
        """ Returns the program name

            :return: The program name
            :rtype: ``str``
        """
        return self.prog

    _get_prog_name = get_prog_name # 2.3.4 <= python < 2.4.0


    def format_help(self, formatter = None):
        """ Returns the formatted help string

            The string consists of the normal option help generated by
            the optparse module and a short description of the old style
            options. All text is tried to be wrapped to fit into the
            current terminal width.

            :param formatter: unused
            :type formatter: any

            :return: The formatted help string
            :rtype: ``str``
        """
        formatter # pylint

        # determine possible with
        width = (util.terminal.getWidth() or 80) - 1
        optionhelp = None
        while optionhelp is None:
            formatter = self._createHelpFormatter(width = width)
            try:
                optionhelp = optparse.OptionParser.format_help(self, formatter)
            except ValueError:
                # terminal too small
                if width < 79:
                    width = 79
                else:
                    width += 10

        oldstyle = self._svnmailer_helper.formatOldStyle(width)
        return "%s\n%s" % (optionhelp, oldstyle)


    def _createSvnmailerOptionHelper(self, background):
        """ Returns the option parser helper class

            We delegate additional operations to an extra class in order
            to not pollute the OptionParser namespace which changes all
            the time.

            :param background: Is daemonizing of the process allowed?
            :type background: ``bool``

            :return: A new OptionHelper instance
            :rtype: `OptionHelper`
        """
        return OptionHelper(self, background)


    def _createHelpFormatter(self, *args, **kwargs):
        """ Returns the option helper formatter

            :param args: Arguments for the formatter
            :param kwargs: Arguments for the formatter

            :return: The formatter instance
            :rtype: ``optparse.IndentedHelpFormatter``
        """
        return optparse.IndentedHelpFormatter(*args, **kwargs)


class OptionHelper(object):
    """ Option parser helper class

        Additional operations are delegated to this class in order
        to not pollute the OptionParser namespace which changes all
        the time.

        :Groups:
         - `Titles`: `_COMMON_TITLE`, `_BEHAVIOR_TITLE`, `_SUPPLEMENTAL_TITLE`
         - `Constraints`: `_PATH_OPTIONS`, `_REQUIRED_OPTIONS`
         - `Mapping Tables`: `_OLD_OPTIONS`, `_OLD_OPTIONS_1_2`

        :CVariables:
         - `_COMMON_TITLE`: Title of the common option group

         - `_BEHAVIOR_TITLE`: Title of the behavior option group

         - `_SUPPLEMENTAL_TITLE`: Title of the supplemental option group

         - `_PATH_OPTIONS`: List of option attributes that need to be
           treated as localized paths. Every entry is a tuple consisting of
           the option attribute name the option name for the error message.
           (``(('name', 'option'), ...)``)

         - `_REQUIRED_OPTIONS`: List of option attributes that are required
           under certain circumstances. Every entry is a tuple consisting of
           the option attribute name, the list of mailer modes (or ``None``
           for all modes) and an error text hint.
           (``(('name', (mode, ...), 'text'), ...)``)

         - `_OLD_OPTIONS`: Mapping table for old style command lines (< svn
           1.2)

         - `_OLD_OPTIONS_1_2`: Mapping table for old style command lines (>=
           svn 1.2 only)

         - `_WIN32_BG_ARG`: fixed argument which is appended to the command
           line of the background process on Win32

        :IVariables:
         - `args`: The argument list to parse
         - `_parser`: The `OptionParser` instance
         - `_background`: Is daemonizing of the process allowed?

        :Types:
         - `_COMMON_TITLE`: ``str``
         - `_BEHAVIOR_TITLE`: ``str``
         - `_SUPPLEMENTAL_TITLE`: ``str``
         - `_PATH_OPTIONS`: ``tuple``
         - `_REQUIRED_OPTIONS`: ``tuple``
         - `_OLD_OPTIONS`: ``dict``
         - `_OLD_OPTIONS_1_2`: ``dict``
         - `_WIN32_BG_ARG`: ``str``

         - `args`: ``list``
         - `_parser`: `OptionParser`
         - `_background`: ``bool``
    """
    _WIN32_BG_ARG = "bg-process"

    _COMMON_TITLE = "COMMON PARAMETERS"
    _BEHAVIOR_TITLE = "BEHAVIOR OPTIONS"
    _SUPPLEMENTAL_TITLE = "SUPPLEMENTAL PARAMETERS"

    _PATH_OPTIONS = (('repository', '--repository'), ('config', '--config'))
    m = settings.MODES
    _REQUIRED_OPTIONS = (
        ('repository', None, 'repository path'),
        ('revision', (m.commit, m.propchange), 'revision number'),
        ('author', (m.propchange, m.lock, m.unlock), 'author parameter'),
        ('propname', (m.propchange,), 'property name parameter'),
    )
    del m

    _OLD_OPTIONS = {
        # svn-mailer commit <rep> <rev> [<cnf>]
        "commit": ("--commit", "--repository", "--revision", "--config"),

        # svn-mailer propchange <rep> <rev> <author> <prop> [<cnf>]
        "propchange": ("--propchange", "--repository", "--revision",
            "--author", "--propname", "--config"),
    }
    _OLD_OPTIONS_1_2 = {
        # svn-mailer propchange2 <rep> <rev> <author> <prop> <act> [<cnf>]
        "propchange2": ("--propchange", "--repository", "--revision",
            "--author", "--propname", "--action", "--config"),

        # svn-mailer lock <rep> <author> [<cnf>]
        "lock": ("--lock", "--repository", "--author", "--config"),

        # svn-mailer unlock <rep> <author> [<cnf>]
        "unlock": ("--unlock", "--repository", "--author", "--config"),
    }

    def __init__(self, parser, background):
        """ Initialization

            :Parameters:
             - `parser`: The `OptionParser` instance
             - `background`: Is daemonizing of the process allowed?

            :Types:
             - `parser`: `OptionParser`
             - `background`: ``bool``

            :exception CommandlineError: The argument list is empty
        """
        self._parser = parser
        self._background = background

        parser.prog = os.path.basename(sys.argv[0])
        self.args = self._transformArgs(sys.argv[1:])
        self._addOptions()


    def fixUp(self, (options, fixed)):
        """ Fixes up the parsed option to match the needs of the mailer

            :Parameters:
             - `options`: The ``OptionContainer`` instance
             - `fixed`: The list of fixed arguments

            :Types:
             - `options`: ``optparse.OptionContainer``
             - `fixed`: ``list``

            :return: The final ``OptionContainer`` instance
            :rtype: ``optparse.OptionContainer``

            :exception CommandlineError: The options are not suitable
        """
        # Check parameter consistency
        length = len(fixed)
        if length > 0:
            # HACK ALERT! somehow.
            if options.background and list(fixed) == [self._WIN32_BG_ARG]:
                self._background = False
            else:
                raise CommandlineError("Too much arguments")

        # fixup action attribute for svn < 1.2
        if not subversion.version.min_1_2:
            options.action = None

        self._ensureRequired(options)
        self._delocalize(options)

        return self._handleBackground(options)


    def formatOldStyle(self, width):
        """ Returns the formatted old style help

            :param `width`: Maximum width of the text
            :type `width`: ``int``

            :return: The formatted help text
            :rtype: ``str``
        """
        import textwrap
        wrapper = textwrap.TextWrapper(width = width)

        oldstyle = wrapper.fill(
            "Alternatively you can use the old style compatibility "
            "command lines (options described above don't apply then):",
        )

        prog = self._parser.get_prog_name()
        clines = [
            "",
            "%(prog)s commit <repos> <revision> [<config>]",
            "%(prog)s propchange <repos> <revision> <author> <propname> "
                     "[<config>]",
        ]
        if subversion.version.min_1_2:
            clines.extend([
                "",
                "svn 1.2 and later:",
                "%(prog)s propchange2 <repos> <revision> <author> <propname> "
                         "<action> [<config>]",
                "%(prog)s lock <repos> <author> [<config>]",
                "%(prog)s unlock <repos> <author> [<config>]",
            ])

        wrapper.subsequent_indent = " " * (len(prog) + 1)
        return "%s\n%s\n" % (oldstyle, '\n'.join([
            wrapper.fill(line % {'prog': prog}) for line in clines
        ]))


    def _handleBackground(self, options):
        """ Evaluates the ``--background`` option

            If daemonizing is not allowed, this method is a noop at all.

            Otherwise the behaviour depends on the platform:

            POSIX systems
                The process just ``fork``\s into the background and detaches
                from the controlling terminal (calls ``setsid(2)``). The
                parent process is exited immediately with return code ``0``.

            Win32/64 systems
                The process spawns itself again (flagged to be detached),
                using ``sys.executable`` and ``sys.argv``. `_WIN32_BG_ARG`
                is added as a fixed parameter to let the spawned process
                know that is does not need to spawn again. If this worked,
                the parent process exits with ``0``. As I don't know if this
                works on all Windows systems as desired, this feature is
                marked experimental on these platforms.

            :param `options`: option container
            :type `options`: ``optparse.OptionContainer``
        """
        if options.background and self._background:
            try:
                import signal
                signal.signal(signal.SIGHUP, signal.SIG_IGN)

                if os.setsid and os._exit: # try existance before the fork
                    pid = os.fork()
                    if pid == 0:
                        pid = os.fork() # no zombies
                    if pid > 0:
                        os._exit(0)
                    else:
                        os.setsid() # detach
            except OSError, exc:
                warnings.warn(
                    "svnmailer: OSError while detaching from foreground: %s" %
                    str(exc)
                )
            except (AttributeError, ImportError):
                msg = "svnmailer: --background is not implemented on this " \
                    "platform"

                if sys.platform != "win32":
                    warnings.warn(msg)
                else:
                    # Is there a better way to hide in the background?
                    from svnmailer import processes

                    args = [sys.executable] + list(sys.argv) + \
                        [self._WIN32_BG_ARG]
                    try:
                        processes.Process.detach(args)
                        os._exit(0)
                    except NotImplementedError:
                        warnings.warn(msg)

        return options


    def _delocalize(self, options):
        """ Delocalizes the supplied paths

            :param `options`: The options to consider
            :type `options`: ``optparse.OptionContainer``

            :exception CommandlineError: Something went wrong
        """
        for attrname, name in self._PATH_OPTIONS:
            attr = getattr(options, attrname)
            if attr:
                try:
                    attr = util.filename.fromLocale(
                        attr, options.path_encoding
                    )
                except UnicodeError, exc:
                    raise CommandlineError(
                        "%s recode problem: %s" % (name, str(exc))
                    )
                setattr(options, attrname, attr)


    def _ensureRequired(self, options):
        """ Ensures that all required options are present

            :param `options`: The options to consider
            :type `options`: ``optparse.OptionContainer``

            :exception CommandlineError: At least one option is missing
        """
        for attrname, modes, errtext in self._REQUIRED_OPTIONS:
            if not getattr(options, attrname):
                if modes is None or options.mode in modes:
                    raise CommandlineError("Missing %s" % errtext)


    def _addOptions(self):
        """ Adds the possible options to the parser """
        self._addCommonOptions()
        self._addBehaviorOptions()
        self._addSupplementalOptions()


    def _addCommonOptions(self):
        """ Adds the common options group """
        group = self._parser.add_option_group(self._COMMON_TITLE)

        group.add_option('--debug',
            action = 'store_true',
            default = False,
            help = "Run in debug mode (means basically that all messages "
                "are sent to STDOUT)",
        )
        group.add_option('-d', '--repository',
            help = 'The repository directory',
        )
        group.add_option('-f', '--config',
            help = 'The configuration file',
        )
        group.add_option('-e', '--path-encoding',
            help = 'Specifies the character encoding to be used for '
                'filenames. By default the encoding is tried to be '
                'determined automatically depending on the locale.'
        )
        group.add_option('-b', '--background',
            action = 'store_true',
            default = False,
            help = 'Lets the mailer do its work in the background. That '
                'way the hook script can exit faster.'
        )


    def _addBehaviorOptions(self):
        """ Adds the behavior options group """
        mode = settings.MODES

        group = self._parser.add_option_group(self._BEHAVIOR_TITLE,
            description = "The behavior options are mutually exclusive, "
                "i.e. the last one wins."
        )
        group.add_option('-c', '--commit',
            dest = 'mode',
            action = 'store_const',
            const = mode.commit,
            default = mode.commit,
            help = 'This is a regular commit of versioned data '
                   '(post-commit hook). This is default.',
        )
        group.add_option('-p', '--propchange',
            dest = 'mode',
            action = 'store_const',
            const = mode.propchange,
            help = 'This is a modification of unversioned properties '
                '(post-revprop-change hook)',
        )

        if subversion.version.min_1_2:
            group.add_option('-l', '--lock',
                dest = 'mode',
                action = 'store_const',
                const = mode.lock,
                help = '(svn 1.2 and later) This is a locking call '
                    '(post-lock hook)',
            )
            group.add_option('-u', '--unlock',
                dest = 'mode',
                action = 'store_const',
                const = mode.unlock,
                help = '(svn 1.2 and later) This is a unlocking call '
                    '(post-unlock hook)',
            )


    def _addSupplementalOptions(self):
        """ Adds the supplemental options """
        group = self._parser.add_option_group(self._SUPPLEMENTAL_TITLE)

        group.add_option('-r', '--revision',
            action = 'store',
            type = 'int',
            help = 'The modified/committed revision number',
        )
        group.add_option('-a', '--author',
            help = 'The author of the modification',
        )
        group.add_option('-n', '--propname',
            help = 'The name of the modified property',
        )

        if subversion.version.min_1_2:
            group.add_option('-o', '--action',
                help = '(svn 1.2 and later) The property change action',
            )


    def _transformArgs(self, args):
        """ Parses the command line according to old style rules

            :param args: The argument list (``['arg', 'arg', ...]``)
            :type args: ``list``

            :return: The argument, possibly transformed to new style
                     (``['arg', 'arg', ...]``)
            :rtype: ``list``

            :exception CommandlineError: The argument list is empty
        """
        length = len(args)
        if length == 0:
            raise CommandlineError(
                "Type '%s --help' for usage" % self._parser.get_prog_name()
            )

        mode = args[0]
        names = self._OLD_OPTIONS.get(mode)
        if names is None and subversion.version.min_1_2:
            names = self._OLD_OPTIONS_1_2.get(mode)

        if names is not None:
            lmax = len(names)
            lmin = lmax - 1
            if lmin <= length <= lmax:
                newlist = [names[0]]
                for idx, arg in enumerate(args):
                    if idx:
                        newlist.extend([names[idx], arg])
                args = newlist

        return args
