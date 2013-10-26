# -*- coding: utf-8 -*-
# pylint-version = 0.7.0
#
# Copyright 2005 André Malo or his licensors, as applicable
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
Chora_ repository browser URL construction

.. _`Chora`: http://horde.org/chora/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Generator']

# global imports
import posixpath
from svnmailer.browser import _base


class Generator(_base.BaseGenerator):
    """ Chora_ template generator

        .. _`Chora`: http://horde.org/chora/

        :cvar `_SESSIONNAME`: The name of the session id query parameter
        :type `_SESSIONNAME`: ``str``
    """
    _SESSIONNAME = u"Horde"

    def _createTemplate(self, base_url, config):
        """ Returns Chora URL templates """
        config # pylint

        url = self._createParsedUrl(base_url)
        url.query.remove([self._SESSIONNAME, u'tr1', u'tr2'])
        dirname, basename = posixpath.split(url.path)
        if basename:
            url.path = dirname
        join = posixpath.join

        tpl = {
            # no revision overview, just browse the root
            'revision': (basename or None, {'remove': [
                u'r', u'r1', u'r2', u'ty', u'num', u'ws'
            ]}),

            'deleted': (join(u"co.php", self._BASE_PATH), {
                'remove': [u'r1', u'r2', u'ty', u'num', u'ws'],
                'set': [(u'r', self._BASE_REVISION)]
            }),

            'deleted_dir': (join(basename, self._BASE_PATH, u""), {
                'remove': [u'r1', u'r2', u'ty', u'num', u'ws'],
                'set': [(u'r', self._BASE_REVISION)]
            }),

            'added': (join(u"co.php", self._PATH), {
                'remove': [u'r1', u'r2', u'ty', u'num', u'ws'],
                'set': [(u'r', self._REVISION)]
            }),

            'added_dir': (join(basename, self._PATH, u""), {
                'remove': [u'r1', u'r2', u'ty', u'num', u'ws'],
                'set': [(u'r', self._REVISION)]
            }),

            'modified': (join(u"diff.php", self._PATH), {
                'remove': [u'r', u'p'],
                'set': [
                    (u'r1', self._BASE_REVISION),
                    (u'r2', self._REVISION),
                ]
            }),
        }
        # not capable of copy diffs
        tpl['copied'] = tpl['added']

        return _base.Template.fromTemplates(url, tpl)
