""" Test module """
from pyplugin.base import PluginManager


def test():
    """Basic test"""
    manager = PluginManager("")
    instance = manager.find("platform.platform").load().instance

    print()
    print(manager.get_string_tree())
