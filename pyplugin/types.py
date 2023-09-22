import typing

from pyplugin.base import Plugin


PluginLike = typing.TypeVar("PluginLike", bound=typing.Union[Plugin, str, typing.Callable])
"""
See :class:`~pyplugin.base.Plugin` initialization argument :code:`plugin` for more information.
"""
