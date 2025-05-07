from typing import Any, Callable, TypeVar, Optional

_T = TypeVar("_T")


class dd:
    def __init__(self, value: Any):
        self._value = value

    def __call__(self, convert: Optional[Callable[[Any], _T]] = None) -> _T:
        if convert is None:
            return self._value
        return convert(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return repr(self._value)
