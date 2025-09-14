# Generated manually for field rename

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_remove_api_consumed_tables'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE otp_sessions RENAME COLUMN otp_code TO verification_id;",
            reverse_sql="ALTER TABLE otp_sessions RENAME COLUMN verification_id TO otp_code;"
        ),
    ]