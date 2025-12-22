import pytest
import sys
import os
from unittest.mock import MagicMock

# 1. Mock psutil BEFORE importing modules that use it
sys.modules["psutil"] = MagicMock()

# 2. Add the parent directory to sys.path so we can import your actual modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_config(mocker):
    """
    Patches the configuration so we can control settings 
    (like blacklist/whitelist) inside tests.
    """
    mocker.patch("config.BRIDGE_ID", "TEST_BRIDGE")
    mocker.patch("config.BRIDGE_NAME", "Test Home")
    mocker.patch("config.RTL_THROTTLE_INTERVAL", 0) # Default to instant for tests
    mocker.patch("config.DEVICE_BLACKLIST", ["SimpliSafe*", "BadDevice*"])
    mocker.patch("config.DEVICE_WHITELIST", [])