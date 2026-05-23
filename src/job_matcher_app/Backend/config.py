from __future__ import annotations

from functools import lru_cache

try:
	from pydantic_settings import BaseSettings
	from pydantic import Field
except Exception:
	from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # sentence-transformers model chạy local
    EMBEDDING_MODEL: str = "alvperez/skill-sim-model"
    # Matching config
    DEFAULT_TOP_K: int = 5
    DEFAULT_THRESHOLD: float = 0.65   # cosine similarity threshold

    
    pg_host: str = Field("192.168.100.221", env="PG_HOST")
    pg_port: int = Field(5432, env="PG_PORT")
    pg_database: str = Field("job_db_2", env="PG_DATABASE")
    pg_user: str = Field("airflow", env="PG_USER")
    pg_password: str = Field("airflow", env="PG_PASSWORD")

    model_path: str = Field("models", env="MODEL_PATH")

    # MinIO configuration via environment variables (recommended)
    minio_endpoint: str = Field("192.168.100.221:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field("ROOTUSER", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("1234567890", env="MINIO_SECRET_KEY")
    minio_bucket: str = Field("models", env="MINIO_BUCKET")
    minio_secure: bool = Field(False, env="MINIO_SECURE")

    # JWT Authentication
    secret_key: str = Field("09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(1440, env="ACCESS_TOKEN_EXPIRE_MINUTES") # 24 hours




    @property
    def database_url(self) -> str:
        user = self.pg_user
        password = self.pg_password
        host = self.pg_host
        port = self.pg_port
        database = self.pg_database
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    @property
    def async_database_url(self) -> str:
        user = self.pg_user
        password = self.pg_password
        host = self.pg_host
        port = self.pg_port
        database = self.pg_database
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
	return Settings()
