.. _getting_started:

User Guide
===========

Loading a Plugin
-----------------

Load Conflict
##############

Attempting to load a plugin will first check if the plugin is already loaded and if the calling arguments are the same
or not. If the plugin is already loaded, and the arguments are different, this is considered a load conflict. You
can pass in :code:`conflict_strategy` to :meth:`~pyplugin.base.Plugin.load` to resolve this which can be one of
"keep_existing", "replace", "force", or "error" (default: "replace").

- :code:`keep_existing`: Ignore the load request
- :code:`replace`: First call :meth:`~pyplugin.base.Plugin.unload` before attempting to load
- :code:`force`: Like :code:`replace` but also will apply if :attr:`load_args` and :attr:`load_kwargs` match.
- :code:`error`: raises :class:`~pyplugin.base.exceptions.PluginLoadError`.

Unloading a Plugin
-------------------

Unload Conflict
###############

Similarly, if a plugin is already unloaded and :meth:`~pyplugin.base.Plugin.unload` is called you may choose to pass
:code:`conflict_strategy` which can be one of "ignore" or "error".
