import pytest

from pyplugin import plugin


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
    def dyn_plugin():
        return upstream()

    assert dyn_plugin() == upstream()

    assert upstream in dyn_plugin.dependencies.values()
    assert dyn_plugin in upstream.dependents

    answer = 5
    upstream(arg=answer)

    assert dyn_plugin.instance == answer


def test_exception_throwing():
    @plugin(anonymous=True)
    def throw_error():
        raise ValueError

    with pytest.raises(ValueError):
        throw_error.load()


def test_callback():
    @plugin(anonymous=True)
    def returns_1():
        return 1

    returns_1.add_callback(lambda instance: instance + 1)

    assert returns_1() == 2
