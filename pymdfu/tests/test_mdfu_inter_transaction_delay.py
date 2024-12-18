"""Tests for the InterTransactionDelay class"""
import pytest
from ..mdfu import InterTransactionDelay

def test_initialization():
    """
    Test that the InterTransactionDelay object is initialized with valid values.
    """
    delay = InterTransactionDelay(1.0)
    assert delay.seconds == 1.0
    assert delay.ns == 1_000_000_000

def test_initialization_with_max_value():
    """
    Test that the max possible value works as initializer.
    """
    delay = InterTransactionDelay(InterTransactionDelay.MAX_INTER_TRANSACTION_DELAY_SECONDS)
    assert delay.seconds == InterTransactionDelay.MAX_INTER_TRANSACTION_DELAY_SECONDS
    assert delay.ns == int(InterTransactionDelay.MAX_INTER_TRANSACTION_DELAY_SECONDS * 1e9)

def test_init_invalid_values():
    """
    Test that the InterTransactionDelay object raises ValueError for invalid values.
    Invalid values are negative or too large.
    """
    with pytest.raises(ValueError):
        InterTransactionDelay(-1)

    with pytest.raises(ValueError):
        InterTransactionDelay(InterTransactionDelay.MAX_INTER_TRANSACTION_DELAY_SECONDS + 1)

def test_from_bytes():
    """
    Test that the from_bytes class method correctly creates an InterTransactionDelay object.
    """
    delay = InterTransactionDelay.from_bytes((123456789).to_bytes(4, byteorder="little"))
    assert delay.seconds == 0.123456789
    assert delay.ns == 123456789

def test_from_bytes_with_invalid_length():
    """
    Test that the from_bytes class method raises ValueError when the byte length is incorrect.
    """
    with pytest.raises(ValueError):
        InterTransactionDelay.from_bytes(b'\x01\x02\x03')  # Only 3 bytes

def test_to_bytes():
    """
    Test that the to_bytes method returns the correct byte representation of the delay.
    """
    delay = InterTransactionDelay(0.123456789)
    assert delay.to_bytes() == (123456789).to_bytes(4, byteorder="little")

# Run the tests
if __name__ == "__main__":
    pytest.main()
