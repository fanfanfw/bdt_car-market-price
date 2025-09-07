#!/usr/bin/env python3
"""
Fill Cars Category ID Script
=============================

Script untuk mengisi field category_id yang masih NULL
di database cars_unified berdasarkan matching dengan brand_categories.

Usage:
    python fill_cars_category_id.py
"""

import os
import django
import sys
from datetime import datetime
import logging
from tqdm import tqdm

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carmarketprice.settings')
django.setup()

from django.db import connection
from main.models import Category, BrandCategory, CarUnified

logger = logging.getLogger(__name__)


def find_category_id(brand):
    """
    Mencari category_id berdasarkan brand
    """
    category_id = None
    
    if not brand:
        return None
    
    try:
        # Cari brand di BrandCategory table
        brand_category = BrandCategory.objects.filter(
            brand__iexact=brand.strip()
        ).first()
        
        if brand_category:
            category_id = brand_category.category_id
                
    except Exception as e:
        logger.error(f"Error dalam pencarian category_id: {e}")
        return None
    
    return category_id


def fill_category_id_for_source(source):
    """
    Mengisi category_id yang NULL untuk source tertentu
    """
    updated_count = 0
    failed_count = 0
    failed_records = []
    
    try:
        logger.info(f"🔍 Mencari record dengan category_id NULL untuk source {source}...")
        
        # Ambil semua record yang category_id nya NULL
        null_records = CarUnified.objects.filter(
            source=source,
            category_id__isnull=True,
            brand__isnull=False
        ).values('id', 'listing_url', 'brand')
        
        logger.info(f"📊 Ditemukan {len(null_records)} record dengan category_id NULL untuk {source}")
        
        if len(null_records) == 0:
            logger.info(f"✅ Tidak ada record yang perlu diupdate untuk {source}")
            return updated_count, failed_count, failed_records
        
        # Progress bar untuk pemrosesan record
        with tqdm(total=len(null_records), desc=f"🔄 {source}", 
                  unit="record", ncols=100, colour='green') as pbar:
            for record in null_records:
                record_id = record['id']
                listing_url = record['listing_url']
                brand = record['brand']
                
                # Cari category_id
                category_id = find_category_id(brand)
                
                if category_id:
                    # Update category_id
                    CarUnified.objects.filter(id=record_id).update(
                        category_id=category_id
                    )
                    updated_count += 1
                    pbar.set_postfix({"✅ Updated": updated_count, "❌ Failed": failed_count})
                else:
                    failed_count += 1
                    failed_records.append({
                        'id': record_id,
                        'listing_url': listing_url,
                        'brand': brand,
                        'source': source
                    })
                    pbar.set_postfix({"✅ Updated": updated_count, "❌ Failed": failed_count})
                
                pbar.update(1)
                
        logger.info(f"✅ {source}: Selesai memproses {len(null_records)} record")
        logger.info(f"   📈 Berhasil update: {updated_count}")
        logger.info(f"   ❌ Gagal match: {failed_count}")
        
        return updated_count, failed_count, failed_records
        
    except Exception as e:
        logger.error(f"❌ Error saat memproses {source}: {str(e)}")
        raise


def fill_all_category_id():
    """
    Mengisi category_id untuk semua source (carlistmy dan mudahmy)
    """
    logger.info("🚀 Memulai proses pengisian category_id untuk record yang NULL...")
    
    start_time = datetime.now()
    total_updated = 0
    total_failed = 0
    all_failed_records = []
    
    try:
        # Check if brand_categories table has data
        brand_categories_count = BrandCategory.objects.count()
        if brand_categories_count == 0:
            logger.error("❌ No brand_categories data found in database!")
            logger.error("💡 Please run: python populate_categories.py")
            return {
                'status': 'error',
                'error': 'Brand categories data not found. Run populate_categories.py first.',
                'total_updated': 0,
                'total_failed': 0
            }
        
        logger.info(f"📖 Found {brand_categories_count} brand_categories records")
        
        # Process CarlistMY
        logger.info("=" * 60)
        logger.info("📋 Memproses source CarlistMY...")
        updated_carlistmy, failed_carlistmy, failed_records_carlistmy = fill_category_id_for_source('carlistmy')
        total_updated += updated_carlistmy
        total_failed += failed_carlistmy
        all_failed_records.extend(failed_records_carlistmy)
        
        # Process MudahMY
        logger.info("=" * 60)
        logger.info("📋 Memproses source MudahMY...")
        updated_mudahmy, failed_mudahmy, failed_records_mudahmy = fill_category_id_for_source('mudahmy')
        total_updated += updated_mudahmy
        total_failed += failed_mudahmy
        all_failed_records.extend(failed_records_mudahmy)
        
        # Summary report
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("📊 SUMMARY REPORT")
        logger.info("=" * 60)
        logger.info(f"⏱️  Waktu eksekusi: {duration}")
        logger.info(f"📈 Total record berhasil diupdate: {total_updated}")
        logger.info(f"❌ Total record gagal match: {total_failed}")
        logger.info("")
        logger.info("📋 Detail per source:")
        logger.info(f"   CarlistMY - Updated: {updated_carlistmy}, Failed: {failed_carlistmy}")
        logger.info(f"   MudahMY   - Updated: {updated_mudahmy}, Failed: {failed_mudahmy}")
        
        # Simpan record yang gagal ke CSV untuk analisis
        failed_filename = None
        if all_failed_records:
            try:
                import pandas as pd
                failed_df = pd.DataFrame(all_failed_records)
                failed_filename = f"failed_category_id_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                failed_df.to_csv(failed_filename, index=False)
                logger.info(f"💾 Record yang gagal match disimpan di: {failed_filename}")
            except ImportError:
                logger.warning("⚠️  pandas tidak tersedia, tidak dapat menyimpan failed records ke CSV")
        
        logger.info("=" * 60)
        if total_updated > 0:
            logger.info("🎉 Proses pengisian category_id BERHASIL!")
        else:
            logger.info("ℹ️  Tidak ada record yang perlu diupdate")
        logger.info("=" * 60)
        
        return {
            'status': 'success',
            'total_updated': total_updated,
            'total_failed': total_failed,
            'duration': str(duration),
            'carlistmy': {'updated': updated_carlistmy, 'failed': failed_carlistmy},
            'mudahmy': {'updated': updated_mudahmy, 'failed': failed_mudahmy},
            'failed_records_file': failed_filename if all_failed_records else None
        }
        
    except Exception as e:
        logger.error(f"❌ Error dalam proses pengisian category_id: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'total_updated': total_updated,
            'total_failed': total_failed
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    result = fill_all_category_id()
    print("\n" + "=" * 60)
    print("HASIL AKHIR:")
    print("=" * 60)
    for key, value in result.items():
        print(f"{key}: {value}")