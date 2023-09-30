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
- Added function :func:`~pyplugin.base.get_registered_plugins` which returns the plugin registry
  (a map from plugin name to Plugin in the order that they were registered).
- Functions will now use :code:`__qualname__` instead of just :code:`__name__` when determining plugin name.
- Added dynamic requirements: loading plugin 1 inside of plugin 2 will be treated in the exact manner
  as if plugin 1 was explicitly declared a requirement of plugin 2.
- Added method :meth:`~pyplugin.base.Plugin.is_registered`.
