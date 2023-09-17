from __future__ import annotations

import contextlib
import inspect
import functools
import typing
import copy

from pyplugin.exceptions import *
from pyplugin.utils import (
    import_helper,
    void_args,
    empty,
    infer_return_type,
)
from pyplugin.settings import Settings


_DELIMITER = "."


def get_plugin_name(plugin: typing.Union[Plugin, str, typing.Callable], name: str = empty):
    """
    Finds a name for the given plugin-like object. For a function this is a fully qualified
    package-module dot-delimited name. Otherwise, takes the override `name` argument, and finally
    resorts to the __name__ attribute if defined.

    Arguments:
        plugin (Plugin | str | None): The plugin-like object to find a name for.
        name (str | :attr:`plugin.utils.empty`): The override name to take if given.
    Returns:
        str: The resolved name of the plugin
    Raises:
        ValueError: If a name could not be resolved
    """
    if name is not empty:
        return name
    if isinstance(plugin, Plugin):
        return plugin.name
    if isinstance(plugin, str):
        return plugin
    if inspect.isfunction(plugin):
        module = inspect.getmodule(plugin)
        return _DELIMITER.join((module.__name__, plugin.__name__))
    if hasattr(plugin, "__name__"):
        return getattr(plugin, "__name__")
    raise ValueError(f"Cannot resolve name for {plugin}")


class Plugin:
    """

    Attributes:
        name (str): The name of the plugin

        load_args (tuple | None): The most-recent positional arguments passed to the plugin when loading
        load_kwargs (dict | None): The most-recent keyword arguments passed to the plugin when loading
        instance (Any | empty): The return-value of the last load. Is :attr:`plugin.utils.empty` if not loaded

        type (type | None): The return-value type of the plugin. (default: None)
        is_class_type (bool): If True, this indicates the return-value is a subclass of :attr:`type`.
            (default: False)
        infer_type (bool): If type is not given upon initialization, will attempt to infer the type from
            type annotations of the callable or the type of the return value upon first load. (default: True)
        enforce_type (bool): If True, will error if any load attempt that does not match :attr:`type`.
            (default: False)

    Arguments:
        plugin (Plugin | str | Callable): The plugin argument can take one of three forms.

            - Callable: This is the base form where the Plugin class will "wrap" this underlying callable
              and call this function upon :meth:`load`.
            - Plugin: This will wrap the underlying callable of the given plugin.
            - str: This is the import form which will either find upon loading (default), or
              find upon initialization (determined by :code:`greedy_import`). That name is expected to be
              in one of the other forms and is found using importlib.


        name (str | empty): The name to assign the plugin. If not provided, determined by :func:`get_plugin_name`
        unload_callable (Callable): A Callable that takes one argument, the :attr:`instance`, and is called when
            :meth:`unload` is called.

        bind (bool): If True, passes self as the first argument into the load callable and unload callable.
            (default: False)
        eager_find (bool): If True, a plugin given in import form will be greedily found at initialization time.
            If False, the find happens at load time. (default: False)

        type (type | None): The return type of the underlying callable. (default: None)
        infer_type (bool): If type is not given upon initialization, will attempt to infer the type from
            type annotations of the callable or the type of the return value upon first load. (default: True)
        enforce_type (bool): If True, will error if any load attempt that does not match :attr:`type`.
            (default: False)
        is_class_type (bool): If True, this indicates the return-value is a subclass of :attr:`type`.
            (default: False)

    """

    def __init__(
        self,
        plugin: typing.Union[Plugin, str, typing.Callable],
        name: str = empty,
        unload_callable: typing.Callable = void_args,
        bind: bool = False,
        is_class_type: bool = False,
        **kwargs,
    ):
        settings = Settings(**{key: value for key, value in kwargs.items() if key in Settings._SETTINGS})

        self.name = get_plugin_name(plugin, name=name)
        self._locked = False
        self._kwargs = {"bind": bind, **settings.to_dict()}

        self.load_args = None
        self.load_kwargs = None

        if isinstance(plugin, Plugin):
            plugin = plugin.__original_callable
            unload_callable = unload_callable if unload_callable != void_args else plugin.__original_unload_callable
        self.__original_callable = self._load_callable = plugin
        self.__original_unload_callable = self._unload_callable = unload_callable

        self.__partially_loaded = False
        self.instance = empty

        self.infer_type = settings["infer_type"]
        self.type = kwargs.get("type", None)
        self.is_class_type = is_class_type
        self.enforce_type = settings["enforce_type"]

        while isinstance(self._load_callable, str):
            self._handle_import_form(
                self._load_callable,
                eager_find=settings["eager_find"],
            )

        if not self.type and self.infer_type:
            self._set_type()

        if bind:
            self._load_callable = self._load_callable.__get__(self, type(self))
            self._unload_callable = self._unload_callable.__get__(self, type(self))

    def __repr__(self):
        attrs = ", ".join(
            (
                repr(self.__original_callable),
                f"name='{self.name}'",
                f"unload_callable={repr(self.__original_unload_callable)}",
            )
        )
        return f"{self.__class__.__name__}(" + attrs + ")"

    def __eq__(self, other):
        if not isinstance(other, Plugin):
            return False

        if self is other:
            return True

        if self.__class__ != other.__class__:
            return False

        return (
            self.name == other.name
            and self.__original_callable == other.__original_callable
            and self.__original_unload_callable == other.__original_unload_callable
            and self.instance == other.instance
            and self._locked == other._locked
        )

    def __copy__(self):
        ret = Plugin(
            self.__original_callable,
            unload_callable=self.__original_unload_callable,
            name=self.name,
            type=self.type,
            infer_type=self.infer_type,
            enforce_type=self.enforce_type,
            is_class_type=self.is_class_type,
            **self._kwargs,
        )
        ret._locked = self._locked
        return ret

    def __call__(self, *args, **kwargs):
        """Alias for :meth:`load`"""
        return self.load(*args, **kwargs)

    def get_full_name(self):
        """
        Returns:
            str: The fully-qualified name
        """
        return self.name

    def lock(self):
        """
        Locks the plugin so that it cannot by loaded or unloaded.
        """
        self._locked = True

    def unlock(self):
        """
        Unlock the plugin so that it may be loaded or unloaded.
        """
        self._locked = False

    def is_locked(self):
        """
        Return:
            bool: True, if plugin is locked else False.
        """
        return self._locked

    def is_loaded(self):
        """
        This is equivalent to checking that :attr:`instance` is not :code:`empty`.

        Returns:
            bool: True if the plugin is currently loaded, false otherwise
        """
        return self.instance is not empty

    def copy(self, dest: str = None):
        """
        Arguments:
            dest (str | None): the new name to give the copy, defaults to the current name
        Returns:
            Plugin: An non-loaded copy of this plugin.
        """
        dest = dest if dest else self.name
        other = copy.copy(self)
        other.name = dest
        return other

    def load(
        self,
        *args,
        conflict_strategy: typing.Literal["keep_existing", "replace", "force", "error"] = "replace",
        default_previous_args: bool = True,
        **kwargs,
    ):
        """
        The main method of the Plugin class. This calls the underlying load callable.

        The arguments are passed to the underlying callable and type checking is done.

        Arguments:
            args: varargs passed to the load callable.
            conflict_strategy ("keep_existing", "replace", "force", "error"): How to handle the case this Plugin
                is already loaded:

                - "keep_existing": Ignore the load request
                - "replace": First :meth:`unload` before attempting to load
                - "force": Like "replace" except will apply if :attr:`load_args` and :attr:`load_kwargs` match.
                - "error": raises PluginLoadError

                (default: "replace")
            default_previous_args (bool): If True, will fill kwargs with defaults from :attr:`load_kwargs`.
                (default: True)
        Raises:
            PluginLockedError: If this Plugin is locked
            PluginPartiallyLoadedError: If this method was called while inside the underlying callable.
            PluginLoadError: If there was an error in loading the requirements or the dependents
            PluginTypeError: If :attr:`enforce_type` is True, and the returned value from the underlying callable
                does not match :attr:`type`.
        """
        args = list(args)

        # check cyclic load
        if self.__partially_loaded:
            raise PluginPartiallyLoadedError(self.get_full_name())

        # check lock
        if self.is_locked():
            raise PluginLockedError(self.get_full_name())

        # set defaults from previous load settings
        if default_previous_args and self.load_kwargs:
            for key, value in self.load_kwargs.items():
                kwargs.setdefault(key, value)

        # check load conflicts
        if self.is_loaded():
            if (self.load_args, self.load_kwargs) == (
                args,
                kwargs,
            ) and conflict_strategy != "force":
                return self.instance
            elif conflict_strategy in ("replace", "force"):
                self.unload()
            elif conflict_strategy == "keep_existing":
                return self.instance
            else:
                raise PluginLoadError(
                    f"{self.get_full_name()}: "
                    "Already loaded with conflicting arguments, "
                    f"old: {(self.load_args, self.load_kwargs)}, new: {(args, kwargs)}"
                )

        self.load_args = args
        self.load_kwargs = kwargs

        with self._partial_load_context():
            instance = self._load_callable(*args, **kwargs)

        if self.enforce_type and self.type:
            if self.is_class_type:
                comparator = issubclass
            else:
                comparator = isinstance
            if not comparator(instance, self.type):
                raise PluginTypeError(
                    f"{self.get_full_name()}: Mismatched type, " f"expected {self.type} but got {type(instance)}"
                )

        if not self.type and self.infer_type:
            self._set_type_from_instance(instance)

        self.instance = instance

        return self.instance

    def unload(
        self,
        conflict_strategy: typing.Literal["ignore", "error"] = "ignore",
    ):
        """
        This calls the underlying unload callable.

        The :attr:`instance` (which is the return value of the load callable) is passed to the unload_callable.

        Arguments:
            conflict_strategy ("ignore", "error"): How to handle the case this Plugin is already unloaded:

                - "ignore": Ignore the unload request
                - "error": raises PluginLoadError

                (default: "ignore")
        Raises:
            PluginLockedError: If this Plugin is locked
            PluginPartiallyLoadedError: If this method was called while inside the underlying callable.
            PluginLoadError: If there was an error in unloading the dependents
        """
        # check cyclic load
        if self.__partially_loaded:
            raise PluginPartiallyLoadedError(self.get_full_name())

        # check enablement
        if self.is_locked():
            raise PluginLockedError(self.get_full_name())

        # check if already unloaded
        if not self.is_loaded():
            if conflict_strategy == "ignore":
                return empty
            elif conflict_strategy == "error":
                raise PluginAlreadyUnloadedError(self.get_full_name())

        with self._partial_load_context():
            ret = self._unload_callable(self.instance)

        self.instance = empty

        return ret

    def _handle_import_form(
        self,
        import_name: str,
        eager_find: bool = False,
    ):
        if eager_find:
            maybe_plugin = import_helper(import_name)
            if isinstance(maybe_plugin, Plugin):
                self._load_callable = maybe_plugin.__original_callable
                self._unload_callable = maybe_plugin.__original_unload_callable
                if not self.type and self.infer_type:
                    self._set_type(plugin=maybe_plugin)
            else:
                self._load_callable = maybe_plugin
                if not self.type and self.infer_type:
                    self.type = infer_return_type(self._load_callable)

        else:

            def load_callable(plugin_: str, *args, **kwargs):
                self._handle_import_form(plugin_, eager_find=True)
                return self.load(*args, **kwargs)

            self._load_callable = functools.partial(load_callable, import_name)

    def _set_type(self, plugin: Plugin = None):
        if not plugin:
            plugin = self

        if plugin.instance is not empty:
            return self._set_type_from_instance(plugin.instance)

        if not isinstance(plugin.__original_callable, str):
            self.type = infer_return_type(plugin.__original_callable)

        return None

    def _set_type_from_instance(self, instance):
        self.type = type(instance)
        if inspect.isclass(self.type) and issubclass(self.type, type):
            self.type = instance
            self.is_class_type = True

    @contextlib.contextmanager
    def _partial_load_context(self):
        if self.__partially_loaded:
            raise PluginPartiallyLoadedError(self.get_full_name())

        self.__partially_loaded = True

        yield

        self.__partially_loaded = False
