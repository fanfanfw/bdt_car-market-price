from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from .models import CarStandard, CarUnified, Category, BrandCategory

def index(request):
    context = {}
    
    # Handle form submission
    if request.method == 'POST':
        category = request.POST.get('category')
        brand = request.POST.get('brand')
        model = request.POST.get('model')
        variant = request.POST.get('variant')
        year = request.POST.get('year')
        user_mileage = request.POST.get('user_mileage')
        
        # Get condition assessment values
        condition_assessments = {
            'exterior_condition': float(request.POST.get('exterior_condition', 0)),
            'interior_condition': float(request.POST.get('interior_condition', 0)),
            'mechanical_condition': float(request.POST.get('mechanical_condition', 0)),
            'accident_history': float(request.POST.get('accident_history', 0)),
            'service_history': float(request.POST.get('service_history', 0)),
            'number_of_owners': float(request.POST.get('number_of_owners', 0)),
            'tires_brakes': float(request.POST.get('tires_brakes', 0)),
            'modifications': float(request.POST.get('modifications', 0)),
            'market_demand': float(request.POST.get('market_demand', 0)),
            'brand_category': float(request.POST.get('brand_category', 0)),
            'price_tier': float(request.POST.get('price_tier', 0))
        }
        
        if category and brand and model and variant and year:
            # Execute the car statistics query
            result = get_car_statistics(brand, model, variant, int(year), user_mileage, condition_assessments)
            if result:
                context['result'] = result
            else:
                context['no_data'] = True
    
    return render(request, 'main/index.html', context)


def get_categories(request):
    """API endpoint to get all categories"""
    try:
        categories = Category.objects.values_list('name', flat=True).order_by('name')
        return JsonResponse(list(categories), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_brands(request):
    """API endpoint to get brands filtered by category"""
    try:
        category_name = request.GET.get('category')
        
        if category_name:
            # Get brands for specific category
            brands = BrandCategory.objects.filter(
                category__name=category_name
            ).values_list('brand', flat=True).distinct().order_by('brand')
        else:
            # Get all brands if no category specified (fallback)
            brands = CarStandard.objects.values_list('brand_norm', flat=True).distinct().order_by('brand_norm')
        
        return JsonResponse(list(brands), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_models(request):
    """API endpoint to get models for selected brand"""
    try:
        brand = request.GET.get('brand')
        if not brand:
            return JsonResponse({'error': 'Brand parameter required'}, status=400)
        
        models = CarStandard.objects.filter(
            brand_norm=brand
        ).values_list('model_norm', flat=True).distinct().order_by('model_norm')
        
        return JsonResponse(list(models), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_variants(request):
    """API endpoint to get variants for selected brand and model"""
    try:
        brand = request.GET.get('brand')
        model = request.GET.get('model')
        
        if not brand or not model:
            return JsonResponse({'error': 'Brand and model parameters required'}, status=400)
        
        variants = CarStandard.objects.filter(
            brand_norm=brand,
            model_norm=model
        ).values_list('variant_norm', flat=True).distinct().order_by('variant_norm')
        
        return JsonResponse(list(variants), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_years(request):
    """API endpoint to get years for selected brand, model, and variant"""
    try:
        brand = request.GET.get('brand')
        model = request.GET.get('model')
        variant = request.GET.get('variant')
        
        if not brand or not model or not variant:
            return JsonResponse({'error': 'Brand, model, and variant parameters required'}, status=400)
        
        # Get cars_standard_id first
        cars_standard = CarStandard.objects.filter(
            brand_norm=brand,
            model_norm=model,
            variant_norm=variant
        ).first()
        
        if not cars_standard:
            return JsonResponse([], safe=False)
        
        # Get years from cars_unified table
        years = CarUnified.objects.filter(
            cars_standard=cars_standard,
            year__isnull=False
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        return JsonResponse(list(years), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_car_statistics(brand, model, variant, year, user_mileage=None, condition_assessments=None):
    """Get car statistics including average mileage and price with condition assessments"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                  s.brand_norm,
                  s.model_norm,
                  s.variant_norm,
                  c.year,
                  ROUND(AVG(c.mileage)) AS rata_rata_mileage_bulat,
                  ROUND(AVG(c.price)) AS rata_rata_price_bulat,
                  COUNT(*) AS total_data
                FROM
                  public.cars_unified c
                JOIN
                  public.cars_standard s
                ON
                  c.cars_standard_id = s.id
                WHERE
                  s.brand_norm = %s
                  AND s.model_norm = %s
                  AND s.variant_norm = %s
                  AND c.year = %s
                  AND c.mileage IS NOT NULL
                  AND c.price IS NOT NULL
                GROUP BY
                  s.brand_norm,
                  s.model_norm,
                  s.variant_norm,
                  c.year
            """, [brand, model, variant, year])
            
            row = cursor.fetchone()
            if row:
                result = {
                    'brand_norm': row[0],
                    'model_norm': row[1],
                    'variant_norm': row[2],
                    'year': row[3],
                    'rata_rata_mileage_bulat': row[4],
                    'rata_rata_price_bulat': row[5],
                    'total_data': row[6],
                }
                
                # Calculate price adjustments with 2-layer system
                avg_mileage = float(row[4])
                avg_price = float(row[5])
                
                # Layer 1: Mileage-based reduction (max 15%)
                layer1_reduction = 0
                mileage_diff_percent = 0
                
                if user_mileage is not None:
                    user_mileage = float(user_mileage)
                    if user_mileage > avg_mileage:
                        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
                        # Every 10% mileage increase = 2% price reduction
                        layer1_reduction = (mileage_diff_percent / 10) * 2
                        # Cap at maximum 15%
                        layer1_reduction = min(layer1_reduction, 15)
                    else:
                        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
                
                # Layer 2: Condition assessment reduction (max 70%)
                layer2_reduction = 0
                condition_breakdown = {}
                
                if condition_assessments is not None:
                    # Calculate total from all assessments
                    total_condition_reduction = sum(condition_assessments.values())
                    # Cap at maximum 70%
                    layer2_reduction = min(total_condition_reduction, 70)
                    condition_breakdown = condition_assessments.copy()
                
                # Total reduction = Layer 1 + Layer 2 (max 85%)
                total_reduction = layer1_reduction + layer2_reduction
                total_reduction = min(total_reduction, 85)  # Safety cap
                
                # Calculate final adjusted price
                adjusted_price = avg_price * (1 - total_reduction / 100)
                price_savings = avg_price - adjusted_price
                
                # Update result with all calculations
                if user_mileage is not None:
                    result.update({
                        'user_mileage': int(user_mileage),
                        'mileage_diff_percent': round(mileage_diff_percent, 1),
                    })
                
                result.update({
                    'layer1_reduction': round(layer1_reduction, 1),
                    'layer2_reduction': round(layer2_reduction, 1),
                    'total_reduction': round(total_reduction, 1),
                    'adjusted_price': round(adjusted_price),
                    'price_savings': round(price_savings),
                    'condition_breakdown': condition_breakdown
                })
                
                return result
    except Exception as e:
        print(f"Error in get_car_statistics: {e}")
        return None
    
    return None
