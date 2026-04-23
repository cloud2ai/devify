from django.db import migrations, models


def copy_legacy_llm_binding(apps, schema_editor):
    ThreadlineWorkflowConfig = apps.get_model(
        "threadline",
        "ThreadlineWorkflowConfig",
    )
    for config in ThreadlineWorkflowConfig.objects.all():
        if config.llm_config_uuid and not config.image_llm_config_uuid:
            config.image_llm_config_uuid = config.llm_config_uuid
        if config.llm_config_uuid and not config.text_llm_config_uuid:
            config.text_llm_config_uuid = config.llm_config_uuid
        if not config.llm_config_uuid:
            config.llm_config_uuid = (
                config.text_llm_config_uuid or config.image_llm_config_uuid
            )
        config.save(
            update_fields=[
                "image_llm_config_uuid",
                "text_llm_config_uuid",
                "llm_config_uuid",
                "updated_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("threadline", "0027_threadlineworkflowconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="threadlineworkflowconfig",
            name="image_llm_config_uuid",
            field=models.UUIDField(
                blank=True,
                help_text="Bound multimodal model UUID for image understanding",
                null=True,
                verbose_name="Image LLM Config UUID",
            ),
        ),
        migrations.AddField(
            model_name="threadlineworkflowconfig",
            name="text_llm_config_uuid",
            field=models.UUIDField(
                blank=True,
                help_text="Bound text model UUID for content processing",
                null=True,
                verbose_name="Text LLM Config UUID",
            ),
        ),
        migrations.RunPython(
            copy_legacy_llm_binding,
            migrations.RunPython.noop,
        ),
    ]
