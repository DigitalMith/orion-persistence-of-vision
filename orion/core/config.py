"""Configuration loading and management for Orion."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class ConfigLoader:
    """Load and manage YAML configuration files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            config_path: Path to the YAML config file. If None, uses default.
        """
        if config_path is None:
            config_path = self._find_default_config()
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def _find_default_config(self) -> str:
        """Find the default config file location."""
        # Check common locations
        possible_paths = [
            "config/orion.yaml",
            "config/default.yaml",
            "orion.yaml",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        # Return default path even if it doesn't exist yet
        return "config/orion.yaml"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}"
            )
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        return self.config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to config."""
        # Allow overriding specific config values via env vars
        # Format: ORION_<SECTION>_<KEY>=value
        prefix = "ORION_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split('_')
                self._set_nested_value(self.config, parts, value)
    
    def _set_nested_value(self, d: Dict, keys: list, value: Any):
        """Set a nested dictionary value using a list of keys."""
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Dot-separated path to the config value (e.g., 'memory.database')
            default: Default value if key not found
            
        Returns:
            The configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Dot-separated path to the config value
            value: Value to set
        """
        keys = key.split('.')
        self._set_nested_value(self.config, keys, value)
    
    def save(self, path: Optional[str] = None):
        """
        Save configuration to YAML file.
        
        Args:
            path: Path to save to. If None, uses original path.
        """
        save_path = Path(path) if path else self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
