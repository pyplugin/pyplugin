from __future__ import annotations
import functools
import typing
from typing import MutableSequence

from pyplugin.base import Plugin, _R, get_registered_plugin
from pyplugin.utils import void_args, empty
from pyplugin.exceptions import PluginNotFoundError


class PluginGroup(Plugin[list[_R]], MutableSequence[Plugin[_R]]):
    def __init__(
        self,
        plugin: typing.Callable = void_args,
        unload_callable: typing.Callable = void_args,
        plugins: typing.Iterable[Plugin[_R]] = None,
        **kwargs,
    ):
        self.plugins = list(plugins) if plugins else []
        super().__init__(
            plugin,
            unload_callable=unload_callable,
            **kwargs,
        )
        self._load_callable = functools.partial(self._load, self._load_callable)
        self._unload_callable = functools.partial(self._unload, self._unload_callable)

    def _handle_enforce_type(self, instance, type_=None, is_class_type=None):
        type_ = type_ if type_ else self.type
        is_class_type = is_class_type if is_class_type else self.is_class_type

        if self.enforce_type and type_:
            for plugin in instance:
                super()._handle_enforce_type(plugin, type_=type_, is_class_type=is_class_type)

    def _load(self, load_callable, *args, **kwargs) -> list[_R]:
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

        ret = []
        for plugin in plugins:
            instance = plugin.load(*args, **kwargs)
            if not self.type:
                self._set_type_from_instance(instance)
            ret.append(instance)

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def _unload(self, unload_callable, instance, *args, **kwargs) -> list[typing.Any]:
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
        for plugin in plugins:
            ret.append(plugin.unload(instance, *args, **kwargs))

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def _set_type(self, plugin: PluginGroup = None) -> typing.Optional[typing.Type]:
        if not plugin:
            plugin = self

        if len(self) != 0:
            plugin = plugin[0]

        return super()._set_type(plugin=plugin)

    def __getitem__(self, index: int) -> Plugin[_R]:
        return self.plugins[index]

    def __setitem__(self, index: int, value: Plugin[_R]):
        self.plugins[index] = value
        if not self.type and self.infer_type:
            super()._set_type(plugin=value)

    def __delitem__(self, index: int):
        self.plugins.pop(index)

    def __len__(self) -> int:
        return len(self.plugins)

    def insert(self, index: int, value: Plugin[_R]):
        self.plugins.insert(index, value)
        if not self.type and self.infer_type:
            super()._set_type(plugin=value)

    def __contains__(self, plugin: typing.Union[Plugin, str]) -> bool:
        if isinstance(plugin, Plugin):
            return super().__contains__(plugin)

        if not isinstance(plugin, str):
            return False

        try:
            plugin = get_registered_plugin(plugin)
        except PluginNotFoundError:
            return False
        else:
            return super().__contains__(plugin)
