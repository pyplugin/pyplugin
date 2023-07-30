import os

from collections import namedtuple


_setting = namedtuple("_setting", ("type", "envvar", "default"))


_TYPE_MAP = {
    bool: lambda value: value.lower() == "true",
}


class Settings:
    _PREFIX = "PYPLUGIN"
    _SETTINGS = {
        "eager_find": _setting(
            type=bool, envvar=f"{_PREFIX}_EAGER_FIND", default=False
        ),
        "infer_type": _setting(type=bool, envvar=f"{_PREFIX}_INFER_TYPE", default=True),
        "enforce_type": _setting(
            type=bool, envvar=f"{_PREFIX}_ENFORCE_TYPE", default=False
        ),
    }
    __slots__ = tuple(_SETTINGS.keys())

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key not in self._SETTINGS:
                raise KeyError(f"{key} is not a valid setting.")

        for key, (type_, envvar, default) in self._SETTINGS.items():
            value = os.getenv(envvar, default)
            if isinstance(value, str):
                value = _TYPE_MAP[type_](value)
            setattr(self, key, kwargs.get(key, value))

    def to_dict(self):
        return {key: getattr(self, key) for key in self._SETTINGS}
