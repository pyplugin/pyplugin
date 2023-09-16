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

This paradigm naturally puts an emphasis on the structure of applications and less on its orchestration.
This allows consumers of applications to easily swap or add plugins while guaranteeing conformity to API
contracts.

Install
--------
The package is available on pypi and can be installed with::

    pip install plugin

For the latest experimental version::

    pip install plugin --pre

Quickstart
-----------------

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

or by explicitly calling the :meth:`load` method (useful for passing additional load options)::

    client = db_client.load()

Unloading a Plugin
###################
We can define an unload operation upon definition::

    from pyplugin import plugin

    @plugin(
        unload_callable=lambda instance: instance.disconnect()
    )
    def db_client(uri):
        return db_library.connect(uri)

Now if we call the :meth:`unload` method, the :code:`unload_callable` will be called.

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
