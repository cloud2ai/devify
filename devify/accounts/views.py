import logging

from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import Profile
from .serializers import WeChatLoginSerializer

# Base URL for WeChat API to exchange code for session info
WECHAT_BASE_URL = (
    "https://api.weixin.qq.com/sns/jscode2session"
)

# Initialize logger
logger = logging.getLogger(__name__)


class WeChatAppLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=WeChatLoginSerializer)
    def post(self, request):
        # Get the code from the request data
        code = request.data.get("code")
        if not code:
            # Log missing code error and return response
            logger.warning("Code is required but not provided")
            return Response(
                {"error": _("Code is required")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FIXME(Ray): Add default value for mock
        # Get WeChat API credentials from settings
        app_id = getattr(settings, "WECHAT_APP_ID", 1234567890)
        app_secret = getattr(settings, "WECHAT_APP_SECRET", "secret")
        wechat_url = (
            f"{WECHAT_BASE_URL}?appid={app_id}&secret={app_secret}"
            f"&js_code={code}&grant_type=authorization_code"
        )

        try:
            # FIXME(Ray): Implement this method according to real project
            # Send request to WeChat to get session info
            # response = requests.get(wechat_url, timeout=5)
            # response.raise_for_status()  # Raise error for HTTP errors
            # wechat_data = response.json()

            # TODO(Ray): Remove this line after implementing the above code
            wechat_data = {"openid": "1234567890"}
            logger.info("WeChat response received: %s", wechat_data)
        except requests.RequestException as e:
            # Log network or HTTP error and return response
            logger.error("Network error with WeChat API: %s", e)
            return Response(
                {"error": "Failed to connect to WeChat API", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except ValueError:
            # Log JSON decoding error and return response
            logger.error("Invalid JSON received from WeChat API")
            return Response(
                {"error": "Invalid response from WeChat API"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Validate if the openid is in the response data
        if "openid" not in wechat_data:
            # Log missing openid error and return response
            logger.warning("Failed to get openid in WeChat response: %s",
                           wechat_data)
            return Response(
                {"error": "Failed to get openid", "details": wechat_data},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract openid and session_key from WeChat response
        openid = wechat_data["openid"]
        session_key = wechat_data.get("session_key")

        # Get or create a user associated with the openid
        user, created = User.objects.get_or_create(
            username=f"wx_{openid}",
            defaults={"first_name": "WeChat User"}
        )
        if created:
            logger.info("New user created with openid: %s", openid)

        # Get or create profile, associate it with the openid
        profile, profile_created = Profile.objects.get_or_create(user=user)
        profile.openid = openid
        profile.save()
        logger.info("Profile updated with openid: %s", openid)

        # Get or create authentication token for the user
        refresh = RefreshToken.for_user(user)
        logger.info(f"Token generated for user: {user.username}: {refresh}")

        # Return the token and new user status in response
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": created
            },
            status=status.HTTP_200_OK
        )
