"""Machine profiles management."""

import os
import json
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QStandardPaths


class ProfileManager:
    def __init__(self):
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.m_profilesDir = os.path.join(app_data, "Candle", "profiles")
        os.makedirs(self.m_profilesDir, exist_ok=True)
        self.m_currentProfile: str = "Default"

    def profiles(self) -> List[str]:
        profs = ["Default"]
        if os.path.exists(self.m_profilesDir):
            for fname in os.listdir(self.m_profilesDir):
                if fname.endswith(".json"):
                    name = os.path.splitext(fname)[0]
                    if name not in profs:
                        profs.append(name)
        return profs

    def saveProfile(self, name: str, settings: Dict[str, Any]) -> bool:
        try:
            path = os.path.join(self.m_profilesDir, f"{name}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception:
            return False

    def loadProfile(self, name: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.m_profilesDir, f"{name}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def deleteProfile(self, name: str) -> bool:
        if name == "Default":
            return False
        path = os.path.join(self.m_profilesDir, f"{name}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception:
                return False
        return False
