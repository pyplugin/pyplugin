import functools
import importlib
import pkgutil
import typing
import inspect
from collections import OrderedDict


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
        return getattr(module, name)
    except AttributeError:
        if not ignore_missing:
            raise
        else:
            return None


def void_no_args():
    return None


def void_args(*args, **kwargs):
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


def make_safe_args(func: typing.Callable, args=(), kwargs=None, default_args=(), default_kwargs=None):
    """
    Prepares args and kwargs to use to call the function, only passing in what the function signature calls for.

    Can optionally provide default_args and default_kwargs to default to if not provided.

    Arguments:
        func (Callable): The argument to inspect
        args (Iterable): Positional arguments
        kwargs (dict | None): Keyword arguments
        default_args (Iterable): Positional arguments to default to if not provided by args or kwargs
        default_kwargs (dict | None): Keyword arguments to default to if not provided in kwargs
    Returns:
        tuple[tuple, dict]: The args and kwargs to pass into func (e.g. :code:`func(*args, **kwargs`)
    """
    args = list(args) if args else []
    kwargs = kwargs if kwargs else {}
    default_args = list(default_args) if default_args else []
    default_kwargs = default_kwargs if default_kwargs else {}

    param_args = OrderedDict({})
    param_kwargs = OrderedDict({})

    is_partial = isinstance(func, functools.partial)
    orig_func = func

    # unwrap partial and unwrap the args, kwargs
    if is_partial:
        args = list(func.args) + args
        for key, value in func.keywords.items():
            kwargs[key] = value
        func = func.func

    # Use __init__ function if a class
    if inspect.isclass(func):
        func = func.__init__

    argspec = inspect.getfullargspec(func)

    # For each parameter, find a source and populate args / kwargs
    # Search order is: kwargs, args, default_kwargs, default_args
    for param in inspect.signature(func).parameters:
        if param in kwargs:
            param_kwargs[param] = kwargs.pop(param)
        elif args:
            param_args[param] = args[0]
            args = args[1:]
            default_args = default_args[1:]
        elif param in default_kwargs:
            param_kwargs[param] = default_kwargs.pop(param)
        elif default_args:
            param_args[param] = default_args[0]
            default_args = default_args[1:]

    args_, kwargs_ = list(param_args.values()), param_kwargs.copy()

    # Append extra arguments for varargs and varkwargs
    if argspec.varargs:
        args_.extend(args)
        args_.extend(default_args[len(args) :])

    if argspec.varkw:
        for key, value in kwargs.items():
            kwargs_.setdefault(key, value)
        for key, value in default_kwargs.items():
            kwargs_.setdefault(key, value)

    # Remove initial arguments if this was a partial function
    if is_partial:
        args_ = args_[len(orig_func.args) :]
        kwargs_ = {key: value for key, value in kwargs_.items() if key not in orig_func.keywords}

    return tuple(args_), kwargs_
