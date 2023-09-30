from pyplugin import plugin, lookup_plugin


@plugin
def upstream(arg=4):
    return arg


@plugin(requires="tests.test_example.upstream")
def two_plus_two(**kwargs):
    return kwargs


def test_example():
    answer = 4
    assert two_plus_two()[upstream.name] == answer

    answer = 5
    upstream(arg=answer)

    assert two_plus_two.instance[upstream.name] == answer


def test_dynamic_req():
    @plugin
    def dyn_plugin(**kwargs):
        return upstream()

    assert dyn_plugin() == upstream()

    assert upstream in dyn_plugin.dependencies.values()
    assert dyn_plugin in upstream.dependents

    answer = 5
    upstream(arg=answer)

    assert dyn_plugin() == answer
