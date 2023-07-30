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
