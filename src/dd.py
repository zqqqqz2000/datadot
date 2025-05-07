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


class dd:
    """数据访问主类，用于初始化一个数据导航操作"""

    def __init__(self, value: Any, operations=None, null_safe=False):
        self._value = value
        self._operations = operations or []
        self._null_safe = null_safe

    def __getattr__(self, attr: str):
        if attr == "_":
            # 返回一个新的dd实例，使用相同的值和操作，但启用null_safe
            return dd(self._value, self._operations, True)
        # 返回一个新的dd实例，添加属性操作
        return dd(self._value, self._operations + [_DDAttributeOperation(attr)], self._null_safe)

    def __getitem__(self, key: Any):
        if key is Ellipsis:  # 处理 [...]
            # 返回一个新的dd实例，添加展开操作
            return dd(self._value, self._operations + [_DDExpandOperation()], self._null_safe)
        # 返回一个新的dd实例，添加索引操作
        return dd(self._value, self._operations + [_DDItemOperation(key)], self._null_safe)

    def __call__(self, convert: Optional[Callable[[Any], _T]] = None) -> Any:
        """执行所有操作并获取最终结果"""
        result = self._value
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

        # 即使convert为None也应该到达这里，保持所有操作的应用
        if convert is not None:
            try:
                return convert(result)
            except Exception as e:
                if self._null_safe:
                    return None
                raise DDException(f"Conversion error: {str(e)}", path, result)

        return result
