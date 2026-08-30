"""Hierarchical settings storage backed by QSettings and JSON."""

import json
import os
from typing import Any, Dict
from PyQt6.QtCore import QSettings
from ..config import DEFAULT_SETTINGS


class SettingsStorage:
    def __init__(self, organization: str = "Candle", application: str = "Candle"):
        self.m_settings = QSettings(organization, application)
        self.m_cache: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.m_cache:
            return self.m_cache[key]
        if default is not None:
            return default
        return DEFAULT_SETTINGS.get(key, None)

    def set(self, key: str, value: Any) -> None:
        self.m_cache[key] = value
        self.m_settings.setValue(key, value)

    def load(self) -> None:
        for key, def_val in DEFAULT_SETTINGS.items():
            if self.m_settings.contains(key):
                val = self.m_settings.value(key)
                if isinstance(def_val, bool):
                    if isinstance(val, str):
                        self.m_cache[key] = (val.lower() == 'true')
                    else:
                        self.m_cache[key] = bool(val)
                elif isinstance(def_val, int):
                    try:
                        self.m_cache[key] = int(val)
                    except (ValueError, TypeError):
                        self.m_cache[key] = def_val
                elif isinstance(def_val, float):
                    try:
                        self.m_cache[key] = float(val)
                    except (ValueError, TypeError):
                        self.m_cache[key] = def_val
                elif isinstance(def_val, list):
                    if isinstance(val, list):
                        self.m_cache[key] = val
                    elif isinstance(val, str):
                        try:
                            self.m_cache[key] = json.loads(val)
                        except Exception:
                            self.m_cache[key] = def_val
                else:
                    self.m_cache[key] = val
            else:
                self.m_cache[key] = def_val

    def sync(self) -> None:
        for key, val in self.m_cache.items():
            if isinstance(val, list):
                self.m_settings.setValue(key, json.dumps(val))
            else:
                self.m_settings.setValue(key, val)
        self.m_settings.sync()

    def exportToJson(self, filepath: str) -> bool:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.m_cache, f, indent=2)
            return True
        except Exception:
            return False

    def importFromJson(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.items():
                self.m_cache[k] = v
            self.sync()
            return True
        except Exception:
            return False
