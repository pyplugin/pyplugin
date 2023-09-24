# pylint: disable=empty-docstring


class PluginError(Exception):
    """ """


class PluginLockedError(PluginError):
    """ """


class PluginTypeError(PluginError, TypeError):
    """ """


class PluginLoadError(PluginError):
    """ """


class PluginPartiallyLoadedError(PluginLoadError):
    """ """


class PluginAlreadyLoadedError(PluginLoadError):
    """ """


class DependencyError(PluginError):
    """ """


class CircularDependencyError(DependencyError):
    """ """


class InconsistentDependencyError(DependencyError):
    """ """


class PluginUnloadError(PluginError):
    """ """


class PluginAlreadyUnloadedError(PluginUnloadError):
    """ """


class PluginRegisterError(PluginError):
    """ """


class PluginNotFoundError(PluginRegisterError):
    """ """


class PluginRequirementError(PluginError):
    """ """
