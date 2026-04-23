from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count, Prefetch

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.user_bootstrap import UserBootstrapService

User = get_user_model()


def _safe_int(value, default, min_value=1, max_value=100):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min(parsed, max_value), min_value)


def _paginated_payload(items, total, page, page_size):
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": items,
    }


def _display_name(user):
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}".strip()
    if user.first_name:
        return user.first_name.strip()
    try:
        profile = user.profile
    except Exception:
        profile = None
    if profile and profile.nickname:
        return profile.nickname
    return user.username


def _group_payload(group):
    return {
        "id": group.pk,
        "name": group.name,
        "user_count": getattr(group, "user_count", None),
        "permission_count": getattr(group, "permission_count", None),
    }


def _user_payload(user):
    if user is None:
        return None

    try:
        profile = user.profile
    except Exception:
        profile = None

    language = profile.language if profile else "zh-CN"
    timezone = profile.timezone if profile else "Asia/Shanghai"

    ordered_groups = getattr(user, "ordered_groups", None)
    if ordered_groups is None:
        ordered_groups = user.groups.all().order_by("name")

    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "display_name": _display_name(user),
        "is_staff": bool(user.is_staff),
        "is_active": bool(user.is_active),
        "date_joined": (
            user.date_joined.isoformat() if user.date_joined else None
        ),
        "language": language,
        "timezone": timezone,
        "groups": [_group_payload(group) for group in ordered_groups],
    }


class ManagementUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        page = _safe_int(request.query_params.get("page"), default=1)
        page_size = _safe_int(
            request.query_params.get("page_size"),
            default=20,
        )
        groups_prefetch = Prefetch(
            "groups",
            queryset=Group.objects.order_by("name"),
            to_attr="ordered_groups",
        )
        qs = (
            User.objects.select_related("profile")
            .prefetch_related(groups_prefetch)
            .order_by("id")
        )
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = [_user_payload(user) for user in qs[start:end]]
        return Response(_paginated_payload(items, total, page, page_size))

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        is_staff = bool(request.data.get("is_staff", False))
        is_active = request.data.get("is_active", True)
        language = (request.data.get("language") or "").strip() or "zh-CN"
        timezone = (
            request.data.get("timezone") or ""
        ).strip() or "Asia/Shanghai"
        group_ids = request.data.get("group_ids") or []

        if not username:
            return Response(
                {
                    "detail": "Username is required.",
                    "code": "username_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {
                    "detail": "Password is required.",
                    "code": "password_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {
                    "detail": "A user with that username already exists.",
                    "code": "username_taken",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if email and User.objects.filter(email=email).exists():
            return Response(
                {
                    "detail": "A user with that email already exists.",
                    "code": "email_taken",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email or "",
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            if is_staff:
                user.is_staff = True
            user.is_active = bool(is_active)
            user.save(update_fields=["is_staff", "is_active"])

            UserBootstrapService.bootstrap_user(
                user,
                language=language,
                timezone_str=timezone,
                scene=None,
                email_config=(
                    UserBootstrapService.build_auto_assign_email_config()
                ),
                prompt_description="User prompt configuration",
                email_description="User email configuration",
                email_alias=username,
            )

            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)

        user.refresh_from_db()
        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class ManagementGroupListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        page = _safe_int(request.query_params.get("page"), default=1)
        page_size = _safe_int(
            request.query_params.get("page_size"),
            default=20,
        )
        qs = (
            Group.objects.annotate(
                user_count=Count("user", distinct=True),
                permission_count=Count("permissions", distinct=True),
            )
            .order_by("name")
        )
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = [_group_payload(group) for group in qs[start:end]]
        return Response(_paginated_payload(items, total, page, page_size))

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response(
                {"detail": "Group name is required.", "code": "name_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Group.objects.filter(name=name).exists():
            return Response(
                {
                    "detail": "A group with that name already exists.",
                    "code": "name_taken",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        group = Group.objects.create(name=name)
        return Response(_group_payload(group), status=status.HTTP_201_CREATED)
