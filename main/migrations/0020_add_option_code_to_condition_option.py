from django.db import migrations, models
from django.utils.text import slugify


def _normalize_code(value: str) -> str:
    normalized = slugify((value or "").strip()).replace("-", "_")
    return normalized[:100] or "option"


def _with_suffix(base: str, suffix: int) -> str:
    suffix_part = f"_{suffix}"
    return f"{base[:100 - len(suffix_part)]}{suffix_part}"


def populate_option_codes(apps, schema_editor):
    ConditionOption = apps.get_model('main', 'ConditionOption')

    for option in ConditionOption.objects.all().order_by('category_id', 'id'):
        base_code = _normalize_code(option.option_code or option.label)
        candidate = base_code
        suffix = 2

        while ConditionOption.objects.filter(
            category_id=option.category_id,
            option_code=candidate,
        ).exclude(id=option.id).exists():
            candidate = _with_suffix(base_code, suffix)
            suffix += 1

        ConditionOption.objects.filter(id=option.id).update(option_code=candidate)


def clear_option_codes(apps, schema_editor):
    ConditionOption = apps.get_model('main', 'ConditionOption')
    ConditionOption.objects.all().update(option_code='')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_add_phone_tracking_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='conditionoption',
            name='option_code',
            field=models.CharField(
                blank=True,
                help_text='Stable API code for integration (example: excellent, poor, no_accident)',
                max_length=100,
            ),
        ),
        migrations.RunPython(populate_option_codes, clear_option_codes),
        migrations.AlterUniqueTogether(
            name='conditionoption',
            unique_together={('category', 'label'), ('category', 'option_code')},
        ),
    ]
