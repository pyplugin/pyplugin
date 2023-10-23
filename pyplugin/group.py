from __future__ import annotations
import functools
import typing
from collections.abc import MutableSequence

from pyplugin.base import Plugin, _R, get_registered_plugin, lookup_plugin, get_aliases
from pyplugin.utils import void_args, empty
from pyplugin.exceptions import (
    PluginNotFoundError,
    PluginLoadError,
    PluginUnloadError,
    DependencyError,
)


class PluginGroup(Plugin[list[_R]], MutableSequence[typing.Union[Plugin[_R], str]]):
    """
    This class groups together plugins under certain guarantees:

    - If this group is loaded, then every plugin in this group is loaded, and the instance of this plugin is a list
      of instances in order.
    - Loading this group will attempt to load all plugins, consequently changing any one of these plugins will also
      reload this group.
    - Unloading this group will unload all plugins in this group

    Note: Plugins in this group may still be loaded individually and separately.

    The load_ and unload_callables for a PluginGroup are of a different form than normal. They are written in
    contextlib.contextmanager style with a single yield statement. The load callable is passed the list of plugins
    in addition to the load args and load kwargs. It may yield back these three things which will be used to determine
    load order and load args. The unload_callable similarly is passed the list of instances along with unload
    args / kwargs.

    Attributes:
        plugins (list[Plugin | str]): The list of plugins in this group

    Arguments:
        plugins (Iterable[Plugin | str]): The plugins to initialize this group with

    """

    def __init__(
        self,
        plugin: typing.Callable = void_args,
        unload_callable: typing.Callable = void_args,
        plugins: typing.Iterable[Plugin[_R] | str] = None,
        **kwargs,
    ):
        self.plugins: list[typing.Union[Plugin[_R], str]] = list(plugins) if plugins else []
        super().__init__(
            plugin,
            unload_callable=unload_callable,
            **kwargs,
        )
        self._load_callable = functools.partial(self._group_load, self._load_callable)
        self._unload_callable = functools.partial(self._group_unload, self._unload_callable)

    def _handle_enforce_type(self, instance, type_=None, is_class_type=None):
        type_ = type_ if type_ else self.type
        is_class_type = is_class_type if is_class_type else self.is_class_type

        if self.enforce_type and type_:
            for plugin in instance:
                super()._handle_enforce_type(plugin, type_=type_, is_class_type=is_class_type)

    def _load_dependencies(self, kwargs):
        ret = {}
        for dest, plugin in self.dependencies.copy().items():
            if plugin in self:
                continue
            if dest in kwargs:
                continue
            ret[dest] = plugin.load(conflict_strategy="keep_existing")
        return ret

    def _group_load(self, load_callable, *args, **kwargs) -> list[_R]:
        plugins, args, kwargs = self.plugins, args, kwargs

        gen = load_callable(self.plugins, *args, **kwargs)

        ret = None
        if gen:
            try:
                ret = next(gen)
            except StopIteration as err:
                ret = err.value

        if ret:
            if not (isinstance(ret, typing.Sequence) and len(ret) == 3 and isinstance(ret[0], typing.Iterable)):
                ret = ret, args, kwargs
            plugins_, args_, kwargs_ = ret
            plugins, args, kwargs = (
                plugins_ if plugins_ else plugins,
                args_ if args_ else args,
                kwargs_ if kwargs_ else kwargs,
            )

        kwargs.setdefault("safe_args", True)
        kwargs.setdefault("conflict_strategy", "keep_existing")
        ret = []

        for plugin in plugins:
            if not isinstance(plugin, Plugin):
                try:
                    plugin = lookup_plugin(plugin, import_lookup=self._settings["import_lookup"])
                except PluginNotFoundError as err:
                    raise PluginLoadError(f"{self.get_full_name()}: Could not find plugin in group {plugin}") from err
            instance = plugin.load(*args, **kwargs)
            if not self.type and self.infer_type:
                self._set_type_from_instance(instance)
            ret.append(instance)

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def _group_unload(self, unload_callable, instance, *args, **kwargs) -> list[typing.Any]:
        plugins, instance = self.plugins, instance

        gen = unload_callable(self.plugins, instance)

        ret = None
        if gen:
            try:
                ret = next(gen)
            except StopIteration as err:
                ret = err.value

        if ret:
            if not (isinstance(ret, typing.Sequence) and len(ret) == 2 and isinstance(ret[0], typing.Iterable)):
                ret = ret, instance, args, kwargs
            plugins_, instance_, args_, kwargs_ = ret
            plugins, instance, args, kwargs = (
                plugins_ if plugins_ else plugins,
                instance_ if instance_ is not empty else instance,
                args_ if args_ else args,
                kwargs_ if kwargs_ else kwargs,
            )

        ret = []
        for plugin in reversed(plugins):
            if not isinstance(plugin, Plugin):
                try:
                    plugin = lookup_plugin(plugin, import_lookup=self._settings["import_lookup"])
                except PluginNotFoundError as err:
                    raise PluginUnloadError(f"{self.get_full_name()}: Could not find plugin in group {plugin}") from err
            ret.append(plugin._unload(*args, _unload_dependents=False, **kwargs))

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def _set_type(self, plugin: PluginGroup = None) -> typing.Optional[typing.Type]:
        if not plugin:
            plugin = self

        for plugin_ in plugin:
            if isinstance(plugin_, Plugin):
                return super()._set_type(plugin=plugin)

        return None

    def _add(self, value: typing.Union[Plugin[_R], str]):
        if self.enforce_type and self.type and value.type:
            super()._handle_enforce_type(value.type, type_=self.type, is_class_type=True)
        self.add_requirement(value)

    def _infer_type_from(self, value: typing.Union[Plugin[_R], str]):
        if not self.type and self.infer_type and isinstance(value, Plugin):
            super()._set_type(plugin=value)

    add = MutableSequence.append

    def safe_add(self, value: typing.Union[Plugin[_R], str]):
        """
        Adds the given plugin to this group, unloading first before adding and then reloading if it was loaded.

        Arguments:
            value (Plugin | str): The plugin to add
        """
        is_loaded = self.is_loaded()
        if is_loaded:
            self.unload()
        self.append(value)
        if is_loaded:
            self.load()

    def __getitem__(self, index: int) -> Plugin[_R]:
        return self.plugins[index]

    def __setitem__(self, index: int, value: typing.Union[Plugin[_R], str]):
        self._add(value)
        self.plugins[index] = value
        self._infer_type_from(value)

    def __delitem__(self, index: int):
        self.plugins.pop(index)

    def __len__(self) -> int:
        return len(self.plugins)

    def insert(self, index: int, value: typing.Union[Plugin[_R], str]):
        self._add(value)
        self.plugins.insert(index, value)
        self._infer_type_from(value)

    def __contains__(self, plugin: typing.Union[Plugin, str]) -> bool:
        if super(MutableSequence, self).__contains__(plugin):
            return True

        if isinstance(plugin, Plugin) and any(
            super(MutableSequence, self).__contains__(alias) for alias in get_aliases(plugin)
        ):
            return True

        if not isinstance(plugin, str):
            return False

        try:
            plugin = get_registered_plugin(plugin)
        except PluginNotFoundError:
            return False
        else:
            return super(MutableSequence, self).__contains__(plugin)
