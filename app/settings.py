import os
from dataclasses import dataclass

from sqlalchemy import URL


@dataclass(frozen=True)
class Settings:
    project_name: str
    app_name: str
    app_env: str
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_username: str
    mysql_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            project_name=os.environ.get("PROJECT_NAME", "eastman-adms-server"),
            app_name=os.environ.get("APP_NAME", "eastman-adms-server"),
            app_env=os.environ.get("APP_ENV", "production"),
            mysql_host=os.environ["MYSQL_HOST"],
            mysql_port=int(os.environ.get("MYSQL_PORT", "3306")),
            mysql_database=os.environ["MYSQL_DATABASE"],
            mysql_username=os.environ["MYSQL_USERNAME"],
            mysql_password=os.environ["MYSQL_PASSWORD"],
        )

    def database_url(self) -> URL:
        # Build the SQLAlchemy URL from .env fields so operators only maintain one source of truth.
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_username,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
        )
