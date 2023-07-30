import functools
import importlib
import pkgutil
import typing
import inspect


empty = object()
""" An object to use when None is a valid value for an argument """


class _MethodDecoratorAdapter:
    def __init__(self, decorator, func):
        self.decorator = decorator
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.decorator(self.func)(*args, **kwargs)

    def __get__(self, instance, owner):
        return self.decorator(self.func.__get__(instance, owner))


def auto_adapt_to_methods(decorator):
    def adapt(func):
        return _MethodDecoratorAdapter(decorator, func)

    return adapt


@auto_adapt_to_methods
def maybe_decorator(func: typing.Callable):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not args:
            return maybe_decorator(functools.partial(func, **kwargs))
        return func(*args, **kwargs)

    return wrapper


def import_helper(name: str, ignore_missing: bool = True):
    *module, name = name.split(".")
    module = ".".join(module)
    if not module:
        module, name = name, ""

    try:
        module = importlib.import_module(module)
    except (ModuleNotFoundError, ValueError):
        if not ignore_missing:
            raise
        else:
            return None

    if not name:
        return module

    if hasattr(module, "__path__"):
        for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
            if module_name != name:
                continue
            try:
                submodule = loader.find_module(module_name).load_module(module_name)
            except ImportError:
                continue
            setattr(module, module_name, submodule)

    try:
        return module.__getattribute__(name)
    except AttributeError:
        if not ignore_missing:
            raise
        else:
            return None


def void_no_args():
    return None


def void_args(*args):
    return None


def infer_return_type(obj: typing.Any):
    if inspect.isfunction(obj):
        return obj.__annotations__.get("return", None)
    elif inspect.isclass(obj):
        return obj
    raise TypeError(f"Invalid type {type(obj)}, expected a function or class.")


def ensure_a_list(data):
    """Ensure data is a list or wrap it in a list"""
    if not data:
        return []
    if isinstance(data, (list, tuple, set)):
        return list(data)
    return [data]
