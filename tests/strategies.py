import inspect
import random
import typing
from string import printable

import hypothesis.strategies as st


def _add(x: int, y: int, **kwargs) -> int:
    return x + y


def _concat(value1: str, value2: str, delimiter: str, **kwargs) -> str:
    return delimiter.join((value1, value2))


_FUNCS = [
    _add,
    _concat,
]


_TYPES = [
    dict,
]


json = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(printable),
    lambda children: st.lists(children) | st.dictionaries(st.text(printable), children),
)

_TYPE_MAP = {
    dict: st.dictionaries(keys=st.text(), values=json),
    str: st.text(),
    typing.Any: st.text(),
    int: st.integers(),
    float: st.floats(),
}


@st.composite
def kallable(draw):
    ret = random.choice(_FUNCS)
    return draw(st.one_of(st.functions(like=ret), st.just(random.choice(_TYPES))))


@st.composite
def function_and_call(draw, func=kallable()):
    func = draw(func)

    func_ = func
    if inspect.isclass(func):
        func_ = func.__init__

    argspec = inspect.getfullargspec(func_)

    kwargs = {}
    for arg in argspec.args:
        if arg not in argspec.annotations:
            continue
        kwargs[arg] = draw(_TYPE_MAP[argspec.annotations[arg]])

    return func, kwargs
