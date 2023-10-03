Changes in 0.3.0
==========================

Features
---------

- Added :class:`~pyplugin.group.PluginGroup` class which is a collection of plugins that can be loaded and unloaded
  together sharing requirements, along with a pre- and post-load hooking mechanism for group loading.
- Added parameter :code:`make_safe` to the :meth:`~pyplugin.base.Plugin.load` method that will make the calling args
  and kwargs safe, i.e. only passing in parameters that are defined in the signature.
- Dynamic requirements no longer force-ably passes in the plugin instance on reload.

Fixes
------

Other Changes
--------------

- Improved exception handling in the :meth:`~pyplugin.base.Plugin.load` and :meth:`~pyplugin.base.Plugin.unload`
  methods.
