"""
API endpoints for data retrieval
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models import Category
from ..api_client import (
    get_brands, get_models, get_variants, get_years, get_car_records,
    get_car_detail, APIError, APINotFoundError
)


def get_categories(request):
    """API endpoint to get all categories"""
    try:
        categories = Category.objects.values_list('name', flat=True).order_by('name')
        return JsonResponse(list(categories), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_brands_api(request):
    """API endpoint to get all brands"""
    try:
        # Get brands from FastAPI
        brands = get_brands()
        return JsonResponse(list(brands), safe=False)
    except APIError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'FastAPI connection failed'}, status=500)


def get_models_api(request):
    """API endpoint to get models for selected brand"""
    try:
        brand = request.GET.get('brand')
        if not brand:
            return JsonResponse({'error': 'Brand parameter required'}, status=400)

        models = get_models(brand)
        return JsonResponse(list(models), safe=False)
    except APIError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'FastAPI connection failed'}, status=500)


def get_variants_api(request):
    """API endpoint to get variants for selected brand and model"""
    try:
        brand = request.GET.get('brand')
        model = request.GET.get('model')

        if not brand or not model:
            return JsonResponse({'error': 'Brand and model parameters required'}, status=400)

        variants = get_variants(brand, model)
        return JsonResponse(list(variants), safe=False)
    except APIError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'FastAPI connection failed'}, status=500)


def get_years_api(request):
    """API endpoint to get years for selected brand, model, and variant"""
    try:
        brand = request.GET.get('brand')
        model = request.GET.get('model')
        variant = request.GET.get('variant')

        if not brand or not model or not variant:
            return JsonResponse({'error': 'Brand, model, and variant parameters required'}, status=400)

        years = get_years(brand, model, variant)
        return JsonResponse(list(years), safe=False)
    except APIError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'FastAPI connection failed'}, status=500)


def car_data_api(request):
    """API endpoint for DataTables car data"""
    from django.views.decorators.csrf import csrf_exempt
    from django.contrib.auth.decorators import login_required, user_passes_test
    from .utils import is_staff_user

    @csrf_exempt
    @login_required
    @user_passes_test(is_staff_user, login_url='/login/')
    def _car_data_api(request):
        try:
            # DataTables parameters
            draw = int(request.GET.get('draw', 1))
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            search_value = request.GET.get('search[value]', '').strip()

            # Ordering
            order_column_index = int(request.GET.get('order[0][column]', 0))
            order_direction = request.GET.get('order[0][dir]', 'asc')

            # Column mapping for ordering
            columns = ['id', 'source', 'brand', 'model', 'variant', 'year', 'mileage', 'price']
            order_column = str(order_column_index) if order_column_index < len(columns) else '0'

            # Additional filtering
            source_filter = request.GET.get('source_filter')
            year_filter = request.GET.get('year_filter')
            price_filter = request.GET.get('price_filter')
            brand_filter = request.GET.get('brand_filter')
            model_filter = request.GET.get('model_filter')
            variant_filter = request.GET.get('variant_filter')
            year_value_raw = request.GET.get('year_value')
            year_value = int(year_value_raw) if year_value_raw and year_value_raw.isdigit() else None

            # Normalize string filters
            source_filter = source_filter.strip() if source_filter else None
            year_filter = year_filter.strip() if year_filter else None
            price_filter = price_filter.strip() if price_filter else None
            brand_filter = brand_filter.strip() if brand_filter else None
            model_filter = model_filter.strip() if model_filter else None
            variant_filter = variant_filter.strip() if variant_filter else None

            # Call FastAPI
            result = get_car_records(
                draw=draw,
                start=start,
                length=length,
                search=search_value if search_value else None,
                order_column=order_column,
                order_direction=order_direction,
                source_filter=source_filter,
                year_filter=year_filter,
                price_filter=price_filter,
                brand_filter=brand_filter,
                model_filter=model_filter,
                variant_filter=variant_filter,
                year_value=year_value
            )

            return JsonResponse(result)

        except APIError as e:
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'error': 'FastAPI connection failed'}, status=500)

    return _car_data_api(request)


def car_detail_api(request, car_id):
    """API endpoint to get detailed car information"""
    from django.views.decorators.csrf import csrf_exempt
    from django.contrib.auth.decorators import login_required, user_passes_test
    from .utils import is_staff_user

    @csrf_exempt
    @login_required
    @user_passes_test(is_staff_user, login_url='/login/')
    def _car_detail_api(request, car_id):
        try:
            source = request.GET.get('source') or None
            car_detail = get_car_detail(car_id, source)
            # Format response with success flag for template compatibility
            return JsonResponse({
                'success': True,
                'data': car_detail
            })
        except APINotFoundError:
            return JsonResponse({
                'success': False,
                'error': 'Car not found'
            }, status=404)
        except APIError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'FastAPI connection failed'
            }, status=500)

    return _car_detail_api(request, car_id)
