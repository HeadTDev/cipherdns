import json
import os

def get_base_dir() -> str:
    """Returns the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_profiles() -> list[dict]:
    """Loads DNS provider profiles from data/profiles.json."""
    profiles_path = os.path.join(get_base_dir(), 'data', 'profiles.json')
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading profiles: {e}")
    return []

def load_settings() -> dict:
    """Loads user settings from data/settings.json."""
    settings_path = os.path.join(get_base_dir(), 'data', 'settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading settings: {e}")
    return {"auto_switch": False, "network_memory": {}}

def save_settings(settings: dict) -> bool:
    """Saves user settings to data/settings.json."""
    data_dir = os.path.join(get_base_dir(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    settings_path = os.path.join(data_dir, 'settings.json')
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Config] Error saving settings: {e}")
        return False
