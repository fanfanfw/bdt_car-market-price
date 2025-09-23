"""
Admin management views and dashboard
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from io import BytesIO

from ..models import (
    VerifiedPhone, OTPSession, MileageConfiguration, VehicleConditionCategory,
    ConditionOption, Category, BrandCategory, PriceTier, CalculationLog
)
from ..api_client import (
    get_statistics, get_today_count, get_car_records, get_car_detail,
    get_brands, get_brand_car_counts, APIError, APINotFoundError
)
from .utils import is_staff_user, export_verified_phones, export_otp_sessions


class CustomAdminLoginView(LoginView):
    """Custom admin login view"""
    template_name = 'admin/admin-login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/panel/dashboard/'

    def form_valid(self, form):
        """Check if user is staff before allowing login"""
        user = form.get_user()

        if not user.is_staff:
            form.add_error(None, 'You do not have admin privileges.')
            return self.form_invalid(form)

        messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        """Redirect if already authenticated and is staff"""
        if request.user.is_authenticated and request.user.is_staff:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)


@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def admin_dashboard_view(request):
    """Admin dashboard"""
    # Get statistics
    try:
        # Get statistics from FastAPI
        fastapi_stats = get_statistics()
        today_count = get_today_count()

        stats = {
            'verified_phones': VerifiedPhone.objects.filter(is_active=True).count(),
            'car_records': fastapi_stats.get('car_records', 0),
            'today_calculations': CalculationLog.get_today_count(),
            'today_ads_data': today_count,
        }
    except APIError:
        # Fallback to local database if FastAPI fails
        stats = {
            'verified_phones': VerifiedPhone.objects.filter(is_active=True).count(),
            'car_records': 0,
            'today_calculations': CalculationLog.get_today_count(),
            'today_ads_data': 0,
        }

    # Get recent activity (mock data for now)
    recent_activities = [
        {
            'icon': 'phone',
            'description': 'New phone verification',
            'timestamp': timezone.now()
        },
        {
            'icon': 'calculator',
            'description': 'Price calculation performed',
            'timestamp': timezone.now()
        },
    ]

    context = {
        'stats': stats,
        'recent_activities': recent_activities,
    }

    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def admin_logout_view(request):
    """Admin logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')


@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def formula_config_edit(request):
    """Edit formula configuration"""
    config, created = MileageConfiguration.objects.get_or_create(defaults={
        'threshold_percent': 10.0,
        'reduction_percent': 2.0,
        'max_reduction_cap': 15.0,
        'layer2_max_cap': 70.0
    })

    if request.method == 'POST':
        try:
            config.threshold_percent = float(request.POST.get('threshold_percent', 10.0))
            config.reduction_percent = float(request.POST.get('reduction_percent', 2.0))
            config.max_reduction_cap = float(request.POST.get('max_reduction_cap', 15.0))
            config.layer2_max_cap = float(request.POST.get('layer2_max_cap', 70.0))
            config.save()

            messages.success(request, 'Formula configuration updated successfully.')
            return redirect('main:formula_config_edit')
        except Exception as e:
            messages.error(request, f'Error updating configuration: {str(e)}')

    context = {
        'config': config
    }
    return render(request, 'admin/formula-config.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def condition_categories_manage(request):
    """Manage condition categories and their options"""
    # Exclude brand_category and price_tier as they are now handled automatically
    categories = VehicleConditionCategory.objects.prefetch_related('options').exclude(category_key__in=['brand_category', 'price_tier']).order_by('order')

    context = {
        'categories': categories
    }
    return render(request, 'admin/condition-categories.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def condition_option_edit(request, option_id):
    """Edit a condition option"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        option = get_object_or_404(ConditionOption, id=option_id)
        data = json.loads(request.body)

        option.label = data.get('label', '').strip()
        option.reduction_percentage = float(data.get('reduction_percentage', 0))

        if not option.label:
            return JsonResponse({'error': 'Option label is required'}, status=400)

        option.save()

        return JsonResponse({
            'success': True,
            'message': f'Option "{option.label}" updated successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def condition_option_add(request, category_id):
    """Add new option to a category"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        category = get_object_or_404(VehicleConditionCategory, id=category_id)
        data = json.loads(request.body)

        label = data.get('label', '').strip()
        reduction_percentage = float(data.get('reduction_percentage', 0))

        if not label:
            return JsonResponse({'error': 'Option label is required'}, status=400)

        # Check for duplicate labels
        if category.options.filter(label=label).exists():
            return JsonResponse({'error': 'Option with this label already exists'}, status=400)

        # Get next order
        next_order = category.options.count()

        option = ConditionOption.objects.create(
            category=category,
            label=label,
            reduction_percentage=reduction_percentage,
            order=next_order
        )

        return JsonResponse({
            'success': True,
            'message': f'Option "{option.label}" added successfully',
            'option_id': option.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def condition_option_delete(request, option_id):
    """Delete a condition option"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        option = get_object_or_404(ConditionOption, id=option_id)
        category = option.category

        # Prevent deleting if only one option left
        if category.options.count() <= 1:
            return JsonResponse({
                'error': 'Cannot delete the last option. At least one option is required.'
            }, status=400)

        option_label = option.label
        option.delete()

        return JsonResponse({
            'success': True,
            'message': f'Option "{option_label}" deleted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def car_data_view(request):
    """Car database management view with DataTables"""
    try:
        # Get statistics from FastAPI
        fastapi_stats = get_statistics()

        context = {
            'page_title': 'Car Database',
            'total_cars': fastapi_stats.get('car_records', 0),
            'total_brands': fastapi_stats.get('total_brands', 0),
            'total_models': fastapi_stats.get('total_models', 0),
            'sources': [('carlistmy', 'CarlistMY'), ('mudahmy', 'MudahMY')],
        }
    except APIError:
        # Fallback if FastAPI fails
        context = {
            'page_title': 'Car Database',
            'total_cars': 0,
            'total_brands': 0,
            'total_models': 0,
            'sources': [('carlistmy', 'CarlistMY'), ('mudahmy', 'MudahMY')],
        }

    return render(request, 'admin/car-data.html', context)


# Verified Phones Management
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def verified_phones_view(request):
    """Verified phones management view with DataTables"""
    context = {
        'page_title': 'Verified Phones',
        'total_phones': VerifiedPhone.objects.count(),
        'active_phones': VerifiedPhone.objects.filter(is_active=True).count(),
        'expired_phones': VerifiedPhone.objects.filter(is_active=True).filter(
            verified_at__lt=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        'today_verifications': VerifiedPhone.objects.filter(
            verified_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'admin/verified-phones.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def verified_phones_api(request):
    """API endpoint for DataTables verified phones data"""
    try:
        # Check if export is requested
        export_format = request.GET.get('export')
        if export_format in ['csv', 'excel']:
            return export_verified_phones(request, export_format)

        # DataTables parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '').strip()

        # Ordering
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Column mapping for ordering
        columns = ['id', 'phone_number', 'verified_at', 'last_accessed', 'access_count', 'is_active', 'ip_address']
        order_column = columns[order_column_index] if order_column_index < len(columns) else 'id'

        if order_direction == 'desc':
            order_column = '-' + order_column

        # Base queryset
        queryset = VerifiedPhone.objects.all()

        # Additional filtering
        status_filter = request.GET.get('status_filter')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'expired':
            queryset = queryset.filter(
                is_active=True,
                verified_at__lt=timezone.now() - timezone.timedelta(days=30)
            )

        # Search filtering
        if search_value:
            queryset = queryset.filter(
                Q(phone_number__icontains=search_value) |
                Q(ip_address__icontains=search_value) |
                Q(user_agent__icontains=search_value)
            )

        # Total records
        total_records = VerifiedPhone.objects.count()
        filtered_records = queryset.count()

        # Apply ordering and pagination
        queryset = queryset.order_by(order_column)[start:start + length]

        # Build data for DataTables
        data = []
        for phone in queryset:
            # Check if expired
            is_expired = phone.is_expired()

            # Format status
            if not phone.is_active:
                status_badge = '<span class="badge badge-error">Inactive</span>'
            elif is_expired:
                status_badge = '<span class="badge badge-warning">Expired</span>'
            else:
                status_badge = '<span class="badge badge-success">Active</span>'

            # Format access count with badge
            access_count_formatted = f'<span class="badge badge-outline">{phone.access_count}</span>'

            # Format phone number (mask middle digits for privacy)
            masked_phone = phone.phone_number[:4] + '*' * (len(phone.phone_number) - 8) + phone.phone_number[-4:]

            # Actions column
            actions = f'''<div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-info btn-sm" onclick="viewPhoneDetails({phone.id})" title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
                <button type="button" class="btn btn-warning btn-sm" onclick="togglePhoneStatus({phone.id}, {str(phone.is_active).lower()})" title="Toggle Status">
                    <i class="fas fa-toggle-{'on' if phone.is_active else 'off'}"></i>
                </button>
            </div>'''

            data.append([
                phone.id,
                masked_phone,
                phone.verified_at.strftime('%Y-%m-%d %H:%M'),
                phone.last_accessed.strftime('%Y-%m-%d %H:%M'),
                access_count_formatted,
                status_badge,
                phone.ip_address or '-',
                actions
            ])

        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def verified_phone_detail_api(request, phone_id):
    """API endpoint to get detailed phone information"""
    try:
        phone = get_object_or_404(VerifiedPhone, id=phone_id)

        data = {
            'id': phone.id,
            'phone_number': phone.phone_number,
            'verified_at': phone.verified_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_accessed': phone.last_accessed.strftime('%Y-%m-%d %H:%M:%S'),
            'access_count': phone.access_count,
            'is_active': phone.is_active,
            'is_expired': phone.is_expired(),
            'user_agent': phone.user_agent,
            'ip_address': phone.ip_address,
        }

        return JsonResponse({
            'success': True,
            'data': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def toggle_phone_status(request, phone_id):
    """Toggle phone active status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        phone = get_object_or_404(VerifiedPhone, id=phone_id)
        phone.is_active = not phone.is_active
        phone.save()

        return JsonResponse({
            'success': True,
            'message': f'Phone status updated to {"Active" if phone.is_active else "Inactive"}',
            'is_active': phone.is_active
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# OTP Sessions Management
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def otp_sessions_view(request):
    """OTP sessions management view with DataTables"""
    context = {
        'page_title': 'OTP Sessions',
        'total_sessions': OTPSession.objects.count(),
        'used_sessions': OTPSession.objects.filter(is_used=True).count(),
        'active_sessions': OTPSession.objects.filter(is_used=False).count(),
        'today_sessions': OTPSession.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'admin/otp-sessions.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def otp_sessions_api(request):
    """API endpoint for DataTables OTP sessions data"""
    try:
        # Check if export is requested
        export_format = request.GET.get('export')
        if export_format in ['csv', 'excel']:
            return export_otp_sessions(request, export_format)

        # DataTables parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '').strip()

        # Ordering
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_direction = request.GET.get('order[0][dir]', 'asc')

        # Column mapping for ordering
        columns = ['id', 'phone_number', 'verification_id', 'created_at', 'is_used', 'ip_address']
        order_column = columns[order_column_index] if order_column_index < len(columns) else 'id'

        if order_direction == 'desc':
            order_column = '-' + order_column

        # Base queryset
        queryset = OTPSession.objects.all()

        # Additional filtering
        status_filter = request.GET.get('status_filter')
        if status_filter == 'used':
            queryset = queryset.filter(is_used=True)
        elif status_filter == 'unused':
            queryset = queryset.filter(is_used=False)
        elif status_filter == 'expired':
            queryset = queryset.filter(
                is_used=False,
                created_at__lt=timezone.now() - timezone.timedelta(minutes=1)
            )

        # Search filtering
        if search_value:
            queryset = queryset.filter(
                Q(phone_number__icontains=search_value) |
                Q(verification_id__icontains=search_value) |
                Q(ip_address__icontains=search_value)
            )

        # Total records
        total_records = OTPSession.objects.count()
        filtered_records = queryset.count()

        # Apply ordering and pagination
        queryset = queryset.order_by(order_column)[start:start + length]

        # Build data for DataTables
        data = []
        for otp in queryset:
            # Check if expired
            is_expired = otp.is_expired()

            # Format status
            if otp.is_used:
                status_badge = '<span class="badge badge-success">Used</span>'
            elif is_expired:
                status_badge = '<span class="badge badge-error">Expired</span>'
            else:
                status_badge = '<span class="badge badge-warning">Active</span>'

            # Format phone number (mask middle digits for privacy)
            masked_phone = otp.phone_number[:4] + '*' * (len(otp.phone_number) - 8) + otp.phone_number[-4:]

            # Format verification ID (partially masked for security)
            masked_verification_id = (otp.verification_id[:3] + '***' + otp.verification_id[-3:]) if otp.verification_id and len(otp.verification_id) > 6 else (otp.verification_id or '-')

            # Actions column
            actions = f'''<div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-info btn-sm" onclick="viewOTPDetails({otp.id})" title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
            </div>'''

            data.append([
                otp.id,
                masked_phone,
                masked_verification_id,
                otp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                status_badge,
                otp.ip_address or '-',
                actions
            ])

        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def otp_session_detail_api(request, session_id):
    """API endpoint to get detailed OTP session information"""
    try:
        otp = get_object_or_404(OTPSession, id=session_id)

        data = {
            'id': otp.id,
            'phone_number': otp.phone_number,
            'verification_id': otp.verification_id,
            'created_at': otp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_used': otp.is_used,
            'is_expired': otp.is_expired(),
            'is_valid': otp.is_valid(),
            'ip_address': otp.ip_address,
            'expires_at': (otp.created_at + timezone.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'),
        }

        return JsonResponse({
            'success': True,
            'data': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Categories Management (Brand Categories System)
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def categories_management_view(request):
    """Categories management view with CRUD operations"""
    # Get categories with brand counts
    categories = Category.objects.annotate(
        brand_count=Count('brandcategory')
    ).order_by('name')

    # Get unclassified brands count via FastAPI
    try:
        all_brands = get_brands()  # From FastAPI
        # Get only valid classified brands (that exist in FastAPI)
        valid_classified_brands = BrandCategory.objects.filter(brand__in=all_brands)
        classified_brands_count = valid_classified_brands.count()
        unclassified_count = len(all_brands) - classified_brands_count
        total_unique_brands = len(all_brands)
    except APIError:
        # Fallback if FastAPI is down
        classified_brands_count = BrandCategory.objects.count()
        unclassified_count = 0
        total_unique_brands = 0

    context = {
        'page_title': 'Brand Categories Management',
        'categories': categories,
        'total_categories': categories.count(),
        'total_classified_brands': classified_brands_count,
        'unclassified_brands': unclassified_count,
        'total_unique_brands': total_unique_brands,
    }
    return render(request, 'admin/categories-management.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def category_create(request):
    """Create new category"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        reduction_percentage = data.get('reduction_percentage', 0.0)

        if not name:
            return JsonResponse({'error': 'Category name is required'}, status=400)

        # Validate reduction percentage
        try:
            reduction_percentage = float(reduction_percentage)
            if reduction_percentage < 0 or reduction_percentage > 100:
                return JsonResponse({'error': 'Reduction percentage must be between 0 and 100'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid reduction percentage'}, status=400)

        # Check for duplicate
        if Category.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Category with this name already exists'}, status=400)

        category = Category.objects.create(name=name, reduction_percentage=reduction_percentage)

        return JsonResponse({
            'success': True,
            'message': f'Category "{category.name}" created successfully',
            'category_id': category.id,
            'category_name': category.name
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def category_edit(request, category_id):
    """Edit existing category"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        category = get_object_or_404(Category, id=category_id)
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        reduction_percentage = data.get('reduction_percentage', category.reduction_percentage)

        if not new_name:
            return JsonResponse({'error': 'Category name is required'}, status=400)

        # Validate reduction percentage
        try:
            reduction_percentage = float(reduction_percentage)
            if reduction_percentage < 0 or reduction_percentage > 100:
                return JsonResponse({'error': 'Reduction percentage must be between 0 and 100'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid reduction percentage'}, status=400)

        # Check for duplicate (excluding current category)
        if Category.objects.filter(name=new_name).exclude(id=category_id).exists():
            return JsonResponse({'error': 'Category with this name already exists'}, status=400)

        old_name = category.name
        category.name = new_name
        category.reduction_percentage = reduction_percentage
        category.save()

        return JsonResponse({
            'success': True,
            'message': f'Category updated from "{old_name}" to "{new_name}"',
            'category_id': category.id,
            'category_name': category.name
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def category_delete(request, category_id):
    """Delete category (with safety checks)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        category = get_object_or_404(Category, id=category_id)

        # Check if category has brands assigned
        brand_count = category.brandcategory_set.count()
        if brand_count > 0:
            return JsonResponse({
                'error': f'Cannot delete category. It has {brand_count} brands assigned. Please reassign or remove the brands first.'
            }, status=400)

        category_name = category.name
        category.delete()

        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" deleted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def category_brands_api(request, category_id):
    """Get brands assigned to a specific category"""
    try:
        category = get_object_or_404(Category, id=category_id)
        brand_categories = BrandCategory.objects.filter(category=category).order_by('brand')

        brands = []
        for bc in brand_categories:
            # Get car count from FastAPI (we'll mock this for now since we don't have specific endpoint)
            try:
                # For now, we'll use a simple approach - you can add specific endpoint later
                car_count = 0  # TODO: Add FastAPI endpoint for brand car count
            except:
                car_count = 0
            brands.append({
                'id': bc.id,
                'brand': bc.brand,
                'car_count': car_count,
                'created_at': bc.created_at.strftime('%Y-%m-%d %H:%M')
            })

        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name
            },
            'brands': brands,
            'total_brands': len(brands)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Brand Classification Interface
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def brand_classification_view(request):
    """Brand classification interface"""
    # Get all brands from FastAPI
    try:
        existing_brands = set(get_brands())
    except APIError:
        existing_brands = set()

    # Get only valid classified brands (that exist in FastAPI)
    valid_classified_brands = BrandCategory.objects.filter(brand__in=existing_brands)

    # Get statistics
    total_brands = len(existing_brands)
    classified_brands = valid_classified_brands.count()
    unclassified_brands = total_brands - classified_brands
    total_categories = Category.objects.count()

    context = {
        'page_title': 'Brand Classification',
        'total_brands': total_brands,
        'classified_brands': classified_brands,
        'unclassified_brands': unclassified_brands,
        'total_categories': total_categories,
        'categories': Category.objects.all().order_by('name'),
    }
    return render(request, 'admin/brand-classification.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def brands_data_api(request):
    """API for brand classification DataTables"""
    try:
        # DataTables parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '').strip()

        # Filter parameters
        status_filter = request.GET.get('status_filter', '')  # classified, unclassified, all
        category_filter = request.GET.get('category_filter', '')

        # Get all brands from FastAPI
        try:
            all_fastapi_brands = get_brands()
        except APIError:
            all_fastapi_brands = []

        # Get classified brands mapping
        brand_categories_map = {}
        for bc in BrandCategory.objects.select_related('category'):
            brand_categories_map[bc.brand] = {
                'category_id': bc.category.id,
                'category_name': bc.category.name,
                'mapping_id': bc.id
            }

        # Get car counts for all brands in bulk from FastAPI
        try:
            brand_car_counts = get_brand_car_counts()
        except APIError:
            brand_car_counts = {}

        # Create brand list with car counts from FastAPI
        brands_with_counts = []
        for brand in all_fastapi_brands:
            car_count = brand_car_counts.get(brand, 0)
            brands_with_counts.append({
                'brand': brand,
                'car_count': car_count,
                'category_info': brand_categories_map.get(brand)
            })

        # Filter brands based on status
        if status_filter == 'classified':
            brands_with_counts = [b for b in brands_with_counts if b['category_info'] is not None]
        elif status_filter == 'unclassified':
            brands_with_counts = [b for b in brands_with_counts if b['category_info'] is None]

        # Filter by category if specified
        if category_filter and category_filter != 'all':
            try:
                category_id = int(category_filter)
                brands_with_counts = [
                    b for b in brands_with_counts
                    if b['category_info'] and b['category_info']['category_id'] == category_id
                ]
            except ValueError:
                pass

        # Search filtering
        if search_value:
            brands_with_counts = [
                b for b in brands_with_counts
                if search_value.lower() in b['brand'].lower() or
                (b['category_info'] and search_value.lower() in b['category_info']['category_name'].lower())
            ]

        # Sort brands
        brands_with_counts.sort(key=lambda x: x['brand'])

        # Total and filtered counts
        total_records = len(brands_with_counts)
        filtered_records = total_records

        # Pagination
        paginated_brands = brands_with_counts[start:start + length]

        # Build data for DataTables
        data = []
        for brand_info in paginated_brands:
            brand = brand_info['brand']
            car_count = brand_info['car_count']
            category_info = brand_info['category_info']

            # Status and category display
            if category_info:
                status_badge = f'<span class="badge badge-success">Classified</span>'
                category_display = f'<span class="badge badge-outline">{category_info["category_name"]}</span>'
                actions = f'''<div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-warning btn-sm" onclick="reassignBrand('{brand}', {category_info['category_id']}, {category_info['mapping_id']})" title="Reassign Category">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-danger btn-sm" onclick="removeBrandClassification('{brand}', {category_info['mapping_id']})" title="Remove Classification">
                        <i class="fas fa-times"></i>
                    </button>
                </div>'''
            else:
                status_badge = f'<span class="badge badge-error">Unclassified</span>'
                category_display = '-'
                actions = f'''<button type="button" class="btn btn-primary btn-sm" onclick="assignBrand('{brand}')" title="Assign Category">
                    <i class="fas fa-plus"></i> Assign
                </button>'''

            # Car count with badge
            car_count_formatted = f'<span class="badge badge-outline">{car_count:,}</span>'

            data.append([
                brand,
                car_count_formatted,
                status_badge,
                category_display,
                actions
            ])

        return JsonResponse({
            'draw': draw,
            'recordsTotal': len(all_fastapi_brands),
            'recordsFiltered': filtered_records,
            'data': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def assign_brand_to_category(request):
    """Assign brand to category"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        data = json.loads(request.body)
        brand = data.get('brand_name', data.get('brand', '')).strip()
        category_id = data.get('category_id')

        if not brand or not category_id:
            return JsonResponse({'error': 'Brand and category are required'}, status=400)

        # Get category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=400)

        # Check if brand already classified
        if BrandCategory.objects.filter(brand=brand).exists():
            return JsonResponse({'error': 'Brand is already classified. Use reassign instead.'}, status=400)

        # Create brand category mapping
        brand_category = BrandCategory.objects.create(brand=brand, category=category)

        return JsonResponse({
            'success': True,
            'message': f'Brand "{brand}" assigned to category "{category.name}" successfully',
            'mapping_id': brand_category.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def reassign_brand_to_category(request):
    """Reassign brand to different category"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        data = json.loads(request.body)
        brand = data.get('brand_name', data.get('brand', '')).strip()
        new_category_id = data.get('category_id')
        mapping_id = data.get('mapping_id')

        if not brand or not new_category_id:
            return JsonResponse({'error': 'Brand and category are required'}, status=400)

        # Get new category
        try:
            new_category = Category.objects.get(id=new_category_id)
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=400)

        # Get existing mapping
        try:
            if mapping_id:
                brand_category = BrandCategory.objects.get(id=mapping_id, brand=brand)
            else:
                brand_category = BrandCategory.objects.get(brand=brand)
        except BrandCategory.DoesNotExist:
            return JsonResponse({'error': 'Brand mapping not found'}, status=400)

        old_category_name = brand_category.category.name
        brand_category.category = new_category
        brand_category.save()

        return JsonResponse({
            'success': True,
            'message': f'Brand "{brand}" reassigned from "{old_category_name}" to "{new_category.name}" successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def remove_brand_classification(request):
    """Remove brand classification"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        data = json.loads(request.body)
        brand = data.get('brand_name', data.get('brand', '')).strip()
        mapping_id = data.get('mapping_id')

        if not brand:
            return JsonResponse({'error': 'Brand is required'}, status=400)

        # Get and delete mapping
        try:
            if mapping_id:
                brand_category = BrandCategory.objects.get(id=mapping_id, brand=brand)
            else:
                brand_category = BrandCategory.objects.get(brand=brand)
            category_name = brand_category.category.name
            brand_category.delete()

            return JsonResponse({
                'success': True,
                'message': f'Brand "{brand}" removed from category "{category_name}" successfully'
            })
        except BrandCategory.DoesNotExist:
            return JsonResponse({'error': 'Brand mapping not found'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def get_unclassified_brands_api(request):
    """Get list of unclassified brands"""
    try:
        # Get all brands from FastAPI
        try:
            all_brands = get_brands()
        except APIError:
            all_brands = []

        # Get classified brands
        classified_brands = set(BrandCategory.objects.values_list('brand', flat=True))

        # Get unclassified brands
        unclassified_brands = [brand for brand in all_brands if brand not in classified_brands]
        unclassified_brands.sort()

        return JsonResponse({
            'success': True,
            'brands': unclassified_brands,
            'total': len(unclassified_brands)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Price Tiers Management
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def price_tiers_management_view(request):
    """Price Tiers Management View"""
    try:
        # Get all price tiers
        price_tiers = PriceTier.objects.all().order_by('order', 'min_price')

        # Calculate statistics
        total_tiers = price_tiers.count()
        active_tiers = price_tiers.filter(is_active=True).count()

        # Check for price gaps or overlaps
        has_issues = False
        issues = []

        active_price_tiers = price_tiers.filter(is_active=True).order_by('min_price')
        for i, tier in enumerate(active_price_tiers):
            if i > 0:
                prev_tier = active_price_tiers[i-1]
                if prev_tier.max_price and float(prev_tier.max_price) < float(tier.min_price):
                    # Gap detected (only if there's actually a gap, not just different by 1)
                    has_issues = True
                    issues.append(f"Price gap between {prev_tier.name} and {tier.name}")
                elif prev_tier.max_price and float(prev_tier.max_price) > float(tier.min_price):
                    # Overlap detected (only if max price is greater than min price of next tier)
                    has_issues = True
                    issues.append(f"Price overlap between {prev_tier.name} and {tier.name}")

        context = {
            'price_tiers': price_tiers,
            'total_tiers': total_tiers,
            'active_tiers': active_tiers,
            'inactive_tiers': total_tiers - active_tiers,
            'has_issues': has_issues,
            'issues': issues,
        }

        return render(request, 'admin/price-tiers-management.html', context)

    except Exception as e:
        messages.error(request, f'Error loading price tiers: {str(e)}')
        return redirect('main:categories_management_view')


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def price_tier_create(request):
    """Create new price tier"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        reduction_percentage = data.get('reduction_percentage', 0.0)

        if not name:
            return JsonResponse({'error': 'Tier name is required'}, status=400)

        # Validate prices
        try:
            min_price = float(min_price)
            if min_price < 0:
                return JsonResponse({'error': 'Minimum price cannot be negative'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid minimum price'}, status=400)

        if max_price:
            try:
                max_price = float(max_price)
                if max_price <= min_price:
                    return JsonResponse({'error': 'Maximum price must be greater than minimum price'}, status=400)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'Invalid maximum price'}, status=400)
        else:
            max_price = None

        # Validate reduction percentage
        try:
            reduction_percentage = float(reduction_percentage)
            if reduction_percentage < 0 or reduction_percentage > 100:
                return JsonResponse({'error': 'Reduction percentage must be between 0 and 100'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid reduction percentage'}, status=400)

        # Check for duplicate name
        if PriceTier.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Price tier with this name already exists'}, status=400)

        # Get next order
        next_order = PriceTier.objects.count()

        tier = PriceTier.objects.create(
            name=name,
            min_price=min_price,
            max_price=max_price,
            reduction_percentage=reduction_percentage,
            order=next_order
        )

        return JsonResponse({
            'success': True,
            'message': f'Price tier "{tier.name}" created successfully',
            'tier_id': tier.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def price_tier_edit(request, tier_id):
    """Edit existing price tier"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        tier = get_object_or_404(PriceTier, id=tier_id)
        data = json.loads(request.body)

        new_name = data.get('name', '').strip()
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        reduction_percentage = data.get('reduction_percentage', tier.reduction_percentage)

        if not new_name:
            return JsonResponse({'error': 'Tier name is required'}, status=400)

        # Validate prices
        try:
            min_price = float(min_price)
            if min_price < 0:
                return JsonResponse({'error': 'Minimum price cannot be negative'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid minimum price'}, status=400)

        if max_price:
            try:
                max_price = float(max_price)
                if max_price <= min_price:
                    return JsonResponse({'error': 'Maximum price must be greater than minimum price'}, status=400)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'Invalid maximum price'}, status=400)
        else:
            max_price = None

        # Validate reduction percentage
        try:
            reduction_percentage = float(reduction_percentage)
            if reduction_percentage < 0 or reduction_percentage > 100:
                return JsonResponse({'error': 'Reduction percentage must be between 0 and 100'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid reduction percentage'}, status=400)

        # Check for duplicate name (excluding current tier)
        if PriceTier.objects.filter(name=new_name).exclude(id=tier_id).exists():
            return JsonResponse({'error': 'Price tier with this name already exists'}, status=400)

        old_name = tier.name
        tier.name = new_name
        tier.min_price = min_price
        tier.max_price = max_price
        tier.reduction_percentage = reduction_percentage
        tier.save()

        return JsonResponse({
            'success': True,
            'message': f'Price tier updated from "{old_name}" to "{new_name}"',
            'tier_id': tier.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_user, login_url='/login/')
def price_tier_delete(request, tier_id):
    """Delete price tier"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    try:
        tier = get_object_or_404(PriceTier, id=tier_id)
        tier_name = tier.name
        tier.delete()

        return JsonResponse({
            'success': True,
            'message': f'Price tier "{tier_name}" deleted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)