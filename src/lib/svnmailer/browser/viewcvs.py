# -*- coding: iso-8859-1 -*-
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
ViewCVS_ repository browser URL construction

.. _`ViewCVS`: http://viewcvs.sourceforge.net/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Generator']

# global imports
from svnmailer.browser import _base


class Generator(_base.BaseGenerator):
    """ ViewCVS_ template generator

        .. _`ViewCVS`: http://viewcvs.sourceforge.net/
    """

    def _createTemplate(self, base_url, config):
        """ Returns ViewCVS URL templates """
        config # pylint

        url = self._createParsedUrl(base_url)
        while url.path[-1:] == u'/':
            url.path = url.path[:-1]

        tpl = {
            'revision': (None, {
                'remove': [u'p1', u'p2', u'r1', u'r2'],
                'set': [
                    (u'view', u'rev'),
                    (u'rev', self._REVISION),
                ]
            }),

            'deleted': (self._BASE_PATH, {
                'remove': [u'p1', u'p2', u'r1', u'r2'],
                'set': [
                    (u'view', u'auto'),
                    (u'rev',  self._BASE_REVISION),
                ]
            }),

            'added': (self._PATH, {
                'remove': [u'p1', u'p2', u'r1', u'r2'],
                'set': [
                    (u'view', u'auto'),
                    (u'rev',  self._REVISION),
                ]
            }),

            'copied': (self._PATH, {'set': [
                (u'view', u'diff'),
                (u'rev',  self._REVISION),
                (u'p1',   self._BASE_PATH),
                (u'r1',   self._BASE_REVISION),
                (u'p2',   self._PATH),
                (u'r2',   self._REVISION),
            ]}),

            'modified': (self._PATH, {'remove': [u'p1', u'p2'], 'set': [
                (u'view', u'diff'),
                (u'rev',  self._REVISION),
                (u'r1',   self._BASE_REVISION),
                (u'r2',   self._REVISION),
            ]}),
        }
        tpl['deleted_dir'] = (u"%s/" % self._BASE_PATH, tpl['deleted'][1])
        tpl['added_dir'] = (u"%s/" % self._PATH, tpl['added'][1])

        return _base.Template.fromTemplates(url, tpl)
