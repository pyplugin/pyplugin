# pylint: disable=empty-docstring


class PluginError(Exception):
    """ """


class PluginLockedError(PluginError):
    """ """


class PluginTypeError(PluginError):
    """ """


class PluginLoadError(PluginError):
    """ """


class PluginPartiallyLoadedError(PluginLoadError):
    """ """


class PluginUnloadError(PluginError):
    """ """


class PluginAlreadyUnloadedError(PluginUnloadError):
    """ """


class PluginRegisterError(PluginError):
    """ """


class PluginNotFoundError(PluginRegisterError):
    """ """
