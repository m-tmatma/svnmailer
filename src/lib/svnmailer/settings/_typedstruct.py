# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0613
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
=======================
 Typed Data Structures
=======================

The classes defined in this module are responsible for the separation of
the settings logic from the application logic. Each container created by
`StructCreator` binds his member names to a set of functions, which get
some string input and covert it to the "proper" type -- which is, what
the application gets.

The `Member` class provides the interface for those conversion functions.
Each converter class should inherit from it. The `Struct` class is the base
class for all containers that want to be created by `StructCreator` (basically
because of its ``__metaclass__``).
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Member', 'MetaClass', 'Struct', 'StructCreator']

# global imports
from types import MethodType as instancemethod
from svnmailer import util


class Member(object):
    """ Base class for members descriptors

        :IVariables:
         - `mapper`: The associated mapper function (or ``None``)
         - `arg`: The custom initialization argument
         - `instance`: The owner instance
         - `param`: The descriptor parameter

        :Types:
         - `mapper`: ``callable``
         - `arg`: any
         - `instance`: `Struct`
         - `param`: any
    """
    def __init__(self, mapper, arg, param):
        """ Initialization

            :Parameters:
             - `mapper`: The associated mapper function (or ``None``)
             - `arg`: The custom initialization argument
             - `param`: The descriptor parameter

            :Types:
             - `mapper`: ``callable``
             - `arg`: any
             - `param`: any
        """
        self.mapper = mapper
        self.arg = arg
        self.param = param
        self.instance = None

        self.init()


    def init(self):
        """ Custom initialization """
        pass


    def premap(self, value):
        """ Premapper - passes through by default

            The premapper is called if the value is set before doing
            anything else.

            :note: It is not called if no mapper function is defined (or it
                   is ``None``).
    
            :param `value`: The value to premap
            :type `value`: any

            :return: The premapped value
            :rtype: any
        """
        return value


    def transform(self, value):
        """ Transformer - passes through by default

            Override this method in order to do any value transformation,
            e.g. compile the input string as regex or split it into a list.

            The `transform` method is called with the value returned from
            the `premap` method. The result is stored as final member value.

            :param `value`: The value to tranform
            :type `value`: any

            :return: The transformed value
            :rtype: any
        """
        return value


    def substitute(self, value, subst):
        r"""Substituter - passes through by default

            Use this method to do any dynamic processing on
            the retrieved value before it's being `postmap`\ped.

            :Parameters:
             - `value`: The value to substitute
             - `subst`: The substitution record

            :Types:
             - `value`: any
             - `subst`: ``dict``

            :return: The substituted value
            :rtype: any
        """
        return value


    def postmap(self, value):
        """ Postmapper - passes through by default

            The postmapper is called before the value is finally returned
            to the caller (after being substituted).

            :note: The postmapper is not called if no mapper function
                   is defined (or it is ``None``).

            :param `value`: The value to postmap
            :type `value`: any

            :return: The postmapped value
            :rtype: any
        """
        return value


class MetaClass(type):
    """ Metaclass for Struct """

    def __new__(mcs, name, bases, cdict):
        """ Constructor """
        try:
            del cdict['__dict__']
        except KeyError:
            """ ignore """
            pass
        cdict['__slots__'] = tuple(cdict.get('__slots__', ()))

        return type.__new__(mcs, name, bases, cdict)


class Struct(object):
    """ General structure stub """
    __metaclass__ = MetaClass

    def __init__(self, **kwargs):
        """ Stub Initialization

            :param `kwargs`: The initial member values
        """
        for name, value in kwargs.items():
            setattr(self, name, value)


class StructCreator(object):
    """ Struct creator class

        :CVariables:
         - `_BASESTRUCT`: Base class for all structs. This is used for
           type checking in ``__eq__`` and ``__ne__``
         - `_DEFAULTSTRUCT`: The default struct class
         - `_DEFAULTMEMBER`: The default member class

        :IVariables:
         - `_cls`: The struct class to use
         - `_members`: The prepared members
           (``{('name', 'alias', 'alias', ...): (spec, param), ...}``)
         - `_aliases`: The member aliases. (``{'alias': 'real', ...}``)
         - `_names`: The member names as ``tuple`` (without aliases)
         - `_eqignore`: Member names to be ignored in EQ comparisons
           (``dict`` for faster lookup)

        :Types:
         - `_BASESTRUCT`: `MetaClass`
         - `_DEFAULTSTRUCT`: `Struct`
         - `_DEFAULTMEMBER`: `Member`

         - `_cls`: `MetaClass`
         - `_members`: ``dict``
         - `_aliases`: ``dict``
         - `_names`: ``tuple``
         - `_eqignore`: ``dict``
    """
    _BASESTRUCT    = Struct
    _DEFAULTSTRUCT = Struct
    _DEFAULTMEMBER = Member

    def __init__(self, members, cls = None, aliases = None, typemap = None,
                 eqignore = None):
        """ Initialization
    
            :Parameters:
             - `cls`: The class to create. It should inherit from `Struct`

             - `members`: The list of members. This is either a list of
               strings (representing the name) or a dict, where each key
               is the member name and the value specifies the type of the
               member. Actually, a plain list a special case of the latter.
               It can also be written as a ``dict`` with all values set to
               ``None``. (``{'name': any, ...}``)

             - `aliases`: The member aliases. (``{'alias': 'real', ...}``)

             - `typemap`: The type map (``{'type': descriptor class}``)

             - `eqignore`: Member names to be ignored in EQ comparisons. If
               ``None``, different containers are always considered different.

            :Types:
             - `cls`: `Struct`
             - `members`: iterable or ``dict``
             - `aliases`: ``dict``
             - `typemap`: ``dict``
             - `eqignore`: sequence
        """
        self._cls = cls or self._DEFAULTSTRUCT
        self._aliases = aliases or {}

        self._members, self._names = self._prepareMembers(members, typemap)

        if eqignore is None:
            eqignore = None
        else:
            eqignore = dict.fromkeys(eqignore)
        self._eqignore = eqignore


    def create(self, maps = None, arg = None, initkw = None):
        """ Creates a new struct with extended properties

            :Parameters:
             - `maps`: The mappers to use (``{'membername': mapper, ...}``)
             - `arg`: Initializer argument for the descriptors
             - `initkw`: Initial values of members
               (``{'name', 'value', ...}``)

            :Types:
             - `maps`: ``dict``
             - `arg`: any
             - `initkw`: ``dict``

            :return: A new instance of the class
            :rtype: `Struct`

            :exception AssertionError: The parameter set was inconsistent
        """
        cls = self._cls
        private = self._createPrivate()

        # merge alias maps to real
        maps = dict(maps or {})
        for alias, real in self._aliases.items():
            if maps.has_key(alias):
                maps[real] = maps[alias]
                del maps[alias]

        # add members
        space = self._generateMembers(private, maps, arg)
        space.update({'__module__': cls.__module__, '__slots__': self._names})

        # create new class
        cls = self._createMetaClass(cls.__name__, (cls,), space)

        # add __special__s
        for name, func in self._generateSpecials(private).items():
            setattr(cls, name, instancemethod(func, None, cls))

        # return instance of the new class
        return cls(**(initkw or {}))


    def _generateSpecials(self, private):
        """ Generates the special methods

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The special methods (``{'name': method, ...}``)
            :rtype: ``dict``
        """
        space = {
            '__setitem__': self._generateSetItem(private),
            '__getitem__': self._generateGetItem(private),
            '__repr__'   : self._generateRepr(private),
            '__call__'   : self._generateCall(private),
        }
        if self._eqignore is not None:
            space.update({
                '__eq__': self._generateEq(private),
                '__ne__': self._generateEq(private, False),
            })

        return space


    def _generateMembers(self, private, maps, arg):
        """ Generates the members descriptors

            :Parameters:
             - `private`: The private data container
             - `maps`: The mappers to use (``{'membername': mapper, ...}``)
             - `arg`: Initializer argument for the descriptors

            :Types:
             - `private`: `Private`
             - `maps`: ``dict``
             - `arg`: any

            :return: The member descriptors (``{'name': descriptor, ...}``)
            :rtype: ``dict``

            :exception AssertionError: Something was inconsistent or wrong
        """
        space = {}

        # optimize for speed and readability
        descriptor = self._createDescriptor
        entries = dict.fromkeys
        mapper  = maps.get
        update  = space.update

        for names, (spec, param) in self._members.items():
            name = names[0]
            update(entries(names,
                descriptor(name, private, spec(mapper(name), arg, param))
            ))

        return space


    def _prepareMembers(self, members, typemap):
        """ Prepares the member specs for later processing

            :Parameters:
             - `members`: The list of members. This is either a list of
               strings (representing the name) or a dict, where each key
               is the member name and the value specifies the type of the
               member. Actually, a plain list a special case of the latter.
               It can also be written as a dict with all values set to
               ``None``. (``{'name': any, ...}``)

             - `typemap`: The type map (``{'type': descriptor class}``)

            :Types:
             - `members`: sequence or mapping
             - `typemap`: ``dict``

            :return: The prepared members (``{('name', 'alias', 'alias', ...):
                     (spec, param), ...}``) and the member names as sequence
                     (``('name', ...)``)
            :rtype: ``tuple``

            :exception AssertionError: Something in the member or typemap
                                       spec is bogus
        """
        typemap = dict(typemap or {})
        typemap[None] = typemap.get(None, self._DEFAULTMEMBER)

        try:
            items = members.items()
        except AttributeError:
            members = dict.fromkeys(members)
            items = members.items()

        # build reverse alias dict
        raliases = {}
        for alias, real in self._aliases.items():
            if alias.startswith('__'):
                raise AssertionError(
                    "%r is not allowed as alias name" % (alias,))
            if real not in members:
                raise AssertionError(
                    "Alias %r points to unknown member %r" % (alias, real))

            raliases.setdefault(real, []).append(alias)

        # build members dict
        newmembers = {}
        for name, spec in items:
            if name.startswith('__'):
                raise AssertionError(
                    "%r is not allowed as member name" % (name,))

            if spec is None or isinstance(spec, basestring):
                param = None
            else:
                try:
                    spec, param = spec
                except (TypeError, ValueError):
                    raise AssertionError('Invalid member specification %r' %
                        (spec,))

            try:
                spec = typemap[spec]
            except KeyError:
                raise AssertionError('Invalid typemap definition for %r' %
                    (name,))

            names = tuple([name] + raliases.get(name, []))
            newmembers[names] = (spec, param)

        return newmembers, tuple(members.keys())


    def _generateSetItem(self, private):
        """ Returns the ``__setitem__`` method

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The method function
            :rtype: ``callable``
        """
        def __setitem__(this, name, value):
            """ Sets a key-value pair for substitutions

                :Parameters:
                 - `name`: The name to substitute
                 - `value`: The value to be used for subsitution

                :Types:
                 - `name`: ``unicode``
                 - `value`: ``unicode``
            """
            private.subst[name] = value

        return __setitem__


    def _generateGetItem(self, private):
        """ Returns the ``__getitem__`` method

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The method function
            :rtype: ``callable``
        """
        def __getitem__(this, name):
            """ Returns substitution value

                :param `name`: The name to retrieve
                :type `name`: ``unicode``

                :return: The associated substitution value
                :rtype: ``unicode``

                :exception KeyError: The key was not found
            """
            return private.subst[name]

        return __getitem__


    def _generateRepr(self, private):
        """ Returns the ``__repr__`` method

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The method function
            :rtype: ``callable``
        """
        cls = self._cls

        def __repr__(this):
            """ Returns a representation of the struct for debugging

                :return: A string representation of the struct
                :rtype: ``str``
            """
            members = ',\n    '.join([
                "%s = %r" % (name, val) for name, val in [(name, val)
                for name, val in private.values.items()
            ] if val is not None])
            if members:
                members = "\n    %s\n" % members

            return "%s.%s(%s)" % (
                cls.__module__, cls.__name__, members
            )

        return __repr__


    def _generateCall(self, private):
        """ Returns the __call__ method

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The method function
            :rtype: ``callable``
        """
        def __call__(this, name):
            """ Returns a value specified by `name`

                :param `name`: The key to retrieve. Possible values are:
                               ``members``, ``subst``, ``values``
                :type `name`: ``str``

                :return: The requested value
                :rtype: any

                :exception KeyError: `name` was not recognized
            """
            if name == 'members':
                return private.members
            elif name == 'subst':
                return util.ReadOnlyDict(private.subst)
            elif name == 'values':
                return util.ReadOnlyDict(private.values)

            raise KeyError("%s not recognized")

        return __call__


    def _generateEq(self, private, iseq = True):
        """ Returns ``__eq__``/``__ne__`` descriptor

            :param `private`: The private data container
            :type `private`: `Private`

            :return: The method function
            :rtype: ``callable``
        """
        base = self._BASESTRUCT

        def __eq__(this, other):
            """ Compares with `other` for equality

                :param `other`: The other object to compare
                :type `other`: any

                :return: Are the objects equal?
                :rtype: ``bool``
            """
            if not(isinstance(this, base) and isinstance(other, base)):
                return False

            ignore = private.eqignore
            attrs = [name for name in private.members if name not in ignore]

            for name in attrs:
                try:
                    if getattr(this, name) != getattr(other, name):
                        return False
                except AttributeError:
                    return False

            return True

        if iseq:
            return __eq__

        def __ne__(this, other):
            """ Negates ``__eq__`` """
            return not(__eq__(this, other))

        return __ne__


    def _createPrivate(self):
        """ Returns a new `Private` instance

            :return: A new `Private` instance
            :rtype: `Private`
        """
        return Private(self._names, self._eqignore)


    def _createDescriptor(self, name, private, member):
        """ Returns a new `Descriptor` instance

            :Parameters:
             - `name`: The name of the member
             - `private`: The private data container
             - `member`: The actual member instance

            :Types:
             - `name`: ``str``
             - `private`: `Private`
             - `member`: `Member`

            :return: A new `Descriptor` instance
            :rtype: `Descriptor`
        """
        return Descriptor(name, private, member)


    def _createMetaClass(self, name, bases, cdict):
        """ Returns a new `MetaClass` instance

            :Parameters:
             - `name`: The name of the new class
             - `bases`: The base classes
             - `cdict`: The initial dictionary

            :Types:
             - `name`: ``str``
             - `bases`: ``tuple``
             - `cdict`: ``dict``

            :return: A new `MetaClass` instance
            :rtype: `MetaClass`
        """
        return MetaClass(name, bases, cdict)


class Private(object):
    """ Private container class for Struct internals

        :IVariables:
         - `members`: The list of members
         - `eqignore`: List of ignorable members in comparisions (as
           ``dict`` for faster lookup)
         - `values`: The member values
         - `subst`: The substitution record

        :Types:
         - `members`: ``tuple``
         - `eqignore`: ``dict``
         - `values`: ``dict``
         - `subst`: ``dict``
    """

    def __init__(self, names, eqignore):
        """ Initialization

            :Parameters:
             - `names`: The member names to serve
             - `eqignore`: The member names to ignore in comparisons

            :Types:
             - `names`: ``tuple``
             - `eqignore`: sequence
        """
        self.members  = names
        self.eqignore = eqignore
        self.values   = {}
        self.subst    = {}


class Descriptor(object):
    """ Member descriptor class

        :IVariables:
         - `name`: The name of the member
         - `private`: The private data container
         - `member`: The actual member instance

        :Types:
         - `name`: ``str``
         - `private`: `Private`
         - `member`: `Member`
    """

    def __init__(self, name, private, member):
        """ Initialization

            :Parameters:
             - `name`: The name of the member
             - `private`: The private data container
             - `member`: The actual member instance

            :Types:
             - `name`: ``str``
             - `private`: `Private`
             - `member`: `Member`
        """
        self.name = name
        self.private = private
        self.member = member


    def __set__(self, instance, value):
        """ Sets the member value """
        member = self.member
        member.instance = instance
        try:
            if member.mapper is not None:
                value = member.premap(value)
            value = member.transform(value)
        finally:
            member.instance = None

        self.private.values[self.name] = value 


    def __get__(self, instance, owner):
        """ Gets the member value """
        if instance is None:
            return None

        private = self.private
        member = self.member
        member.instance = instance
        try:
            value = member.substitute(
                private.values.get(self.name),
                util.ReadOnlyDict(private.subst)
            )
            if member.mapper is not None:
                value = member.postmap(value)
        finally:
            member.instance = None

        return value


    def __delete__(self, instance):
        """ Deletes the value from the dict (keeps the name) """
        try:
            del self.private.values[self.name]
        except KeyError:
            """ didn't exist, well... """
            pass
