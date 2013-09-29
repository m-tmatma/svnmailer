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
Text based news notifier (via NNTP)
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['getNotifier']


def getNotifier(settings, groupset):
    """ Returns an initialized notifier or nothing

        @param settings: The svnmailer settings
        @type settings: C{svnmailer.settings.Settings}

        @param groupset: The groupset to process
        @type groupset: C{list}

        @return: The list of notifiers (containing 0 or 1 member)
        @rtype: C{list}
    """
    from svnmailer.notifier import _textnews

    cls = None
    if settings.general.nntp_host:
        cls = NNTPSubmitter

    if cls:
        return _textnews.getNotifier(cls, settings, groupset)

    return []


class NNTPSubmitter(object):
    """ Use NNTP to submit the notification as news article """
    _settings = None

    def sendNews(self, posting):
        """ Sends the posting via nntp """
        import cStringIO, nntplib

        fp = cStringIO.StringIO()
        try:
            posting.dump(fp)
            fp.seek(0)

            general = self._settings.general
            host, port = (general.nntp_host, nntplib.NNTP_PORT)
            if ':' in host and host.find(':') == host.rfind(':'):
                host, port = host.split(':', 1)

            conn = nntplib.NNTP(
                host = host, port = int(port), readermode = True,
                user = general.nntp_user, password = general.nntp_pass,
            )
            conn.post(fp)
            conn.quit()
        finally:
            fp.close()
