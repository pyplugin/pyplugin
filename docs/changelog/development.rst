Development
==========================

Features
---------

- Added :class:`~pyplugin.group.PluginGroup` class which is a collection plugins that can be loaded and unloaded
  together sharing requirements, along with a pre- and post-load hooking mechanism for the group loader.

Fixes
------

Other Changes
--------------

- Improved exception handling in the :meth:`~pyplugin.base.Plugin.load` and :meth:`~pyplugin.base.Plugin.unload`
  methods.
