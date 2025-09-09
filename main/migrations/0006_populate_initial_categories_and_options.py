# Populate initial categories and options for new pricing system

from django.db import migrations


def populate_categories_and_options(apps, schema_editor):
    """Create initial categories and options based on screenshot data"""
    VehicleConditionCategory = apps.get_model('main', 'VehicleConditionCategory')
    ConditionOption = apps.get_model('main', 'ConditionOption')
    MileageConfiguration = apps.get_model('main', 'MileageConfiguration')
    
    # Create default mileage configuration
    MileageConfiguration.objects.create(
        threshold_percent=10.0,
        reduction_percent=2.0,
        max_reduction_cap=15.0
    )
    
    # Define categories and their options based on screenshot
    categories_data = [
        {
            'category_key': 'exterior_condition',
            'display_name': 'Exterior Condition',
            'order': 1,
            'options': [
                ('Excellent', 0.00),
                ('Good', 3.00),
                ('Fair', 6.00),
                ('Poor', 10.00),
            ]
        },
        {
            'category_key': 'interior_condition',
            'display_name': 'Interior Condition',
            'order': 2,
            'options': [
                ('Excellent', 0.00),
                ('Good', 3.00),
                ('Fair', 6.00),
                ('Poor', 10.00),
            ]
        },
        {
            'category_key': 'mechanical_condition',
            'display_name': 'Mechanical Condition',
            'order': 3,
            'options': [
                ('Excellent', 0.00),
                ('Good', 7.00),
                ('Fair', 13.00),
                ('Poor', 20.00),
            ]
        },
        {
            'category_key': 'accident_history',
            'display_name': 'Accident History',
            'order': 4,
            'options': [
                ('None', 0.00),
                ('Minor', 8.00),
                ('Major', 15.00),
            ]
        },
        {
            'category_key': 'service_history',
            'display_name': 'Service History',
            'order': 5,
            'options': [
                ('Full', 0.00),
                ('Partial', 3.00),
                ('None', 5.00),
            ]
        },
        {
            'category_key': 'number_of_owners',
            'display_name': 'Number of Owners',
            'order': 6,
            'options': [
                ('1 Owner', 0.00),
                ('2 Owners', 2.00),
                ('3+ Owners', 5.00),
            ]
        },
        {
            'category_key': 'tires_brakes',
            'display_name': 'Tires & Brakes',
            'order': 7,
            'options': [
                ('New', 0.00),
                ('Fair', 2.50),
                ('Needs Replacement', 5.00),
            ]
        },
        {
            'category_key': 'modifications',
            'display_name': 'Modifications',
            'order': 8,
            'options': [
                ('None', 0.00),
                ('Minor', 2.50),
                ('Major', 5.00),
            ]
        },
        {
            'category_key': 'market_demand',
            'display_name': 'Market Demand',
            'order': 9,
            'options': [
                ('High', 0.00),
                ('Average', 5.00),
                ('Low', 10.00),
            ]
        },
        {
            'category_key': 'brand_category',
            'display_name': 'Brand Category',
            'order': 10,
            'options': [
                ('Japanese Car', 0.00),
                ('Local Car', 8.00),
                ('Continental', 10.00),
                ('Super Car', 30.00),
            ]
        },
        {
            'category_key': 'price_tier',
            'display_name': 'Price Tier',
            'order': 11,
            'options': [
                ('>RM50k', 0.00),
                ('RM20k-50k', 6.00),
                ('<RM20k', 12.00),
            ]
        },
    ]
    
    # Create categories and options
    for category_data in categories_data:
        category = VehicleConditionCategory.objects.create(
            category_key=category_data['category_key'],
            display_name=category_data['display_name'],
            order=category_data['order'],
            is_active=True
        )
        
        # Create options for this category
        for order, (label, percentage) in enumerate(category_data['options']):
            ConditionOption.objects.create(
                category=category,
                label=label,
                reduction_percentage=percentage,
                order=order
            )


def reverse_populate_categories_and_options(apps, schema_editor):
    """Remove all categories and options"""
    VehicleConditionCategory = apps.get_model('main', 'VehicleConditionCategory')
    ConditionOption = apps.get_model('main', 'ConditionOption')
    MileageConfiguration = apps.get_model('main', 'MileageConfiguration')
    
    ConditionOption.objects.all().delete()
    VehicleConditionCategory.objects.all().delete()
    MileageConfiguration.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_remove_old_pricing_and_create_new'),
    ]

    operations = [
        migrations.RunPython(
            populate_categories_and_options,
            reverse_populate_categories_and_options
        ),
    ]