import hypothesis.strategies as st
from hypothesis import assume
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    rule,
    multiple,
)

from pyplugin import Plugin
from pyplugin.base import empty, get_plugin_name, _PLUGIN_REGISTRY

from tests.strategies import function_and_call


class PluginStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self._plugins = []

    plugins = Bundle("plugins")

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

        plugin.load_kwargs = load_kwargs
        self._plugins.append(plugin)
        return plugin

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

        requirement = plugin2 if not use_name else plugin2.get_full_name()
        plugin1.add_requirement(requirement)

        return multiple()

    @rule(
        target=plugins,
        plugin=plugins,
        conflict_strategy=st.one_of(st.just("keep_existing"), st.just("replace"), st.just("force")),
    )
    def load_plugin(self, plugin, conflict_strategy):
        plugin.load(conflict_strategy=conflict_strategy, **plugin.load_kwargs)

        assert plugin.is_loaded()

        return multiple()

    @rule(
        target=plugins,
        plugin=plugins,
    )
    def unload_plugin(self, plugin):
        assume(plugin.is_loaded())

        plugin.unload()

        assert not plugin.is_loaded()

        return multiple()

    def teardown(self):
        _PLUGIN_REGISTRY.clear()


TestPluginStateMachine = PluginStateMachine.TestCase
