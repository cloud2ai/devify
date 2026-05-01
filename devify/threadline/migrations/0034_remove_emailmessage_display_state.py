from django.db import migrations


def drop_display_state_column(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "threadline_emailmessage"
    column_name = "display_state"

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND column_name = %s
            """,
            [table_name, column_name],
        )
        (exists,) = cursor.fetchone()

        if exists:
            schema_editor.execute(
                f"ALTER TABLE `{table_name}` DROP COLUMN `{column_name}`"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("threadline", "0033_emailmessage_merge_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveIndex(
                    model_name="emailmessage",
                    name="threadline__user_id_708251_idx",
                ),
                migrations.RemoveField(
                    model_name="emailmessage",
                    name="display_state",
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    drop_display_state_column,
                    reverse_code=migrations.RunPython.noop,
                )
            ],
        )
    ]
