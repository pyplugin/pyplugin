import functools
import typing
from typing import MutableSequence

from pyplugin.base import Plugin, _R
from pyplugin.utils import void_args, empty


def load_all(plugins, *args, **kwargs):
    return [plugin.load(*args, **kwargs) for plugin in plugins]


def unload_all(plugins, instances=()):
    return [plugin.unload(instance) for plugin, instance in zip(plugins, instances)]


class PluginGroup(Plugin, MutableSequence[Plugin]):
    def __init__(
        self,
        plugin: typing.Callable[..., _R] = void_args,
        unload_callable: typing.Callable[[_R], typing.Any] = void_args,
        **kwargs,
    ):
        self.plugins = []

        super().__init__(
            plugin,
            unload_callable=unload_callable,
            **kwargs,
        )
        self._load_callable = functools.partial(self._load, self._load_callable)
        self._unload_callable = functools.partial(self._unload, self._unload_callable)

    def _load(self, load_callable, *args, **kwargs):
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

        ret = load_all(plugins, *args, **kwargs)

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def _unload(self, unload_callable, instance):
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
                ret = ret, instance
            plugins_, instance_ = ret
            plugins, instance = (
                plugins_ if plugins_ else plugins,
                instance_ if instance_ is not empty else instance,
            )

        ret = unload_all(plugins, instance)

        if gen:
            try:
                next(gen)
            except StopIteration:
                pass

        return ret

    def __getitem__(self, index: int) -> Plugin:
        return self.plugins[index]

    def __setitem__(self, index: int, value: Plugin):
        self.plugins[index] = value

    def __delitem__(self, index: int):
        self.plugins.pop(index)

    def __len__(self) -> int:
        return len(self.plugins)

    def insert(self, index: int, value: Plugin):
        self.plugins.insert(index, value)
