# Conditional field rename

from django.db import migrations


def rename_otp_code_to_verification_id(apps, schema_editor):
    """Safely rename otp_code to verification_id if column exists"""
    with schema_editor.connection.cursor() as cursor:
        # Check if otp_code column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'otp_sessions'
                AND column_name = 'otp_code'
            );
        """)
        column_exists = cursor.fetchone()[0]

        if column_exists:
            cursor.execute("ALTER TABLE otp_sessions RENAME COLUMN otp_code TO verification_id;")
            print("✓ Renamed otp_code to verification_id")
        else:
            print("✓ Column otp_code not found (OK)")


def reverse_rename_field(apps, schema_editor):
    """Reverse operation"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE otp_sessions RENAME COLUMN verification_id TO otp_code;")


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_remove_api_consumed_tables'),
    ]

    operations = [
        migrations.RunPython(
            rename_otp_code_to_verification_id,
            reverse_rename_field
        ),
    ]