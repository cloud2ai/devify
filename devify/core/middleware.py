"""
Custom middleware for the core application.
"""
from django.conf import settings


class LanguageCodeMappingMiddleware:
    """
    Middleware to map browser language codes to Django language codes.

    Uses LANGUAGE_CODE_MAPPING from settings to dynamically map
    browser language codes (e.g., zh-CN) to Django language codes
    (e.g., zh-hans). This allows browsers to send various language
    code formats while Django uses standardized language codes.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Get mapping from settings, default to empty dict if not defined
        self.language_mapping = getattr(
            settings,
            'LANGUAGE_CODE_MAPPING',
            {}
        )

    def __call__(self, request):
        # Get language from Accept-Language header
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')

        # Parse Accept-Language header and map if needed
        # Format: "zh-CN,zh;q=0.9,en;q=0.8"
        if accept_language and self.language_mapping:
            # Split by comma and get the first language
            parts = accept_language.split(',')
            first_part = parts[0].strip()
            first_lang = first_part.lower()
            # Remove quality value if present (e.g., "zh-cn;q=0.9" -> "zh-cn")
            first_lang = first_lang.split(';')[0].strip()

            # Map to Django language code if needed
            mapped_lang = self.language_mapping.get(first_lang)
            if mapped_lang:
                # Replace the first language code in Accept-Language header
                # Keep the rest of the header intact
                quality_part = first_part.split(';', 1)
                if len(quality_part) > 1:
                    # Keep quality value if present
                    new_first_part = f"{mapped_lang};{quality_part[1]}"
                else:
                    new_first_part = mapped_lang

                # Reconstruct Accept-Language header
                remaining_parts = ','.join(parts[1:]) if len(parts) > 1 else ''
                new_accept_language = (
                    f"{new_first_part},{remaining_parts}".rstrip(',')
                )
                request.META['HTTP_ACCEPT_LANGUAGE'] = new_accept_language

        response = self.get_response(request)
        return response
