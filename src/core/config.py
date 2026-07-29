import json
import os
import sys

def get_bundle_dir() -> str:
    """Returns the bundle directory (sys._MEIPASS when frozen by PyInstaller, or project root)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_user_data_dir() -> str:
    """Returns a writable user data directory in %APPDATA%/CipherDNS or local data dir."""
    appdata = os.environ.get('APPDATA')
    if appdata:
        user_dir = os.path.join(appdata, 'CipherDNS')
    else:
        user_dir = os.path.join(get_bundle_dir(), 'data')
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_resource_path(relative_path: str) -> str:
    """Returns the absolute path to bundled resource files (assets, profiles, etc.)."""
    return os.path.join(get_bundle_dir(), relative_path)

def load_profiles() -> list[dict]:
    """Loads DNS provider profiles from data/profiles.json."""
    profiles_path = get_resource_path(os.path.join('data', 'profiles.json'))
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading profiles: {e}")
    return []

def load_settings() -> dict:
    """Loads user settings from %APPDATA%/CipherDNS/settings.json or local fallback."""
    settings_path = os.path.join(get_user_data_dir(), 'settings.json')
    if not os.path.exists(settings_path):
        # Fallback check for local data/settings.json
        local_path = get_resource_path(os.path.join('data', 'settings.json'))
        if os.path.exists(local_path):
            settings_path = local_path

    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading settings: {e}")
    return {"auto_switch": False, "network_memory": {}}

def save_settings(settings: dict) -> bool:
    """Saves user settings to %APPDATA%/CipherDNS/settings.json."""
    user_dir = get_user_data_dir()
    settings_path = os.path.join(user_dir, 'settings.json')
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Config] Error saving settings: {e}")
        return False
