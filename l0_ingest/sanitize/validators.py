"""
可组合数据验证器

FiniteValidator  — NaN/Inf 检查
PositiveValidator — 正值检查
RangeValidator    — 数值范围检查
ValidatorChain    — 链式组合器
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class Validator(ABC):
    """验证器基类"""

    @abstractmethod
    def validate(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        """
        Returns:
            (ok, error_msg) — ok=True 表示通过
        """
        ...

    def __call__(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        return self.validate(value, field)


class FiniteValidator(Validator):
    """
    检查数值是否为有限数（非 NaN、非 Inf）。

    与当前 sanitization.py 的 _is_finite_and_valid() 逻辑相同。
    """

    def validate(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        if value is None:
            return True, None   # None 由上层决策是否允许
        try:
            f = float(value)
        except (TypeError, ValueError):
            return False, f"{field}: cannot convert {value!r} to float"
        if not math.isfinite(f):
            return False, f"{field}: non-finite value {f}"
        return True, None


class PositiveValidator(Validator):
    """检查数值 > 0（允许 None 通过，由上层决策）"""

    def __init__(self, allow_zero: bool = False) -> None:
        self.allow_zero = allow_zero

    def validate(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return False, f"{field}: cannot convert {value!r} to float"
        if self.allow_zero:
            if f < 0:
                return False, f"{field}: expected >= 0, got {f}"
        else:
            if f <= 0:
                return False, f"{field}: expected > 0, got {f}"
        return True, None


class RangeValidator(Validator):
    """检查数值在 [min_val, max_val] 范围内"""

    def __init__(self, min_val: float, max_val: float) -> None:
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return False, f"{field}: cannot convert {value!r} to float"
        if not (self.min_val <= f <= self.max_val):
            return False, (
                f"{field}: {f} out of range [{self.min_val}, {self.max_val}]"
            )
        return True, None


class ValidatorChain(Validator):
    """
    链式验证器 — 按序执行所有验证器，全部通过才返回 ok。

    例:
        chain = ValidatorChain([FiniteValidator(), PositiveValidator()])
        ok, err = chain.validate(price, "bid")
    """

    def __init__(self, validators: list[Validator]) -> None:
        self._validators = validators

    def validate(self, value: Any, field: str = "") -> Tuple[bool, Optional[str]]:
        for v in self._validators:
            ok, err = v.validate(value, field)
            if not ok:
                return False, err
        return True, None

    def append(self, validator: Validator) -> "ValidatorChain":
        """返回新链（不可变语义）"""
        return ValidatorChain(self._validators + [validator])
