"""
Multi-language prompt configuration manager for Threadline

This module manages YAML-based prompt templates for different
languages and scenes. It provides dynamic language detection and
fallback mechanisms for international users.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class PromptConfigManager:
    """
    Manager for multi-language prompt configuration

    Loads prompt templates from YAML files and provides
    language/scene-specific configurations with automatic
    fallback mechanisms.
    """

    def __init__(self):
        config_dir = settings.THREADLINE_CONFIG_PATH
        self.config_path = os.path.join(config_dir, 'prompts.yaml')
        self.yaml_config = self._load_yaml_config()

        if not self.yaml_config:
            raise FileNotFoundError(
                f"Required YAML config file not found or invalid: "
                f"{self.config_path}"
            )

    def _load_yaml_config(self) -> Optional[Dict[str, Any]]:
        """Load YAML configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(
                    f"Loaded YAML config from {self.config_path}"
                )
                return config
        except FileNotFoundError:
            logger.warning(
                f"YAML config file not found: {self.config_path}"
            )
            return None
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading YAML config: {e}")
            return None

    def get_language_config(self, language: str) -> Dict[str, Any]:
        """Get language configuration for display purposes"""
        self._ensure_config_exists('language_config')
        lang_config = self.yaml_config['language_config'].get(language)
        if not lang_config:
            raise KeyError(f"Language '{language}' not found")
        return lang_config

    def get_scene_config(self, scene: str, language: str) -> \
            Dict[str, Any]:
        """Get scene configuration for specific language"""
        lang = self._normalize_language(language)
        self._ensure_config_exists('scene_config')

        scene_config = self.yaml_config['scene_config'].get(scene)
        if not scene_config or lang not in scene_config:
            raise KeyError(
                f"Scene '{scene}' or language '{lang}' not found"
            )

        return {
            'name': scene_config[lang],
            'description': scene_config.get('description', {})
                          .get(lang, '')
        }

    def get_prompt_config(self, scene: str, language: str) -> \
            Dict[str, Any]:
        """Get prompt configuration for specific scene and language"""
        lang = self._normalize_language(language)
        self._ensure_config_exists('scene_prompt_config')

        scene_prompts = self.yaml_config['scene_prompt_config']\
                       .get(scene)
        if not scene_prompts or lang not in scene_prompts:
            raise KeyError(
                f"Scene '{scene}' or language '{lang}' not found"
            )

        return scene_prompts[lang]

    def _normalize_language(self, language: str) -> str:
        """Normalize language code with fallback mechanism"""
        if self._language_exists(language):
            return language
        if language.startswith('zh') and self._language_exists('zh-CN'):
            return 'zh-CN'
        return settings.DEFAULT_LANGUAGE

    def _language_exists(self, language: str) -> bool:
        """Check if language exists in configuration"""
        return (self.yaml_config.get('language_config', {})
                .get(language) is not None)

    def _ensure_config_exists(self, config_key: str) -> None:
        """Ensure configuration section exists"""
        if config_key not in self.yaml_config:
            raise KeyError(
                f"{config_key} not found in YAML configuration"
            )

    def generate_user_config(self, language: str, scene: str) -> \
            Dict[str, Any]:
        """Generate user configuration based on language and scene"""
        lang = self._normalize_language(language)
        config = {'language': lang, 'scene': scene}
        config.update(self.get_prompt_config(scene, lang))
        return config

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Get available languages with display names"""
        self._ensure_config_exists('language_config')
        return self.yaml_config['language_config']

    def get_available_scenes(self) -> list:
        """Get list of available scenes"""
        self._ensure_config_exists('scene_prompt_config')
        return sorted(self.yaml_config['scene_prompt_config'].keys())
