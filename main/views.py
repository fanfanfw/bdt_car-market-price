from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import connection, models
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
import json
import random
import re
from .models import (
    CarStandard, CarUnified, Category, BrandCategory, VerifiedPhone, OTPSession,
    MileageConfiguration, VehicleConditionCategory, ConditionOption
)

def index(request):
    """Main index page with car price estimation form"""
    # Get all active vehicle condition categories with their options
    categories = VehicleConditionCategory.objects.filter(
        is_active=True
    ).prefetch_related('options').order_by('order')
    
    context = {
        'condition_categories': categories,
    }
    return render(request, 'main/index.html', context)

def result(request):
    """Display calculation result page with secure OTP verification"""
    context = {}
    
    if request.method == 'POST':
        # Handle form submission directly
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
        
        if brand and model and variant and year:
            # Store form data in session for security (encrypted)
            request.session['calculation_request'] = {
                'brand': brand,
                'model': model,
                'variant': variant,
                'year': int(year),
                'user_mileage': user_mileage,
                'condition_assessments': condition_assessments
            }
            
            # Check if user has verified phone in cookie (1 day session)
            verified_phone_cookie = request.COOKIES.get('verified_phone')
            phone_already_verified = False
            cookie_should_be_deleted = False
            
            if verified_phone_cookie:
                # Check if phone is still active in database (1 month verification)
                try:
                    verified_phone = VerifiedPhone.objects.get(phone_number=verified_phone_cookie)
                    if not verified_phone.is_expired() and verified_phone.is_active:
                        phone_already_verified = True
                        context['verified_phone'] = verified_phone_cookie
                    else:
                        # Phone expired, mark for cookie deletion
                        cookie_should_be_deleted = True
                except VerifiedPhone.DoesNotExist:
                    # Phone not found in database, mark for cookie deletion
                    cookie_should_be_deleted = True
            
            context['phone_not_verified'] = not phone_already_verified
            context['car_info'] = f"{brand} {model} {variant} ({year})"
            
            # If phone already verified, we can show results immediately via JavaScript
            if phone_already_verified:
                context['skip_otp'] = True
        else:
            messages.error(request, 'Please complete all required data.')
            return redirect('main:index')
    else:
        # GET request - redirect to index
        messages.info(request, 'Please fill out the form first.')
        return redirect('main:index')
    
    # Create response and handle cookie deletion if needed
    response = render(request, 'main/result.html', context)
    
    if cookie_should_be_deleted:
        response.delete_cookie('verified_phone')
    
    return response


def get_categories(request):
    """API endpoint to get all categories"""
    try:
        categories = Category.objects.values_list('name', flat=True).order_by('name')
        return JsonResponse(list(categories), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_brands(request):
    """API endpoint to get all brands"""
    try:
        # Get all brands directly from CarStandard
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


def get_mileage_config():
    """Get the mileage configuration"""
    try:
        return MileageConfiguration.objects.first()
    except MileageConfiguration.DoesNotExist:
        # Return default values if no config exists
        return type('obj', (object,), {
            'threshold_percent': 10.0,
            'reduction_percent': 2.0,
            'max_reduction_cap': 15.0
        })


def get_car_statistics(brand, model, variant, year, user_mileage=None, condition_assessments=None):
    """Get car statistics including average mileage and price with condition assessments"""
    try:
        # Get mileage configuration
        mileage_config = get_mileage_config()

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
                
                # Calculate price adjustments with dynamic 2-layer system
                avg_mileage = float(row[4])
                avg_price = float(row[5])
                
                # Layer 1: Mileage-based reduction
                layer1_reduction = 0
                mileage_diff_percent = 0
                
                if user_mileage is not None:
                    user_mileage = float(user_mileage)
                    if user_mileage > avg_mileage:
                        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
                        threshold = float(mileage_config.threshold_percent)
                        reduction_per_threshold = float(mileage_config.reduction_percent)
                        layer1_reduction = (mileage_diff_percent / threshold) * reduction_per_threshold
                        # Apply cap
                        layer1_reduction = min(layer1_reduction, float(mileage_config.max_reduction_cap))
                    else:
                        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
                
                # Layer 2: Condition assessment reduction
                layer2_reduction = 0
                condition_breakdown = {}
                
                if condition_assessments is not None:
                    # Calculate total from all assessments
                    layer2_reduction = sum(condition_assessments.values())
                    # Apply Layer 2 cap
                    layer2_reduction = min(layer2_reduction, float(mileage_config.layer2_max_cap))
                    condition_breakdown = condition_assessments.copy()
                
                # Total reduction
                total_reduction = layer1_reduction + layer2_reduction
                
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
                    'condition_breakdown': condition_breakdown,
                    'config_version': 'simplified'
                })
                
                return result
    except Exception as e:
        print(f"Error in get_car_statistics: {e}")
        return None
    
    return None


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def normalize_phone_number(phone, country_code):
    """Normalize phone number format"""
    # Remove all non-digits
    phone_digits = re.sub(r'\D', '', phone)
    
    # Add country code if not present
    if not phone_digits.startswith('60') and not phone_digits.startswith('62'):
        country_digits = country_code.replace('+', '')
        phone_digits = country_digits + phone_digits
    
    return '+' + phone_digits


def generate_otp():
    """Generate 6-digit OTP"""
    return str(random.randint(100000, 999999))


@csrf_exempt
@require_http_methods(["POST"])
def check_phone_status(request):
    """Check if phone number is already verified and active"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        country_code = data.get('country_code', '+60')
        
        if not phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)
        
        # Normalize phone number
        full_phone = normalize_phone_number(phone, country_code)
        
        # Check if phone exists and is active
        try:
            verified_phone = VerifiedPhone.objects.get(phone_number=full_phone)
            
            if verified_phone.is_expired():
                # Phone expired, mark as inactive
                verified_phone.is_active = False
                verified_phone.save()
                return JsonResponse({
                    'verified': False,
                    'expired': True,
                    'message': 'Phone verification has expired. Please verify again.'
                })
            
            # Phone is active and valid
            verified_phone.access_count += 1
            verified_phone.save()
            
            return JsonResponse({
                'verified': True,
                'phone': full_phone,
                'message': 'Phone number is already verified.'
            })
            
        except VerifiedPhone.DoesNotExist:
            return JsonResponse({
                'verified': False,
                'message': 'Phone number not verified yet.'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_otp(request):
    """Send OTP to phone number"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        country_code = data.get('country_code', '+60')
        
        if not phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)
        
        # Normalize phone number
        full_phone = normalize_phone_number(phone, country_code)
        
        # Validate phone number format
        if country_code == '+60':
            # Malaysia format validation
            if not re.match(r'^\+60\d{8,10}$', full_phone):
                return JsonResponse({'error': 'Invalid Malaysian phone number format'}, status=400)
        elif country_code == '+62':
            # Indonesia format validation
            if not re.match(r'^\+62\d{8,12}$', full_phone):
                return JsonResponse({'error': 'Invalid Indonesian phone number format'}, status=400)
        
        # Generate OTP
        otp_code = generate_otp()
        
        # Clean up old OTP sessions for this phone (optional - keep only latest)
        OTPSession.objects.filter(phone_number=full_phone, is_used=False).update(is_used=True)
        
        # Create new OTP session
        otp_session = OTPSession.objects.create(
            phone_number=full_phone,
            otp_code=otp_code,
            ip_address=get_client_ip(request)
        )
        
        # For testing - return OTP in response (remove in production)
        return JsonResponse({
            'success': True,
            'message': f'OTP sent to {full_phone}',
            'otp': otp_code,  # For testing only!
            'expires_in': 60  # seconds
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """Verify OTP and mark phone as verified"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        otp_code = data.get('otp')
        country_code = data.get('country_code', '+60')
        
        if not phone or not otp_code:
            return JsonResponse({'error': 'Phone number and OTP required'}, status=400)
        
        # Normalize phone number
        full_phone = normalize_phone_number(phone, country_code)
        
        # Find valid OTP session
        try:
            otp_session = OTPSession.objects.filter(
                phone_number=full_phone,
                otp_code=otp_code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not otp_session:
                return JsonResponse({'error': 'Invalid OTP code'}, status=400)
            
            if otp_session.is_expired():
                return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)
            
            # Mark OTP as used
            otp_session.is_used = True
            otp_session.save()
            
            # Create or update verified phone
            verified_phone, created = VerifiedPhone.objects.get_or_create(
                phone_number=full_phone,
                defaults={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': get_client_ip(request),
                    'access_count': 1,
                    'is_active': True
                }
            )
            
            if not created:
                # Phone already exists, extend expiry
                verified_phone.extend_expiry()
                verified_phone.user_agent = request.META.get('HTTP_USER_AGENT', '')
                verified_phone.ip_address = get_client_ip(request)
                verified_phone.access_count += 1
                verified_phone.save()
            
            # Set session cookie for user convenience
            response = JsonResponse({
                'success': True,
                'phone': full_phone,
                'message': 'Phone number verified successfully!'
            })
            
            from django.conf import settings
            cookie_age = getattr(settings, 'OTP_SESSION_COOKIE_AGE', 86400)
            response.set_cookie(
                'verified_phone', 
                full_phone, 
                max_age=cookie_age,
                httponly=True,
                samesite='Strict'
            )
            
            return response
            
        except Exception as e:
            return JsonResponse({'error': 'Verification failed'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_secure_results(request):
    """Get calculation results only if phone is verified"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return JsonResponse({'error': 'Phone number required'}, status=400)
        
        # Verify phone is active
        try:
            verified_phone = VerifiedPhone.objects.get(phone_number=phone_number)
            if verified_phone.is_expired():
                return JsonResponse({'error': 'Phone verification expired'}, status=403)
        except VerifiedPhone.DoesNotExist:
            return JsonResponse({'error': 'Phone not verified'}, status=403)
        
        # Get calculation data from session
        calculation_data = request.session.get('calculation_request')
        if not calculation_data:
            return JsonResponse({'error': 'No calculation data found'}, status=400)
        
        # Perform calculation
        result_data = get_car_statistics(
            calculation_data['brand'],
            calculation_data['model'], 
            calculation_data['variant'],
            calculation_data['year'],
            calculation_data.get('user_mileage'),
            calculation_data.get('condition_assessments')
        )
        
        if result_data:
            # Update access count
            verified_phone.access_count += 1
            verified_phone.save()
            
            # Don't clear session data so user can recalculate with same data
            # Session data will be cleared when user starts new calculation
            
            return JsonResponse({
                'success': True,
                'result': result_data
            })
        else:
            return JsonResponse({
                'success': False,
                'no_data': True,
                'message': 'No data found for the selected combination'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Admin Views
def is_staff_user(user):
    """Check if user is staff"""
    return user.is_authenticated and user.is_staff

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
    stats = {
        'total_users': User.objects.count(),
        'verified_phones': VerifiedPhone.objects.filter(is_active=True).count(),
        'car_records': CarUnified.objects.count(),
        'today_calculations': 0,  # This would need to be tracked separately
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


# Simplified Pricing Configuration Admin Views

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
    categories = VehicleConditionCategory.objects.prefetch_related('options').order_by('order')
    
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
