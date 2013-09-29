# -*- coding: utf-8 -*-
#
# Copyright 2005-2006 André Malo or his licensors, as applicable
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
notifier selector module
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['Selector']


class Selector(object):
    """ Notifier selector class

        @ivar _settings: The svnmailer settings
        @type _settings: C{svnmailer.settings.Settings}
    """

    def __init__(self, settings):
        """ Initialization

            @param settings: the svnmailer settings
            @type settings: C{svnmailer.settings.Settings}
        """
        self._settings = settings


    def selectNotifiers(self, groupset):
        """ Returns the initialized notifiers for the specified groupset

            @param groupset: The groupset to process
            @type groupset: C{list}

            @return: The notifiers
            @rtype: C{list} of C{svnmailer.notifier.*}
        """
        from svnmailer.notifier import mail, news, cia_xmlrpc

        notifiers = []

        notifiers.extend(mail.getNotifier(self._settings, groupset))
        notifiers.extend(news.getNotifier(self._settings, groupset))
        notifiers.extend(cia_xmlrpc.getNotifier(self._settings, groupset))

        # STDOUT as fallback
        if not notifiers:
            from svnmailer.notifier import stdout
            notifiers.extend(stdout.getNotifier(self._settings, groupset))

        return notifiers
