# Conditional cleanup of old models - safe for fresh installs

from django.db import migrations, models


def safe_cleanup_old_tables(apps, schema_editor):
    """Safely cleanup old tables if they exist"""
    with schema_editor.connection.cursor() as cursor:
        # List of tables to check and remove
        tables_to_remove = [
            'configuration_history',
            'layer1_configurations',
            'layer2_conditions',
            'pricing_configurations'
        ]

        for table_name in tables_to_remove:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """, [table_name])

            table_exists = cursor.fetchone()[0]
            if table_exists:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                print(f"✓ Dropped table: {table_name}")
            else:
                print(f"✓ Table not found (OK): {table_name}")


def reverse_safe_cleanup(apps, schema_editor):
    """Reverse operation - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_add_layer2_cap'),
    ]

    operations = [
        migrations.RunPython(
            safe_cleanup_old_tables,
            reverse_safe_cleanup
        ),
        # Add reduction_percentage field to Category
        migrations.AddField(
            model_name='category',
            name='reduction_percentage',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Reduction percentage for this category (0-100%)', max_digits=5),
        ),
        # Fix ConditionOption unique constraint
        migrations.AlterUniqueTogether(
            name='conditionoption',
            unique_together={('category', 'label')},
        ),
    ]