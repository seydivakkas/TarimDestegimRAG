from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TarımDestekRAG merkezi ayarları."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Genel
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Veritabanı
    database_url: str = Field(default="sqlite:///./data/tarim_destek.db", alias="DATABASE_URL")

    # Dosya yolları
    raw_data_path: str = Field(default="./data/raw", alias="RAW_DATA_PATH")
    normalized_data_path: str = Field(default="./data/normalized", alias="NORMALIZED_DATA_PATH")
    index_path: str = Field(default="./data/indexes", alias="INDEX_PATH")
    snapshot_path: str = Field(default="./data/snapshots", alias="SNAPSHOT_PATH")

    # Vektör Arama & Modeller
    embedding_model_name: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL_NAME",
    )
    vector_dimension: int = 384
    retrieval_top_k: int = 5

    # Kazıyıcı Ayarları
    scraper_rate_limit_seconds: float = 1.5
    scraper_timeout_seconds: float = 30.0
    scraper_max_retries: int = 3

    @classmethod
    def load_from_yaml(cls, yaml_path: str = "configs/app.yaml") -> "Settings":
        """YAML dosyasından ayarları yükler ve ortam değişkenleriyle birleştirir."""
        data: dict[str, Any] = {}
        path = Path(yaml_path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                raw_yaml = yaml.safe_load(f) or {}
                if "app" in raw_yaml:
                    data["app_env"] = raw_yaml["app"].get("environment", "development")
                    data["log_level"] = raw_yaml["app"].get("log_level", "INFO")
                    data["api_host"] = raw_yaml["app"].get("api_host", "0.0.0.0")
                    data["api_port"] = raw_yaml["app"].get("api_port", 8000)
                if "database" in raw_yaml:
                    data["database_url"] = raw_yaml["database"].get(
                        "url", "sqlite:///./data/tarim_destek.db"
                    )
                if "storage" in raw_yaml:
                    storage = raw_yaml["storage"]
                    data["raw_data_path"] = storage.get("raw_data_path", "./data/raw")
                    data["normalized_data_path"] = storage.get(
                        "normalized_data_path", "./data/normalized"
                    )
                    data["index_path"] = storage.get("index_path", "./data/indexes")
                    data["snapshot_path"] = storage.get("snapshot_path", "./data/snapshots")
                if "retrieval" in raw_yaml:
                    retrieval = raw_yaml["retrieval"]
                    data["embedding_model_name"] = retrieval.get(
                        "embedding_model", data.get("embedding_model_name")
                    )
                    data["vector_dimension"] = retrieval.get("vector_dimension", 384)
                    data["retrieval_top_k"] = retrieval.get("top_k", 5)
                if "scraper" in raw_yaml:
                    scraper = raw_yaml["scraper"]
                    data["scraper_rate_limit_seconds"] = scraper.get("rate_limit_seconds", 1.5)
                    data["scraper_timeout_seconds"] = scraper.get("timeout_seconds", 30.0)
                    data["scraper_max_retries"] = scraper.get("max_retries", 3)
        return cls(**data)


settings = Settings.load_from_yaml()
