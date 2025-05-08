from typing import Any, Callable, TypeVar, Optional, List, Union

_R = TypeVar("_R")  # Return type for converters


class DDException(Exception):
    """Custom exception class for beautifying error messages in DD operations"""

    def __init__(self, message: str, path: List[str], value: Any):
        self.message: str = message
        self.path: List[str] = path
        self.value: Any = value
        super().__init__(f"{message} at full path: {'.'.join(path)}, from value: {repr(value)}")


class _DDOperation:
    """Base class to record DD operations"""

    def apply(self, value: Any, path: List[str]) -> Any:
        raise NotImplementedError()


class _DDAttributeOperation(_DDOperation):
    """Operation to get an attribute"""

    def __init__(self, attr: str, null_safe: bool):
        self.attr: str = attr
        self.null_safe: bool = null_safe

    def apply(self, value: Any, path: List[str]) -> Any:
        path.append(self.attr)
        if value is None and self.null_safe:
            return None
        try:
            return value[self.attr]
        except KeyError as e:
            if self.null_safe:
                return None
            raise DDException(f"Failed to get attribute '{self.attr}': {str(e)}", path, value) from e
        except IndexError as e:
            if self.null_safe:
                return None
            raise DDException(f"Failed to get attribute '{self.attr}': {str(e)}", path, value) from e
        except Exception as e:
            raise DDException(f"Failed to get attribute '{self.attr}': {str(e)}", path, value) from e


class _DDItemOperation(_DDOperation):
    """Operation to get an item by index/key"""

    def __init__(self, key: Any, null_safe: bool):
        self.key: Any = key
        self.null_safe: bool = null_safe

    def apply(self, value: Any, path: List[str]) -> Any:
        path.append(f"[{repr(self.key)}]")
        if value is None and self.null_safe:
            return None
        try:
            return value[self.key]
        except KeyError as e:
            if self.null_safe:
                return None
            raise DDException(f"Failed to get attribute '{self.key}': {str(e)}", path, value) from e
        except IndexError as e:
            if self.null_safe:
                return None
            raise DDException(f"Failed to get attribute '{self.key}': {str(e)}", path, value) from e
        except Exception as e:
            raise DDException(f"Failed to get item with key '{self.key}': {str(e)}", path, value) from e


class _DDExpandOperation(_DDOperation):
    """Expansion operation [...]"""

    def apply(self, value: Any, path: List[str]) -> List[Any]:
        path.append("[...]")
        if value is None:
            return []
        try:
            if isinstance(value, dict):
                return list(value.values())
            elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                return list(value)
            else:
                raise DDException("Cannot expand non-iterable", path, value)
        except Exception as e:
            if isinstance(e, DDException):
                raise
            raise DDException(f"Failed to expand: {str(e)}", path, value) from e


class _DDMapOperation(_DDOperation):
    """Mapping operation, apply operations to each element in a list"""

    def __init__(self, operation: _DDOperation, expansion_level: int = 1):
        self.operation: _DDOperation = operation
        self.expansion_level: int = expansion_level  # Current expansion level for this mapping operation

    def apply(self, value: Any, path: List[str]) -> List[Any]:
        if value is None:
            return []

        # If not a list, treat as a single-element list
        if not isinstance(value, list):
            result = self.operation.apply(value, path)
            return [result]

        result: List[Any] = []
        for i, item in enumerate(value):
            item_path = path + [f"[{i}]"]
            # If the operation itself is another _DDMapOperation, need to consider expansion level
            if isinstance(self.operation, _DDMapOperation):
                # If current item is a list and expansion level > 1, need to recursively apply mapping
                if isinstance(item, list) and self.expansion_level > 1:
                    inner_results: List[Any] = []
                    for j, inner_item in enumerate(item):
                        inner_path = item_path + [f"[{j}]"]
                        operation_copy = self.operation.operation  # Get inner operation
                        # Create a new mapping operation with expansion level reduced by 1
                        new_op = _DDMapOperation(operation_copy, self.expansion_level - 1)
                        inner_results.append(new_op.apply(inner_item, inner_path))
                    result.append(inner_results)
                else:
                    result.append(self.operation.apply(item, item_path))
            else:
                result.append(self.operation.apply(item, item_path))

        return result


class dd:
    """Main data access class, initializes a data navigation operation"""

    def __init__(
        self,
        value: Any,
        operations: Optional[List[_DDOperation]] = None,
        null_safe: bool = False,
        expansion_levels: Optional[List[int]] = None,
    ):
        self._value: Any = value
        self._operations: List[_DDOperation] = operations or []
        self._null_safe: bool = null_safe
        self._expansion_levels: List[int] = expansion_levels or []  # Record each expansion level

    def __getattr__(self, attr: str) -> "dd":
        if attr == "_":
            # Return a new dd instance with the same value and operations, but with null_safe enabled
            return dd(self._value, self._operations, True, self._expansion_levels)

        # Create a new attribute operation
        attr_op = _DDAttributeOperation(attr, self._null_safe)

        # If expansion levels exist, need to wrap the operation with _DDMapOperation
        if self._expansion_levels:
            # Create nested mapping operations for each expansion level
            op: _DDOperation = attr_op
            for level in reversed(self._expansion_levels):
                op = _DDMapOperation(op, level)
            return dd(self._value, self._operations + [op], self._null_safe, self._expansion_levels)
        else:
            return dd(self._value, self._operations + [attr_op], self._null_safe, [])

    def __getitem__(self, key: Any) -> "dd":
        if key is Ellipsis:  # Handle [...]
            # Add a new expansion level
            new_levels = self._expansion_levels + [1]
            # Return a new dd instance, add expansion operation, and record expansion level
            return dd(self._value, self._operations + [_DDExpandOperation()], self._null_safe, new_levels)

        # Create a new item operation
        item_op = _DDItemOperation(key, self._null_safe)

        # If expansion levels exist, need to wrap the operation with _DDMapOperation
        if self._expansion_levels:
            # Create nested mapping operations for each expansion level
            op: _DDOperation = item_op
            for level in reversed(self._expansion_levels):
                op = _DDMapOperation(op, level)
            return dd(self._value, self._operations + [op], self._null_safe, self._expansion_levels)
        else:
            return dd(self._value, self._operations + [item_op], self._null_safe, [])

    def __call__(self, convert: Optional[Callable[[Any], _R]] = None) -> Union[_R, Any]:
        """Execute all operations and get the final result"""
        result: Any = self._value
        path: List[str] = ["dd"]

        for op in self._operations:
            if result is None and self._null_safe:
                result = None
                break

            try:
                result = op.apply(result, path)
            except Exception as e:
                if isinstance(e, DDException):
                    raise
                raise DDException(f"Unexpected error: {str(e)}", path, result) from e

        # Should reach here even if convert is None, to keep all operations applied
        if convert is not None:
            try:
                return convert(result)
            except Exception as e:
                raise DDException(f"Conversion error: {str(e)}", path, result) from e

        return result
