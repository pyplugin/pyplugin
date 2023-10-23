import contextlib
import os
import typing

from collections import namedtuple

from pyplugin.exceptions import SettingNotFound, InvalidSettingError
from pyplugin.utils import empty


_setting = namedtuple("_setting", ("name", "type", "envvar", "values", "default"))


_TYPE_MAP = {
    bool: lambda value: value.lower() == "true",
}

_PREFIX = "PYPLUGIN"

INFER_TYPE = _setting(name="infer_type", type=bool, envvar=f"{_PREFIX}_INFER_TYPE", values=(True, False), default=True)
""" Attempt to infer the type of defined plugins upon initialization and upon loading. """

ENFORCE_TYPE = _setting(
    name="enforce_type", type=bool, envvar=f"{_PREFIX}_ENFORCE_TYPE", values=(True, False), default=False
)
""" Throw an error if a plugin is loaded that returns an object that does not match its defined type. """

IMPORT_LOOKUP = _setting(
    name="import_lookup", type=bool, envvar=f"{_PREFIX}_IMPORT_LOOKUP", values=(True, False), default=True
)
""" 
When using the :func:`~pyplugin.base.lookup_plugin` function, (e.g. in dependency lookups), default
to using :code:`importlib` as a fallback to find and register the plugin. 
"""

DYNAMIC_REQUIREMENTS = _setting(
    name="dynamic_requirements", type=bool, envvar=f"{_PREFIX}_DYNAMIC_REQUIREMENTS", values=(True, False), default=True
)
""" 
Loading Plugin 1 within Plugin 2 will dynamically set Plugin 1 as a requirement for Plugin 2 as if it was explicitly 
defined in :code:`requires`.
"""

REGISTER_MODE = _setting(
    name="register_mode",
    type=str,
    envvar=f"{_PREFIX}_REGISTER_MODE",
    values=("eager", "replace", "transient", "replace+transient"),
    default="eager",
)
"""
Handles registering plugins on initialization. :code:`eager`:  register as normal, :code:`replace`: replace the
already registered plugin, :code:`transient`: registering a plugin with same name will replace the current
plugin, :code:`replace+transient` is a combination of the two.
"""

_SETTINGS: dict[str, _setting] = {
    setting.name: setting for setting in (INFER_TYPE, ENFORCE_TYPE, IMPORT_LOOKUP, DYNAMIC_REQUIREMENTS, REGISTER_MODE)
}


def set_flag(setting: typing.Union[str, _setting], value: typing.Any):
    """
    Arguments:
      setting (str): The setting name to set
      value (Any): The value to set
    """
    if isinstance(setting, str):
        if setting not in _SETTINGS:
            raise SettingNotFound(setting)
        setting = _SETTINGS[setting]

    os.environ[setting.envvar] = value


def unset_flag(setting: str):
    """
    Arguments:
      setting (str): The setting name to unset
    Returns:
        Any | None: The previously set value or None
    """
    if isinstance(setting, str):
        if setting not in _SETTINGS:
            raise SettingNotFound(setting)
        setting = _SETTINGS[setting]

    return os.environ.pop(setting.envvar, None)


@contextlib.contextmanager
def with_flag(setting: typing.Union[str, _setting], value: typing.Any):
    if isinstance(setting, str):
        if setting not in _SETTINGS:
            raise SettingNotFound(setting)
        setting = _SETTINGS[setting]
    old_value = os.getenv(setting.envvar, empty)

    set_flag(setting, value)
    try:
        yield
    finally:
        if old_value is not empty:
            set_flag(setting, old_value)


class Settings:
    __slots__ = tuple(_SETTINGS.keys())

    def __init__(self, **kwargs):
        self.merge(kwargs)

    def __getitem__(self, key):
        if key not in _SETTINGS:
            raise KeyError(key)
        return getattr(self, key)

    def to_dict(self):
        return {key: getattr(self, key) for key in _SETTINGS}

    def merge(self, data):
        for key, value in data.items():
            if key not in _SETTINGS:
                raise KeyError(f"{key} is not a valid setting.")

        for key, (_, type_, envvar, values, default) in _SETTINGS.items():
            value = os.getenv(envvar, default)
            if isinstance(value, str):
                value = _TYPE_MAP.get(type_, type_)(value)
            if value not in values:
                raise InvalidSettingError(f"Invalid setting value {values} for setting {key}, expected one of {values}")
            setattr(self, key, data.get(key, value))
