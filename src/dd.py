from typing import Any, Callable, TypeVar, Optional, List

_T = TypeVar("_T")


class DDException(Exception):
    """自定义异常类，用于美化DD操作中的错误信息"""

    def __init__(self, message: str, path: List[str], value: Any):
        self.message = message
        self.path = path
        self.value = value
        super().__init__(f"{message} at path: {'.'.join(path)}, value: {repr(value)}")


class _DDOperation:
    """记录DD操作的基类"""

    def apply(self, value: Any, path: List[str]) -> Any:
        raise NotImplementedError()


class _DDAttributeOperation(_DDOperation):
    """获取属性操作"""

    def __init__(self, attr: str):
        self.attr = attr

    def apply(self, value: Any, path: List[str]) -> Any:
        current_path = path + [self.attr]
        if value is None:
            return None
        try:
            return getattr(value, self.attr)
        except Exception as e:
            raise DDException(f"Failed to get attribute '{self.attr}': {str(e)}", current_path, value)


class _DDItemOperation(_DDOperation):
    """获取索引/键操作"""

    def __init__(self, key: Any):
        self.key = key

    def apply(self, value: Any, path: List[str]) -> Any:
        current_path = path + [f"[{repr(self.key)}]"]
        if value is None:
            return None
        try:
            return value[self.key]
        except Exception as e:
            raise DDException(f"Failed to get item with key '{self.key}': {str(e)}", current_path, value)


class _DDExpandOperation(_DDOperation):
    """展开操作 [...]"""

    def apply(self, value: Any, path: List[str]) -> List[Any]:
        current_path = path + ["[...]"]
        if value is None:
            return []
        try:
            if isinstance(value, dict):
                return list(value.values())
            elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                return list(value)
            else:
                raise DDException("Cannot expand non-iterable", current_path, value)
        except Exception as e:
            if isinstance(e, DDException):
                raise
            raise DDException(f"Failed to expand: {str(e)}", current_path, value)


class _DDProxy:
    """代理类，用于构建链式操作"""

    def __init__(self, dd_instance, operations=None, null_safe=False):
        self._dd_instance = dd_instance
        self._operations = operations or []
        self._null_safe = null_safe

    def __getattr__(self, attr: str) -> "_DDProxy":
        if attr == "_":
            # 设置所有后续操作为null_safe
            return _DDProxy(self._dd_instance, self._operations, True)

        # 使用当前的null_safe状态创建新的代理
        return _DDProxy(self._dd_instance, self._operations + [_DDAttributeOperation(attr)], self._null_safe)

    def __getitem__(self, key: Any) -> "_DDProxy":
        if key is Ellipsis:  # 处理 [...]
            return _DDProxy(self._dd_instance, self._operations + [_DDExpandOperation()], self._null_safe)
        return _DDProxy(self._dd_instance, self._operations + [_DDItemOperation(key)], self._null_safe)

    def __call__(self, convert: Optional[Callable[[Any], _T]] = None) -> Any:
        """执行所有操作并获取最终结果"""
        result = self._dd_instance._value
        path = ["dd"]

        for op in self._operations:
            # 如果当前值为None并且启用了null_safe，则直接返回None
            if result is None and self._null_safe:
                return None

            try:
                result = op.apply(result, path)
            except Exception as e:
                # 如果启用了null_safe，则返回None而不是抛出异常
                if self._null_safe:
                    return None
                if isinstance(e, DDException):
                    raise
                raise DDException(f"Unexpected error: {str(e)}", path, result)

        if convert is not None:
            try:
                return convert(result)
            except Exception as e:
                if self._null_safe:
                    return None
                raise DDException(f"Conversion error: {str(e)}", path, result)

        return result


class dd:
    def __init__(self, value: Any):
        self._value = value

    def __getattr__(self, attr: str) -> _DDProxy:
        if attr == "_":
            return _DDProxy(self, null_safe=True)
        return _DDProxy(self, [_DDAttributeOperation(attr)])

    def __getitem__(self, key: Any) -> _DDProxy:
        if key is Ellipsis:  # 处理 [...]
            return _DDProxy(self, [_DDExpandOperation()])
        return _DDProxy(self, [_DDItemOperation(key)])

    def __call__(self, convert: Optional[Callable[[Any], _T]] = None) -> _T:
        if convert is None:
            return self._value
        try:
            return convert(self._value)
        except Exception as e:
            raise DDException("Conversion error in base dd", ["dd"], self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return repr(self._value)
