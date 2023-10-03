pyplugin |release|
=======================

.. toctree::
   :hidden:

   getting_started
   user_guide
   settings
   reference
   changelog

Pyplugin is a plugin framework library, supporting declarative-style plugin writing, allowing modular, swappable
functionality in any codebase.

See the source code for this version :source_code:`on github <.>`

Getting Started
-----------------
To get started see :ref:`Getting Started <getting_started>`.

Contributing
---------------
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github!
`Open Issues <https://github.com/pyplugin/pyplugin/issues>`_.

We welcome any developer who enjoys the package enough to contribute!
Please check out the `Developer's Guide <https://github.com/pyplugin/pyplugin/wiki/Developer's-Guide>`_.

What's New in |release|
------------------------

Features
^^^^^^^^^

- Added :class:`~pyplugin.group.PluginGroup` class which is a collection of plugins that can be loaded and unloaded
  together sharing requirements, along with a pre- and post-load hooking mechanism for group loading.
- Added parameter :code:`make_safe` to the :meth:`~pyplugin.base.Plugin.load` method that will make the calling args
  and kwargs safe, i.e. only passing in parameters that are defined in the signature.
- Dynamic requirements no longer force-ably passes in the plugin instance on reload.

Other Changes
^^^^^^^^^^^^^^

- Improved exception handling in the :meth:`~pyplugin.base.Plugin.load` and :meth:`~pyplugin.base.Plugin.unload`
  methods.

