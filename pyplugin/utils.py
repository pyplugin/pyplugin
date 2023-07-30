import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)


def import_helper(name: str, ignore_missing: bool = True):
    *module, name = name.split(".")
    module = ".".join(module)
    if not module:
        module = name

    try:
        module = importlib.import_module(module)
    except (ModuleNotFoundError, ValueError) as err:
        error_message = ("Module '%s' not found.", module)
        if not ignore_missing:
            logger.error(*error_message, stacklevel=2)
            raise err
        else:
            logger.error(*error_message, stacklevel=2)
            return None

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
    except AttributeError as err:
        error_message = ("Attribute '%s' not found in module '%s'.", name, module)
        if not ignore_missing:
            logger.error(*error_message, stacklevel=2)
            raise err
        else:
            logger.error(*error_message, stacklevel=2)
            return None
