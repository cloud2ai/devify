"""
Factory Boy factories for Threadline models

This module provides factories for creating test data for all
Threadline models.
"""

import factory
import uuid
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from factory.django import DjangoModelFactory

from threadline.models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    Issue,
    EmailTodo,
    ThreadlineShareLink
)


class UserFactory(DjangoModelFactory):
    """
    Factory for creating User instances
    """

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'testuser{n}')
    email = factory.LazyAttribute(
        lambda obj: f'{obj.username}@example.com'
    )
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override _create to use get_or_create to avoid duplicate users
        """
        username = kwargs.get('username')
        if username:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=kwargs
            )
            return user
        return super()._create(model_class, *args, **kwargs)


class SettingsFactory(DjangoModelFactory):
    """
    Factory for creating Settings instances
    """

    class Meta:
        model = Settings

    user = factory.SubFactory(UserFactory)
    key = factory.Sequence(lambda n: f'test_setting_{n}')
    value = factory.LazyFunction(
        lambda: {'theme': 'light', 'language': 'en'}
    )
    description = factory.Faker('sentence', nb_words=6)
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override _create to use get_or_create to avoid duplicate settings
        """
        user = kwargs.get('user')
        key = kwargs.get('key')
        if user and key:
            setting, created = Settings.objects.get_or_create(
                user=user,
                key=key,
                defaults=kwargs
            )
            return setting
        return super()._create(model_class, *args, **kwargs)


class EmailTaskFactory(DjangoModelFactory):
    """
    Factory for creating EmailTask instances
    """

    class Meta:
        model = EmailTask

    status = 'running'
    task_type = 'IMAP_EMAIL_FETCH'


class EmailMessageFactory(DjangoModelFactory):
    """
    Factory for creating EmailMessage instances
    """

    class Meta:
        model = EmailMessage

    user = factory.SubFactory(UserFactory)
    message_id = factory.LazyFunction(
        lambda: f"{uuid.uuid4().hex}@example.com"
    )
    subject = factory.Faker('sentence', nb_words=6)
    sender = factory.Faker('email')
    recipients = factory.Faker('email')
    received_at = factory.Faker('date_time_this_year')
    html_content = factory.Faker('text', max_nb_chars=500)
    text_content = factory.Faker('text', max_nb_chars=500)
    status = 'fetched'


class EmailAttachmentFactory(DjangoModelFactory):
    """
    Factory for creating EmailAttachment instances
    """

    class Meta:
        model = EmailAttachment

    user = factory.SubFactory(UserFactory)
    email_message = factory.SubFactory(EmailMessageFactory)
    filename = factory.Faker('file_name', extension='pdf')
    safe_filename = factory.LazyAttribute(lambda obj: obj.filename)
    content_type = 'application/pdf'
    # 1KB to 10MB
    file_size = factory.Faker('random_int', min=1024, max=10485760)
    file_path = factory.LazyAttribute(
        lambda obj: f'/uploads/{obj.safe_filename}'
    )
    is_image = False


class IssueFactory(DjangoModelFactory):
    """
    Factory for creating Issue instances
    """

    class Meta:
        model = Issue

    user = factory.SubFactory(UserFactory)
    email_message = factory.SubFactory(EmailMessageFactory)
    title = factory.Faker('sentence', nb_words=8)
    description = factory.Faker('text', max_nb_chars=1000)
    priority = factory.Iterator(
        ['low', 'medium', 'high', 'critical', 'urgent']
    )
    engine = factory.Iterator(
        ['jira', 'email', 'slack', 'github', 'gitlab']
    )
    external_id = factory.Sequence(lambda n: f'ISSUE-{n}')
    issue_url = factory.LazyAttribute(
        lambda obj: (
            f'https://{obj.engine}.example.com/'
            f'issues/{obj.external_id}'
        )
    )
    metadata = factory.LazyFunction(
        lambda: {'project': 'TEST', 'assignee': 'testuser'}
    )


# Specialized factories for specific test scenarios

class SettingsWithJsonValueFactory(SettingsFactory):
    """
    Factory for creating Settings with complex JSON values
    """
    key = 'complex_config'
    value = factory.LazyFunction(lambda: {
        'theme': 'dark',
        'notifications': {
            'email': True,
            'push': False,
            'sms': True
        },
        'preferences': {
            'language': 'zh-CN',
            'timezone': 'Asia/Shanghai',
            'date_format': 'YYYY-MM-DD'
        }
    })


class EmailMessageWithAttachmentsFactory(EmailMessageFactory):
    """
    Factory for creating EmailMessage with attachments
    """
    @factory.post_generation
    def attachments(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # If attachments are provided, use them
            for attachment in extracted:
                self.attachments.add(attachment)
        else:
            # Create default attachments
            EmailAttachmentFactory.create_batch(2, email_message=self)


class EmailMessageWithSummaryFactory(EmailMessageFactory):
    """
    Factory for creating EmailMessage with summary information
    """
    summary_title = factory.Faker('sentence', nb_words=5)
    summary_content = factory.Faker('text', max_nb_chars=300)
    summary_priority = factory.Iterator(['low', 'medium', 'high'])
    llm_content = factory.Faker('text', max_nb_chars=800)
    status = 'success'


class IssueWithMetadataFactory(IssueFactory):
    """
    Factory for creating Issue with complex metadata
    """
    metadata = factory.LazyFunction(lambda: {
        'project': 'THREADLINE',
        'assignee': 'testuser',
        'labels': ['bug', 'priority-high'],
        'custom_fields': {
            'environment': 'production',
            'version': '1.0.0',
            'component': 'email-processing'
        }
    })


class EmailTodoFactory(DjangoModelFactory):
    """
    Factory for creating EmailTodo instances
    """

    class Meta:
        model = EmailTodo

    user = factory.SubFactory(UserFactory)
    email_message = factory.SubFactory(EmailMessageFactory)
    content = factory.Faker('sentence', nb_words=10)
    is_completed = False
    completed_at = None
    priority = factory.Iterator(['high', 'medium', 'low', None])
    owner = factory.Faker('name')
    deadline = factory.Faker('date_time_this_month', tzinfo=None)
    location = factory.Faker('city')
    metadata = factory.LazyFunction(lambda: {})


class EmailTodoWithEmailFactory(EmailTodoFactory):
    """
    Factory for creating EmailTodo with email message
    """
    email_message = factory.SubFactory(EmailMessageFactory)


class ThreadlineShareLinkFactory(DjangoModelFactory):
    """
    Factory for creating ThreadlineShareLink instances
    """

    class Meta:
        model = ThreadlineShareLink

    email_message = factory.SubFactory(EmailMessageFactory)
    owner = factory.LazyAttribute(lambda obj: obj.email_message.user)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    password_hash = factory.LazyFunction(lambda: make_password('123456'))



class EmailTodoWithoutEmailFactory(EmailTodoFactory):
    """
    Factory for creating manually created EmailTodo (no email_message)
    """
    email_message = None
