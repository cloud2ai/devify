from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmailWorkflowUsage',
        ),
        migrations.CreateModel(
            name='EmailWorkflowUsage',
            fields=[
                (
                    'credits_transaction',
                    models.OneToOneField(
                        help_text='One-to-one mapping with credits transaction',
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name='workflow_usage',
                        serialize=False,
                        to='billing.emailcreditstransaction'
                    )
                ),
                (
                    'llm_call_count',
                    models.IntegerField(default=0)
                ),
                (
                    'llm_success_count',
                    models.IntegerField(default=0)
                ),
                (
                    'llm_total_input_tokens',
                    models.IntegerField(default=0)
                ),
                (
                    'llm_total_output_tokens',
                    models.IntegerField(default=0)
                ),
                (
                    'llm_total_tokens',
                    models.IntegerField(default=0)
                ),
                (
                    'ocr_call_count',
                    models.IntegerField(default=0)
                ),
                (
                    'ocr_success_count',
                    models.IntegerField(default=0)
                ),
                (
                    'ocr_total_images',
                    models.IntegerField(default=0)
                ),
                (
                    'llm_calls_detail',
                    models.JSONField(
                        default=list,
                        help_text='List of all LLM calls with tokens, success status, errors'
                    )
                ),
                (
                    'ocr_calls_detail',
                    models.JSONField(
                        default=list,
                        help_text='List of all OCR calls with filenames, success status, errors'
                    )
                ),
                (
                    'estimated_cost_usd',
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        help_text='Estimated cost based on pricing config',
                        max_digits=10,
                        null=True
                    )
                ),
                (
                    'created_at',
                    models.DateTimeField(auto_now_add=True)
                ),
            ],
            options={
                'verbose_name': 'Email Workflow Usage',
                'verbose_name_plural': 'Email Workflow Usages',
                'db_table': 'billing_email_workflow_usage',
                'ordering': ['-created_at'],
            },
        ),
    ]
