"""Проверки валидаторов настроек."""

from __future__ import annotations

import re

from src.settings.validators import (
    CompositeValidator,
    EnumValidator,
    RangeValidator,
    RegexValidator,
    TypeValidator,
)


def test_type_validator_success() -> None:
    validator = TypeValidator(int)
    assert validator.validate(5) == (True, "")


def test_type_validator_failure() -> None:
    validator = TypeValidator(str)
    is_valid, error = validator.validate(123)
    assert not is_valid
    assert "str" in error


def test_range_validator_within_bounds() -> None:
    validator = RangeValidator(1, 10)
    assert validator.validate(5) == (True, "")


def test_range_validator_out_of_bounds() -> None:
    validator = RangeValidator(1, 10)
    is_valid, error = validator.validate(11)
    assert not is_valid
    assert "out of range" in error


def test_enum_validator_success() -> None:
    validator = EnumValidator(["ru", "en"])
    assert validator.validate("ru") == (True, "")


def test_enum_validator_failure() -> None:
    validator = EnumValidator(["ru", "en"])
    is_valid, error = validator.validate("es")
    assert not is_valid
    assert "allowed values" in error


def test_regex_validator_success() -> None:
    validator = RegexValidator(r"^[A-Z]+$")
    assert validator.validate("ABC") == (True, "")


def test_regex_validator_failure_when_not_string() -> None:
    validator = RegexValidator(r"^[A-Z]+$")
    is_valid, error = validator.validate(123)
    assert not is_valid
    assert "string" in error


def test_regex_validator_failure_pattern() -> None:
    validator = RegexValidator(r"^[A-Z]+$")
    is_valid, error = validator.validate("abc")
    assert not is_valid
    assert "does not match" in error


def test_composite_validator_stops_on_first_error() -> None:
    validator = CompositeValidator([TypeValidator(int), RangeValidator(0, 10)])
    is_valid, error = validator.validate("not int")
    assert not is_valid
    assert "type" in error


def test_composite_validator_all_pass() -> None:
    validator = CompositeValidator([TypeValidator(str), RegexValidator(r"^[a-z]+$")])
    assert validator.validate("abc") == (True, "")


def test_regex_validator_supports_compiled_pattern() -> None:
    pattern = re.compile(r"^[0-9]+$")
    validator = RegexValidator(pattern)
    assert validator.validate("1234") == (True, "")
