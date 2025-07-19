.. _getting_started:

Getting Started
===================

Introduction
-------------
Plugins are arbitrary callables. They can declare other plugins as requirements while operating under
certain guarantees:

- A plugin can be loaded (i.e. called) exactly once until it is unloaded.
- A plugin's dependencies will be loaded before.
- A plugin's loaded dependents will be reloaded after.
- When a plugin is unloaded, its loaded dependents will be unloaded before.

This paradigm naturally puts an emphasis on the structure of packages applications and less on its orchestration.
This allows consumers of applications to easily swap or add plugins while guaranteeing conformity to API
contracts.

Install
--------
```
pip install pyplugin
```

Quickstart
-----------------

This quickstart guide is intended to give you the bare bones needed to begin writing simple plugins. For thorough
documentation, please see the :ref:`user_guide`.

Defining a Plugin
#################

The fastest way to define a plugin is by using the built-in decorator::

    from pyplugin import plugin

    @plugin
    def db_client(uri):
        return db_library.connect(uri)

Loading a Plugin
#################

You can load the plugin by simply calling it::

    client = db_client()

or by explicitly calling the :meth:`~pyplugin.base.Plugin.load` method::

    client = db_client.load()


Plugin Requirements
++++++++++++++++++++

We can define prerequisite plugins that will and must be loaded before loading::

    from pyplugin import plugin

    @plugin
    def db_client(uri):
        return db_library.connect(uri)

    @plugin(requires="db_client")
    def db_writer(db_client):
        def func(doc):
            return db_client.insert_one(doc)
        return func

Note: Plugins are automatically named and registered under their fully-qualified dot-delimited package-name with
using :code:`__name__`. To set the name, use the :code:`name` argument.

Now to use :code:`db_writer`, :code:`db_client` must be loaded (or it will attempt to load). In addition, this
allows consumers of this library an opportunity to swap :code:`db_client` with a custom user-defined implementation.
For example::

    # User Code (Option 1)
    from my_library import db_client

    db_client.load(uri="mongodb://localhost:27018")

    # User Code (Option 2)
    from my_library import db_client
    from pyplugin import plugin, register

    @plugin
    class DictDB(dict):
        def insert_one(doc):
            self[doc["_id"]] = doc

    # Replace (Option 1)
    replace_registered_plugin("db_client", DictDB)

    # Replace (Option 2)
    db_client.replace_with(DictDB)

Now whenever :code:`db_writer` is used, it will use the new :code:`DictDB`.

Unloading a Plugin
###################
We can define an unload operation upon definition::

    from pyplugin import plugin

    @plugin(
        unload_callable=lambda instance: instance.disconnect()
    )
    def db_client(uri):
        return db_library.connect(uri)

Now if we call the :meth:`~pyplugin.base.Plugin.unload` method, the :code:`unload_callable` will be called.
Before a plugin is unloaded, any dependent plugins are unloaded first. For example, unloading :code:`db_client` will
result in :code:`db_writer` to be unloaded beforehand.

Loading the Plugin Again
#########################
Now, say we want to load :code:`db_client` again with a different :code:`uri`::

    client = db_client("mongodb://localhost:27017")
    client = db_client("mongodb://localhost:27018")

Unravelling the calls this will be equivalent to::

    client = db_client.load("mongodb://localhost:27017", conflict_strategy="replace")
    > client = db_library.connect("mongodb://localhost:27017")
    client = db_client.load("mongodb://localhost:27018", conflict_strategy="replace")
    > db_client.unload()
    >> db_library.disconnect("mongodb://localhost:27017")
    > client = db_library.connect("mongodb://localhost:27018")

