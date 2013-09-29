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
Text based email notifiers (either piped to a program or via SMTP)
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['getNotifier']


def getNotifier(config, groupset):
    """ Returns an initialized notifier or nothing

        @param config: The svnmailer config
        @type config: C{svnmailer.settings.Settings}

        @param groupset: The groupset to process
        @type groupset: C{list}

        @return: The list of notifiers (containing 0 or 1 member)
        @rtype: C{list}
    """
    from svnmailer import settings
    from svnmailer.notifier import _textmail, _multimail

    cls = None
    if config.general.sendmail_command:
        cls = SendmailSubmitter
    elif config.general.smtp_host:
        cls = SMTPSubmitter

    if cls:
        mtype = (groupset.groups[0].mail_type or u'single').split()[0].lower()
        is_commit = (config.runtime.mode == settings.modes.commit)
        mod = (is_commit and mtype == u'multipart') and \
            _multimail or _textmail
        return mod.getNotifier(cls, config, groupset)

    return []


class SMTPSubmitter(object):
    """ Use SMTP to submit the mail """
    _settings = None

    def sendMail(self, sender, to_addr, mail):
        """ Sends the mail via SMTP """
        import smtplib, cStringIO

        fp = cStringIO.StringIO()
        mail.dump(fp)
        mail = fp.getvalue()
        fp.close()

        general = self._settings.general
        conn = smtplib.SMTP(general.smtp_host)
        if general.smtp_user:
            conn.login(general.smtp_user, general.smtp_pass)

        conn.sendmail(sender, to_addr, mail)
        conn.quit()


class SendmailSubmitter(object):
    """ Pipe all stuff to a mailer """
    _settings = None

    def sendMail(self, sender, to_addr, mail):
        """ Sends the mail via a piped mailer """
        from svnmailer import util

        pipe = util.getPipe2(self._getMailCommand(sender, to_addr))
        pipe.fromchild.close() # we don't expect something
        mail.dump(pipe.tochild)
        pipe.tochild.close()

        # what do we do with the return code?
        pipe.wait()


    def _getMailCommand(self, sender, to_addr):
        """ Returns the mailer command

            The command is created using sendmail conventions.
            If you want another commandline, override this method.

            @param sender: The sender address
            @type sender: C{str}

            @param to_addr: The receivers
            @type to_addr: C{list}

            @return: The command
            @rtype: C{list}
        """
        cmd = list(self._settings.general.sendmail_command)
        cmd[1:] = [(isinstance(arg, unicode) and
            [arg.encode("utf-8")] or [arg])[0] for arg in cmd[1:]
        ]
        cmd.extend(['-f', sender])
        cmd.extend(to_addr)

        return cmd
