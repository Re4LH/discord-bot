"""
Configuration management for the Discord bot
"""

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages server-specific configuration"""
    
    def __init__(self, config_file: str = "config/servers.json"):
        self.config_file = config_file
        self.configs = {}
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Load existing configurations
        self.load_configs()
    
    def load_configs(self):
        """Load configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.configs = json.load(f)
                logger.info(f"Loaded {len(self.configs)} server configurations")
            else:
                self.configs = {}
                logger.info("No existing configuration file found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            self.configs = {}
    
    def save_configs(self):
        """Save configurations to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, indent=2, ensure_ascii=False)
            logger.debug("Configurations saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for a new guild"""
        return {
            "enabled": False,
            "channel_id": None,
            "poll_hour": 8,  # 8 AM
            "poll_minute": 0,
            "timezone": "UTC",
            "poll_options": [
                "✅ Свободен цял ден",
                "🌅 Свободен сутрин (9:00 - 12:00)",
                "☀️ Свободен следобед (12:00 - 18:00)",
                "🌙 Свободен вечер (18:00 - 23:00)",
                "🌃 Свободен късно вечер (23:00+)",
                "🤔 Не съм сигурен",
                "❌ Не съм свободен"
            ],
            "poll_history": []  # Track last poll message IDs for cleanup
        }
    
    def initialize_guild(self, guild_id: str):
        """Initialize configuration for a new guild"""
        guild_id = str(guild_id)
        if guild_id not in self.configs:
            self.configs[guild_id] = self.get_default_config()
            self.save_configs()
            logger.info(f"Initialized configuration for guild {guild_id}")
    
    def get_guild_config(self, guild_id: str) -> Dict[str, Any]:
        """Get configuration for a specific guild"""
        guild_id = str(guild_id)
        if guild_id not in self.configs:
            self.initialize_guild(guild_id)
        return self.configs.get(guild_id, self.get_default_config())
    
    def save_guild_config(self, guild_id: str, config: Dict[str, Any]):
        """Save configuration for a specific guild"""
        guild_id = str(guild_id)
        self.configs[guild_id] = config
        self.save_configs()
        logger.debug(f"Saved configuration for guild {guild_id}")
    
    def remove_guild(self, guild_id: str):
        """Remove configuration for a guild (when bot is removed)"""
        guild_id = str(guild_id)
        if guild_id in self.configs:
            del self.configs[guild_id]
            self.save_configs()
            logger.info(f"Removed configuration for guild {guild_id}")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all guild configurations"""
        return self.configs.copy()
    
    def update_guild_setting(self, guild_id: str, key: str, value: Any):
        """Update a specific setting for a guild"""
        guild_id = str(guild_id)
        config = self.get_guild_config(guild_id)
        config[key] = value
        self.save_guild_config(guild_id, config)
        logger.debug(f"Updated {key} for guild {guild_id}")
    
    def get_enabled_guilds(self) -> list:
        """Get list of guild IDs with enabled polls"""
        return [
            guild_id for guild_id, config in self.configs.items()
            if config.get('enabled', False)
        ]
