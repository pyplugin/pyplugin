Development
==========================

Features
---------

- Added new setting :code:`register_mode` which can be used to configure how plugins get registered upon
  initialization.
- Added :func:`~pyplugin.settings.set_flag` function that will set a particular setting globally.
- Added :func:`~pyplugin.settings.unset_flag` function to reset a setting to default.
- Added :func:`~pyplugin.settings.with_flag` context manager to temporarily set a setting.

Fixes
------

- Fixes dynamic requirements being registered in other parts of the load function (e.g. when loading a dependency).
- Fixes groups reloading entirely when loading individual elements.
- Fixes copying of requirements when copying a Plugin.

Other Changes
--------------
