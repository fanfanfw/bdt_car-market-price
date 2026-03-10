from django.db import migrations, models


def populate_display_values(apps, schema_editor):
    ConditionOption = apps.get_model('main', 'ConditionOption')
    for option in ConditionOption.objects.all().iterator():
        if not option.display_value:
            ConditionOption.objects.filter(id=option.id).update(display_value=option.label)


def clear_display_values(apps, schema_editor):
    ConditionOption = apps.get_model('main', 'ConditionOption')
    ConditionOption.objects.all().update(display_value='')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_add_option_code_to_condition_option'),
    ]

    operations = [
        migrations.AddField(
            model_name='conditionoption',
            name='display_value',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional display text for integrations/UI. Falls back to label when empty.',
                max_length=150,
            ),
        ),
        migrations.RunPython(populate_display_values, clear_display_values),
    ]
