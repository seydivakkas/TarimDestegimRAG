import json
import logging

from tarim_destek_rag.config.settings import Settings
from tarim_destek_rag.logging.logger import StructuredJsonFormatter, setup_logger


def test_health():
    """Temel sağlık smoke testi."""
    assert True


def test_config_defaults():
    """Varsayılan konfigürasyon doğrulaması."""
    cfg = Settings()
    assert cfg.app_env in ["development", "production", "test"]
    assert cfg.api_port == 8000
    assert "sqlite" in cfg.database_url


def test_structured_logger():
    """Yapılandırılmış log formatlayıcı testi."""
    logger = setup_logger("test_logger", "DEBUG")
    assert logger is not None
    record = logging.LogRecord(
        name="test_component",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test mesajı",
        args=(),
        exc_info=None,
    )
    setattr(record, "component", "test_modul")
    setattr(record, "event", "TEST_EVENT")
    formatter = StructuredJsonFormatter()
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["component"] == "test_modul"
    assert parsed["event"] == "TEST_EVENT"
    assert parsed["message"] == "Test mesajı"
