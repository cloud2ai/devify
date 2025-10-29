"""
Multi-language prompt configuration manager for Threadline

This module manages YAML-based prompt templates for different
languages and scenes. It provides dynamic language detection and
fallback mechanisms for international users.
"""

import os
import re
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
        self.config_dir = settings.THREADLINE_CONFIG_PATH

        self.languages_config = self._load_yaml_file(
            os.path.join(self.config_dir, 'languages.yaml')
        )
        self.scenarios_config = self._load_yaml_file(
            os.path.join(self.config_dir, 'scenarios.yaml')
        )

        default_prompt_path = os.path.join(
            self.config_dir,
            self.scenarios_config.get(
                'default_prompt_file',
                'prompts/default.yaml'
            )
        )
        self.default_prompts = self._load_yaml_file(default_prompt_path)

        if not all([
            self.languages_config,
            self.scenarios_config,
            self.default_prompts
        ]):
            raise FileNotFoundError(
                f"Required configuration files not found in: "
                f"{self.config_dir}"
            )

        self.scene_prompts_cache = {}

    def _load_yaml_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded YAML config from {file_path}")
                return config
        except FileNotFoundError:
            logger.warning(f"YAML config file not found: {file_path}")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading YAML config: {e}")
            return None

    def _load_scene_prompts(
        self,
        scene: str
    ) -> Optional[Dict[str, Any]]:
        """Load scene-specific prompts from prompts/{scene}.yaml"""
        if scene in self.scene_prompts_cache:
            return self.scene_prompts_cache[scene]

        scenarios = self.scenarios_config.get('scenarios', {})
        scene_info = scenarios.get(scene)

        if not scene_info:
            logger.warning(f"Scene '{scene}' not found in scenarios.yaml")
            return None

        prompt_file = scene_info.get('prompt_file')
        if not prompt_file:
            logger.warning(
                f"No prompt_file specified for scene '{scene}'"
            )
            return None

        prompt_path = os.path.join(self.config_dir, prompt_file)
        scene_prompts = self._load_yaml_file(prompt_path)

        if scene_prompts:
            self.scene_prompts_cache[scene] = scene_prompts

        return scene_prompts

    def _render_prompt(
        self,
        prompt_text: str,
        shared_snippets: Dict[str, str]
    ) -> str:
        """
        Render prompt by replacing {var} with shared snippets
        Supports nested references
        """
        if not prompt_text or not shared_snippets:
            return prompt_text

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            original_text = prompt_text

            for key, value in shared_snippets.items():
                pattern = r'\{' + re.escape(key) + r'\}'
                prompt_text = re.sub(pattern, value, prompt_text)

            if prompt_text == original_text:
                break

            iteration += 1

        if iteration >= max_iterations:
            logger.warning(
                "Max iterations reached in prompt rendering, "
                "possible circular reference"
            )

        return prompt_text

    def _merge_prompts(
        self,
        scene_prompts: Optional[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """
        Merge scene prompts with default prompts
        Priority: scene prompts > language-specific > common prompts
        Common prompts are rendered with English shared snippets
        Language-specific prompts are rendered with their language snippets
        """
        merged = {}

        # Get language display name for {language} variable
        lang_display = self._get_language_display_name(language)

        en_shared_snippets = self.default_prompts.get('shared', {}).get(
            'en-US',
            {}
        ).copy()
        en_shared_snippets['language'] = lang_display

        common_prompts = self.default_prompts.get('common', {})
        for key, value in common_prompts.items():
            if isinstance(value, str):
                merged[key] = self._render_prompt(value, en_shared_snippets)
            else:
                merged[key] = value

        lang_shared_snippets = self.default_prompts.get('shared', {}).get(
            language,
            {}
        ).copy()
        lang_shared_snippets['language'] = lang_display

        default_lang_prompts = self.default_prompts.get(language, {})
        for key, value in default_lang_prompts.items():
            if isinstance(value, str):
                merged[key] = self._render_prompt(value, lang_shared_snippets)
            else:
                merged[key] = value

        if scene_prompts:
            scene_lang_prompts = scene_prompts.get(language, {})
            for key, value in scene_lang_prompts.items():
                if isinstance(value, str):
                    merged[key] = self._render_prompt(
                        value,
                        lang_shared_snippets
                    )
                else:
                    merged[key] = value

        return merged

    def get_language_config(self, language: str) -> Dict[str, Any]:
        """Get language configuration for display purposes"""
        languages = self.languages_config.get('languages', [])

        for lang in languages:
            if lang.get('code') == language:
                return {
                    'name': lang.get('name'),
                    'native_name': lang.get('native_name')
                }

        raise KeyError(f"Language '{language}' not found")

    def get_scene_config(
        self,
        scene: str,
        language: str
    ) -> Dict[str, Any]:
        """Get scene configuration for specific language"""
        lang = self._normalize_language(language)

        scenarios = self.scenarios_config.get('scenarios', {})
        scene_info = scenarios.get(scene)

        if not scene_info:
            raise KeyError(f"Scene '{scene}' not found")

        if lang not in scene_info:
            raise KeyError(
                f"Language '{lang}' not found for scene '{scene}'"
            )

        return {
            'name': scene_info[lang],
            'description': scene_info.get('description', {}).get(lang, '')
        }

    def get_prompt_config(
        self,
        scene: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Get prompt configuration for specific scene and language
        Loads scene prompts, merges with defaults, and renders variables
        """
        lang = self._normalize_language(language)

        scene_prompts = self._load_scene_prompts(scene)

        merged_prompts = self._merge_prompts(scene_prompts, lang)

        if not merged_prompts:
            raise KeyError(
                f"No prompts found for scene '{scene}' "
                f"and language '{lang}'"
            )

        return merged_prompts

    def _get_language_display_name(self, language: str) -> str:
        """
        Get language display name from languages.yaml

        Args:
            language: Language code (e.g., 'zh-CN', 'en-US', 'es')

        Returns:
            str: Language display name (e.g., '中文', 'English')
        """
        languages = self.languages_config.get('languages', [])

        for lang in languages:
            if lang.get('code') == language:
                return lang.get('native_name', language)

        # Fallback for common variations
        if language.startswith('zh'):
            return '中文'
        if language.startswith('en'):
            return 'English'
        if language.startswith('es'):
            return 'Español'

        return language

    def _normalize_language(self, language: str) -> str:
        """Normalize language code with fallback mechanism"""
        if self._language_exists(language):
            return language
        if language.startswith('zh') and self._language_exists('zh-CN'):
            return 'zh-CN'
        return settings.DEFAULT_LANGUAGE

    def _language_exists(self, language: str) -> bool:
        """Check if language exists in configuration"""
        languages = self.languages_config.get('languages', [])
        for lang in languages:
            if lang.get('code') == language:
                return True
        return False

    def generate_user_config(
        self,
        language: str,
        scene: str
    ) -> Dict[str, Any]:
        """Generate user configuration based on language and scene"""
        lang = self._normalize_language(language)
        config = {'language': lang, 'scene': scene}
        config.update(self.get_prompt_config(scene, lang))
        return config

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Get available languages with display names"""
        result = {}
        languages = self.languages_config.get('languages', [])

        for lang in languages:
            code = lang.get('code')
            if code:
                result[code] = {
                    'name': lang.get('name'),
                    'native_name': lang.get('native_name')
                }

        return result

    def get_available_scenes(self) -> list:
        """Get list of available scenes"""
        scenarios = self.scenarios_config.get('scenarios', {})
        return sorted(scenarios.keys())
