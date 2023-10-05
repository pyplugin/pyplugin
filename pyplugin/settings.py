import os
import typing

from collections import namedtuple

from pyplugin.exceptions import SettingNotFound, InvalidSettingError


__all__ = ["_SETTINGS", "set_flag", "unset_flag", "Settings"]


_setting = namedtuple("_setting", ("type", "envvar", "values", "default"))


_TYPE_MAP = {
    bool: lambda value: value.lower() == "true",
}

_PREFIX = "PYPLUGIN"

_SETTINGS: dict[str, _setting] = {
    "infer_type": _setting(type=bool, envvar=f"{_PREFIX}_INFER_TYPE", values=(True, False), default=True),
    "enforce_type": _setting(type=bool, envvar=f"{_PREFIX}_ENFORCE_TYPE", values=(True, False), default=False),
    "import_lookup": _setting(type=bool, envvar=f"{_PREFIX}_IMPORT_LOOKUP", values=(True, False), default=True),
    "dynamic_requirements": _setting(
        type=bool, envvar=f"{_PREFIX}_DYNAMIC_REQUIREMENTS", values=(True, False), default=True
    ),
    "register_mode": _setting(
        type=str,
        envvar=f"{_PREFIX}_REGISTER_MODE",
        values=("eager", "replace", "transient", "replace+transient"),
        default="eager",
    ),
}


for key in _SETTINGS:
    globals()[key.upper()] = key
    __all__.append(key.upper())


def set_flag(setting: str, value: typing.Any):
    """
    Arguments:
      setting (str): The setting name to set
      value (Any): The value to set
    """
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
    if setting not in _SETTINGS:
        raise SettingNotFound(setting)

    setting = _SETTINGS[setting]

    return os.environ.pop(setting.envvar, None)


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

        for key, (type_, envvar, values, default) in _SETTINGS.items():
            value = os.getenv(envvar, default)
            if isinstance(value, str):
                value = _TYPE_MAP.get(type_, type_)(value)
            if value not in values:
                raise InvalidSettingError(f"Invalid setting value {values} for setting {key}, expected one of {values}")
            setattr(self, key, data.get(key, value))
