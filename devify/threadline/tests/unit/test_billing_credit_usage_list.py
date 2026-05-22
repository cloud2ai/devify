from types import SimpleNamespace

from billing.viewsets import _get_credit_usage_display_title


def test_credit_usage_display_title_prefers_canonical_summary_title():
    canonical_email = SimpleNamespace(
        summary_title='Canonical summary title',
        subject='Canonical subject',
    )
    child_email = SimpleNamespace(
        merged_into_id=10,
        merged_into=canonical_email,
        summary_title='',
        subject='',
    )

    result = _get_credit_usage_display_title(child_email)

    assert result == 'Canonical summary title'


def test_credit_usage_display_title_falls_back_to_subject():
    email = SimpleNamespace(
        merged_into_id=None,
        merged_into=None,
        summary_title='',
        subject='Raw subject',
    )

    result = _get_credit_usage_display_title(email)

    assert result == 'Raw subject'
