from pyplugin.base import Plugin
from pyplugin.utils import maybe_decorator


@maybe_decorator
def plugin(*args, cls=Plugin, **kwargs):
    return cls(*args, **kwargs)
