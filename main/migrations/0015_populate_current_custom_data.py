# Load current custom data as default for new installations

from django.db import migrations
from django.core.management import call_command

def load_current_data(apps, schema_editor):
    """Load current custom data from fixtures"""
    call_command('loaddata', 'main/fixtures/current_data.json')

def reverse_current_data(apps, schema_editor):
    """Remove custom data"""
    Category = apps.get_model('main', 'Category')
    BrandCategory = apps.get_model('main', 'BrandCategory')
    VehicleConditionCategory = apps.get_model('main', 'VehicleConditionCategory')
    ConditionOption = apps.get_model('main', 'ConditionOption')

    # Delete in reverse order to avoid foreign key issues
    ConditionOption.objects.all().delete()
    BrandCategory.objects.all().delete()
    VehicleConditionCategory.objects.all().delete()
    Category.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_rename_otp_code_to_verification_id'),
    ]

    operations = [
        migrations.RunPython(load_current_data, reverse_current_data),
    ]