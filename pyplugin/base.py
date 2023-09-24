from __future__ import annotations

import contextlib
import dataclasses
import inspect
import typing
import copy

from pyplugin.exceptions import *
from pyplugin.utils import (
    import_helper,
    void_args,
    empty,
    infer_return_type,
    ensure_a_list,
)
from pyplugin.settings import Settings


_DELIMITER = "."

# ------------------------------------------
# Plugin Registry
# ------------------------------------------

_PLUGIN_REGISTRY: dict[str, Plugin] = {}


def register(
    plugin: PluginLike,
    name: str = None,
    conflict_strategy: typing.Literal["replace", "keep_existing", "error"] = "error",
):
    """
    Arguments:
        plugin (PluginLike): The plugin to register
        name (str): The name to register the plugin under if not the plugin's full name (default: the plugin's
            full name)
        conflict_strategy ("replace" | "keep_existing" | "error"): Handle the case that a different plugin is already
            registered under the same name:

                - "keep_existing": Ignore the incoming register request
                - "replace": Unregister the existing plugin first (if it's not loaded).
                - "error": raises PluginRegisterError
    Raises:
        PluginRegisterError: If there was an error in registering the plugin (e.g. trying to replace an already loaded
            plugin)
    Returns:
        Plugin: The newly registered plugin or the existing plugin if conflict_strategy is "keep_existing"
    """
    # TODO: evyn.machi: perhaps in the future we can have a register hook
    if not isinstance(plugin, Plugin):
        plugin = Plugin(plugin, anonymous=True)

    if not name:
        name = plugin.get_full_name()

    if name in _PLUGIN_REGISTRY:
        if _PLUGIN_REGISTRY[name] == plugin:
            return _PLUGIN_REGISTRY[name]

        if conflict_strategy == "keep_existing":
            return _PLUGIN_REGISTRY[name]
        elif conflict_strategy == "replace":
            unregister(name, conflict_strategy="error")
        elif conflict_strategy == "error":
            raise PluginRegisterError(f"Plugin with name {name} already registered.")

    if name != plugin.get_full_name():
        plugin.full_name = name

    _PLUGIN_REGISTRY[name] = plugin

    return _PLUGIN_REGISTRY[name]


def unregister(
    plugin: typing.Union[str, Plugin],
    conflict_strategy: typing.Literal["ignore", "error"] = "error",
):
    """

    Arguments:
        plugin (Plugin | str): The plugin to unregister
        conflict_strategy ("ignore" | "error"): Handle the case that the name is not registered.

            - "ignore": Ignore the incoming unregister request
            - "error": raises PluginRegisterError
    Raises:
        PluginRegisterError: If there was an error in unregistering the plugin
    Returns:
        Plugin | None: The unregistered plugin or None
    """
    name = plugin if isinstance(plugin, str) else plugin.get_full_name()

    # TODO: evyn.machi: perhaps in the future we can have an unregister hook
    if name not in _PLUGIN_REGISTRY:
        if conflict_strategy == "ignore":
            return
        elif conflict_strategy == "error":
            raise PluginRegisterError(f"Plugin {name} is not registered")

    if _PLUGIN_REGISTRY[name].is_loaded():
        raise PluginRegisterError(f"Cannot unregister already loaded plugin {name}.")

    return _PLUGIN_REGISTRY.pop(name)


def get_registered_plugin(name: str):
    """
    Arguments:
        name (str): The name of the plugin
    Returns:
        Plugin: The plugin registered with the given name
    Raises:
        PluginNotFoundError: If the plugin with the given name is not found
    """
    if name not in _PLUGIN_REGISTRY:
        raise PluginNotFoundError(name)
    return _PLUGIN_REGISTRY[name]


# ------------------------------------------
# Plugin Misc Utils
# ------------------------------------------


def get_plugin_name(plugin: PluginLike, name: str = empty):
    """
    Finds a name for the given plugin-like object. For a function this is a fully qualified
    package-module dot-delimited name. Otherwise, takes the override `name` argument, and finally
    resorts to the __name__ attribute if defined.

    Arguments:
        plugin (PluginLike): The plugin-like object to find a name for.
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


def lookup_plugin(name: str, import_lookup: bool = True):
    """
    Arguments:
        name (str): The plugin name to lookup
        import_lookup (bool): If True and :code:`name` is not registered, will attempt to import the name
            and wrap in :class:`Plugin`.
    Returns:
        Plugin: The plugin with the registered name, falling back to an import lookup that wraps
    """
    try:
        return get_registered_plugin(name)
    except PluginNotFoundError:
        if not import_lookup:
            raise
        plugin_like = import_helper(name)
        if not callable(plugin_like):
            raise
        return Plugin(import_helper(name))


# ------------------------------------------
# Plugin Requirements / Dependencies
# ------------------------------------------
@dataclasses.dataclass
class PluginRequirement:
    """

    Attributes:
        plugin (Plugin, str): The plugin dependency, if this is a string, will perform a :func:`lookup_plugin` before
            loading.
        dest (str): The keyword name to call :meth:`Plugin.load` with.

    """

    plugin: typing.Union[Plugin, str]
    dest: str

    @classmethod
    def from_tuple(cls, value):
        return PluginRequirement(*value)


class Plugin:
    """

    Attributes:
        name (str): The (relative) name of the plugin
        full_name (str): The fully qualified dot-delimited name of the plugin

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

        requirements (dict[str, PluginRequirement]): The dependencies this plugin requires before loading.
            Requirements will be passed via keyword argument using the :attr:`PluginRequirement.dest` name.
        dependencies (dict[str, Plugin]): A map from :attr:`PluginRequirement.dest` to the resolved plugin.
            This map is populated upon loading along with the corresponding :attr:`dependents` list of the
            required Plugin.
        dependents (list[Plugin]): A list of Plugins that depend on this Plugin. This list is populated when
            the dependent Plugin is loaded and the dependent Plugin is guaranteed to have this Plugin in
            its :attr:`dependencies` map.

    Arguments:
        plugin (Callable): This is the base form where the Plugin class will "wrap" this underlying callable
            and call this function upon :meth:`load`.


        name (str | empty): The name to assign the plugin. If not provided, determined by :func:`get_plugin_name`
        unload_callable (Callable): A Callable that takes one argument, the :attr:`instance`, and is called when
            :meth:`unload` is called.

        bind (bool): If True, passes self as the first argument into the load callable and unload callable.
            (default: False)
        anonymous (bool): If True, will not globally register the plugin under its :attr:`full_name` (default: False).

        type (type | None): The return type of the underlying callable. (default: None)
        infer_type (bool): If type is not given upon initialization, will attempt to infer the type from
            type annotations of the callable or the type of the return value upon first load. (default: True)
        enforce_type (bool): If True, will error if any load attempt that does not match :attr:`type`.
            (default: False)
        is_class_type (bool): If True, this indicates the return-value is a subclass of :attr:`type`.
            (default: False)

        requires (PluginLike | PluginRequirement | tuple[PluginLike, str] | Iterable[...]): Any plugin dependencies to
            load beforehand.

    """

    def __init__(
        self,
        plugin: typing.Callable,
        name: str = empty,
        unload_callable: typing.Callable = void_args,
        bind: bool = False,
        requires: typing.Union[
            typing.Union[PluginLike, PluginRequirement, tuple[PluginLike, str]],
            typing.Iterable[typing.Union[PluginLike, PluginRequirement, tuple[PluginLike, str]]],
        ] = (),
        **kwargs,
    ):
        self._settings = Settings(**{key: value for key, value in kwargs.items() if key in Settings._SETTINGS})
        requires = ensure_a_list(requires)

        self._full_name = None
        self._name = None
        self.full_name = get_plugin_name(plugin, name=name)

        self._locked = False
        self._kwargs = {"bind": bind, **kwargs}

        self.load_args = None
        self.load_kwargs = None

        if isinstance(plugin, Plugin):
            plugin = plugin.__original_callable
            unload_callable = unload_callable if unload_callable != void_args else plugin.__original_unload_callable
        self.__original_callable = self._load_callable = plugin
        self.__original_unload_callable = self._unload_callable = unload_callable

        self.__partially_loaded = False
        self.instance = empty

        self.infer_type = self._settings["infer_type"]
        self.type = kwargs.get("type", None)
        self.is_class_type = kwargs.get("is_class_type", False)
        self.enforce_type = self._settings["enforce_type"]

        if not self.type and self.infer_type:
            self._set_type()

        if bind:
            self._load_callable = self._load_callable.__get__(self, type(self))
            self._unload_callable = self._unload_callable.__get__(self, type(self))

        self.requirements = {}
        self.dependencies = {}
        self.dependents = []

        for requirement in requires:
            self.add_requirement(requirement)

        if not kwargs.get("anonymous", False):
            register(self, name=self.full_name)

    def __repr__(self):
        attrs = ", ".join(
            (
                repr(self.__original_callable),
                f"name='{self.get_full_name()}'",
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
        kwargs = self._kwargs.copy()
        kwargs.update(
            anonymous=True,
        )

        ret = Plugin(
            self.__original_callable,
            unload_callable=self.__original_unload_callable,
            name=self.name,
            type=self.type,
            requires=self.requirements.copy().values(),
            **kwargs,
        )
        ret._locked = self._locked
        return ret

    def __call__(self, *args, **kwargs):
        """Alias for :meth:`load`"""
        return self.load(*args, **kwargs)

    def _set_full_name(self, value):
        self._full_name = value
        self._name = self._full_name.split(_DELIMITER)[-1]

    def get_full_name(self):
        """
        Returns:
            str: The fully-qualified name
        """
        return self._full_name

    full_name = property(get_full_name, _set_full_name)

    def _set_name(self, value):
        self._name = value

        parts = self._full_name.split(_DELIMITER)
        self._full_name = _DELIMITER.join((*parts[:-1], self._name))

    def get_name(self):
        return self._name

    name = property(get_name, _set_name)

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
            Plugin: An anonymous, non-loaded copy of this plugin.
        """
        dest = dest if dest else self.name
        other = copy.copy(self)
        other.name = dest
        return other

    def add_requirement(
        self,
        requirement: typing.Union[PluginLike, str, PluginRequirement, tuple[PluginLike, str]],
        conflict_strategy: typing.Literal["replace", "keep_existing", "error"] = "error",
    ):
        """

        Arguments:
            requirement (PluginLike | str | PluginRequirement | tuple[PluginLike, str]): The plugin that this plugin
                depends on and that will be passed upon :meth:`load`.
            conflict_strategy ("replace" | "keep_existing" | "error"): Handles the case where
                :attr:`PluginRequirement.dest` conflicts with a current requirement:

                    - "replace": Remove the existing requirement
                    - "keep_existing": Keep the existing requirement
                    - "error": Raise PluginRequirementError
        Returns:
            PluginRequirement: The formatted PluginRequirement
        Raises:
            PluginRequirementError: If there was an issue registering the requirement
        """
        if self.is_loaded():
            raise PluginRequirementError("Cannot add requirements to an already loaded plugin.")

        if isinstance(requirement, PluginRequirement):
            pass
        elif isinstance(requirement, tuple):
            requirement = PluginRequirement.from_tuple(requirement)
        elif isinstance(requirement, str):
            requirement = PluginRequirement(requirement, dest=requirement.split(_DELIMITER)[-1])
        elif isinstance(requirement, Plugin):
            requirement = PluginRequirement(requirement, dest=requirement.name)
        else:
            plugin = Plugin(requirement)
            requirement = PluginRequirement(plugin, dest=plugin.name)

        if requirement.dest in self.requirements and requirement != self.requirements[requirement.dest]:
            if conflict_strategy == "replace":
                del self.requirements[requirement.dest]
            elif conflict_strategy == "keep_existing":
                return self.requirements[requirement.dest]
            elif conflict_strategy == "error":
                raise PluginRequirementError(f"Plugin requirement with dest {requirement.dest} already registered")

        self.requirements[requirement.dest] = requirement

        return self.requirements[requirement.dest]

    def _populate_dependencies(self, seen=None):
        seen = seen if seen else []

        if self in seen:
            raise CircularDependencyError(
                " --> ".join((*(plugin.get_full_name() for plugin in seen), self.get_full_name()))
            )

        for requirement in self.requirements.values():
            plugin = (
                lookup_plugin(requirement.plugin, import_lookup=self._settings["import_lookup"])
                if isinstance(requirement.plugin, str)
                else requirement.plugin
            )
            plugin._populate_dependencies(seen=seen + [self])

            self.dependencies[requirement.dest] = plugin
            if self not in plugin.dependents:
                plugin.dependents.append(self)

    def _load_dependencies(self, kwargs):
        for dest, plugin in self.dependencies.items():
            if dest in kwargs:
                continue
            kwargs[dest] = plugin.load(conflict_strategy="keep_existing")

    def _load_dependents(self, dependents):
        for dependent in dependents:
            for dest, plugin in dependent.dependencies.items():
                if plugin == self:
                    dependent.load(**{dest: self.instance})
                    return
            raise InconsistentDependencyError(
                f"Did not find {self.get_full_name()} in dependencies of dependent plugin {dependent.get_full_name()}"
            )
        return

    def _unload_dependents(self):
        for dependent in self.dependents:
            dependent.unload(conflict_strategy="ignore")

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
                - "force": Like "replace" but also will apply if :attr:`load_args` and :attr:`load_kwargs` match.
                - "error": raises PluginLoadError

                (default: "replace")
            default_previous_args (bool): If True, will fill kwargs with defaults from :attr:`load_kwargs`.
                (default: True)
        Raises:
            PluginLockedError: If this Plugin is locked
            PluginPartiallyLoadedError: If this method was called while inside the underlying callable.
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

        self._populate_dependencies()

        loaded_dependents = [plugin for plugin in self.dependents if plugin.is_loaded()]

        self._load_dependencies(kwargs)

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
                raise PluginAlreadyLoadedError(
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

        self._load_dependents(loaded_dependents)

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
                - "error": raises PluginAlreadyUnloadedError

                (default: "ignore")
        Raises:
            PluginLockedError: If this Plugin is locked
            PluginPartiallyLoadedError: If this method was called while inside the underlying callable.
            PluginAlreadyUnloadedError: If conflict_strategy is "error" and this plugin is already unloaded.
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

        self._unload_dependents()

        with self._partial_load_context():
            ret = self._unload_callable(self.instance)

        self.instance = empty

        return ret

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


PluginLike = typing.TypeVar("PluginLike", Plugin, typing.Callable)
"""
See :class:`Plugin` initialization argument :code:`plugin` for more information.
"""
