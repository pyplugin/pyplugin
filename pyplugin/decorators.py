from pyplugin.base import Plugin
from pyplugin.group import PluginGroup
from pyplugin.utils import maybe_decorator


@maybe_decorator
def plugin(*args, cls=Plugin, **kwargs):
    return cls(*args, **kwargs)


@maybe_decorator
def group(*args, cls=PluginGroup, **kwargs):
    return cls(*args, **kwargs)
