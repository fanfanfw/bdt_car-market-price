import os
import sys
import django
import csv
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Setup Django environment using environment variable
django_settings = os.getenv('DJANGO_SETTINGS_MODULE', 'carmarket.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', django_settings)
django.setup()

from main.models import Category, BrandCategory

def populate_categories():
    """Populate categories and brand_categories from CSV file"""
    
    print("📋 Category Data Population")
    print("-" * 40)
    print(f"🔧 Django Settings: {os.getenv('DJANGO_SETTINGS_MODULE', 'carmarket.settings')}")
    print(f"🗄️ Database: {os.getenv('DB_NAME', 'default')}")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    csv_file = script_dir / 'data-category.csv'
    
    if not csv_file.exists():
        print(f"❌ Error: {csv_file} not found")
        # Try alternative path (when run from project root)
        csv_file = Path('commands/data-category.csv')
        if not csv_file.exists():
            print(f"❌ Error: data-category.csv not found in {script_dir} or commands/")
            return
    
    print(f"📄 Using CSV file: {csv_file}")
    print("🚀 Starting category population...")
    
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
    
    print(f"📊 Found {len(categories_set)} unique categories")
    print(f"📊 Found {len(brand_mappings)} brand-category mappings")
    
    # Create categories
    created_categories = 0
    for category_name in categories_set:
        category, created = Category.objects.get_or_create(name=category_name)
        if created:
            created_categories += 1
            print(f"✅ Created category: {category_name}")
    
    print(f"📥 Created {created_categories} new categories")
    
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
                print(f"✅ Created mapping: {brand} -> {category_name}")
        except Category.DoesNotExist:
            print(f"⚠️ Warning: Category '{category_name}' not found for brand '{brand}'")
    
    print(f"📥 Created {created_mappings} new brand-category mappings")
    
    # Summary
    print("\n" + "="*50)
    print("✅ CATEGORY POPULATION COMPLETED")
    print("="*50)
    print(f"📋 Categories: {created_categories} new, {len(categories_set)} total")
    print(f"🔗 Mappings: {created_mappings} new, {len(brand_mappings)} total")
    print("🎉 Population completed successfully!")

if __name__ == '__main__':
    try:
        populate_categories()
    except Exception as e:
        print(f"\n❌ Error during category population: {e}")
        sys.exit(1)