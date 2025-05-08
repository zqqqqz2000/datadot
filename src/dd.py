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
            return value[self.attr]
        except Exception as e:
            raise DDException(f"Failed to get attribute '{self.attr}': {str(e)}", current_path, value) from e


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
            raise DDException(f"Failed to get item with key '{self.key}': {str(e)}", current_path, value) from e


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
            raise DDException(f"Failed to expand: {str(e)}", current_path, value) from e


class _DDMapOperation(_DDOperation):
    """映射操作，将操作应用于列表中的每个元素"""

    def __init__(self, operation: _DDOperation, expansion_level: int = 1):
        self.operation = operation
        self.expansion_level = expansion_level  # 当前映射操作对应的展开级别

    def apply(self, value: Any, path: List[str]) -> List[Any]:
        if value is None:
            return []

        # 如果不是列表，将其视为单元素列表处理
        if not isinstance(value, list):
            try:
                result = self.operation.apply(value, path)
                return [result]
            except DDException as e:
                return [None]

        result = []
        for i, item in enumerate(value):
            item_path = path + [f"[{i}]"]
            try:
                # 如果操作本身是另一个_DDMapOperation，需要考虑展开级别
                if isinstance(self.operation, _DDMapOperation):
                    # 如果当前项是列表，且展开级别 > 1，需要递归应用映射
                    if isinstance(item, list) and self.expansion_level > 1:
                        inner_results = []
                        for j, inner_item in enumerate(item):
                            inner_path = item_path + [f"[{j}]"]
                            operation_copy = self.operation.operation  # 获取内部操作
                            # 创建一个展开级别减1的新映射操作
                            new_op = _DDMapOperation(operation_copy, self.expansion_level - 1)
                            inner_results.append(new_op.apply(inner_item, inner_path))
                        result.append(inner_results)
                    else:
                        result.append(self.operation.apply(item, item_path))
                else:
                    result.append(self.operation.apply(item, item_path))
            except DDException as e:
                # 如果某个元素操作失败，将None添加到结果中
                result.append(None)

        return result


class dd:
    """数据访问主类，用于初始化一个数据导航操作"""

    def __init__(self, value: Any, operations=None, null_safe=False, expansion_levels=None):
        self._value = value
        self._operations: list[_DDOperation] = operations or []
        self._null_safe = null_safe
        self._expansion_levels = expansion_levels or []  # 记录每次展开的层级

    def __getattr__(self, attr: str):
        if attr == "_":
            # 返回一个新的dd实例，使用相同的值和操作，但启用null_safe
            return dd(self._value, self._operations, True, self._expansion_levels)

        # 创建一个新的属性操作
        attr_op = _DDAttributeOperation(attr)

        # 如果存在展开层级，则需要使用_DDMapOperation包装操作
        if self._expansion_levels:
            # 为每个展开级别创建嵌套的映射操作
            op = attr_op
            for level in reversed(self._expansion_levels):
                op = _DDMapOperation(op, level)
            return dd(self._value, self._operations + [op], self._null_safe, self._expansion_levels)
        else:
            return dd(self._value, self._operations + [attr_op], self._null_safe, [])

    def __getitem__(self, key: Any):
        if key is Ellipsis:  # 处理 [...]
            # 添加一个新的展开层级
            new_levels = self._expansion_levels + [1]
            # 返回一个新的dd实例，添加展开操作，并记录展开层级
            return dd(self._value, self._operations + [_DDExpandOperation()], self._null_safe, new_levels)

        # 创建一个新的索引操作
        item_op = _DDItemOperation(key)

        # 如果存在展开层级，则需要使用_DDMapOperation包装操作
        if self._expansion_levels:
            # 为每个展开级别创建嵌套的映射操作
            op = item_op
            for level in reversed(self._expansion_levels):
                op = _DDMapOperation(op, level)
            return dd(self._value, self._operations + [op], self._null_safe, self._expansion_levels)
        else:
            return dd(self._value, self._operations + [item_op], self._null_safe, [])

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
                raise DDException(f"Unexpected error: {str(e)}", path, result) from e

        # 即使convert为None也应该到达这里，保持所有操作的应用
        if convert is not None:
            try:
                return convert(result)
            except Exception as e:
                if self._null_safe:
                    return None
                raise DDException(f"Conversion error: {str(e)}", path, result) from e

        return result
