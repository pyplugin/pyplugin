from pyplugin import plugin


@plugin
def upstream(arg=4):
    return arg


@plugin(requires="tests.test_example.upstream")
def two_plus_two(**kwargs):
    return kwargs


def test_example():
    answer = 4
    assert two_plus_two()["upstream"] == answer

    answer = 5
    upstream(answer)

    assert two_plus_two.instance["upstream"] == answer
