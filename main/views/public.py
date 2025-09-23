"""
Public views for end users (non-admin)
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from ..models import VehicleConditionCategory, VerifiedPhone
from .utils import get_car_statistics


def index(request):
    """Main index page with car price estimation form"""
    # Get all active vehicle condition categories with their options
    # Exclude brand_category and price_tier as they will be handled automatically
    categories = VehicleConditionCategory.objects.filter(
        is_active=True
    ).exclude(category_key__in=['brand_category', 'price_tier']).prefetch_related('options').order_by('order')

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

        # Get condition assessment values (excluding auto-detected categories)
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
            # brand_category and price_tier are now auto-detected, not from form
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