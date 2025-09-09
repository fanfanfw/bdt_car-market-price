# Manual migration to add layer2_max_cap field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_populate_initial_categories_and_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='mileageconfiguration',
            name='layer2_max_cap',
            field=models.DecimalField(decimal_places=2, default=70.0, help_text='Maximum reduction percentage cap for Layer 2 (Conditions)', max_digits=5),
        ),
        migrations.AlterField(
            model_name='mileageconfiguration',
            name='max_reduction_cap',
            field=models.DecimalField(decimal_places=2, default=15.0, help_text='Maximum reduction percentage cap for Layer 1 (Mileage)', max_digits=5),
        ),
    ]