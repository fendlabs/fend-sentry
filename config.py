"""
Configuration management for Fend Sentry

Handles loading and saving configuration files for SSH connections,
Django log paths, and AI API keys.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigError(Exception):
    """Configuration related errors"""
    pass

class Config:
    """Manages Fend Sentry configuration"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            config_dir: Custom config directory (defaults to ~/.fend-sentry)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / '.fend-sentry'
        
        self.config_file = self.config_dir / 'config.yaml'
        self.ensure_config_dir()
        
        # Load environment variables
        load_dotenv()
        
        # Also try to load from project .env file
        project_env = Path.cwd() / '.env'
        if project_env.exists():
            load_dotenv(project_env)
    
    def ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
    
    def save(self, config_data: Dict[str, Any]):
        """Save configuration to file
        
        Args:
            config_data: Configuration dictionary
            
        Raises:
            ConfigError: If saving fails
        """
        try:
            # Validate required fields
            self._validate_config(config_data)
            
            # Save to YAML file with secure permissions
            with open(self.config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            # Set secure file permissions (readable only by owner)
            os.chmod(self.config_file, 0o600)
            
        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigError: If config file doesn't exist or is invalid
        """
        if not self.config_file.exists():
            raise ConfigError(
                "Configuration file not found. Run 'fend-sentry init' to setup."
            )
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Validate loaded config
            self._validate_config(config_data)
            
            return config_data
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid configuration file format: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def exists(self) -> bool:
        """Check if configuration file exists"""
        return self.config_file.exists()
    
    def delete(self):
        """Delete configuration file"""
        if self.config_file.exists():
            self.config_file.unlink()
    
    def _validate_config(self, config_data: Dict[str, Any]):
        """Validate configuration structure
        
        Args:
            config_data: Configuration to validate
            
        Raises:
            ConfigError: If configuration is invalid
        """
        if not isinstance(config_data, dict):
            raise ConfigError("Configuration must be a dictionary")
        
        # Required top-level keys
        required_keys = ['server', 'app', 'ai']
        for key in required_keys:
            if key not in config_data:
                raise ConfigError(f"Missing required configuration section: {key}")
        
        # Validate server section
        server = config_data['server']
        required_server_keys = ['host', 'port', 'username']
        for key in required_server_keys:
            if key not in server:
                raise ConfigError(f"Missing required server configuration: {key}")
        
        # Must have either private_key_path or password
        if not server.get('private_key_path') and not server.get('password'):
            raise ConfigError("Must specify either private_key_path or password for SSH")
        
        # Validate SSH key path exists if specified (and not using password)
        if server.get('private_key_path') and not server.get('password'):
            key_path = Path(server['private_key_path']).expanduser()
            if not key_path.exists():
                # Don't fail if this is just the default key path - user might use password
                if server['private_key_path'] != str(Path.home() / '.ssh' / 'id_rsa'):
                    raise ConfigError(f"SSH private key not found: {server['private_key_path']}")
                # For default key path, just warn and switch to password auth requirement
                server['private_key_path'] = None
        
        # Validate app section
        app = config_data['app']
        if 'name' not in app or 'log_path' not in app:
            raise ConfigError("App configuration must include 'name' and 'log_path'")
        
        # Validate AI section
        ai = config_data['ai']
        if 'gemini_api_key' not in ai or not ai['gemini_api_key']:
            raise ConfigError("Gemini API key is required")
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration section"""
        config_data = self.load()
        return config_data['server']
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get app configuration section"""
        config_data = self.load()
        return config_data['app']
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration section"""
        config_data = self.load()
        return config_data['ai']
    
    def update_section(self, section: str, updates: Dict[str, Any]):
        """Update a specific configuration section
        
        Args:
            section: Section name ('server', 'app', or 'ai')  
            updates: Dictionary of updates to apply
            
        Raises:
            ConfigError: If update fails
        """
        config_data = self.load()
        
        if section not in config_data:
            raise ConfigError(f"Unknown configuration section: {section}")
        
        config_data[section].update(updates)
        self.save(config_data)
    
    def get_env_defaults(self) -> Dict[str, Any]:
        """Get default configuration from environment variables"""
        return {
            'server': {
                'host': os.getenv('SENTRY_SERVER_HOST', 'localhost'),
                'port': int(os.getenv('SENTRY_SERVER_PORT', '22')),
                'username': os.getenv('SENTRY_SERVER_USER', os.getenv('USER', 'ubuntu')),
                'private_key_path': os.getenv('SENTRY_SSH_KEY', str(Path.home() / '.ssh' / 'id_rsa')),
                'password': os.getenv('SENTRY_SSH_PASSWORD')  # Only use if no key
            },
            'app': {
                'name': os.getenv('SENTRY_APP_NAME', 'Django Application'),
                'log_path': os.getenv('SENTRY_LOG_PATH', '/var/log/django/django.log'),
                'environment': os.getenv('SENTRY_APP_ENV', 'production')
            },
            'ai': {
                'gemini_api_key': os.getenv('GEMINI_API_KEY', '')
            },
            'monitoring': {
                'check_interval': int(os.getenv('SENTRY_CHECK_INTERVAL', '300')),  # 5 minutes default
                'max_log_lines': int(os.getenv('SENTRY_MAX_LOG_LINES', '1000'))
            },
            'alerts': {
                'email': os.getenv('SENTRY_ALERT_EMAIL', ''),
                'webhook_url': os.getenv('SENTRY_ALERT_WEBHOOK', ''),
                'enabled': os.getenv('SENTRY_ALERTS_ENABLED', 'false').lower() == 'true'
            }
        }
    
    def load_with_env_fallback(self) -> Dict[str, Any]:
        """Load config with environment variable fallbacks"""
        try:
            # Try to load from config file first
            if self.config_file.exists():
                config_data = self.load()
            else:
                config_data = {}
            
            # Get environment defaults
            env_defaults = self.get_env_defaults()
            
            # Merge config file with environment defaults
            merged_config = self._deep_merge(env_defaults, config_data)
            
            return merged_config
            
        except ConfigError:
            # If config file doesn't exist or is invalid, use environment defaults
            return self.get_env_defaults()
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result