.. _user_guide:

User Guide
===========

Introduction
-------------
Plugins are arbitrary callables. They can declare other plugins as requirements while operating under
certain guarantees:

- A plugin can be loaded (i.e. called) exactly once until it is unloaded.
- A plugin's dependencies will be loaded before.
- A plugin's loaded dependents will be reloaded after.
- When a plugin is unloaded, its loaded dependents will be unloaded before.

This paradigm naturally puts an emphasis on the structure of packages and applications and less on its orchestration.
This allows consumers of applications to easily swap or add plugins while guaranteeing conformity to API
contracts.

Install
--------
The package is currently **not available** on pypi pending a `PEP 541 request <https://github.com/pypi/support/issues/3063>`_

The package can be configured as a Github dependency in a :code:`requirements.txt` ::

    pyplugin @ git+https://github.com/pyplugin/pyplugin@main

or to pin to a tag ::

    pyplugin @ git+https://github.com/pyplugin/pyplugin@v0.1

Defining a Plugin
------------------

The fastest way to define a plugin is by using the built-in decorator::

    from pyplugin import plugin

    @plugin
    def db_client(uri):
        return db_library.connect(uri)


We may also use the :class:`~pyplugin.base.Plugin` class::

    from pyplugin import Plugin

    my_plugin = Plugin(my_func)

We can also extend the :class:`~pyplugin.base.Plugin` class and use the built-in decorator
for ease of use::

    from pyplugin import Plugin, plugin

    @plugin(cls=Plugin)
    def db_client(uri):
        return db_library.connect(uri)


Naming & Registering
#######################

Plugins are globally registered under their fully-qualified dot-delimited package-name with using :code:`__name__`.
To change this, you may pass in :code:`name`::

    @plugin(name="my_plugin")
    def db_client(uri):
        return db_library.connect(uri)


Plugins are automatically registered globally under their name. To register or unregister plugins, there are the
:func:`~pyplugin.base.register` and :func:`~pyplugin.base.unregister` functions.

Anonymous Plugins
++++++++++++++++++

It may also be desirable to anonymize plugins so that they are not automatically registered upon definition::

    @plugin(anonymous=True)
    def db_client(uri):
        return db_library.connect(uri)

This may be useful if you want to defer registering a plugin without having to unregister it first::

    @plugin
    def db_client(uri):
        return db_library.connect(uri)

    @plugin(anonymous=True)
    def replacement_for_db_client():
        return foo

    register(
        replacement_for_db_client,
        name="special_name",
    )

Passing Plugin Instance
+++++++++++++++++++++++

It may be beneficial in some cases to have the plugin passed in to the load callable, this is possible with the
:code:`bind` argument::

    @plugin(bind=True)
    def db_client(self, uri):
        assert self.get_full_name() == "db_client"
        return db_library.connect(uri)


Plugin Type Definition
+++++++++++++++++++++++

By default, plugins will cache the return value type in the :attr:`~pyplugin.base.Plugin.type` attribute, including a
:attr:`~pyplugin.base.Plugin.is_class_type` attribute, which means that the plugin returned a class type and
:attr:`~pyplugin.base.Plugin.type` is that class.

You can explicitly set the type when defining a plugin::

    @plugin(type=DatabaseClient)
    def db_client(uri):
        return db_library.connect(uri)

You may also choose for your plugins to error if the return value does not match the type using the
:code:`enforce_type` argument (default: False).

See :ref:`settings` for changing these settings (:code:`infer_type` and :code:`enforce_type`).


Requirements
#############

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

Now to load :code:`db_writer`, :code:`db_client` must be passed in or loaded (or it will attempt to load).

Defining Requirements
++++++++++++++++++++++

The :code:`requires` parameter can be in a few different forms:

1. :code:`str`: This will call :func:`~pyplugin.base.lookup_plugin` before loading to find the dependency.
2. :class:`~pyplugin.base.Plugin`: This will explicitly pin a dependency to a specific plugin.
3. :code:`tuple`: A tuple where the first element is 1 or 2 and the second element is the keyword arg we will pass to
   the plugin.
4. :class:`~pyplugin.base.PluginRequirement`: Which is a dataclass with two elements described in 3.
5. :code:`Iterable`: An iterable of any of the above.


.. _dynamic_requirements:

Dynamic Requirements
+++++++++++++++++++++

It is possible to load a plugin from within another plugin. By default, this will mark the loaded plugin as a
requirement of the calling plugin as if it was defined in :code:`requires`. For example::

    @plugin
    def upstream(arg=4):
        return arg

    @plugin
    def dyn_plugin():
        return upstream()

    assert dyn_plugin() == 4
    upstream(arg=5)
    assert dyn_plugin.instance == 5

Reloading :code:`upstream` with :code:`arg=5` also reloaded :code:`dyn_plugin`.

See :ref:`settings` :code:`dynamic_requirements` for more.

Replacing Plugins
++++++++++++++++++
This requirement framework allows consumers of this library an opportunity to swap :code:`db_client` with a
custom user-defined implementation. For example::

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

See :func:`~pyplugin.base.replace_registered_plugin` and :meth:`~pyplugin.base.Plugin.replace_with` for more.

Note: The :meth:`~pyplugin.base.Plugin.replace_with` method by default will keep the type of the original plugin
(changed with the :code:`replace_type` argument).

Loading a Plugin
-----------------

You can load the plugin by simply calling it::

    client = db_client()

or by explicitly calling the :meth:`~pyplugin.base.Plugin.load` method::

    client = db_client.load()

Plugin load can be broken down into the following steps:

1. Find, resolve, and cross-correlate dependencies
2. Load dependencies
3. Resolve any load conflicts (e.g. unload this plugin first then continue on)
4. Call the underlying callable
5. Reload loaded dependents

Find, Resolve, and Cross-Correlate Dependencies
#################

Before loading, all dependencies defined in :attr:`~pyplugin.base.Plugin.requirements` will be resolved.
If the dependency is a :code:`str`, then :func:`~pyplugin.base.lookup_plugin` will be used which will first check
if there's a registered plugin with the same name, then it will optionally attempt to import the name and register the
plugin automatically. If :ref:`dynamic_requirements` are enabled, this will also be handled.

Afterward the resolved dependency will be added to the :attr:`~pyplugin.base.Plugin.dependencies` map
(which maps kwarg to plugin). In addition, we will append this plugin to each dependency's
:attr:`~pyplugin.base.Plugin.dependents` list.

Load Dependencies
#################

In this step, the calling arguments are inspected. For each keyword argument which are the keys of
the :attr:`~pyplugin.base.Plugin.dependencies` map, if the keyword is not in the varkwargs used to load the plugin, it
will attempt to load the mapped plugin (without any arguments).

Resolve Load Conflicts
#################

If the plugin is already loaded, and the arguments are different, this is considered a load conflict. You
can pass in :code:`conflict_strategy` to :meth:`~pyplugin.base.Plugin.load` to resolve this which can be one of
"keep_existing", "replace", "force", or "error" (default: "replace").

- :code:`keep_existing`: Ignore the load request
- :code:`replace`: First call :meth:`~pyplugin.base.Plugin.unload` before attempting to load
- :code:`force`: Like :code:`replace` but also will apply if :attr:`load_args` and :attr:`load_kwargs` match.
- :code:`error`: raises :class:`~pyplugin.base.exceptions.PluginLoadError`.

Call Underlying Callable
#################

The plugin's underlying :attr:`~pyplugin.base.Plugin.load_callable` is then passed the arguments and keyword arguments
and the return value is then saved.

Reload Loaded Dependents
#################

The plugin's loaded dependents are then reloaded with the new return value of the plugin.

Unloading a Plugin
-------------------

We can define an unload operation upon definition::

    from pyplugin import plugin

    @plugin(
        unload_callable=lambda instance: instance.disconnect()
    )
    def db_client(uri):
        return db_library.connect(uri)

Now if we call the :meth:`~pyplugin.base.Plugin.unload` method, the :code:`unload_callable` will be called.
Before a plugin is unloaded, any dependent plugins are unloaded first.

Similarly, plugin unload can be broken down into the following:

1. Resolve any unload conflicts (e.g. ignore and return if already unloaded)
2. Unload dependents
3. Call underlying unload callable

Resolve Unload Conflicts
###############

If a plugin is already unloaded and :meth:`~pyplugin.base.Plugin.unload` is called you may choose to pass
:code:`conflict_strategy` which can be one of "ignore" or "error".

Unload Dependents
###############

Before unloading, a plugin's dependents (as appears in :attr:`~pyplugin.base.Plugin.dependents`), will first be
unloaded. (This guarantees that a plugin's requirements are up to date, and a plugin's state fully encapsulates
its consumers.)

Call Underlying Unload Callable
###############

Finally, the loaded instance is passed into the underlying :attr:`~pyplugin.base.Plugin.load_callable` and returned.
