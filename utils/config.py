import json
import os
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model_name": "gpt-3.5-turbo",
    "ffmpeg_path": os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")
}

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), CONFIG_FILE)
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Merge with default to ensure all keys exist
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()

    def save_config(self, new_config):
        self.config.update(new_config)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config({key: value})
