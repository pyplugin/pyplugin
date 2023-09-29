Development
==========================

Features
---------
- Added function :func:`~pyplugin.base.get_registered_plugins()` which returns the plugin registry
  (a map from plugin name to Plugin in the order that they were registered).

Fixes
------
- Passing in a Plugin to :code:`get_plugin_name` returns full name.
- Name import-found Plugin using import name.

Other Changes
--------------
