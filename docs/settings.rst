.. _settings:

Settings
===========

.. list-table::
   :widths: 25 25 75 50 25
   :header-rows: 1

   * - Setting Name
     - Environment Variable
     - Description
     - Values
     - Default
   * - :code:`infer_type`
     - :code:`PYPLUGIN_INFER_TYPE`
     - Attempt to infer the type of defined plugins if not given upon initialization and upon loading.
     - :code:`bool`
     - :code:`True`
   * - :code:`enforce_type`
     - :code:`PYPLUGIN_ENFORCE_TYPE`
     - Throw an error if a plugin is loaded that returns an object that does not match its defined type.
     - :code:`bool`
     - :code:`False`
   * - :code:`import_lookup`
     - :code:`PYPLUGIN_IMPORT_LOOKUP`
     - When using the :func:`~pyplugin.base.lookup_plugin` function, (e.g. in dependency lookups), default
       to using :code:`importlib` as a fallback to find and register the plugin.
     - :code:`bool`
     - :code:`True`