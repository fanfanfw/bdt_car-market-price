"""
API endpoints for data retrieval
"""
import json
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render

from ..models import Category, VehicleConditionCategory
from ..api_client import (
    get_brands, get_models, get_variants, get_years, get_car_records,
    get_car_detail, APIError, APINotFoundError
)
from .utils import get_car_statistics


def require_api_key(view_func):
    """Protect integration endpoints with X-API-Key header."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        configured_api_key = getattr(settings, 'API_KEY', '')
        if not configured_api_key:
            return JsonResponse({'error': 'API key is not configured on server'}, status=503)

        provided_api_key = request.headers.get('X-API-Key') or request.META.get('HTTP_X_API_KEY')
        if provided_api_key != configured_api_key:
            return JsonResponse({'error': 'Invalid API key'}, status=401)

        return view_func(request, *args, **kwargs)

    return _wrapped


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


def swagger_ui(request):
    """Serve Swagger UI page for integration APIs."""
    return render(request, 'main/swagger-ui.html')


def openapi_schema(request):
    """Serve OpenAPI schema for integration APIs."""
    schema = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Car Market Price Integration API',
            'version': '1.0.0',
            'description': 'Integration endpoints for condition options and price estimation.',
        },
        'servers': [
            {'url': '/'},
        ],
        'tags': [
            {'name': 'Lookup', 'description': 'Brand/model/variant/year lookup endpoints'},
            {'name': 'Integration', 'description': 'Integration endpoints for condition options and price calculation'},
        ],
        'components': {
            'securitySchemes': {
                'ApiKeyAuth': {
                    'type': 'apiKey',
                    'in': 'header',
                    'name': 'X-API-Key',
                    'description': 'Provide API key in X-API-Key header.',
                }
            },
            'schemas': {
                'ConditionOption': {
                    'type': 'object',
                    'properties': {
                        'option_code': {'type': 'string', 'example': 'excellent'},
                        'label': {'type': 'string', 'example': 'Excellent'},
                        'reduction_percentage': {'type': 'number', 'format': 'float', 'example': 0.0},
                    },
                    'required': ['option_code', 'label', 'reduction_percentage'],
                },
                'ConditionCategory': {
                    'type': 'object',
                    'properties': {
                        'category_key': {'type': 'string', 'example': 'exterior_condition'},
                        'display_name': {'type': 'string', 'example': 'Exterior Condition'},
                        'options': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/ConditionOption'},
                        },
                    },
                    'required': ['category_key', 'display_name', 'options'],
                },
                'PriceEstimateRequest': {
                    'type': 'object',
                    'properties': {
                        'brand': {'type': 'string', 'example': 'TOYOTA'},
                        'model': {'type': 'string', 'example': 'YARIS'},
                        'variant': {'type': 'string', 'example': 'E'},
                        'year': {'type': 'integer', 'example': 2025},
                        'mileage': {'type': 'integer', 'nullable': True, 'example': 85000},
                        'condition': {
                            'type': 'object',
                            'additionalProperties': {'type': 'string'},
                            'example': {
                                'exterior_condition': 'good',
                                'interior_condition': 'good',
                                'mechanical_condition': 'fair',
                                'accident_history': 'none',
                                'service_history': 'full',
                                'number_of_owners': '2_owners',
                                'tires_brakes': 'fair',
                                'modifications': 'minor',
                                'market_demand': 'average',
                            },
                        },
                    },
                    'required': ['brand', 'model', 'variant', 'year', 'condition'],
                },
            },
        },
        'paths': {
            '/api/brands/': {
                'get': {
                    'tags': ['Lookup'],
                    'summary': 'Get brands',
                    'description': 'Returns all available car brands.',
                    'responses': {
                        '200': {
                            'description': 'Brand list',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                    'example': ['TOYOTA', 'HONDA', 'PROTON']
                                }
                            },
                        },
                    },
                }
            },
            '/api/models/': {
                'get': {
                    'tags': ['Lookup'],
                    'summary': 'Get models by brand',
                    'description': 'Returns models for a selected brand.',
                    'parameters': [
                        {
                            'name': 'brand',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'TOYOTA',
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'Model list',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                    'example': ['YARIS']
                                }
                            },
                        },
                        '400': {'description': 'Brand parameter required'},
                    },
                }
            },
            '/api/variants/': {
                'get': {
                    'tags': ['Lookup'],
                    'summary': 'Get variants by brand and model',
                    'description': 'Returns variants for a selected brand and model.',
                    'parameters': [
                        {
                            'name': 'brand',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'TOYOTA',
                        },
                        {
                            'name': 'model',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'YARIS',
                        },
                    ],
                    'responses': {
                        '200': {
                            'description': 'Variant list',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                    },
                                    'example': ['E']
                                }
                            },
                        },
                        '400': {'description': 'Brand and model parameters required'},
                    },
                }
            },
            '/api/years/': {
                'get': {
                    'tags': ['Lookup'],
                    'summary': 'Get years by brand, model, and variant',
                    'description': 'Returns years for a selected brand, model, and variant.',
                    'parameters': [
                        {
                            'name': 'brand',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'TOYOTA',
                        },
                        {
                            'name': 'model',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'YARIS',
                        },
                        {
                            'name': 'variant',
                            'in': 'query',
                            'required': True,
                            'schema': {'type': 'string'},
                            'example': 'E',
                        },
                    ],
                    'responses': {
                        '200': {
                            'description': 'Year list',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'type': 'integer'},
                                    },
                                    'example': [2025]
                                }
                            },
                        },
                        '400': {'description': 'Brand, model, and variant parameters required'},
                    },
                }
            },
            '/api/condition-options/': {
                'get': {
                    'tags': ['Integration'],
                    'summary': 'Get condition categories and options',
                    'description': 'Returns dynamic condition categories and stable option_code values for integrations.',
                    'security': [{'ApiKeyAuth': []}],
                    'responses': {
                        '200': {
                            'description': 'Condition options retrieved',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'categories': {
                                                'type': 'array',
                                                'items': {'$ref': '#/components/schemas/ConditionCategory'},
                                            }
                                        },
                                    }
                                }
                            },
                        },
                        '401': {'description': 'Invalid API key'},
                    },
                }
            },
            '/api/price-estimate/': {
                'post': {
                    'tags': ['Integration'],
                    'summary': 'Calculate price estimation',
                    'description': 'Calculate final estimated price using mileage and condition option_code values.',
                    'security': [{'ApiKeyAuth': []}],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/PriceEstimateRequest'}
                            }
                        },
                    },
                    'responses': {
                        '200': {
                            'description': 'Calculation success',
                            'content': {'application/json': {'schema': {'type': 'object'}}},
                        },
                        '400': {'description': 'Validation error'},
                        '401': {'description': 'Invalid API key'},
                    },
                }
            },
        },
    }
    return JsonResponse(schema)


@csrf_exempt
@require_http_methods(["POST"])
@require_api_key
def price_estimate_api(request):
    """API endpoint to calculate car price estimation from integration payload."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    brand = (data.get('brand') or '').strip()
    model = (data.get('model') or '').strip()
    variant = (data.get('variant') or '').strip()
    year = data.get('year')
    mileage = data.get('mileage')
    condition = data.get('condition')

    if not all([brand, model, variant]) or year is None or not isinstance(condition, dict):
        return JsonResponse({
            'error': 'Required fields: brand, model, variant, year, condition'
        }, status=400)

    try:
        year = int(year)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'year must be an integer'}, status=400)

    if mileage in ['', None]:
        mileage = None
    else:
        try:
            mileage = int(mileage)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'mileage must be an integer when provided'}, status=400)

    categories = list(
        VehicleConditionCategory.objects.filter(is_active=True)
        .exclude(category_key__in=['brand_category', 'price_tier'])
        .prefetch_related('options')
        .order_by('order')
    )

    expected_category_keys = {category.category_key for category in categories}
    provided_category_keys = set(condition.keys())

    missing_categories = sorted(expected_category_keys - provided_category_keys)
    unknown_categories = sorted(provided_category_keys - expected_category_keys)

    if missing_categories:
        return JsonResponse({
            'error': 'Missing condition categories',
            'missing_categories': missing_categories,
        }, status=400)

    if unknown_categories:
        return JsonResponse({
            'error': 'Unknown condition categories',
            'unknown_categories': unknown_categories,
        }, status=400)

    condition_assessments = {}
    invalid_options = []

    for category in categories:
        option_code = (condition.get(category.category_key) or '').strip()
        if not option_code:
            invalid_options.append({
                'category_key': category.category_key,
                'error': 'option_code is required',
            })
            continue

        option = category.options.filter(option_code=option_code).first()
        if option is None:
            invalid_options.append({
                'category_key': category.category_key,
                'option_code': option_code,
                'error': 'invalid option_code',
            })
            continue

        condition_assessments[category.category_key] = float(option.reduction_percentage)

    if invalid_options:
        return JsonResponse({
            'error': 'Invalid condition options',
            'details': invalid_options,
        }, status=400)

    result_data = get_car_statistics(
        brand=brand,
        model=model,
        variant=variant,
        year=year,
        user_mileage=mileage,
        condition_assessments=condition_assessments,
    )

    if result_data is None:
        return JsonResponse({
            'success': False,
            'no_data': True,
            'message': 'No data found for the selected combination',
        })

    return JsonResponse({
        'success': True,
        'result': result_data,
    })


@require_api_key
def get_condition_options_api(request):
    """API endpoint to get dynamic condition categories and option codes."""
    try:
        categories = (
            VehicleConditionCategory.objects.filter(is_active=True)
            .exclude(category_key__in=['brand_category', 'price_tier'])
            .prefetch_related('options')
            .order_by('order')
        )

        payload = []
        for category in categories:
            options = []
            for option in category.options.all():
                options.append({
                    'option_code': option.option_code,
                    'label': option.label,
                    'reduction_percentage': float(option.reduction_percentage),
                })

            payload.append({
                'category_key': category.category_key,
                'display_name': category.display_name,
                'options': options,
            })

        return JsonResponse({'categories': payload})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
