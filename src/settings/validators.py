"""Набор переиспользуемых валидаторов, обеспечивающих корректность настроек."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Pattern, Tuple


class Validator(ABC):
    """Абстрактный валидатор значения."""

    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Возвращает (True, \"\") при успехе либо (False, описание ошибки)."""


class TypeValidator(Validator):
    """Проверяет, что значение принадлежит заданному типу или набору типов."""

    def __init__(self, expected_type: type | Tuple[type, ...]) -> None:
        self.expected_type = expected_type

    def _expected_name(self) -> str:
        if isinstance(self.expected_type, tuple):
            return ", ".join(t.__name__ for t in self.expected_type)
        return self.expected_type.__name__

    def validate(self, value: Any) -> Tuple[bool, str]:
        if isinstance(value, self.expected_type):
            return True, ""
        return (
            False,
            f"Expected value of type {self._expected_name()}, got {type(value).__name__}",
        )


class RangeValidator(Validator):
    """Контролирует принадлежность числового значения к диапазону."""

    def __init__(self, min_value: Optional[Any] = None, max_value: Optional[Any] = None) -> None:
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> Tuple[bool, str]:
        if (self.min_value is not None and value < self.min_value) or (
            self.max_value is not None and value > self.max_value
        ):
            return False, f"Value {value} is out of range [{self.min_value}, {self.max_value}]"
        return True, ""


class EnumValidator(Validator):
    """Проверяет, что значение принадлежит конечному набору."""

    def __init__(self, allowed_values: Iterable[Any]) -> None:
        self.allowed_values = list(allowed_values)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value in self.allowed_values:
            return True, ""
        return False, f"Value {value!r} not in allowed values: {self.allowed_values}"


class RegexValidator(Validator):
    """Проверяет строку по регулярному выражению."""

    def __init__(self, pattern: str | Pattern[str]) -> None:
        self.pattern: Pattern[str] = re.compile(pattern) if isinstance(pattern, str) else pattern

    def validate(self, value: Any) -> Tuple[bool, str]:
        if not isinstance(value, str):
            return False, "RegexValidator expects string values"
        if self.pattern.fullmatch(value):
            return True, ""
        return False, f"Value '{value}' does not match pattern {self.pattern.pattern!r}"


class CompositeValidator(Validator):
    """Комбинирует несколько валидаторов и возвращает первую ошибку."""

    def __init__(self, validators: Iterable[Validator]) -> None:
        self.validators: List[Validator] = list(validators)

    def validate(self, value: Any) -> Tuple[bool, str]:
        for validator in self.validators:
            is_valid, error = validator.validate(value)
            if not is_valid:
                return False, error
        return True, ""
