# -*- coding: utf-8 -*-
# pylint: disable-msg = W0613
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
Typed Data Structures
=====================

This module provides helpers for creating typed data structures.

Basic Usage
-----------
In order to create a new data structure, you inherit from C{Struct} and
define the members like so (the booleans are explained later)::

    class MyStruct(typedstruct.Struct):
        __slots__ = typedstruct.members(locals(), {
            'name1': None,
            # ... and/or ...
            'name2': <type>,
            # ... and/or ...
            'name3': (<type>, <param>),
        })

If there are no fixed types at all (always C{None}, you can still benefit
from the features of the L{Struct} class and further write it a bit simpler::

    class MyStruct(typedstruct.Struct):
        __slots__ = typedstruct.members(locals(), (
            'name1', 'name2', ...
        ))

Well, the main reason for using the Struct class is to get some level of type
safety and automatic conversion without a complex written definition of
C{property} for each and every member (it uses some property like descriptors
internally, however). This encapsulates a lot of ugly logic and error handling
(more or less) into a single piece of code and makes the member definitions
I{much} easier to read and maintain. For example, you can create a struct
member of type C{regex}. Now you assign a string to this member and it is
automatically compiled to a regex, which you get, if you retrieve the
value later. As you'll see, the C{regex} type needs to be defined as a class
which should be inherited from the L{MemberDescriptor} class and assigned
to the C{regex} type name via a type mapping dict::

    class RegexMember(typedstruct.MemberDescriptor):
        def transform(self, value, arg):
            import re
            return re.compile(value)
    # ...
    typemap = {'regex': RegexMember}
    # ...
    class MyStruct(typedstruct.Struct):
        __slots__ = typedstruct.members(locals(), {
            'checker': 'regex',
        }, typemap = typemap)
    # ...
    store = MyStruct()
    store.checker = r'[a-zA-Z]$'
    # ...
    if store.checker.match(stringtocheck):
        # do something

Constraints
-----------
Member names must be valid python identifiers. Further all names starting
I{and} ending with underscores are reserved for L{Struct}'s or python's
own purposes.
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['members', 'Struct', 'MemberDescriptor']

# global imports
from svnmailer import util


class MemberDescriptor(object):
    """ Base class for members descriptors

        @ivar name: The name of the member
        @type name: C{str}

        @ivar param: The descriptor parameter
        @type param: any

        @ivar __private: The reference to the private container
        @type __private: C{StructPrivate}
    """
    def __init__(self, name, private, param = None):
        """ Initialization """
        self.name = name
        self.param = param
        self.__private = private


    def __get__(self, instance, owner):
        """ Gets the member value """
        if instance is None:
            return None

        priv = self.__private
        arg = priv.getArg(instance)
        mapper = priv.getMaps(instance).get(self.name)

        value = self.substitute(
            priv.getValues(instance).get(self.name),
            util.ReadOnlyDict(priv.getSubst(instance)),
            arg
        )
        if mapper is not None:
            value = self.postmap(value, mapper, arg)

        return value


    def __set__(self, instance, value):
        """ Sets the members value """
        priv = self.__private
        arg = priv.getArg(instance)
        mapper = priv.getMaps(instance).get(self.name)

        if mapper is not None:
            value = self.premap(value, mapper, arg)

        priv.getValues(instance)[self.name] = self.transform(value, arg)


    def __delete__(self, instance):
        """ Raises an AttributeError """
        raise AttributeError(
            "member '%s' cannot be deleted" % self.name
        )


    def premap(self, value, mapper, arg):
        """ Premapper - passes through by default

            The premapper is called if the value is set before doing
            anything else.

            @note: It is not called if no mapper function is defined (or it
                is C{None}).
    
            @param value: The value to premap
            @type value: any

            @param mapper: The mapping argument
            @type mapper: any

            @param arg: The argument used for struct initialization
            @type arg: any
        """
        return value


    def transform(self, value, arg):
        """ Transformer - passes through by default

            Override this method in order to do any value transformation,
            e.g. compile the input string as regex or split it into a list.

            The C{transform} method is called with the value returned from
            the L{premap} method. The result is stored as final member value.

            @param value: The value to tranform
            @type value: any

            @param arg: The argument used for struct initialization
            @type arg: any

            @return: The transformed value
            @rtype: any
        """
        return value


    def substitute(self, value, subst, arg):
        """ Substituter - passes through by default

            Use this method to do any dynamic processing on
            the retrieved value before it's being L{postmap}ped.

            @param value: The value to substitute
            @type value: any

            @param subst: The substitution dictionary
            @type subst: C{dict}

            @param arg: The argument used for struct initialization
            @type arg: any

            @return: The substituted value
            @rtype: any
        """
        return value


    def postmap(self, value, mapper, arg):
        """ Postmapper - passes through by default

            The postmapper is called before the value is finally returned
            to the caller (after being substituted).

            @note: The postmapper is not called if no mapper function
                is defined (or it is C{None}).

            @param value: The value to postmap
            @type value: any

            @param mapper: The mapping argument
            @type mapper: any

            @param arg: The argument used for struct initialization
            @type arg: any
        """
        return value


class Struct(object):
    """ General structure stub """
    _set_ = _members_ = None # satisfy pylint

    def __new__(cls, _maps_ = None, _arg_ = None, **kwargs):
        """ Object creation

            @param _maps_: The maps to use
            @type _maps_: C{dict}

            @param _arg_: The opaque argument for custom descriptors
            @type _arg_: any
        """
        self = object.__new__(cls)
        self._set_.private.initInstance(self, _maps_, _arg_)

        return self


    def __init__(self, _maps_ = None, _arg_ = None, **kwargs):
        """ Stub Initialization

            @param _maps_: unused, but consistent to L{__new__}
            @type _maps_: C{dict}

            @param _arg_: unused, but consistent to L{__new__}
            @type _arg_: any
        """
        for name, value in kwargs.items():
            self._set_(name, value)


    def __del__(self):
        """ Removes all references from private container """
        self._set_.private.removeInstance(self)


    def __repr__(self):
        """ Representation for debugging purposes

            @return: A pythonic representation of the struct
            @rtype: C{str}
        """
        return "%s.%s(\n    %s\n)" % (
            self.__class__.__module__,
            self.__class__.__name__,
            ',\n    '.join([
                "_maps_ = %r" % self._set_.private.getMaps(self),
                "_arg_ = %r" % self._set_.private.getArg(self),
                ] + [
                "%s = %r" % (name, getattr(self, name))
                for name in self._members_
                if getattr(self, name) is not None
            ])
        )


def members(space, the_members, aliases = None, typemap = None):
    """ supply the member and slot entries

        @param space: The namespace to pollute
        @type space: C{dict}

        @param the_members: The member list / description
        @type the_members: C{tuple} or C{dict}

        @param aliases: The member name aliases
        @type aliases: C{dict}

        @param typemap: The type mapping table
        @type typemap: C{dict}

        @return: The list of __slots__ to use.
        @rtype: C{list}
    """
    if type(the_members) in [tuple, list]: 
        the_members = dict.fromkeys(the_members)
    names = the_members.keys()

    private = StructPrivate(names, aliases or {})
    typemap = dict(typemap or {})
    typemap[None] = MemberDescriptor

    for name, param in the_members.items():
        if name[:1] == '_' and name[-1:] == '_':
            raise AttributeError("%r is not allowed as member name" % name)

        if type(param) in (tuple, list):
            space[name] = typemap[param[0]](name, private, param[1])
        else:
            space[name] = typemap[param](name, private)

    space.update({
        '_set_'    : StructSetDescriptor(private),
        '_sub_'    : StructSubDescriptor(private),
        '_members_': StructMembersDescriptor(private),
        '_dict_'   : StructDictDescriptor(private),
    })

    return names

# ====================================================================
# PRIVATE STUFF
# ====================================================================

class StructPrivate(object):
    """ Private container class for Struct internals """

    def __init__(self, names, aliases):
        """ Initialization

            @param names: The member names to serve
            @type names: C{tuple}

            @param aliases: The name mappings
            @type aliases: C{dict}
        """
        self.members = tuple(names)
        self.aliases = util.ReadOnlyDict(aliases)
        self.values  = {}
        self.subst   = {}
        self.maps    = {}
        self.args    = {}


    def initInstance(self, instance, maps, arg):
        """ Initializes the class for a particular instance

            @param instance: The instance in question
            @type instance: C{object}

            @param maps: The maps to use
            @type maps: C{dict}

            @param arg: The initialization argument
            @type arg: any
        """
        this = id(instance)

        # merge alias maps to real
        maps = dict(maps or {})
        for alias, real in self.aliases.items():
            if maps.has_key(alias):
                maps[real] = maps[alias]
                del maps[alias]

        self.maps[this]   = util.ReadOnlyDict(maps)
        self.args[this]   = arg
        self.values[this] = {}
        self.subst[this]  = {}


    def removeInstance(self, instance):
        """ Removes all data, referring to a particular instance

            @param instance: The instance in question
            @type instance: C{object}
        """
        this = id(instance)

        try:
            del self.args[this]
            del self.maps[this]
            del self.values[this]
            del self.subst[this]
        except KeyError:
            raise RuntimeError("%r was not properly initialized" % self)


    def getValues(self, instance):
        """ Returns the value dict for the particular instance

            @param instance: The instance in question
            @type instance: C{object}

            @return: The value dictionary
            @rtype: C{dict}
        """
        this = id(instance)
        return self.values[this]


    def getSubst(self, instance):
        """ Returns the subst dict for the particular instance

            @param instance: The instance in question
            @type instance: C{object}

            @return: The substitution dict
            @rtype: C{dict}
        """
        this = id(instance)
        return self.subst[this]


    def getMaps(self, instance):
        """ Returns the map dict for the particular instance

            @param instance: The instance in question
            @type instance: C{object}

            @return: The map dictionary
            @rtype: C{dict}
        """
        this = id(instance)
        return self.maps[this]


    def getArg(self, instance):
        """ Returns the arg for the particular instance 

            @param instance: The instance in question
            @type instance: C{object}

            @return: The arg used for initialization
            @rtype: any
        """
        this = id(instance)
        return self.args[this]


class StructDescriptor(object):
    """ Base class for struct descriptors

        @ivar private: The private data container
        @type private: C{StructPrivate}
    """
    def __init__(self, private):
        """ Initialization

            @param private: The private data container
            @type private: C{StructPrivate}
        """
        self.private = private


    def __set__(self, instance, value):
        """ setting is not allowed """
        raise AttributeError("attribute is read-only")


    def __delete__(self, instance):
        """ deleting is not allowed """
        raise AttributeError("attribute is read-only")


class StructSetDescriptor(StructDescriptor):
    """ _set_ descriptor """

    def __get__(self, instance, owner):
        """ Returns an aliasing setter function """
        def aliassetter(name, value):
            """ Set the self.name = value

                @param name: Name of the struct member or an alias
                @type name: C{str}

                @param value: Value of the struct member
                @type value: any

                @exception AttributeError: The specified struct member doesn't
                    exist (nor is it an alias)
            """
            name = self.private.aliases.get(name, name)
            if name[:1] == '_' and name[-1:] == '_':
                raise AttributeError("%r is not a struct member" % name)

            setattr(instance or owner, name, value)

        # starting point for the Struct class
        aliassetter.private = self.private

        return aliassetter


class StructSubDescriptor(StructDescriptor):
    """ _sub_ descriptor """

    def __get__(self, instance, owner):
        """ Returns an aliasing setter function """

        def subsetter(name, value, default = False):
            """ Sets a key-value-pair for substitutions

                If C{default} is true and the name already exists,
                it will not be overidden.

                @param name: The key
                @type name: C{str}

                @param value: The value
                @type value: C{str}

                @param default: Is the supplied value a default?
                @type default: C{bool}
            """
            if instance is None:
                raise AttributeError(
                    "%s._sub_ only works on instances" % owner.__name__
                )

            subst = self.private.getSubst(instance)
            if not default or not subst.has_key(name):
                subst[name] = value

        def getdict():
            """ Returns the current dict (read-only) """
            return util.ReadOnlyDict(self.private.getSubst(instance))

        subsetter.dict = getdict
        return subsetter


class StructMembersDescriptor(StructDescriptor):
    """ _members_ descriptor """
    def __get__(self, instance, owner):
        """ Returns the struct members as tuple """
        return self.private.members


class StructDictDescriptor(StructDescriptor):
    """ _dict_ descriptor """
    def __get__(self, instance, owner):
        """ Returns the values dict read-only """
        if instance is None:
            return util.ReadOnlyDict.fromkeys(self.private.members)

        return util.ReadOnlyDict(self.private.getValues(instance))
