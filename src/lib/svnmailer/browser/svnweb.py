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
`SVN::Web`_ repository browser URL construction

.. _`SVN::Web`: http://freshmeat.net/projects/svnweb/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Generator']

# global imports
import posixpath
from svnmailer.browser import _base


class Generator(_base.BaseGenerator):
    """ `SVN::Web`_ template generator

        .. _`SVN::Web`: http://freshmeat.net/projects/svnweb/
    """

    def _createTemplate(self, base_url, config):
        """ Returns SVN::Web URL templates """
        config # pylint

        url = self._createParsedUrl(base_url)
        join = posixpath.join

        tpl = {
            'revision': (u"revision/", {'remove': [u'rev1', u'rev2'], 'set': [
                (u'rev', self._REVISION),
            ]}),

            'deleted': (join(u"checkout", self._BASE_PATH), {
                'remove': [u'rev1', u'rev2'],
                'set': [(u'rev', self._BASE_REVISION)]
            }),

            'deleted_dir': (join(u"browse", self._BASE_PATH, u""), {
                'remove': [u'rev1', u'rev2'],
                'set': [(u'rev', self._BASE_REVISION)]
            }),

            'added': (join(u"checkout", self._PATH), {
                'remove': [u'rev1', u'rev2'],
                'set': [(u'rev', self._REVISION)]
            }),

            'added_dir': (join(u"browse", self._PATH, u""), {
                'remove': [u'rev1', u'rev2'],
                'set': [(u'rev', self._REVISION)]
            }),

            'modified': (join(u"diff", self._PATH), {'set': [
                (u'rev',  self._REVISION),
                (u'rev1', self._BASE_REVISION),
                (u'rev2', self._REVISION),
            ]}),
        }
        # copy diffs are not possible currently, just browse the new file
        tpl['copied'] = tpl['added']

        return _base.Template.fromTemplates(url, tpl)
