class PluginError(Exception):
    """ """


class PluginRegistrationError(PluginError):
    """ """


class PluginDisabledError(PluginError):
    """ """


class PluginTypeError(PluginError):
    """ """


class PluginLoadError(PluginError):
    """ """


class PluginPartiallyLoadedError(PluginLoadError):
    """ """


class PluginAlreadyLoadedError(PluginLoadError):
    """ """


class PluginUnloadError(PluginError):
    """ """


class PluginAlreadyUnloadedError(PluginUnloadError):
    """ """


class PluginNotFound(KeyError, PluginError):
    """ """
