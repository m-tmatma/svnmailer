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
Respository Browser URL construction
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['getBrowserUrlGenerator']


# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class InvalidBaseUrlError(Error):
    """ Invalid URL was configured """
    pass


def getBrowserUrlGenerator(config):
    """ Returns an initialized repos browser generator

        @param config: The group configuration
        @type config: C{svnmailer.settings.GroupSettingsContainer}

        @return: The generator object or C{None}
        @rtype: C{object}
    """
    if config.browser_base_url:
        b_type, base_url = parseBrowserBase(config.browser_base_url)

        if b_type == "viewcvs":
            return ViewcvsGenerator(base_url)
        elif b_type == "websvn":
            return WebsvnGenerator(base_url)

    elif config.viewcvs_base_url:
        return ViewcvsGenerator(config.viewcvs_base_url)

    return None


def parseBrowserBase(base_config):
    """ Parses the given option value into type and base url

        @param base_config: The option value
        @type base_config: C{str}

        @return: The type and the base url
        @rtype: C{tuple}
    """
    if base_config:
        tokens = base_config.split(None, 1)
        if len(tokens) == 2:
            return (tokens[0].lower(), tokens[1])

    return (None, None)


class ParsedUrl(object):
    """ Container for URL parsing and modification

        @ivar scheme: The scheme
        @type scheme: C{str}
        
        @ivar netloc: The netloc
        @type netloc: C{str}
        
        @ivar path: The path
        @type path: C{str}
        
        @ivar param: The path param
        @type param:C{str}
        
        @ivar query: The query string
        @type query: C{str}
        
        @ivar fragment: The fragment
        @type fragment: C{str}
    """

    def __init__(self, url):
        """ Initialization """
        import urlparse

        (self.scheme, self.netloc, self.path, self.param, self.query,
         self.fragment) = urlparse.urlparse(url)


    def __str__(self):
        """ Returns the URL as string

            @return: The URL as string
            @rtype: C{str}
        """
        import urlparse

        return urlparse.urlunparse((
            self.scheme, self.netloc, self.path, self.param, self.query,
            self.fragment
        ))


class ViewcvsGenerator(object):
    """ viewcvs generator

        @ivar base: The base url
        @type base: C{str}
    """

    def __init__(self, base):
        """ Initialization

            @param base: The base url
            @type base: C{str}
        """
        self.base = base


    def getRevisionUrl(self, revision):
        """ Returns the revision summary URL

            @param revision: The revision number
            @type revision: C{int}

            @return: The url
            @rtype: C{str}
        """
        import urllib
        from svnmailer import util

        url = ParsedUrl(self.base)

        while url.path[-1:] == '/':
            url.path = url.path[:-1]

        url.query = util.modifyQuery(url.query,
            rem = ['p1', 'p2', 'r1', 'r2'],
            set = [
                ('view', 'rev'),
                ('rev', urllib.quote(str(revision))),
            ]
        )

        return str(url)


    def getContentDiffUrl(self, change):
        """ Returns the content diff url for a particular change

            @param change: The change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}
        """
        import urllib, posixpath
        from svnmailer import util

        url = ParsedUrl(self.base)

        url.path = posixpath.join(url.path, urllib.quote((
            change.wasDeleted() and [change.getBasePath()] or [change.path]
        )[0]))

        if change.isDirectory():
            url.path = "%s/" % url.path

        if change.wasDeleted():
            url.query = util.modifyQuery(url.query,
                rem = ['p1', 'p2', 'r1', 'r2'],
                set = [
                    ('view', 'auto'),
                    ('rev',  urllib.quote(str(change.getBaseRevision()))),
                ]
            )

        elif change.wasCopied():
            if change.isDirectory():
                return None # no text changes

            url.query = util.modifyQuery(url.query, set = [
                ('view', 'diff'),
                ('rev',  urllib.quote(str(change.revision))),
                ('p1',   urllib.quote(change.getBasePath())),
                ('r1',   urllib.quote(str(change.getBaseRevision()))),
                ('p2',   urllib.quote(change.path)),
                ('r2',   urllib.quote(str(change.revision))),
            ])

        elif change.wasAdded():
            url.query = util.modifyQuery(url.query,
                rem = ['p1', 'p2', 'r1', 'r2'],
                set = [
                    ('view', 'auto'),
                    ('rev',  urllib.quote(str(change.revision))),
                ]
            )

        else: # modified
            if change.isDirectory():
                return None # no text changes

            url.query = util.modifyQuery(url.query,
                rem = ['p1', 'p2'],
                set = [
                    ('view', 'diff'),
                    ('rev',  urllib.quote(str(change.revision))),
                    ('r1',   urllib.quote(str(change.getBaseRevision()))),
                    ('r2',   urllib.quote(str(change.revision))),
                ]
            )

        return str(url)


class WebsvnGenerator(object):
    """ websvn generator

        @ivar base: The base url
        @type base: C{str}
    """

    def __init__(self, base):
        """ Initialization

            @param base: The base url
            @type base: C{str}
        """
        self.base = base


    def getRevisionUrl(self, revision):
        """ Returns the revision summary URL

            @param revision: The revision number
            @type revision: C{int}

            @return: The url
            @rtype: C{str}
        """
        import urllib, posixpath
        from svnmailer import util

        url = ParsedUrl(self.base)
        parsed_query = util.parseQuery(url.query)

        # no path info...
        if parsed_query.has_key("repname"):
            dirname, basename = posixpath.split(url.path)
            if not basename:
                raise InvalidBaseUrlError("Missing PHP file...?")

            url.path = posixpath.join(dirname, 'listing.php')

        # path info configured
        else:
            while url.path[-1:] == '/':
                url.path = url.path[:-1]
            url.path = "%s/" % url.path

        url.query = util.modifyQuery(parsed_query,
            rem = ['path'],
            set = [
                ('sc', '1'),
                ('rev', urllib.quote(str(revision))),
            ]
        )

        return str(url)


    def getContentDiffUrl(self, change):
        """ Returns the content diff url for a particular change

            @param change: The change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}
        """
        import urllib, posixpath
        from svnmailer import util

        if change.isDirectory() and not change.wasDeleted() and (
                not change.wasAdded() or change.wasCopied()):
            # show only a directory URL on adding and deleting
            return

        url = ParsedUrl(self.base)
        parsed_query = util.parseQuery(url.query)
        cpath = urllib.quote("%s%s" % (
            (change.wasDeleted() and
                [change.getBasePath()] or [change.path])[0],
            ["", "/"][change.isDirectory()]
        ))

        toset = [("rev", urllib.quote(str((change.wasDeleted() and
            [change.getBaseRevision()] or [change.revision]
        )[0])))]

        if parsed_query.has_key("repname"):
            dirname, basename = posixpath.split(url.path)
            if not basename:
                raise InvalidBaseUrlError(
                    "Missing PHP file in '%s'?" % self.base
                )

            url.query = util.modifyQuery(parsed_query,
                set = [('path', "/%s" % cpath)]
            )
            url.path = dirname
            cpath = ["diff.php", ["filedetails.php", "listing.php"]
                    [change.isDirectory()]][
                        change.wasDeleted() or (
                        change.wasAdded() and not change.wasCopied())
                    ]

        else:
            toset.append(("op",
                ["diff", ["file", "dir"][change.isDirectory()]][
                    change.wasDeleted() or (
                    change.wasAdded() and not change.wasCopied())
                ]
            ))

        url.path = posixpath.join(url.path, cpath)
        url.query = util.modifyQuery(url.query, rem = ["sc"], set = toset)

        return str(url)
