import typing

from pyplugin import Plugin


PluginLike = typing.TypeVar("PluginLike", bound=typing.Union[Plugin, typing.Callable])
