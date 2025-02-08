import os
import pytest
from app.core.settings.configurations import ProductionSettings, LocalSettings

def test_settings_local(monkeypatch):
    """Test that local settings load with the correct values."""
    monkeypatch.setenv("ENV", "local")
    local_settings = LocalSettings()
    assert local_settings.DEBUG is True
    assert local_settings.LOG_LEVEL.upper() == "DEBUG"

def test_settings_production(monkeypatch):
    """Test that production settings load with the correct values."""
    monkeypatch.setenv("ENV", "production")
    prod_settings = ProductionSettings()
    assert prod_settings.DEBUG is False
    assert prod_settings.LOG_LEVEL.upper() == "INFO"
