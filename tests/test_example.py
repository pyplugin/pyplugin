from pyplugin import plugin


@plugin
def upstream(arg=4):
    print(arg)
    return arg


@plugin(requires="tests.test_example.upstream")
def two_plus_two(**kwargs):
    print(kwargs)
    return kwargs


two_plus_two()

upstream(5)
