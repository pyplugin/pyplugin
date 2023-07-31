from __future__ import annotations

import contextlib
import inspect
from collections import OrderedDict, namedtuple
import functools
import typing

from plugin.exceptions import *
from plugin.utils import import_helper


empty = object()

PluginRequirement = namedtuple("PluginRequirement", ["name", "type", "dest"])


def get_plugin_name(
    plugin: typing.Union[Plugin, str, typing.Callable], name: str = empty
):
    if name is not empty:
        return name
    if isinstance(plugin, Plugin):
        return plugin.name
    if hasattr(plugin, "__name__"):
        return getattr(plugin, "__name__")
    if hasattr(plugin, "__qualname__"):
        return getattr(plugin, "__qualname__")
    raise ValueError(f"Cannot resolve name for {plugin}")


class Plugin:
    """ """

    def __init__(
        self,
        plugin: typing.Union[Plugin, str, typing.Callable],
        name: str = None,
        manager: PluginManager = None,
        requires: typing.Iterable[typing.Union[str, PluginRequirement]] = (),
        bind: bool = False,
        enabled: bool = True,
        **kwargs,
    ):
        self.name = get_plugin_name(plugin, name=name)
        self.manager = None
        self._enabled = enabled

        self._kwargs = kwargs
        self._kwargs["bind"] = bind
        self._kwargs["requires"] = requires
        self._kwargs["enabled"] = enabled

        self.requires = {}
        for requirement in requires:
            if isinstance(requirement, str):
                requirement = PluginRequirement(
                    name=requirement, type=None, dest=requirement
                )
            self.requires[requirement.name] = requirement

        self.requirements: dict[str, Plugin] = {}
        self.dependents = {}
        for _, _, dest in self.requires.values():
            self.requirements[dest] = None

        self.instance = empty
        self.type = kwargs.get("type", None)
        self.load_args = None
        self.load_kwargs = None

        self.__original_callable = self._load_callable = plugin
        if isinstance(self._load_callable, str):

            def load_callable(plugin_: str, *args, **kwargs):
                return self.manager.find(plugin_).load(*args, **kwargs)

            self._load_callable = functools.partial(load_callable, self._load_callable)

        if bind:
            self._load_callable = self._load_callable.__get__(self, type(self))

        self.__original_unload_callable = (
            self._unload_callable
        ) = lambda *args_, **kwargs_: None
        if bind:
            self._unload_callable = self._unload_callable.__get__(self, type(self))

        self._partially_loaded = False

        if manager:
            manager.register(self)

    def __copy__(self):
        return Plugin(self.__original_callable, name=self.name, **self._kwargs)

    def copy(self, dest: str = None):
        dest = dest if dest else self.name
        other = self.__copy__()
        other.name = dest
        return other

    def __call__(self, *args, **kwargs):
        return self.load(*args, **kwargs)

    def add_requirement(self, requirement: typing.Union[str, PluginRequirement]):
        if isinstance(requirement, str):
            requirement = PluginRequirement(
                name=requirement, type=None, dest=requirement
            )
        self.requires[requirement.name] = requirement

    def _upstream_load(self, kwargs: dict):
        # ensure upstream is loaded & cross-correlate dependencies
        if self.manager:
            for plugin, type_, dest in self.requires:
                if dest in kwargs:
                    continue

                self.requirements[dest] = self.manager.find(plugin)
                self.requirements[dest].dependents[self.get_full_name()] = self
                self.requirements[dest].load(conflict_strategy="replace")

                kwargs.setdefault(dest, self.requirements[dest].instance)

    def _downstream_load(self):
        # reload downstream
        for plugin in self.dependents.values():
            found = False
            for dest_, plugin_ in plugin.requirements:
                if self == plugin_:
                    new_kwargs = plugin.load_kwargs.copy()
                    new_kwargs[dest_] = self.instance
                    plugin.load(*plugin.load_args, loaded_ok=False, **new_kwargs)
                    found = True
                    break

            if not found:
                raise PluginLoadError(
                    f"{self.get_full_name()}: "
                    f"Error in reloading dependent {plugin.get_full_name()}, "
                    "did not find self in requirements"
                )

    def load(
        self,
        *args,
        conflict_strategy: typing.Literal[
            "keep_existing", "replace", "error"
        ] = "replace",
        downstream_reload: bool = True,
        **kwargs,
    ):
        args = list(args)

        # check enablement
        if not self.enabled:
            raise PluginDisabledError(self.get_full_name())

        # check cyclic load
        if self._partially_loaded:
            raise PluginPartiallyLoadedError(self.get_full_name())

        self._upstream_load(kwargs)

        # set defaults from previous load settings
        if self.load_args and len(self.load_args) > len(args):
            args.extend(self.load_args[len(args) :])

        if self.load_kwargs:
            for key, value in self.load_kwargs.items():
                kwargs.setdefault(key, value)

        # check load conflicts
        if self.is_loaded():
            if (self.load_args, self.load_kwargs) == (args, kwargs):
                return self
            if conflict_strategy == "replace":
                self.unload()
            elif conflict_strategy == "keep_existing":
                return self
            else:
                raise PluginLoadError(
                    f"{self.get_full_name()}: "
                    "Already loaded with conflicting arguments, "
                    f"old: {(self.load_args, self.load_kwargs)}, new: {(args, kwargs)}"
                )

        self.load_args = args
        self.load_kwargs = kwargs
        self._partially_loaded = True

        try:
            instance = self._load_callable(*args, **kwargs)
        finally:
            self._partially_loaded = False

        # type check
        if self.type:
            if inspect.isclass(instance):
                comparator = issubclass
            else:
                comparator = isinstance
            if not comparator(self.instance, self.type):
                raise PluginTypeError(
                    f"{self.get_full_name()}: Mismatched type, "
                    f"expected {self.type} but got {type(self.instance)}"
                )
        else:
            self.type = type(instance)

        self.instance = instance

        if downstream_reload:
            self._downstream_load()

        return self

    def is_loaded(self):
        return self.instance is not empty

    def _downstream_unload(self):
        # unload downstream
        for plugin in self.dependents.values():
            found = False
            for dest_, plugin_ in plugin.requirements:
                if self == plugin_:
                    plugin.unload(conflict_strategy="ignore")
                    found = True
                    break

            if not found:
                raise PluginUnloadError(
                    f"{self.get_full_name()}: "
                    f"Error in unloading dependent {plugin.get_full_name()}, "
                    "did not find self in requirements"
                )

    def unload(
        self,
        conflict_strategy: typing.Literal["ignore", "error"] = "ignore",
        downstream_reload: bool = True,
    ):
        # check cyclic load
        if self._partially_loaded:
            raise PluginPartiallyLoadedError(self.get_full_name())

        # check enablement
        if not self.enabled:
            raise PluginDisabledError(self.get_full_name())

        # check if already unloaded
        if not self.is_loaded():
            if conflict_strategy == "ignore":
                pass
            elif conflict_strategy == "error":
                raise PluginAlreadyUnloadedError(self.get_full_name())

        if downstream_reload:
            self._downstream_unload()

        self._partially_loaded = True
        try:
            ret = self._unload_callable(self.instance)
        finally:
            self._partially_loaded = False

        return ret

    def set_enabled(self, value):
        if self._enabled and not value:
            if self.is_loaded():
                raise PluginError(
                    f"{self.get_full_name()}: Cannot disable a loaded plugin."
                )
        self._enabled = value

    def get_enabled(self):
        return self._enabled

    enabled = property(get_enabled, set_enabled)

    def get_full_name(self):
        name = self.name
        if self.manager:
            name = self.manager.delimiter.join((self.manager.get_full_name(), name))
        return name

    def __eq__(self, other):
        if not isinstance(other, Plugin):
            return False
        return (
            self.get_full_name() == other.get_full_name()
            and self.__original_callable == other.__original_callable
            and self.__original_unload_callable == other.__original_unload_callable
            and self.instance == other.instance
            and self.requires == other.requires
            and self.enabled == other.enabled
        )


class PluginManager(Plugin):
    """ """

    delimiter = "."

    def __init__(
        self,
        name: str,
        *args,
        plugin: typing.Union[Plugin, str, typing.Callable] = None,
        plugin_type: type = None,
        **kwargs,
    ):
        if not plugin:

            def plugin():
                return self

        super().__init__(plugin, name=name, *args, **kwargs)
        self._plugins = OrderedDict({})
        self._plugin_type = plugin_type

    def register(
        self,
        plugin: typing.Union[Plugin, str, typing.Callable],
        name: str = empty,
        conflict_strategy: typing.Literal[
            "keep_existing", "replace", "error"
        ] = "error",
        **kwargs,
    ) -> Plugin:
        name = get_plugin_name(plugin, name=name)

        # recursively add middle plugin managers
        first, *rest = name.split(self.delimiter)
        if (first and rest) and first not in self._plugins:
            self._plugins[first] = self.__class__(first)
        if rest:
            name = self.delimiter.join(rest)
            return self._plugins[first].register(plugin, name=name)

        # leaf plugin manager, single name
        name = first
        if not isinstance(plugin, Plugin):
            plugin = Plugin(plugin, name=name, **kwargs)

        # check conflicts
        if name in self._plugins:
            if plugin == self._plugins[name]:
                return self._plugins[name]
            if conflict_strategy == "keep_existing":
                return self._plugins[name]
            elif conflict_strategy == "replace":
                self.unregister(name)
            elif conflict_strategy == "error":
                raise PluginRegistrationError(
                    f"{self.get_full_name()}: "
                    f"Cannot register {plugin} with name {name}, name already registered"
                )

        # register
        self._plugins[name] = plugin
        self._plugins[name].manager = self
        return self._plugins[plugin.name]

    def unregister(self, name: str):
        if self._plugins[name].is_loaded():
            raise PluginRegistrationError(
                f"{self.get_full_name()}: Cannot unregister loaded plugin {name}"
            )
        return self._plugins.pop(name)

    def find_by_name(
        self,
        name: str,
        parent: bool = True,
        dynamic: bool = True,
        **kwargs,
    ) -> Plugin:
        type_ = kwargs.get("type", None)

        first, *rest = name.split(self.delimiter)

        if rest:
            with contextlib.suppress(KeyError):
                return self._plugins[first].find_by_name(
                    self.delimiter.join(rest),
                    parent=parent,
                    type=type_,
                )
        else:
            if first in self._plugins:
                return self._plugins[first]

        if name == self.name:
            return self

        if parent and self.manager:
            with contextlib.suppress(KeyError):
                return self.manager.find_by_name(
                    name,
                    parent=parent,
                    dynamic=dynamic,
                    type=type_,
                )

        # import find
        if dynamic:
            import_name = self.get_full_name()
            if import_name:
                import_name += self.delimiter + name
            else:
                import_name = name

            maybe_plugin = import_helper(import_name, ignore_missing=True)
            if not maybe_plugin:
                raise PluginNotFound(import_name)

            return self.register(
                Plugin(maybe_plugin, name=first),
                name=name,
            )

        raise PluginNotFound(name)

    def find(
        self,
        name: str = None,
        parent: bool = True,
        dynamic: bool = True,
        **kwargs,
    ) -> Plugin:
        type_ = kwargs.get("type", None)

        if not name and not type_:
            raise ValueError("One of 'name' or 'type' is required.")

        if name:
            return self.find_by_name(name, parent=parent, dynamic=dynamic, type=type_)

        # type search
        for plugin in self._plugins.values():
            if issubclass(plugin.type, type_):
                return plugin

        if parent and self.manager:
            return self.manager.find(parent=parent, dynamic=dynamic, type=type_)

        raise PluginNotFound(type_)

    def load(self, names: typing.Iterable[str] = empty, **kwargs):
        if names is empty:
            names = self._plugins.keys()
            names = (
                name
                for name in names
                if not self._plugins[name].is_loaded() and self._plugins[name].enabled
            )
        for name in names:
            self._plugins[name].load(**kwargs)

        kwargs["downstream_reload"] = False
        return super().load(**kwargs)

    def unload(self, names: typing.Iterable[str] = empty, **kwargs):
        if names is empty:
            names = self._plugins.keys()
            names = (
                name
                for name in names
                if self._plugins[name].is_loaded() and self._plugins[name].enabled
            )
        for name in names:
            self._plugins[name].unload(**kwargs)

        kwargs["downstream_reload"] = False
        return super().unload(downstream_reload=False, **kwargs)

    def _get_string_tree(self):
        lines = [f"{self.get_full_name()}"]
        for name, plugin in self._plugins.items():
            if isinstance(plugin, PluginManager):
                other_lines = plugin._get_string_tree()
                for line in other_lines:
                    lines.append(f" {line}")
            else:
                lines.append(f"|-{plugin.name}")
        return lines

    def get_string_tree(self):
        return "\n".join(self._get_string_tree())


ROOT_PLUGIN_MANAGER = PluginManager("")
