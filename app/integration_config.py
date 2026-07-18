import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import IntegrationSetting


def get_config_value(key: str, default: str = "") -> str:
    try:
        with SessionLocal() as session:
            setting = session.get(IntegrationSetting, key)
            if setting and setting.setting_value is not None:
                return setting.setting_value
    except Exception:
        pass
    return os.getenv(key, default)


def get_config_values(keys: list[str]) -> dict[str, str]:
    values = {key: os.getenv(key, "") for key in keys}
    try:
        with SessionLocal() as session:
            rows = session.execute(
                select(IntegrationSetting).where(IntegrationSetting.setting_key.in_(keys))
            ).scalars()
            for row in rows:
                values[row.setting_key] = row.setting_value or ""
    except Exception:
        pass
    return values


def save_config_values(values: dict[str, str]) -> bool:
    try:
        with SessionLocal() as session:
            for key, value in values.items():
                setting = session.get(IntegrationSetting, key)
                if setting:
                    setting.setting_value = value
                else:
                    session.add(IntegrationSetting(setting_key=key, setting_value=value))
            session.commit()
        return True
    except Exception:
        return False
