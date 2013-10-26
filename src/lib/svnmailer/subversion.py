# -*- coding: utf-8 -*-
# pylint: disable-msg=W0232,C0103,W0142,W0201
# pylint-version = 0.7.0
#
# Copyright 2004-2005 André Malo or his licensors, as applicable
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
Access to the subversion respository

:Variables:
 - `version`: The version of the subversion library
 - `_SVN_INVALID_REVNUM`: the invalid revision number

:Types:
 - `version`: `_Version`
 - `_SVN_INVALID_REVNUM`: ``int``
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = [
    'version', 'Repository', 'Error', 'RepositoryError', 'isUnicodeProperty'
    'VersionedPathDescriptor', 'LockedPathDescriptor',
]


# global imports
import os
from svn import core as svn_core
from svn import repos as svn_repos
from svn import fs as svn_fs
from svn import delta as svn_delta

_SVN_INVALID_REVNUM = svn_core.SWIG_SVN_INVALID_REVNUM

# Exceptions
Error = svn_core.SubversionException


class _Version(object):
    """ SVN version container class

        :IVariables:
         - `major`: Major version
         - `minor`: Minor version
         - `patch`: Patch level
         - `revision`: Revision number
         - `tag`: Additional tag
         - `min_1_2`: SVN >= 1.2?

        :Types:
         - `major`: ``int``
         - `minor`: ``int``
         - `patch`: ``int``
         - `revision`: ``int``
         - `tag`: ``str``
         - `min_1_2`: ``bool``
    """

    def __init__(self):
        """ Initialization """
        self.major = svn_core.SVN_VER_MAJOR
        self.minor = svn_core.SVN_VER_MINOR
        self.revision = svn_core.SVN_VER_REVISION
        self.tag = svn_core.SVN_VER_TAG
        try:
            self.patch = svn_core.SVN_VER_PATCH # >=1.1
        except AttributeError:
            self.patch = svn_core.SVN_VER_MICRO # 1.0

        self.min_1_2 = bool(
            self.major > 1 or (self.major == 1 and self.minor >= 2)
        )


    def __repr__(self):
        """ String representation for debugging """
        return "<svn version %d.%d.%d%s rev:%d, 1.2+: %s>" % (
            self.major, self.minor, self.patch,
            self.tag, self.revision, self.min_1_2
        )

version = _Version()


def isUnicodeProperty(name):
    """ Returns if the supplied name represents a translated property

        :param name: The property name
        :type name: ``str``

        :return: The decision
        :rtype: ``bool``
    """
    return bool(svn_core.svn_prop_needs_translation(name))


def isBinary(mtype):
    """ Returns True if the supplied mime type represents a binary

        :param mtype: The mime type
        :type mtype: ``str``

        :return: The decision
        :rtype: ``bool``
    """
    return bool(mtype and
        svn_core.svn_mime_type_is_binary(mtype)
    )


class RepositoryError(Exception):
    """ A repository error occured

        :IVariables:
         - `svn_err_code`: The SVN error code
         - `svn_err_name`: The name of the SVN error (if it could be mapped)
         - `svn_err_str`: The SVN error description

        :Types:
         - `svn_err_code`: ``int``
         - `svn_err_name`: ``str``
         - `svn_err_str`: ``str``
    """

    def __init__(self, sexc):
        """ Initialization

            :param sexc: `svnmailer.subversion.Error`
            :type sexc: `svnmailer.subversion.Error`
        """
        Exception.__init__(self)
        self.svn_err_str, self.svn_err_code = sexc.args
        self.svn_err_name = dict([(getattr(svn_core, var), var)
            for var in vars(svn_core) if var.startswith('SVN_ERR')
        ]).get(self.svn_err_code, 'unknown APR code')


    def __str__(self):
        """ Human readable representation

            :return: The string representation
            :rtype: ``str``
        """
        return str((self.svn_err_code, self.svn_err_name, self.svn_err_str))


# Main repository access class
class Repository(object):
    """ Access to the subversion repository

        :IVariables:
         - `path`: The path to the repository
         - `_pool`: main APR pool
         - `_apr_initialized`: is APR initialized?
         - `_repos`: Reference to the open repository
         - `_fs`: Reference to the repos filesystem
         - `_revRoots`: Cached revision root objects
         - `_revChanges`: Cached revision change lists
         - `_revProps`: Cached revision properties
         - `_revTimes`: Cached revision times
         - `_pathProps`: Cached path properties
         - `_pathPropLists`: Cached path propery lists

        :Types:
         - `path`: ``unicode``
         - `_pool`: swig object
         - `_apr_initialized`: ``bool``
         - `_repos`: swig object
         - `_fs`: swig object
         - `_revRoots`: ``dict``
         - `_revChanges`: ``dict``
         - `_revProps`: ``dict``
         - `_revTimes`: ``dict``
         - `_pathProps`: ``dict``
         - `_pathPropLists`: ``dict``
    """
    _pool = None
    _apr_initialized = False


    def __init__(self, repos_path):
        """ Open the repository

            :param repos_path: The repository path as unicode
            :type repos_path: ``unicode``
        """
        # init APR
        svn_core.apr_initialize()
        self._apr_initialized = True

        # get ourself a pool
        self._pool = svn_core.svn_pool_create(None)

        # normalize the repos path
        repos_path = repos_path.encode("utf-8", "strict")
        repos_path = os.path.normpath(os.path.abspath(repos_path))

        # open the repos
        self._repos = svn_repos.svn_repos_open(repos_path, self._pool)
        self._fs = svn_repos.svn_repos_fs(self._repos)

        # init the rest
        self._revRoots = {}
        self._revChanges = {}
        self._revProps = {}
        self._revTimes = {}
        self._pathProps = {}
        self._pathPropLists = {}
        self.path = repos_path


    def close(self):
        """ Destroy the pool and release the shared lock """
        try:
            if self._pool:
                pool = self._pool
                self._pool = None
                svn_core.svn_pool_destroy(pool)
        finally:
            if self._apr_initialized:
                self._apr_initialized = False
                svn_core.apr_terminate()


    def getChangesList(self, revision):
        """ Return the list of changes of a revisions sorted by path

            :param revision: The revision
            :type revision: ``int``

            :return: The Changes list
            :rtype: ``list``
        """
        try:
            changelist = self._revChanges[revision]
        except KeyError:
            editor = self._getChangeCollector(revision)
            e_pool = editor.getPool()
            e_ptr, e_baton = svn_delta.make_editor(editor, e_pool)
            svn_repos.svn_repos_replay(
                self._getRevisionRoot(revision), e_ptr, e_baton, e_pool
            )

            e_changes = (version.min_1_2 and
                [editor.get_changes()] or [editor.changes])[0]
            changelist = [VersionedPathDescriptor(self, path, revision, change)
                for path, change in e_changes.items()
            ]
            changelist.sort()

            # store in the cache
            self._revChanges[revision] = changelist

            del editor # destroy any subpool

        return changelist


    def getPathProperties(self, path, revision):
        """ Get a dict of properties for a particular path/revision

            :Parameters:
             - `path`: The path
             - `revision`: The revision number

            :Types:
             - `path`: ``str``
             - `revision`: ``int``

            :return: The dict of properties
            :rtype: ``dict``
        """
        try:
            plist = self._pathPropLists[(path, revision)]
        except KeyError:
            rev_root = self._getRevisionRoot(revision)
            plist = self._pathPropLists[(path, revision)] = dict([
                (key, str(value)) for key, value in
                svn_fs.node_proplist(rev_root, path, self._pool).items()
            ])

        return plist


    def getPathProperty(self, name, path, revision):
        """ Get the value of a particular property

            :Parameters:
             - `name`: The name of the property
             - `path`: The path the property is attached to
             - `revision`: The revision number

            :Types:
             - `name`: ``str``
             - `path`: ``str``
             - `revision`: ``int``

            :return: The property value or ``None`` if the property
                     doesn't exist.
            :rtype: ``str``
        """
        try:
            value = self._pathProps[(name, path, revision)]
        except KeyError:
            root = self._getRevisionRoot(revision)
            value = self._pathProps[(name, path, revision)] = svn_fs.node_prop(
                root, path, name, self._pool
            )

        return value


    def getPathMimeType(self, path, revision):
        """ Get the MIME type of a particular path

            :Parameters:
             - `path`: The path
             - `revision`: The revision number

            :Types:
             - `path`: ``str``
             - `revision`: ``int``

            :return: The mime type or ``None``
            :rtype: ``str``
        """
        return self.getPathProperty(
            svn_core.SVN_PROP_MIME_TYPE, path, revision
        )


    def dumpPathContent(self, fp, path, revision):
        """ Dump the contents of a particular path into a file

            :Parameters:
             - `fp`: The file descriptor
             - `path`: The path to process
             - `revision`: The revision number

            :Types:
             - `fp`: ``file``
             - `path`: ``str``
             - `revision`: ``int``
        """
        pool = svn_core.svn_pool_create(self._pool)

        try:
            root = self._getRevisionRoot(revision)
            stream = svn_fs.file_contents(root, path, pool)

            try:
                while True:
                    chunk = svn_core.svn_stream_read(
                        stream, svn_core.SVN_STREAM_CHUNK_SIZE
                    )
                    if not chunk:
                        break

                    fp.write(chunk)
            finally:
                svn_core.svn_stream_close(stream)
        finally:
            svn_core.svn_pool_destroy(pool)


    def getRevisionTime(self, revision):
        """ Returns the time of a particular rev. in seconds since epoch

            :Parameters:
             - `revision`: The revision number

            :Types:
             - `revision`: ``int``

            :return: The time
            :rtype: ``int``
        """
        try:
            rtime = self._revTimes[revision]
        except KeyError:
            svndate = self.getRevisionProperty(
                revision, svn_core.SVN_PROP_REVISION_DATE
            )
            rtime = self._revTimes[revision] = svn_core.secs_from_timestr(
                svndate, self._pool
            )

        return rtime


    def getRevisionAuthor(self, revision):
        """ Returns the author of a particular revision

            :param revision: The revision number
            :type revision: ``int``

            :return: The author
            :rtype: ``str``
        """
        return self.getRevisionProperty(
            revision, svn_core.SVN_PROP_REVISION_AUTHOR
        )


    def getRevisionLog(self, revision):
        """ Returns the log entry of a particular revision

            :param revision: The revision number
            :type revision: ``int``

            :return: The log entry or ``None``
            :rtype: ``str``
        """
        return self.getRevisionProperty(
            revision, svn_core.SVN_PROP_REVISION_LOG
        )


    def getRevisionProperty(self, revision, propname):
        """ Returns the value of a revision property

            :Parameters:
             - `propname`: The property name
             - `revision`: The revision number

            :Types:
             - `propname`: ``str``
             - `revision`: ``int``

            :return: The property value
            :rtype: ``str``
        """
        try:
            value = self._revProps[(revision, propname)]
        except KeyError:
            value = self._revProps[(revision, propname)] = \
                svn_fs.revision_prop(self._fs, revision, propname, self._pool)

        return value


    def _getChangeCollector(self, revision):
        """ Return the RevisionChangeCollector instance

            :param revision: The revision
            :type revision: ``int``

            :return: The Collector instance
            :rtype: `_RevisionChangeCollector`
        """
        return _RevisionChangeCollector(self, revision)

        
    def _getRevisionRoot(self, revision):
        """ Return the root object of a particular revision

            :note: The root objects are cached

            :param revision: The revision number
            :type revision: ``int``

            :return: The revision root
            :rtype: swig object
        """
        try:
            root = self._revRoots[revision]
        except KeyError:
            root = self._revRoots[revision] = svn_fs.revision_root(
                self._fs, revision, self._pool
            )

        return root


class PathDescriptor(object):
    """ Describes the basic information of a particular path

        :IVariables:
         - `path`: The path, we're talking about
         - `repos`: The repository this change belongs to

        :Types:
         - `path`: ``str``
         - `repos`: `Repository`
    """

    def __init__(self, repos, path, *args, **kwargs):
        """ Initialization

            :note: Don't override this method, override `init`
                   instead.

            :Parameters:
             - `repos`: The repository reference
             - `path`: The path

            :Types:
             - `repos`: `Repository`
             - `path`: ``str``
        """
        self.repos = repos
        self.path = (path[:1] == '/' and [path[1:]] or [path])[0]

        self.init(*args, **kwargs)


    def init(self, *args, **kwargs):
        """ Custom initialization """
        pass


    def __cmp__(self, other):
        """ Compares two change objects by path

            :param other: The object compared to
            :type other: hopefully `VersionedPathDescriptor`

            :return: Returns -1, 0 or 1
            :rtype: ``int``
        """
        return cmp(self.path, other.path)


    def isDirectory(self):
        """ Returns whether the path is a directory

            :return: is a directory?
            :rtype: ``bool``
        """
        raise NotImplementedError()


class LockedPathDescriptor(PathDescriptor):
    """ Describes the lock status of a particular path

        :ivar is_locked: is locked?
        :type is_locked: `bool`
    """
    def init(self, *args, **kwargs):
        """ Custom initialization """
        self._init(*args, **kwargs)


    def _init(self, is_locked):
        """ Initialization """
        self.is_locked = is_locked
        self._cache = None


    def isDirectory(self):
        """ Returns whether the path is a directory """
        # currently there's no way to lock directories
        return False


    def _getLockDescription(self):
        """ Returns the lock description object """
        if self._cache is None:
            self._cache = svn_fs.get_lock(
                self.repos._fs, self.path, self.repos._pool
            )

        return self._cache


    def getComment(self):
        """ Returns the lock comment """
        desc = self._getLockDescription()
        if desc:
            return str(desc.comment or "")

        return ""


class VersionedPathDescriptor(PathDescriptor):
    """ Describes the changes of a particular path

        This is a wrapper around ``svn_repos.ChangedPath`` instances.
        outside of this module one shouldn't need to deal with these.

        :IVariables:
         - `revision`: The revision number
         - `_change`: The change

        :Types:
         - `revision`: ``int``
         - `_change`: ``svn_repos.ChangedPath``
    """
    def init(self, *args, **kwargs):
        """ Custom initialization """
        self._init(*args, **kwargs)


    def _init(self, revision, change):
        """ Initialization 

            :Parameters:
             - `revision`: The revision number
             - `change`: The change specification

            :Types:
             - `revision`: ``int``
             - `change`: ``svn_repos.ChangedPath``
        """
        self.revision = revision
        self._change = change


    def getBaseRevision(self):
        """ Returns the revision number of the original path

            :return: The revision number
            :rtype: ``int``
        """
        return self._change.base_rev


    def getBasePath(self):
        """ Returns the original path

            :return: The path
            :rtype: ``str``
        """
        if self._change.base_path is None:
            return None

        # check the difference between 1.1 and 1.2 bindings...
        return (self._change.base_path[:1] == '/' and
            [self._change.base_path[1:]] or [self._change.base_path])[0]


    def getModifiedProperties(self):
        """ Returns the dict of modified properties

            The dict contains the property names as keys and
            a 2-tuple as value where the first element contains the
            old property value and second element the new one.

            :return: The dict of changed properties
            :rtype: ``dict``
        """
        if type(self._change.prop_changes) == type({}):
            return self._change.prop_changes

        if not self._change.prop_changes:
            return {}

        # get the property dicts
        if self.wasAdded():
            propdict1 = {}
        else:
            propdict1 = self.repos.getPathProperties(
                self.getBasePath(), self.getBaseRevision()
            )

        if self.wasDeleted():
            propdict2 = {}
        else:
            propdict2 = self.repos.getPathProperties(
                self.path, self.revision
            )

        # compute diff dict
        # non-existant properties in either version get None as value
        self._change.prop_changes = {}
        for name, value1, value2 in [
                (key, propdict1.get(key), propdict2.get(key)) for key in
                dict.fromkeys(propdict1.keys() + propdict2.keys()).keys()]:

            if value1 != value2:
                self._change.prop_changes[name] = (value1, value2)

        return self._change.prop_changes


    def isDirectory(self):
        """ Returns whether the path is a directory """
        return bool(self._change.item_kind == svn_core.svn_node_dir)


    def isBinary(self):
        """ Returns whether one of the revisions is a binary file

            :return: is binary?
            :rtype: ``bool``
        """
        if not self.wasDeleted():
            if isBinary(self.repos.getPathMimeType(
                self.path, self.revision
            )):
                return True

        if not self.wasAdded() or self.wasCopied():
            return isBinary(self.repos.getPathMimeType(
                self.getBasePath(), self.getBaseRevision()
            ))

        return False


    def hasPropertyChanges(self):
        """ Returns whether the path has property changes

            :return: has property changes?
            :rtype: ``bool``
        """
        return bool(self._change.prop_changes)


    def hasContentChanges(self):
        """ Returns whether the path has content changes

            :return: has content changes?
            :rtype: ``bool``
        """
        return bool(self._change.text_changed)


    def wasDeleted(self):
        """ Returns whether the path was deleted

            :return: was deleted?
            :rtype: ``bool``
        """
        return bool(self._change.path is None)


    def wasAdded(self):
        """ Returns whether the path was added

            :return: was added?
            :rtype: ``bool``
        """
        return bool(self._change.added)


    def wasModified(self):
        """ Returns whether the path was just modified

            :return: was modified?
            :rtype: ``bool``
        """
        return bool(not self._change.added and self._change.path is not None)


    def wasCopied(self):
        """ Returns whether the path was copied

            :return: was copied?
            :rtype: ``bool``
        """
        return bool(
            self._change.added and self._change.base_path and
            self._change.base_rev != _SVN_INVALID_REVNUM
        )


if version.min_1_2:
    class Collector(svn_repos.ChangeCollector, object):
        """ svn 1.2 collector """
        pass
else:
    class Collector(svn_repos.RevisionChangeCollector, object):
        """ svn 1.[01] collector """
        pass


class _RevisionChangeCollector(Collector):
    """ Collect all changes between two particular revisions

        :ivar __pool: The APR subpool
        :type __pool: swig object
    """
    __pool = None

    def __init__(self, repos, revision):
        """ Initialization

            :Parameters:
             - `repos`: Reference to the repository object
             - `revision`: The revision

            :Types:
             - `repos`: `Repository`
             - `revision`: ``int``
        """
        self.__repos = repos
        self.__pool = svn_core.svn_pool_create(repos._pool)

        super(_RevisionChangeCollector, self).__init__(
            repos._fs,
            version.min_1_2 and
                repos._getRevisionRoot(revision) or revision,
            self.__pool,
        )


    def __del__(self):
        """ Destroy the subpool """
        if self.__pool:
            pool = self.__pool
            self.__pool = None
            svn_core.svn_pool_destroy(pool)


    def getPool(self):
        """ Returns the subpool

            :return: the pool
            :rtype: swig object
        """
        return self.__pool


    def _get_root(self, rev):
        """ Return the root of a particular revision

            :note: The root objects are cached

            :param rev: The revision number
            :type rev: ``int``

            :return: The revision root
            :rtype: swig object
        """
        return self.__repos._getRevisionRoot(rev)
