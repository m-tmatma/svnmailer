# -*- coding: utf-8 -*-
# pylint: disable-msg=W0221
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
WebSVN_ repository browser URL construction

.. _`WebSVN`: http://websvn.tigris.org/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'Error',
    'MissingPHPFileError',
    'Generator',
]

# global imports
import posixpath
from svnmailer.browser import Error, _base

# Exceptions
class MissingPHPFileError(Error):
    """ The configured URL misses the php file as basename """
    pass


class Generator(_base.BaseGenerator):
    """ WebSVN_ template generator

        .. _`WebSVN`: http://websvn.tigris.org/
    """

    def _createTemplate(self, base_url, config):
        """ Returns WebSVN URL templates

            :exception MissingPHPFileError: see `_getNopiTemplate`
        """
        config # pylint

        url = self._createParsedUrl(base_url)
        if u"repname" in url.query:
            ttpl = self._getNopiTemplate(url)
        else:
            ttpl = self._getPiTemplate(url)

        return _base.Template.fromTemplates(*ttpl)


    def _getNopiTemplate(self, url):
        """ Returns no-path-info templates

            :param `url`: The parsed URL
            :type `url`: `_base.ParsedUrl`

            :return: The parameters for `_base.Template.fromTemplates`
            :rtype: ``tuple``

            :exception MissingPHPFileError: The URL misses the PHP file
        """
        dirname, basename = posixpath.split(url.path)
        if not basename:
            raise MissingPHPFileError(
                "Missing PHP file in %r...?" % (str(url))
            )
        url.path = dirname

        tpl = {
            'revision': (u"listing.php", {'remove': [u'path'], 'set': [
                (u'sc', u'1'),
                (u'rev', self._REVISION),
            ]}),

            'deleted': (u"filedetails.php", {'remove': [u'sc'], 'set': [
                (u"rev", self._BASE_REVISION),
                (u"path", u"/%s" % self._BASE_PATH)
            ]}),

            'deleted_dir': (u"listing.php", {'remove': [u'sc'], 'set': [
                (u"rev", self._BASE_REVISION),
                (u"path", u"/%s/" % self._BASE_PATH)
            ]}),

            'added': (u"filedetails.php", {'remove': [u'sc'], 'set': [
                (u"rev", self._REVISION),
                (u"path", u"/%s" % self._PATH)
            ]}),

            'added_dir': (u"listing.php", {'remove': [u'sc'], 'set': [
                (u"rev", self._REVISION),
                (u"path", u"/%s/" % self._PATH)
            ]}),

            'copied': (u"diff.php", {'remove': [u'sc'], 'set': [
                (u"rev", self._REVISION),
                (u"path", u"/%s" % self._PATH),
            ]}),
        }
        tpl['modified'] = tpl['copied']

        return (url, tpl)


    def _getPiTemplate(self, url):
        """ Returns path-info templates

            :param `url`: The parsed URL
            :type `url`: `_base.ParsedUrl`

            :return: The parameters for `_base.Template.fromTemplates`
            :rtype: ``tuple``
        """
        while url.path[-1:] == u'/':
            url.path = url.path[:-1]
        url.path = u"%s/" % url.path
        url.query.remove([u"path"])

        tpl = {
            'revision': (None, {'set': [
                (u'sc', u'1'),
                (u'rev', self._REVISION),
            ]}),

            'deleted': (self._BASE_PATH, {'remove': [u"sc"], 'set': [
                (u"rev", self._BASE_REVISION),
                (u"op", u"file"),
            ]}),

            'deleted_dir': (u"%s/" % self._BASE_PATH, {
                'remove': [u"sc"],
                'set': [
                    (u"rev", self._BASE_REVISION),
                    (u"op", u"dir"),
                ]
            }),

            'added': (self._PATH, {'remove': [u"sc"], 'set': [
                (u"rev", self._REVISION),
                (u"op", u"file"),
            ]}),

            'added_dir': (u"%s/" % self._PATH, {'remove': [u"sc"], 'set': [
                (u"rev", self._REVISION),
                (u"op", u"dir"),
            ]}),

            'copied': (self._PATH, {'remove': [u"sc"], 'set': [
                (u"rev", self._REVISION),
                (u"op", u"diff"),
            ]}),
        }
        tpl['modified'] = tpl['copied']

        return (url, tpl)
