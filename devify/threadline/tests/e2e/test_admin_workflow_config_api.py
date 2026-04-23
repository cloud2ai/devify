import uuid

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from agentcore_metering.adapters.django.models import LLMConfig
from agentcore_notifier.adapters.django.models import NotificationChannel
from threadline.models import ThreadlineWorkflowConfig


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username=f"admin-{uuid.uuid4().hex[:8]}",
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        password="adminpass",
    )


@pytest.fixture
def staff_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def non_staff_user(db):
    return User.objects.create_user(
        username=f"user-{uuid.uuid4().hex[:8]}",
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        password="userpass",
    )


@pytest.fixture
def non_staff_client(non_staff_user):
    client = APIClient()
    client.force_authenticate(user=non_staff_user)
    return client


@pytest.mark.django_db
class TestThreadlineWorkflowConfigAPIView:
    def test_get_requires_admin(self, api_client):
        response = api_client.get("/api/v1/admin/threadline/config/")
        assert response.status_code in (401, 403)

    def test_get_forbidden_for_non_staff(self, non_staff_client):
        response = non_staff_client.get("/api/v1/admin/threadline/config/")
        assert response.status_code == 403

    def test_get_returns_singleton_config(self, staff_client):
        response = staff_client.get("/api/v1/admin/threadline/config/")
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["workflow_key"] == "threadline"
        assert body["task_config"] == {}
        assert "image_llm_config_uuid" in body
        assert "text_llm_config_uuid" in body

    def test_put_updates_bindings(self, staff_client):
        image_llm = LLMConfig.objects.create(
            scope=LLMConfig.Scope.GLOBAL,
            user=None,
            model_type=LLMConfig.MODEL_TYPE_LLM,
            provider="openai",
            config={"model": "gpt-4o-mini"},
            is_active=True,
        )
        text_llm = LLMConfig.objects.create(
            scope=LLMConfig.Scope.GLOBAL,
            user=None,
            model_type=LLMConfig.MODEL_TYPE_LLM,
            provider="openai",
            config={"model": "gpt-4.1-mini"},
            is_active=True,
        )
        channel = NotificationChannel.objects.create(
            channel_type=NotificationChannel.TYPE_WEBHOOK,
            name="Default webhook",
            is_active=True,
            is_default=True,
            config={"provider_type": "feishu", "url": "https://example.com"},
        )

        response = staff_client.put(
            "/api/v1/admin/threadline/config/",
            {
                "image_llm_config_uuid": str(image_llm.uuid),
                "text_llm_config_uuid": str(text_llm.uuid),
                "notification_channel_uuid": str(channel.uuid),
                "task_config": {"timeout_minutes": 30},
                "is_active": True,
            },
            format="json",
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["image_llm_config_uuid"] == str(image_llm.uuid)
        assert body["text_llm_config_uuid"] == str(text_llm.uuid)
        assert body["llm_config_uuid"] == str(text_llm.uuid)
        assert body["notification_channel_uuid"] == str(channel.uuid)
        assert body["task_config"] == {"timeout_minutes": 30}

        config = ThreadlineWorkflowConfig.objects.get(
            workflow_key="threadline"
        )
        assert config.image_llm_config_uuid == image_llm.uuid
        assert config.text_llm_config_uuid == text_llm.uuid
        assert config.llm_config_uuid == text_llm.uuid
        assert config.notification_channel_uuid == channel.uuid
        assert config.task_config == {"timeout_minutes": 30}

    def test_put_legacy_llm_uuid_sets_both_bindings(self, staff_client):
        llm = LLMConfig.objects.create(
            scope=LLMConfig.Scope.GLOBAL,
            user=None,
            model_type=LLMConfig.MODEL_TYPE_LLM,
            provider="openai",
            config={"model": "gpt-4o-mini"},
            is_active=True,
        )

        response = staff_client.put(
            "/api/v1/admin/threadline/config/",
            {"llm_config_uuid": str(llm.uuid)},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["image_llm_config_uuid"] == str(llm.uuid)
        assert body["text_llm_config_uuid"] == str(llm.uuid)
        assert body["llm_config_uuid"] == str(llm.uuid)

    def test_put_rejects_unknown_llm_config(self, staff_client):
        response = staff_client.put(
            "/api/v1/admin/threadline/config/",
            {"llm_config_uuid": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        assert response.status_code == 400
        assert "LLM config not found" in str(response.data)

    def test_put_accepts_image_model_without_capability_gate(
        self, staff_client
    ):
        text_only_llm = LLMConfig.objects.create(
            scope=LLMConfig.Scope.GLOBAL,
            user=None,
            model_type=LLMConfig.MODEL_TYPE_LLM,
            provider="openai",
            config={"model": "gpt-4-mini"},
            is_active=True,
        )

        response = staff_client.put(
            "/api/v1/admin/threadline/config/",
            {"image_llm_config_uuid": str(text_only_llm.uuid)},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["image_llm_config_uuid"] == str(text_only_llm.uuid)

    def test_put_rejects_non_feishu_notification_channel(self, staff_client):
        wechat_channel = NotificationChannel.objects.create(
            channel_type=NotificationChannel.TYPE_WEBHOOK,
            name="WeChat webhook",
            is_active=True,
            is_default=False,
            config={
                "provider_type": "wechat",
                "url": "https://example.com",
            },
        )

        response = staff_client.put(
            "/api/v1/admin/threadline/config/",
            {"notification_channel_uuid": str(wechat_channel.uuid)},
            format="json",
        )

        assert response.status_code == 400
        assert "feishu webhook channel" in str(response.data).lower()
