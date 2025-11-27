"""
Multi-language prompt configuration manager for Threadline

This module manages YAML-based prompt templates for different
languages and scenes. It provides dynamic language detection and
fallback mechanisms for international users.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

from django.conf import settings
import yaml

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
        """
        Load scene-specific prompts from prompts/{scene}.yaml

        Note: Scene prompts are cached but language-specific rendering
        happens at runtime, so language changes take effect immediately.
        """
        if scene in self.scene_prompts_cache:
            logger.debug(
                f"Using cached scene prompts for scene: {scene}"
            )
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
        All prompts are now unified in common section
        Priority: scene common prompts > default common prompts
        Runtime replacement of {language} variable with language display name
        """
        merged = {}

        # Get language display name for {language} variable
        lang_display = self._get_language_display_name(language)
        logger.info(
            f"Prompt language config: code={language}, "
            f"display_name={lang_display}"
        )

        # Prepare shared snippets with language variable
        # Currently only {language} variable is used in prompts
        # The 'shared' section is kept for backward compatibility but is empty
        shared_snippets_all = self.default_prompts.get('shared', {})

        # Get shared snippets for default language (fallback to empty dict)
        default_shared_lang = (
            settings.DEFAULT_LANGUAGE
            if settings.DEFAULT_LANGUAGE in shared_snippets_all
            else (list(shared_snippets_all.keys())[0]
                  if shared_snippets_all
                  else settings.DEFAULT_LANGUAGE)
        )
        shared_snippets = shared_snippets_all.get(
            default_shared_lang, {}
        ).copy()

        # Add language variable for prompt rendering
        shared_snippets['language'] = lang_display

        logger.info(
            f"Using language for prompts: {lang_display} "
            f"(code={language})"
        )

        # Load default common prompts
        default_common_prompts = self.default_prompts.get('common', {})
        for key, value in default_common_prompts.items():
            if isinstance(value, str):
                rendered = self._render_prompt(value, shared_snippets)
                merged[key] = rendered
                # Log first 100 chars of prompt to show language usage
                if key in ['summary_prompt', 'metadata_prompt',
                           'email_content_prompt']:
                    preview = rendered[:100].replace('\n', ' ')
                    logger.info(
                        f"Rendered {key} preview (first 100 chars): "
                        f"{preview}..."
                    )
            else:
                merged[key] = value

        # Override with scene-specific prompts if available
        if scene_prompts:
            scene_common_prompts = scene_prompts.get('common', {})
            for key, value in scene_common_prompts.items():
                if isinstance(value, str):
                    rendered = self._render_prompt(value, shared_snippets)
                    merged[key] = rendered
                    if key in ['summary_prompt', 'metadata_prompt',
                               'email_content_prompt']:
                        preview = rendered[:100].replace('\n', ' ')
                        logger.info(
                            f"Scene-specific {key} preview: {preview}..."
                        )
                else:
                    merged[key] = value

        return merged

    def get_language_config(self, language: str) -> Dict[str, Any]:
        """
        Get language configuration for display purposes.

        Args:
            language: Language code (e.g., 'zh-CN', 'en-US', 'es')

        Returns:
            dict: Language configuration with name, native_name, english_name

        Raises:
            KeyError: If language not found
        """
        lang_config = self._find_language_config(language)
        if not lang_config:
            raise KeyError(f"Language '{language}' not found")

        return {
            'name': lang_config.get('name'),
            'native_name': lang_config.get('native_name')
        }

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
        logger.info(
            f"Loading prompt config: scene={scene}, "
            f"input_language={language}, normalized_language={lang}"
        )

        scene_prompts = self._load_scene_prompts(scene)

        merged_prompts = self._merge_prompts(scene_prompts, lang)

        if not merged_prompts:
            raise KeyError(
                f"No prompts found for scene '{scene}' "
                f"and language '{lang}'"
            )

        logger.info(
            f"Prompt config loaded successfully: "
            f"scene={scene}, language={lang}, "
            f"has_summary_prompt={'summary_prompt' in merged_prompts}, "
            f"has_metadata_prompt={'metadata_prompt' in merged_prompts}, "
            f"has_email_content_prompt={'email_content_prompt' in merged_prompts}"
        )

        return merged_prompts

    def _find_language_config(self, language: str) -> Optional[Dict[str, Any]]:
        """
        Find language configuration by code, supporting partial matches.

        Args:
            language: Language code (e.g., 'zh-CN', 'zh', 'en-US', 'en')

        Returns:
            dict: Language config dict or None if not found
        """
        if not language:
            logger.warning("_find_language_config: empty language input")
            return None

        languages = self.languages_config.get('languages', [])
        language_lower = language.lower().strip()
        available_codes = [
            lang.get('code') for lang in languages if lang.get('code')
        ]

        logger.debug(
            f"_find_language_config: input={language}, "
            f"available_codes={available_codes}"
        )

        # First try exact match
        for lang in languages:
            if lang.get('code') == language:
                logger.debug(
                    f"_find_language_config: exact match found: "
                    f"{lang.get('code')} -> {lang.get('name')}"
                )
                return lang

        # Then try prefix match (e.g., 'zh' matches 'zh-CN')
        for lang in languages:
            code = lang.get('code', '').lower()
            if code and (code.startswith(language_lower[:2]) or
                         language_lower.startswith(code[:2])):
                logger.debug(
                    f"_find_language_config: prefix match found: "
                    f"{language} -> {lang.get('code')} ({lang.get('name')})"
                )
                return lang

        logger.warning(
            f"_find_language_config: no match found for language={language}, "
            f"available={available_codes}"
        )
        return None

    def _normalize_language(self, language: str) -> str:
        """
        Normalize language code to full format.

        Examples: 'en' -> 'en-US', 'zh' -> 'zh-CN'

        Returns:
            str: Full language code or default if not found
        """
        if not language:
            logger.warning(
                f"_normalize_language: empty input, "
                f"using default={settings.DEFAULT_LANGUAGE}"
            )
            return settings.DEFAULT_LANGUAGE

        lang_config = self._find_language_config(language)
        if lang_config:
            normalized = lang_config.get('code', settings.DEFAULT_LANGUAGE)
            logger.debug(
                f"_normalize_language: {language} -> {normalized}"
            )
            return normalized

        logger.warning(
            f"_normalize_language: no config found for {language}, "
            f"using default={settings.DEFAULT_LANGUAGE}"
        )
        return settings.DEFAULT_LANGUAGE

    def _get_language_display_name(self, language: str) -> str:
        """
        Get language name for LLM prompts.

        Args:
            language: Language code (e.g., 'zh-CN', 'en-US', 'es')

        Returns:
            str: Language name from config or original code if not found
        """
        lang_config = self._find_language_config(language)
        if lang_config:
            return lang_config.get('name', language)
        return language


    def generate_user_config(
        self,
        language: str,
        scene: str
    ) -> Dict[str, Any]:
        """
        Generate user configuration based on language and scene

        Note: New version stores language and scene, not full prompts.
        Prompts are loaded dynamically at runtime.
        """
        lang = self._normalize_language(language)
        config = {
            'language': lang,
            'scene': scene
        }
        return config

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """
        Get available languages with display names.

        Returns:
            dict: Dictionary mapping language codes to their display info
        """
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

    def load_prompt_config(self, user) -> Dict[str, Any]:
        """
        Load complete prompt configuration for a user, ready for processing.

        This method handles:
        - Loading user's scene preference from Settings
        - Loading user's language preference from Settings
        - Backward compatibility with legacy prompt_config (full prompts)
        - Dynamic generation of prompt_config if needed
        - Fallback to defaults if user settings are missing

        Args:
            user: Django User instance

        Returns:
            dict: Complete prompt_config with all prompts ready to use

        Raises:
            Exception: If even default config cannot be generated
        """
        from threadline.models import Settings

        # Check if user has legacy prompt_config (contains full prompts)
        try:
            prompt_config_raw = Settings.get_user_prompt_config(user)

            # Detect legacy format (contains prompt fields)
            legacy_prompt_fields = [
                'summary_prompt',
                'metadata_prompt',
                'email_content_prompt'
            ]
            has_full_prompts = any(
                key in prompt_config_raw
                for key in legacy_prompt_fields
            )

            if has_full_prompts:
                # Legacy format: return as-is
                # User has custom prompts, prioritize them over dynamic
                # generation
                custom_prompts = [
                    k for k in legacy_prompt_fields
                    if k in prompt_config_raw
                ]
                logger.info(
                    f"Using legacy prompt_config for user {user.id} "
                    f"(custom prompts found: {custom_prompts}). "
                    f"Language field (if present) will be ignored."
                )
                if 'language' in prompt_config_raw:
                    logger.warning(
                        f"User {user.id} has both legacy prompts and "
                        f"language field. Legacy prompts take priority. "
                        f"To use dynamic language-based prompts, remove "
                        f"legacy prompt fields from prompt_config."
                    )
                return prompt_config_raw

            # New format: extract scene and language
            scene = prompt_config_raw.get('scene', settings.DEFAULT_SCENE)
            language = prompt_config_raw.get(
                'language', settings.DEFAULT_LANGUAGE
            )
            logger.info(
                f"Loaded prompt_config from Settings for user {user.id}: "
                f"scene={scene}, language={language}, "
                f"raw_config={prompt_config_raw}"
            )

        except ValueError:
            # No prompt_config found, use defaults
            scene = settings.DEFAULT_SCENE
            language = settings.DEFAULT_LANGUAGE
            logger.info(
                f"No prompt_config found for user {user.id}, "
                f"using defaults: scene={scene}, language={language}"
            )

        # Generate complete prompt_config dynamically
        return self.get_prompt_config(scene, language)
