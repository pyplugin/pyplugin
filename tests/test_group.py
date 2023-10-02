from unittest.mock import MagicMock, call

from pyplugin import plugin, group, PluginGroup


def test_group():
    state = MagicMock()
    preload = "preload"
    post_load = "post_load"

    @group
    def loader(plugins):
        state(preload)

        yield plugins

        state(post_load)

    @plugin
    def plugin1():
        return 1

    @plugin
    def plugin2():
        return 2

    loader.append(plugin1.get_full_name())
    loader.append(plugin2)

    assert plugin1 in loader
    assert plugin1.get_full_name() in loader
    assert plugin2 in loader
    assert plugin2.get_full_name() in loader

    assert loader() == [1, 2]

    assert state.call_args_list == [call(preload), call(post_load)]


def test_group_reqs():
    @plugin
    def upstream(arg="answer"):
        return arg

    my_group_ = PluginGroup(name="my_group", requires=upstream.get_full_name())

    @plugin
    def plugin1(**kwargs):
        return 1, kwargs

    @plugin
    def plugin2(**kwargs):
        return 2, kwargs

    my_group_.append(plugin1)
    my_group_.append(plugin2)

    @plugin(requires=my_group_)
    def downstream(my_group):
        return my_group

    assert downstream() == [(1, {"upstream": "answer"}), (2, {"upstream": "answer"})]
