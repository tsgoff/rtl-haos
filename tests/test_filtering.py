import pytest
from rtl_manager import is_blocked_device

def test_blacklist_logic(mocker):
    """
    Verifies that devices are correctly blocked by ID, Model, or Type.
    """
    # 1. Setup Config with Wildcards
    # We block:
    # - Any ID starting with '123'
    # - Any Model containing 'Tire'
    # - Any Type equal to 'smoke'
    mock_blacklist = ["123*", "*Tire*", "smoke"]
    mocker.patch("config.DEVICE_BLACKLIST", mock_blacklist)

    # 2. Test Cases that should be BLOCKED (True)
    assert is_blocked_device("12345", "Generic", "weather") is True  # Matches ID wildcard
    assert is_blocked_device("99999", "EezTire", "pressure") is True # Matches Model wildcard
    assert is_blocked_device("55555", "Nest", "smoke") is True       # Matches Type exact

    # 3. Test Cases that should be ALLOWED (False)
    assert is_blocked_device("98765", "Generic", "weather") is False
    assert is_blocked_device("55555", "Nest", "co2") is False