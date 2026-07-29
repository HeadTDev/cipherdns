import json
import os

def get_base_dir():
    # Return the directory of the project root (assuming this file is in src/core)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_profiles():
    profiles_path = os.path.join(get_base_dir(), 'data', 'profiles.json')
    with open(profiles_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_settings():
    settings_path = os.path.join(get_base_dir(), 'data', 'settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"auto_switch": False, "network_memory": {}}

def save_settings(settings):
    # Ensure data dir exists
    data_dir = os.path.join(get_base_dir(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    settings_path = os.path.join(data_dir, 'settings.json')
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass
