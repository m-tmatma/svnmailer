# -*- coding: utf-8 -*-
# pylint: disable-msg = W0704
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
Main Logic of the svnmailer
===========================

This module is the central core of the svnmailer. It dispatches all work to be
done. It contains just one class (L{Main}), which reads the config file while
it is initialized. When the C{Main.run()} method is called, it selects the
groups to be notified, the notifiers to be run and runs all notifiers for
each group.

The Main class may raise several exceptions (which all inherit from L{Error}):
    - L{ConfigError} occurs, if the configuration contains errors (like type
      or value errors, unicode errors etc). The L{ConfigError} exception is
      initialized with a string describing what kind of error occured.

    - L{NotifierError} occurs, if one or more of the notifiers throw an
      exception. The L{Main} class catches these exceptions (except
      C{KeyboardInterrupt} and C{SystemExit}) and will initialize the
      L{NotifierError} with the list of traceback strings, one for each
      exception occured. (See the format_exception docs at
      U{http://docs.python.org/lib/module-traceback.html}).

    - L{svnmailer.subversion.RepositoryError} occurs, if something failed
      while accessing the subversion repository. It contains some attributes
      for identifying the error: C{svn_err_code}, C{svn_err_name} and
      C{svn_err_str}
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['Main', 'Error', 'ConfigError', 'NotifierError']

# Exceptions
class Error(Exception):
    """ Base exception for this module """
    pass

class ConfigError(Error):
    """ Configuration error occurred """
    pass

class NotifierError(Error):
    """ An Notifier error occured """
    pass


class Main(object):
    """ main svnmailer logic

        @ivar _settings: The settings to use
        @type _settings: C{svnmailer.settings.Settings}
    """

    def __init__(self, options):
        """ Initialization

            @param options: Command line options
            @type options: C{optparse.OptionParser}

            @exception ConfigError: Configuration error
        """
        self._settings = self._getSettings(options)


    def run(self):
        """ Dispatches the work to be done

            @exception svnmailer.subversion.RepositoryError: Error while
                accessing the subversion repository
            @exception NotifierError: One or more notifiers went crazy
        """
        from svnmailer import subversion

        try:
            try:
                self._openRepository()

                notifier_errors = []
                throwables = (KeyboardInterrupt, SystemExit, subversion.Error)
                selector = self._getNotifierSelector()

                for groupset in self._getGroupSets():
                    notifiers = selector.selectNotifiers(groupset)
                    for notifier in notifiers:
                        try:
                            notifier.run()
                        except throwables:
                            raise
                        except:
                            import sys, traceback
                            info = sys.exc_info()
                            backtrace = traceback.format_exception(
                                info[0], info[1], info[2]
                            )
                            del info
                            backtrace[0] = "Notifier: %s.%s\nRevision: %s\n" \
                                "Groups: %r\n%s" % (
                                notifier.__module__,
                                notifier.__class__.__name__,
                                self._settings.runtime.revision,
                                [group._name for group in groupset.groups],
                                backtrace[0],
                            )
                            notifier_errors.append(''.join(backtrace))
                if notifier_errors:
                    raise NotifierError(*notifier_errors)

            except subversion.Error, exc:
                import sys
                raise subversion.RepositoryError, exc, sys.exc_info()[2]

        finally:
            # IMPORTANT! otherwise the locks are kept and
            # we run into bdb "out of memory" errors some time
            self._closeRepository()


    def _getNotifierSelector(self):
        """ Returns the notifier selector

            @return: The selector
            @rtype: C{svnmailer.notifier.selector.Selector}
        """
        from svnmailer.notifier import selector
        return selector.Selector(self._settings)


    def _getChanges(self):
        """ Returns the list of changes for the requested revision

            @return: The list of changes (C{[Descriptor, ...]})
            @rtype: C{list}

            @exception svnmailer.subversion.Error: Error while accessing the
                subversion repository
        """
        from svnmailer import settings, subversion

        modes = settings.modes
        runtime = self._settings.runtime

        if runtime.mode in (modes.commit, modes.propchange):
            changes = runtime._repos.getChangesList(runtime.revision)
        elif runtime.mode in (modes.lock, modes.unlock):
            is_locked = bool(runtime.mode == modes.lock)
            changes = [
                subversion.LockedPathDescriptor(runtime._repos, path, is_locked)
                for path in runtime.stdin.splitlines() if path
            ]
            changes.sort()
        else:
            raise AssertionError("Unknown runtime.mode %r" % (runtime.mode,))

        return changes


    def _getGroupSets(self):
        """ Returns the list of groupsets (grouped groups...) to notify

            @return: The list (maybe empty). (C{[GroupSet, ...]})
            @rtype: C{list}
        """
        # collect changes and group by group [ ;-) ]
        group_changes = {}
        group_cache = {}
        changes = self._getChanges()
        for change in changes:
            for group in self._getGroupsByChange(change):
                groupid = id(group)
                try:
                    group_changes[groupid].append(change)
                except KeyError:
                    group_cache[groupid] = group
                    group_changes[groupid] = [change]

        # Build the groupset
        # TODO: make group compression configurable?
        group_sets = []
        for groupid, changelist in group_changes.items():
            group = group_cache[groupid]
            for stored in group_sets:
                # We don't need to compare the group with *all*
                # groups of this set. If the group is considered
                # equal to the first stored group, all other stored
                # groups are considered equal as well. (Otherwise
                # they wouldn't been there ...)
                if stored.changes == changelist and \
                        group._compare(stored.groups[0]):
                    stored.groups.append(group)
                    group = None
                    break

            if group is not None:
                group_sets.append(GroupSet([group], changelist, changes))

        return group_sets


    def _getGroupsByChange(self, change):
        """ Returns the matching groups for a particular change 

            @param change: The change to select
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @return: The group list
            @rtype: C{list}
        """
        selected_groups = []
        ignored_groups = []

        # the repos path is always *without* slash (see
        # subversion.Respository.__init__)
        repos_path = change.repos.path.decode("utf-8", "strict")

        # we guarantee, that directories end with a slash
        path = "%s%s" % (change.path, ["", "/"][change.isDirectory()])
        path = path.decode("utf-8", "strict")

        for group in self._settings.groups:
            subst = self._getDefaultSubst(group, repos_path, path)

            # if for_repos is set and does not match -> ignore
            if group.for_repos:
                match = group.for_repos.match(repos_path)
                if match:
                    subst.update(match.groupdict())
                else:
                    continue

            # if exclude_paths is set and does match -> ignore
            if group.exclude_paths and group.exclude_paths.match(path):
                continue

            # if for_paths is set and does not match -> ignore
            if group.for_paths:
                match = group.for_paths.match(path)
                if match:
                    subst.update(match.groupdict())
                else:
                    continue

            # store the substdict for later use
            for name, value in subst.items():
                group._sub_(name, value)

            (selected_groups, ignored_groups)[
                bool(group.ignore_if_other_matches)
            ].append(group)

        # BRAINER: theoretically there could be more than one group
        # in the ignore list, which would have to be ignored at all then.
        # (ignore_if_OTHER_MATCHES, think about it)
        # Instead we select them ALL, so the output isn't lost
        return selected_groups and selected_groups or ignored_groups


    def _getDefaultSubst(self, group, repos_path, path):
        """ Returns the default substitution dict

            @param group: The group to consider
            @type group: C{svnmailer.settings.GroupSettingsContainer}

            @param repos_path: The repository path
            @type repos_path: C{unicode}

            @param path: The change path
            @type path: C{unicode}

            @return: The initialized dictionary
            @rtype: C{dict}

            @exception svnmailer.subversion.Error: An error occured while
                accessing the subversion repository
        """
        from svnmailer.settings import modes

        runtime = self._settings.runtime
        author = runtime.author
        if not author and runtime.mode in (modes.commit, modes.propchange):
            author = runtime._repos.getRevisionAuthor(runtime.revision)

        subst = {
            'author'  : author or 'no_author',
            'group'   : group._name,
            'property': runtime.propname,
            'revision': runtime.revision and u"%d" % runtime.revision,
        }

        if group.extract_x509_author:
            from svnmailer import util

            x509 = util.extractX509User(author)
            if x509:
                from email import Header

                realname, mail = x509
                subst.update({
                    'x509_address': realname and "%s <%s>" % (
                        Header.Header(realname).encode(), mail) or mail,
                    'x509_CN': realname,
                    'x509_emailAddress': mail,
                })

        if group._def_for_repos:
            match = group._def_for_repos.match(repos_path)
            if match:
                subst.update(match.groupdict())

        if group._def_for_paths:
            match = group._def_for_paths.match(path)
            if match:
                subst.update(match.groupdict())

        return subst


    def _getSettings(self, options):
        """ Returns the settings object

            @param options: Command line options
            @type options: C{svnmailer.cli.SvnmailerOptionParser}

            @return: The settings object
            @rtype: C{svnmailer.config.ConfigFileSettings}

            @exception ConfigError: configuration error
        """
        from svnmailer import config

        try:
            return config.ConfigFileSettings(options)
        except config.Error, exc:
            import sys
            raise ConfigError, str(exc), sys.exc_info()[2]


    def _openRepository(self):
        """ Opens the repository

            @exception svnmailer.subversion.Error: Error while accessing the
                subversion repository
        """
        from svnmailer import subversion, util

        config = self._settings.runtime
        repos_path = util.filename.fromLocale(
            config.repository, config.path_encoding
        )
        if isinstance(repos_path, str):
            # !!! HACK ALERT !!!
            #
            # --path-encoding=none
            # subversion needs unicode as path and translates it
            # back to the locale, we try our best by translating
            # literally to unicode...
            repos_path = repos_path.decode("iso-8859-1", "strict")

        config._repos = subversion.Repository(repos_path)


    def _closeRepository(self):
        """ Closes the repository """
        try:
            self._settings.runtime._repos.close()
        except AttributeError:
            # That's ok
            pass


class GroupSet(object):
    """ Container object for a single groupset

        @ivar groups: The groups to process
        @type groups: C{list}

        @ivar changes: The changes that belong to the group
        @type changes: C{list}

        @ivar xchanges: The changes that don't belong to the
            group (only filled if show_nonmatching_paths = yes)
        @type xchanges: C{list}
    """
    
    def __init__(self, groups, changes, allchanges):
        """ Initialization

            @param groups: The groups to process
            @type groups: C{list}

            @param changes: The changes that belong to the group
            @type changes: C{list}

            @param allchanges: All changes
            @type allchanges: C{list}
        """
        from svnmailer.settings import xpath

        self.groups = groups
        self.changes = changes

        nongroups = groups[0].show_nonmatching_paths
        if nongroups == xpath.ignore:
            self.xchanges = None
        elif nongroups == xpath.yes:
            self.xchanges = [
                change for change in allchanges
                if change not in changes
            ]
        else:
            # no is default
            self.xchanges = []
