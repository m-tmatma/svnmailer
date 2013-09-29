# -*- coding: utf-8 -*-
# pylint: disable-msg = C0103, W0221
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
Command line interface
======================

The svnmailer provides two different command line interfaces. On the one hand
there's the compatibility command line to the mailer.py script, which has some
limitations and problems because of its unflexibility. On the other hand
you'll find the new-style command line, which contains no subcommands and
fixed parameters at all.

The CLI simply transforms old-style command lines to the new format internally
and processes these further using the optparse module::

    svn-mailer commit <rep> <rev> [<config>]
 -> svn-mailer --commit --repository <rep> --revision <rev>
              [--config <config>]

    svn-mailer propchange <rep> <rev> <author> <prop> [<conf>]
 -> svn-mailer --propchange --repository <rep> --revision <rev>
               --author <author> --propname <prop>
              [--config <conf>]

    # (useful with svn 1.2 and later)
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
__docformat__ = "epytext en"
__all__       = ['getOptions', 'CommandlineError']

# global imports
import optparse

# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class CommandlineError(Error):
    """ Error in commandline """
    pass


def getOptions(argv = None):
    """ Parse commandline options

        @param argv: Command line list. If argv is None,
            sys.argv[1:] is evaluated instead
        @type argv: C{list}

        @return: option object
        @rtype: C{optparse.OptionParser}

        @exception CommandlineError: Error in command line options
    """
    from svnmailer import util
    from svnmailer.settings import modes

    usage = """%prog <options>"""
    parser = SvnmailerOptionParser(usage = usage, version = True)
    options, args = parser.parse_args(argv)

    # Check parameter consistency
    if args:
        raise CommandlineError("Too much arguments")

    if not options.repository:
        raise CommandlineError("Missing repository path")

    if not options.revision:
        if options.mode in (modes.commit, modes.propchange):
            raise CommandlineError("Missing revision number")

    if not options.author:
        if options.mode in (modes.propchange, modes.lock, modes.unlock):
            raise CommandlineError("Missing author parameter")

    if not options.propname:
        if options.mode == modes.propchange:
            raise CommandlineError("Missing property name parameter")

    # de-localize the paths
    try:
        options.repository = util.filename.fromLocale(
            options.repository, options.path_encoding
        )
    except UnicodeError, exc:
        raise CommandlineError("--repository recode problem: %s" % str(exc))

    if options.config:
        try:
            options.config = util.filename.fromLocale(
                options.config, options.path_encoding
            )
        except UnicodeError, exc:
            raise CommandlineError("--config recode problem: %s" % str(exc))

    return options


class SvnmailerOptionParser(optparse.OptionParser):
    """ Fully initialized option parser

        @ivar _svn: The svn version
        @type _svn: C{tuple}
    """

    def __init__(self, *args, **kwargs):
        """ Initialization """
        from svnmailer import subversion

        self._svn = subversion.version
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self._initSvnmailer()


    def parse_args(self, args = None, *other_args, **kwargs):
        """ Accepts also the old command line """
        args = self._transformSvnmailerOldStyle(args)
        if not args:
            raise CommandlineError(
                "Type '%s --help' for usage" % self.get_prog_name()
            )

        options, fixed = optparse.OptionParser.parse_args(
            self, args, *other_args, **kwargs
        )

        # fixup action attribute (expected later)
        if not self._svn.min_1_2:
            options.action = None

        return (options, fixed)


    def error(self, msg):
        """ We raise an exception instead of exiting

            @param msg: The error message
            @type msg: C{str}

            @exception CommandlineError: command line error
        """
        raise CommandlineError(str(msg))


    def get_version(self):
        """ Returns the version string """
        from svnmailer import version

        return "svnmailer-%s\nwith svn %d.%d.%d%s" % (
            version, self._svn.major, self._svn.minor, self._svn.patch,
            self._svn.tag
        )


    def get_prog_name(self):
        """ Returns the program name """
        try:
            # >= python 2.4
            return optparse.OptionParser.get_prog_name(self)
        except AttributeError:
            try:
                # >= python 2.3.4
                return optparse.OptionParser._get_prog_name(self)
            except AttributeError:
                # <= python 2.3.3
                if self.prog:
                    return self.prog
                else:
                    import os, sys
                    return os.path.basename(sys.argv[0])


    def format_help(self, formatter = None):
        """ Adds a description of the old style options """
        import textwrap

        width = (self._getTerminalWidth() or 80) - 1
        optionhelp = None
        while optionhelp is None:
            try:
                formatter = optparse.IndentedHelpFormatter(width = width)
                optionhelp = optparse.OptionParser.format_help(self, formatter)
            except ValueError:
                # terminal too small *sigh*
                if width < 79:
                    width = 79
                else:
                    width += 10

        oldstyle = textwrap.fill(
            "Alternatively you can use the old style compatibility "
            "command lines (options described above don't apply then):",
            width = width,
        )

        prog = self.get_prog_name()
        indent = " " * (len(prog) + 1)
        clines = [
            "",
            "%(prog)s commit <repos> <revision> [<config>]",
            "%(prog)s propchange <repos> <revision> <author> <propname> "
                     "[<config>]",
        ]
        if self._svn.min_1_2:
            clines.extend([
                "",
                "svn 1.2 and later:",
                "%(prog)s propchange2 <repos> <revision> <author> <propname> "
                         "<action> [<config>]",
                "%(prog)s lock <repos> <author> [<config>]",
                "%(prog)s unlock <repos> <author> [<config>]",
            ])
        clines = ["%s\n" % textwrap.fill(
            line % {'prog': prog}, width = width, subsequent_indent = indent
        ) for line in clines]

        return "%s\n%s\n%s" % (optionhelp, oldstyle, ''.join(clines))


    def _getTerminalWidth(self):
        """ Returns terminal width if determined, None otherwise

            @return: The width
            @rtype: C{int}
        """
        try:
            import errno, fcntl, struct, sys, termios

            def getwidth(fd):
                """ Returns the width for descriptor fd """
                # struct winsize { /* on linux in asm/termios.h */
                #     unsigned short ws_row;
                #     unsigned short ws_col;
                #     unsigned short ws_xpixel;
                #     unsigned short ws_ypixel;
                # }
                return struct.unpack("4H", fcntl.ioctl(
                    fd, termios.TIOCGWINSZ, struct.pack("4H", 0, 0, 0, 0)
                ))[1]

            try:
                return getwidth(sys.stdout.fileno())
            except IOError, exc:
                if exc[0] == errno.EINVAL:
                    return getwidth(sys.stdin.fileno())
                raise # otherwise

        except (SystemExit, KeyboardInterrupt):
            raise

        except:
            # don't even ignore
            pass

        return None


    def _initSvnmailer(self):
        """ Builds the options from option groups """
        self._addSvnmailerCommonOptions()
        self._addSvnmailerBehaviourOptions()
        self._addSvnmailerSupplementalOptions()


    def _addSvnmailerCommonOptions(self):
        """ Adds the common options group """
        common_options = optparse.OptionGroup(
            self, 'COMMON PARAMETERS'
        )
        common_options.add_option('--debug',
            action = 'store_true',
            default = False,
            help = "Run in debug mode (means basically that all messages "
                "are sent to STDOUT)",
        )
        common_options.add_option('-d', '--repository',
            help = 'The repository directory',
        )
        common_options.add_option('-f', '--config',
            help = 'The configuration file',
        )
        common_options.add_option('-e', '--path-encoding',
            help = 'Specifies the character encoding to be used for '
                'filenames. By default the encoding is tried to be '
                'determined automatically depending on the locale.'
        )
        self.add_option_group(common_options)


    def _addSvnmailerBehaviourOptions(self):
        """ Adds the behaviour options group """
        from svnmailer.settings import modes

        behaviour_options = optparse.OptionGroup(
            self, 'BEHAVIOUR OPTIONS',
            description = "The behaviour options are mutually exclusive, "
                "i.e. the last one wins."
        )
        behaviour_options.add_option('-c', '--commit',
            dest = 'mode',
            action = 'store_const',
            const = modes.commit,
            default = modes.commit,
            help = 'This is a regular commit of versioned data '
                   '(post-commit hook). This is default.',
        )
        behaviour_options.add_option('-p', '--propchange',
            dest = 'mode',
            action = 'store_const',
            const = modes.propchange,
            help = 'This is a modification of unversioned properties '
                '(post-revprop-change hook)',
        )

        if self._svn.min_1_2:
            behaviour_options.add_option('-l', '--lock',
                dest = 'mode',
                action = 'store_const',
                const = modes.lock,
                help = '(svn 1.2 and later) This is a locking call '
                    '(post-lock hook)',
            )
            behaviour_options.add_option('-u', '--unlock',
                dest = 'mode',
                action = 'store_const',
                const = modes.unlock,
                help = '(svn 1.2 and later) This is a unlocking call '
                    '(post-unlock hook)',
            )

        self.add_option_group(behaviour_options)


    def _addSvnmailerSupplementalOptions(self):
        """ Adds the supplemental options """
        supp_options = optparse.OptionGroup(
            self, 'SUPPLEMENTAL PARAMETERS'
        )
        
        supp_options.add_option('-r', '--revision',
            action = 'store',
            type = 'int',
            help = 'The modified/committed revision number',
        )
        supp_options.add_option('-a', '--author',
            help = 'The author of the modification',
        )
        supp_options.add_option('-n', '--propname',
            help = 'The name of the modified property',
        )

        if self._svn.min_1_2:
            supp_options.add_option('-o', '--action',
                help = '(svn 1.2 and later) The property change action',
            )

        self.add_option_group(supp_options)


    def _transformSvnmailerOldStyle(self, argv):
        """ Parses the command line according to old style rules

            @param argv: Command line list. If argv is None,
                sys.argv[1:] is evaluated instead
            @type argv: C{list}

            @return: The commandline, possibly transformed to new style
            @rtype: C{list}
        """
        if argv is None:
            import sys
            argv = sys.argv[1:]

        if argv:
            length = len(argv)

            # svn-mailer commit <rep> <rev> [<conf>]
            if argv[0] == "commit" and 3 <= length <= 4:
                config = argv[3:]
                argv = ["--commit",
                        "--repository", argv[1], "--revision", argv[2],
                ]
                if config:
                    argv.extend(["--config", config[0]])

            # svn-mailer propchange <rep> <rev> <author> <prop> [<conf>]
            elif argv[0] == "propchange" and 5 <= length <= 6:
                config = argv[5:]
                argv = ["--propchange",
                        "--repository", argv[1], "--revision", argv[2],
                        "--author", argv[3], "--propname", argv[4],
                ]
                if config:
                    argv.extend(["--config", config[0]])

            else:
                if self._svn.min_1_2:
                    # svn-mailer propchange2 <rep> <rev> <author> <prop> <act>
                    #            [<conf>]
                    if argv[0] == "propchange2" and 6 <= length <= 7:
                        config = argv[6:]
                        argv = ["--propchange",
                                "--repository", argv[1], "--revision", argv[2],
                                "--author", argv[3], "--propname", argv[4],
                                "--action", argv[5],
                        ]
                        if config:
                            argv.extend(["--config", config[0]])

                    # svn-mailer lock <rep> <author> [<conf>]
                    # svn-mailer unlock <rep> <author> [<conf>]
                    elif argv[0] in ("lock", "unlock") and 3 <= length <= 4:
                        config = argv[3:]
                        argv = ["--%s" % argv[0],
                                "--repository", argv[1], "--author", argv[2]
                        ]
                        if config:
                            argv.extend(["--config", config[0]])

        return argv
