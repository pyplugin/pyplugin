import functools

import hypothesis.strategies as st
from hypothesis import assume
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    rule,
    multiple,
)

from pyplugin import Plugin, PluginGroup
from pyplugin.base import _PLUGIN_REGISTRY
from pyplugin.exceptions import CircularDependencyError

from tests.strategies import function_and_call


class PluginStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self._plugins = []

    plugins = Bundle("plugins")
    groups = Bundle("groups")

    @rule(
        target=plugins,
        plugin=function_and_call(),
        name=st.text(),
    )
    def add_plugin(self, plugin, name):
        plugin, load_kwargs = plugin

        assume(name != "")
        assume(name not in _PLUGIN_REGISTRY)

        plugin = Plugin(plugin, name=name)

        plugin._load_callable = functools.partial(plugin._load_callable, **load_kwargs)

        self._plugins.append(plugin)
        return plugin

    @rule(
        targets=(plugins, groups),
        name=st.text(),
    )
    def add_group(self, name):
        assume(name != "")
        assume(name not in _PLUGIN_REGISTRY)

        return PluginGroup(name=name)

    @rule(
        target=groups,
        group=groups,
        plugin=plugins,
    )
    def add_to_group(self, group, plugin):
        assume(plugin not in group)
        assume(plugin is not group)

        try:
            group.safe_add(plugin)
        except CircularDependencyError:
            assume(False)

        return multiple()

    @rule(
        target=plugins,
        plugin1=plugins,
        plugin2=plugins,
        use_name=st.booleans(),
    )
    def add_requirement(self, plugin1, plugin2, use_name):
        assume(plugin1 != plugin2)
        assume(
            not any(
                requirement.plugin in (plugin2, plugin2.get_full_name())
                for requirement in plugin1.requirements.values()
            )
        )
        assume(not plugin1.is_loaded())

        requirement = plugin2 if not use_name else plugin2.get_full_name()
        plugin1.add_requirement(requirement)

        return multiple()

    @rule(
        target=plugins,
        plugin=plugins,
        conflict_strategy=st.one_of(st.just("keep_existing"), st.just("replace"), st.just("force")),
    )
    def load_plugin(self, plugin, conflict_strategy):
        try:
            plugin.load(conflict_strategy=conflict_strategy)
        except CircularDependencyError:
            assume(False)

        assert plugin.is_loaded()
        for dest, dependency in plugin.dependencies.items():
            assert dependency.is_loaded()
            if dest in plugin.load_kwargs and not isinstance(dependency, PluginGroup):
                assert plugin.load_kwargs[dest] == dependency.instance

        return multiple()

    @rule(
        target=plugins,
        plugin=plugins,
    )
    def unload_plugin(self, plugin):
        assume(plugin.is_loaded())

        plugin.unload()

        assert not plugin.is_loaded()
        for dependent in plugin.dependents:
            assert not dependent.is_loaded()

        return multiple()

    def teardown(self):
        _PLUGIN_REGISTRY.clear()


TestPluginStateMachine = PluginStateMachine.TestCase
