import os
import sys
import django
import csv
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carmarketprice.settings')
django.setup()

from main.models import Category, BrandCategory

def populate_categories():
    """Populate categories and brand_categories from CSV file"""
    
    csv_file = 'data-category.csv'
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return
    
    print("Starting category population...")
    
    # Track categories and brand mappings
    categories_set = set()
    brand_mappings = []
    
    # Read CSV file
    with open(csv_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            brand = row['brand'].strip()
            category = row['category'].strip()
            
            if brand and category:
                categories_set.add(category)
                brand_mappings.append((brand, category))
    
    print(f"Found {len(categories_set)} unique categories")
    print(f"Found {len(brand_mappings)} brand-category mappings")
    
    # Create categories
    created_categories = 0
    for category_name in categories_set:
        category, created = Category.objects.get_or_create(name=category_name)
        if created:
            created_categories += 1
            print(f"Created category: {category_name}")
    
    print(f"Created {created_categories} new categories")
    
    # Create brand-category mappings
    created_mappings = 0
    for brand, category_name in brand_mappings:
        try:
            category = Category.objects.get(name=category_name)
            mapping, created = BrandCategory.objects.get_or_create(
                brand=brand,
                category=category
            )
            if created:
                created_mappings += 1
                print(f"Created mapping: {brand} -> {category_name}")
        except Category.DoesNotExist:
            print(f"Warning: Category '{category_name}' not found for brand '{brand}'")
    
    print(f"Created {created_mappings} new brand-category mappings")
    print("Category population completed!")

if __name__ == '__main__':
    populate_categories()