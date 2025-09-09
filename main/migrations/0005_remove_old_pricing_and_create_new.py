# Generated manually for pricing config refactor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_populate_initial_pricing_config'),
    ]

    operations = [
        # Drop all old pricing configuration tables
        migrations.RunSQL("DROP TABLE IF EXISTS configuration_history CASCADE;"),
        migrations.RunSQL("DROP TABLE IF EXISTS condition_options CASCADE;"),  # Old condition_options
        migrations.RunSQL("DROP TABLE IF EXISTS layer2_conditions CASCADE;"),
        migrations.RunSQL("DROP TABLE IF EXISTS layer1_configurations CASCADE;"),
        migrations.RunSQL("DROP TABLE IF EXISTS pricing_configurations CASCADE;"),
        
        # Create new simplified models
        migrations.CreateModel(
            name='MileageConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('threshold_percent', models.DecimalField(decimal_places=2, default=10.0, help_text='Mileage threshold percentage (e.g., 10 = every 10% excess)', max_digits=5)),
                ('reduction_percent', models.DecimalField(decimal_places=2, default=2.0, help_text='Reduction percentage per threshold (e.g., 2 = 2% reduction)', max_digits=5)),
                ('max_reduction_cap', models.DecimalField(decimal_places=2, default=15.0, help_text='Maximum reduction percentage cap', max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'mileage_configurations',
            },
        ),
        migrations.CreateModel(
            name='VehicleConditionCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_key', models.CharField(choices=[('exterior_condition', 'Exterior Condition'), ('interior_condition', 'Interior Condition'), ('mechanical_condition', 'Mechanical Condition'), ('accident_history', 'Accident History'), ('service_history', 'Service History'), ('number_of_owners', 'Number of Owners'), ('tires_brakes', 'Tires & Brakes'), ('modifications', 'Modifications'), ('market_demand', 'Market Demand'), ('brand_category', 'Brand Category'), ('price_tier', 'Price Tier')], max_length=50, unique=True)),
                ('display_name', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'vehicle_condition_categories',
                'ordering': ['order', 'display_name'],
            },
        ),
        migrations.CreateModel(
            name='ConditionOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(help_text="Display label (e.g., 'Excellent', 'Good')", max_length=100)),
                ('reduction_percentage', models.DecimalField(decimal_places=2, help_text='Reduction percentage for this option', max_digits=5)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='main.vehicleconditioncategory')),
            ],
            options={
                'db_table': 'condition_options',
                'ordering': ['category__order', 'order'],
            },
        ),
        migrations.AddConstraint(
            model_name='conditionoption',
            constraint=models.UniqueConstraint(fields=('category', 'label'), name='main_conditionoption_category_id_label_c6f9e8bb_uniq'),
        ),
    ]