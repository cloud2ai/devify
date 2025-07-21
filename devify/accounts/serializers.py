from rest_framework import serializers


class WeChatLoginSerializer(serializers.Serializer):
    """
    Serializer for handling WeChat login.

    Attributes:
        code (CharField): A required field that stores the WeChat login code.
                          The maximum length of this field is 128 characters.
    """
    code = serializers.CharField(required=True, max_length=128)
