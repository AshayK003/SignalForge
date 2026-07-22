import pytest
from bot import categorize_error, validate_user_input


def test_validate_user_input_ok():
    assert validate_user_input("  hello  ") == "hello"


def test_validate_user_input_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_user_input("   ")


def test_validate_user_input_too_long():
    with pytest.raises(ValueError, match="too_long"):
        validate_user_input("x" * 10, max_len=5)


def test_categorize_error():
    assert categorize_error(ValueError("empty_input")) == "validation_empty"
    assert categorize_error(TimeoutError("timeout")) == "timeout"
    assert categorize_error(RuntimeError("rate limit exceeded")) == "rate_limit"
