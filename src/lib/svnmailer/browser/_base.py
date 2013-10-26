# -*- coding: utf-8 -*-
# pylint: disable-msg=R0921
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
=====================================================
Base Classes for Respository Browser URL Construction
=====================================================

All browser generator classes should utilize the tools and base classes
provides by this module.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['ParsedQuery', 'ParsedUrl', 'Template', 'BaseGenerator']

# global imports
import posixpath, re, urllib, urlparse
from svnmailer import util


class ParsedQuery(object):
    """ Class for query string parsing and modification

        :CVariables:
         - `_QUERYRE`: Regex for splitting a query string
           on possible delimiters (``&`` and ``;``)

        :Ivariables:
         - `_query_dict`: Dictionary of key->valuelist pairs
           (``{'key': ['val1', 'val2'], ...}``)

         - `_keyorder`: Original order of the keys (``['key', ...]``)

         - `_delim`: The delimiter to use for reconstructing the query string

        :Types:
         - `_QUERYRE`: ``_sre.SRE_Pattern``
         - `_query_dict`: ``dict``
         - `_keyorder`: ``list``
         - `_delim`: ``str``
    """
    _QUERYRE = re.compile(r'[&;]')

    def __init__(self, query = '', delim = '&'):
        """ Initialization

            :Parameters:
             - `query`: The query string to store
             - `delim`: The delimiter for reconstructing the query

            :Types:
             - `query`: ``str`` or ``unicode`` or `ParsedQuery`
             - `delim`: ``str``
        """
        if not query:
            query_dict = {}
            keyorder = []
        elif hasattr(query, '_QUERYRE'):
            query_dict = dict([(key, list(val))
                for key, val in query._query_dict.items()
            ])
            keyorder = list(query._keyorder)
        else:
            query_dict = {}
            keyorder = []
            for tup in [pair.split('=', 1)
                    for pair in self._QUERYRE.split(query)]:
                if len(tup) == 1:
                    key, val = tup[0], None
                else:
                    key, val = tup
                query_dict.setdefault(key, []).append(val)
                keyorder.append(key)

        self._keyorder = keyorder
        self._query_dict = query_dict
        self._delim = delim


    def __str__(self):
        """ Returns the query as string again

            :return: The query as string (type depends on the input)
            :rtype:  ``str`` or ``unicode``
        """
        result = []
        qdict = self._query_dict.copy() # we're going to destroy it
        for key in self._keyorder:
            val = qdict[key].pop(0)
            if val is None:
                result.append(key)
            else:
                result.append("%s=%s" % (key, val))

        return self._delim.join(result)


    def __contains__(self, key):
        """ Returns whether `key` occurs in the query as parameter name

            :param `key`: The key to lookup
            :type `key`: ``str`` or ``unicode``

            :return: Does `key` occur?
            :rtype: ``bool``
        """
        return key in self._query_dict


    def __getitem__(self, key):
        """ Returns the value list for parameter named `key`

            Don't modify the returned list without adjusting `_keyorder`,
            too. At best don't modify it directly at all :)

            :param `key`: The key to lookup
            :type `key`: ``str`` or ``unicode``

            :return: The value list (``['val1', 'val2', ...]``)
            :rtype: ``list``

            :exception KeyError: The key does not exist
        """
        return self._query_dict[key]


    def remove(self, keys):
        """ Removes certain parameters from the query if present

            Non-present parameters are silently ignored

            :param `keys`: The names of the parameters to remove
            :type `keys`: sequence
        """
        for key in keys:
            if key in self._query_dict:
                del self._query_dict[key]
                self._keyorder = [
                    nkey for nkey in self._keyorder if nkey != key
                ]


    def add(self, toadd):
        """ Adds certain key value pairs to the query

            :param `toadd`: A sequence of key-value-pairs
                          (``(('key', 'value), ...)``)
            :type `toadd`: sequence
        """
        for key, val in toadd:
            self._query_dict.setdefault(key, []).append(val)
            self._keyorder.append(key)


    def modify(self, remove = None, add = None, set = None):
        """ Summarizes certain query modification methods

            `set` is a convenience parameter, it's actually a combination of
            `remove` and `add`. The order of processing is:

            1. append the set parameters to `remove` and `add`
            2. apply `remove`
            3. apply `add`

            :Parameters:
             - `remove`: parameters to remove (see `ParsedQuery.remove`
               method)

             - `add`: parameters to add (see `ParsedQuery.add` method)

             - `set`: parameters to override (see `ParsedQuery.add` for the
               format)

            :Types:
             - `remove`: sequence
             - `add`: sequence
             - `set`: sequence
        """
        remove = list(remove or [])
        add = list(add or [])
        set = list(set or [])

        # append set list to remove and add
        remove.extend([tup[0] for tup in set])
        add.extend(set)

        self.remove(remove)
        self.add(add)


class ParsedUrl(object):
    """ Container for URL parsing and modification

        :CVariables:
         - `PARSENAMES`: names for the urlparse tuple

        :IVariables:
         - `scheme`: The scheme (``http``)
         - `netloc`: The netloc (``www.example.org``)
         - `path`: The path (``/foo/bar``)
         - `param`: The path parameter (``jsessionid=abcdef``)
         - `query`: The query string (``a=b&c=d``)
         - `fragment`: The fragment (``anchor``)

        :Types:
         - `PARSENAMES`: ``tuple``
         - `scheme`: ``str``
         - `netloc`: ``str``
         - `path`: ``str``
         - `param`: ``str``
         - `query`: `ParsedQuery`
         - `fragment`: ``str``
    """
    PARSENAMES = ('scheme', 'netloc', 'path', 'param', 'query', 'fragment')

    def __init__(self, url):
        """ Initialization

            :param `url`: The url to parse
            :type `url`: ``str`` or `ParsedUrl`

            :exception AttributeError: If `url` is a `ParsedUrl` and
                one or more of the attributes named in `PARSENAMES` are
                missing.
        """
        if hasattr(url, 'PARSENAMES'):
            self.__dict__.update(dict([
                (name, getattr(url, name)) for name in self.PARSENAMES
            ]))
        else:
            self.__dict__.update(
                dict(zip(self.PARSENAMES, urlparse.urlparse(url)))
            )
        self.query = self._createParsedQuery(self.query)


    def __str__(self):
        """ Returns the URL as string

            :return: The URL as string
            :rtype: ``str``
        """
        return urlparse.urlunparse([
            str(getattr(self, name)) for name in self.PARSENAMES
        ])


    def copy(self):
        """ Returns a new identical object

            :return: The new `ParsedUrl` instance
            :rtype: `ParsedUrl`
        """
        return self.__class__(self)


    def _createParsedQuery(self, query):
        """ Creates a new `ParsedQuery` instance

            :param `query`: The query to parse
            :type `query`: ``str`` or `ParsedQuery`

            :return: The `ParsedQuery` instance
            :rtype: `ParsedQuery`
        """
        return ParsedQuery(query)


class Template(object):
    """ Template storage, selector

        :CVariables:
         - `_TYPES`: List of possible template types (``('type', ...)``)

        :IVariables:
         - `_templates`: The actual templates (``{'type': 'template', ...}``)

        :Types:
         - `_TYPES`: ``tuple``
         - `_templates`: ``dict``
    """
    _TYPES = (
        'revision',
        'deleted',  'deleted_dir',
        'copied',   'copied_dir',
        'added',    'added_dir',
        'modified', 'modified_dir',
    )

    def __init__(self, **kwargs):
        """ Initialization

            :param `kwargs`: The templates (``{'type': 'template', ...}``)

            :exception AttributeError: A type was not recognized
        """
        templates = dict.fromkeys(self._TYPES)

        for key, val in kwargs.items():
            if key not in templates:
                raise AttributeError("unrecognized template type %r" % key)
            templates[key] = val

        self._templates = templates


    def fromTemplates(cls, base_url, templates):
        """ Creates a Template class from template templates

            :Parameters:
             - `base_url`: The base url, which should be modified
               by the template templates.

             - `templates`: The template templates. This is a dict, which
               contains an entry for each template type (see `_TYPES` for all
               possibilities). The value is a tuple consisting of the path
               that should be added to `base_url` and keyword parameters for
               ``base_url.query.modify``. Both may be ``None``.
               (``'type': ('path', {dict(querykw)})``)

            :Types:
             - `base_url`: `ParsedUrl`
             - `templates`: ``dict``

            :return: A new Template instance
            :rtype: `Template`

            :exception AttributeError: An unknown template type was supplied
                by the `templates` parameter
        """
        initkw = {}
        for key, (cpath, querykw) in templates.items():
            url = base_url.copy()
            if cpath is not None:
                url.path = posixpath.join(url.path, cpath)
            if querykw is not None:
                url.query.modify(**querykw)

            initkw[key] = str(url)

        return cls(**initkw)

    fromTemplates = classmethod(fromTemplates)


    def hasTemplates(self):
        """ Returns whether there are templates at all

            :return: Are there templates?
            :rtype: ``bool``
        """
        return bool([item for item in self._templates.values() if item])

        
    def getRevisionUrl(self):
        """ Returns the revision URL template

            :return: The template or ``None`` if there's no such template
            :rtype: ``str`` or ``unicode``
        """
        return self._templates['revision']


    def selectByChange(self, change):
        """ Returns the approriate diff URL template

            :param `change`: The change description
            :type `change`: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The template or ``None`` if there's no such template
            :rtype: ``str`` or ``unicode``
        """
        if change.wasDeleted():
            template = 'deleted'
        elif change.wasCopied():
            template = 'copied'
        elif change.wasAdded():
            template = 'added'
        else: # modified
            template = 'modified'

        if change.isDirectory():
            template += "_dir"

        return self._templates[template]


class BaseGenerator(object):
    """ Abstract base URL generator

        Actual generators need to implement the `_createTemplate`
        method.

        :Groups:
         - `Format Names`: `_N_REVISION`, `_N_BASE_REVISION`, `_N_PATH`,
           `_N_BASE_PATH`
         - `Format Strings`: `_REVISION`, `_BASE_REVISION`, `_PATH`,
           `_BASE_PATH`

        :CVariables:
         - `_N_REVISION`: The revision format name
         - `_N_BASE_REVISION`: The base revision format name
         - `_N_PATH`: The format name of the changed path
         - `_N_BASE_PATH`: The format name of the previous path of the
           changed file
         - `_REVISION`: The revision format string
         - `_BASE_REVISION`: The base revision format string
         - `_PATH`: The changed path (without a leading slash)
         - `_BASE_PATH`: The previous path of the changed file
         - `_QUERY_ENCODING`: The character encoding to use for url parameters

        :IVariables:
         - `_subst`: The substitution record

        :Types:
         - `_N_REVISION`: ``unicode``
         - `_N_BASE_REVISION`: ``unicode``
         - `_N_PATH`: ``unicode``
         - `_N_BASE_PATH`: ``unicode``
         - `_REVISION`: ``unicode``
         - `_BASE_REVISION`: ``unicode``
         - `_PATH`: ``unicode``
         - `_BASE_PATH`: ``unicode``
         - `_QUERY_ENCODING`: ``str``

         - `_subst`: ``dict``
    """
    _N_REVISION      = u"revision"
    _N_BASE_REVISION = u"base_revision"
    _N_PATH          = u"path"
    _N_BASE_PATH     = u"base_path"

    _REVISION      = u"%%(%s)s" % _N_REVISION
    _BASE_REVISION = u"%%(%s)s" % _N_BASE_REVISION
    _PATH          = u"%%(%s)s" % _N_PATH
    _BASE_PATH     = u"%%(%s)s" % _N_BASE_PATH

    _QUERY_ENCODING = "utf-8"


    def __init__(self, base_url, config, **kwargs):
        """ Initialization

            :Parameters:
             - `base_url`: The base URL
             - `config`: The group configuration

            :Types:
             - `base_url`: ``unicode``
             - `config`: ``svnmailer.settings._base.GroupSettingsContainer``

            :Exceptions:
             - `svnmailer.browser.Error`: The configured URL is invalid
             - `AttributeError`: see `_createTemplate`
             - `NotImplementedError`: see `_createTemplate`
        """
        self._subst = config("subst")
        self._template = self._createTemplate(base_url, config)


    def hasTemplates(self):
        """ Returns whether there are any templates stored

            :return: Are there any templates?
            :rtype: ``bool``
        """
        return self._template.hasTemplates()


    def getRevisionUrl(self):
        """ Returns the revision summary URL

            :return: The URL or ``None`` if not appropriate template could be
                     found
            :rtype: ``str``
        """
        return util.substitute(
            self._template.getRevisionUrl(), self._quoteDict(self._subst)
        )


    def getContentDiffUrl(self, change):
        """ Returns the content diff URL for a particular change

            :param `change`: The change to process
            :type `change`: `svnmailer.subversion.VersionedPathDescriptor`

            :return: The URL or ``None`` if no appropriate template could be
                     found
            :rtype: ``str``
        """
        template = self._template.selectByChange(change)

        if template is not None:
            subst = {
                self._N_BASE_PATH    : (
                    change.getBasePath() or '').decode('utf-8'),
                self._N_PATH         : change.path.decode('utf-8'),
                self._N_BASE_REVISION: u"%d" % change.getBaseRevision(),
            }
            # mailer.py compat
            subst[u'base_rev'] = subst[self._N_BASE_REVISION]
            subst[u'rev'] = self._subst[self._N_REVISION]

            # merge with otherwise supplied params
            subst.update(self._subst)

            # and go!
            return util.substitute(template, self._quoteDict(subst))

        return None


    def _quoteDict(self, toquote):
        """ URL-escapes the values of the supplied dict

            All values are first UTF-8 encoded and then URL escaped.
            If you need something else, feel free to override this method
            in your particular generator. If you just need another encoding,
            override the `_QUERY_ENCODING` class variable. But be prepared to
            get an ``UnicodeError`` if an entity is not mappable to
            your different encoding.

            :param `toquote`: The dict to process
            :type `toquote`: ``dict``

            :return: The quoted dict
            :rtype: ``dict``
        """
        newdict = {}
        for key, value in toquote.items():
            newdict[key] = urllib.quote(
                (value or u"").encode('utf-8')
            ).decode('utf-8')
 
        return newdict


    def _createParsedUrl(self, url):
        """ Returns a ParsedUrl instance

            :param `url`: The url to parse
            :type `url`: ``str``, ``unicode`` or `ParsedUrl`

            :return: The new `ParsedUrl` instance
            :rtype: `ParsedUrl`
        """
        return ParsedUrl(url)


    def _createTemplate(self, base_url, config):
        """ Returns a Template instance

            :Parameters:
             - `base_url`: The base URL
             - `config`: The complete group configuration

            :Types:
             - `base_url`: ``unicode``
             - `config`: `svnmailer.settings._base.GroupSettingsContainer`

            :exception NotImplementedError: The method was not overridden
        """
        raise NotImplementedError()
