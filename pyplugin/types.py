import typing

from pyplugin import Plugin


PluginLike = typing.TypeVar("PluginLike", bound=typing.Union[Plugin, typing.Callable])
"""
See :class:`Plugin` initialization argument :code:`plugin` for more information.
"""
