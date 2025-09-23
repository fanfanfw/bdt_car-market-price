# Generated manually for phone verification tracking enhancement

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_add_otp_code_to_otpsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='verifiedphone',
            name='first_verified_at',
            field=models.DateTimeField(auto_now_add=True, help_text='First time verified (never changes)', default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='verifiedphone',
            name='last_reverified_at',
            field=models.DateTimeField(blank=True, help_text='Last time re-verified', null=True),
        ),
        migrations.AddField(
            model_name='verifiedphone',
            name='reverification_count',
            field=models.PositiveIntegerField(default=0, help_text='Number of times re-verified'),
        ),
        migrations.AlterField(
            model_name='verifiedphone',
            name='verified_at',
            field=models.DateTimeField(auto_now_add=True, help_text='Current verification expiry reference'),
        ),
        migrations.AlterField(
            model_name='verifiedphone',
            name='access_count',
            field=models.PositiveIntegerField(default=1, help_text='Number of times used for calculation'),
        ),
        migrations.AlterField(
            model_name='verifiedphone',
            name='last_accessed',
            field=models.DateTimeField(auto_now=True, help_text='Last time accessed for calculation'),
        ),
    ]