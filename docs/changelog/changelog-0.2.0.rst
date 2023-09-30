Changes in 0.2.0
==========================

Features
---------
- Added function :func:`~pyplugin.base.get_registered_plugins` which returns the plugin registry
  (a map from plugin name to Plugin in the order that they were registered).
- Functions will now use :code:`__qualname__` instead of just :code:`__name__` when determining plugin name.
- Added dynamic requirements: loading plugin 1 inside of plugin 2 will be treated in the exact manner
  as if plugin 1 was explicitly declared a requirement of plugin 2.
- Added method :meth:`~pyplugin.base.Plugin.is_registered`.

Fixes
------

Other Changes
--------------
