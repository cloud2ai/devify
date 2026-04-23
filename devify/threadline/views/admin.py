"""
Admin API for Threadline workflow bindings.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from threadline.serializers.admin import (
    ThreadlineWorkflowConfigSerializer,
    ThreadlineWorkflowConfigUpdateSerializer,
)
from threadline.services.workflow_config import (
    serialize_threadline_workflow_config,
    update_threadline_workflow_config,
)


class ThreadlineWorkflowConfigAPIView(APIView):
    """
    GET/PUT the singleton Threadline workflow config.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            ThreadlineWorkflowConfigSerializer(
                serialize_threadline_workflow_config()
            ).data
        )

    def put(self, request):
        serializer = ThreadlineWorkflowConfigUpdateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        update_threadline_workflow_config(
            llm_config_uuid=serializer.validated_data.get("llm_config_uuid"),
            image_llm_config_uuid=serializer.validated_data.get(
                "image_llm_config_uuid"
            ),
            text_llm_config_uuid=serializer.validated_data.get(
                "text_llm_config_uuid"
            ),
            notification_channel_uuid=serializer.validated_data.get(
                "notification_channel_uuid"
            ),
            task_config=serializer.validated_data.get("task_config"),
            is_active=serializer.validated_data.get("is_active"),
        )
        return Response(
            ThreadlineWorkflowConfigSerializer(
                serialize_threadline_workflow_config()
            ).data,
            status=status.HTTP_200_OK,
        )
