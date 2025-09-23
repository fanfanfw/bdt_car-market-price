"""
Authentication views for OTP and phone verification
"""
import json
import re
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from decouple import config

from ..models import VerifiedPhone, OTPSession, CalculationLog
from .utils import (
    normalize_phone_number, get_client_ip, get_car_statistics, generate_otp
)
from ..copycode_client import copycode_client, CopyCodeAPIError


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

            # Check if phone is manually set to inactive
            if not verified_phone.is_active:
                return JsonResponse({
                    'verified': False,
                    'expired': True,
                    'message': 'Phone verification is inactive. Please verify again.'
                })

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

            # Set cookie for user convenience (same as OTP verification)
            response = JsonResponse({
                'verified': True,
                'phone': full_phone,
                'message': 'Phone number is already verified.'
            })

            cookie_age = getattr(settings, 'OTP_SESSION_COOKIE_AGE', 86400)
            response.set_cookie(
                'verified_phone',
                full_phone,
                max_age=cookie_age,
                httponly=False,  # Allow JavaScript access
                samesite='Strict'
            )

            return response

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
@require_http_methods(["GET"])
def check_copycode_balance(request):
    """Check CopyCode API balance for admin monitoring"""
    try:
        # Check if user has permission (you can add more sophisticated auth here)
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        try:
            balance_data = copycode_client.check_balance()

            return JsonResponse({
                'success': True,
                'provider': 'copycode',
                'balance': balance_data.get('balance', 0),
                'timestamp': timezone.now().isoformat()
            })

        except CopyCodeAPIError as e:
            return JsonResponse({
                'success': False,
                'error': f'CopyCode API Error: {str(e)}'
            }, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_otp(request):
    """Send OTP to phone number using CopyCode API"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        country_code = data.get('country_code', '+60')

        if not phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)

        # Use CopyCode API for OTP
        return _send_otp_copycode(request, phone, country_code)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




def _send_otp_copycode(request, phone, country_code):
    """Send OTP using CopyCode API"""
    try:
        # Validate phone number format using CopyCode client
        is_valid, error_msg = copycode_client.validate_phone_format(phone, country_code)
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)

        # Create normalized full phone number for our database
        full_phone = normalize_phone_number(phone, country_code)

        # Generate 6-digit OTP code
        otp_code = generate_otp()

        # Clean up old VALID (not expired) OTP sessions for this phone
        # Expired OTPs should remain is_used=False to show "Expired" status
        from decouple import config
        expiry_minutes = int(config('OTP_EXPIRY_MINUTES', default=5))
        cutoff_time = timezone.now() - timezone.timedelta(minutes=expiry_minutes)

        # Only mark valid (not expired) OTPs as used to prevent multiple valid OTPs
        OTPSession.objects.filter(
            phone_number=full_phone,
            is_used=False,
            created_at__gt=cutoff_time  # Only OTPs that are still valid
        ).update(is_used=True)

        # Send OTP via CopyCode API
        try:
            response_data = copycode_client.send_otp(phone, country_code, otp_code)

            # Create new OTP session with generated code
            otp_session = OTPSession.objects.create(
                phone_number=full_phone,
                otp_code=otp_code,
                ip_address=get_client_ip(request)
            )

            # Get configured expiry time
            expiry_minutes = int(config('OTP_EXPIRY_MINUTES', default=5))

            return JsonResponse({
                'success': True,
                'message': f'OTP sent to {full_phone} via WhatsApp',
                'expires_in': expiry_minutes * 60  # convert to seconds
            })

        except CopyCodeAPIError as e:
            return JsonResponse({'error': f'CopyCode Error: {str(e)}'}, status=400)

    except Exception as e:
        return JsonResponse({'error': f'Send OTP error: {str(e)}'}, status=500)




@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """Verify OTP using CopyCode and mark phone as verified"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        otp_code = data.get('otp')
        country_code = data.get('country_code', '+60')

        if not phone or not otp_code:
            return JsonResponse({'error': 'Phone number and OTP required'}, status=400)

        # Use CopyCode for OTP verification
        return _verify_otp_copycode(request, phone, otp_code, country_code)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _verify_otp_copycode(request, phone, otp_code, country_code):
    """Verify OTP using local verification (CopyCode)"""
    try:
        # Validate OTP code format (should be 6 digits for CopyCode)
        if not otp_code or not otp_code.isdigit() or len(otp_code) != 6:
            return JsonResponse({'error': 'OTP code must be 6 digits'}, status=400)

        # Create normalized full phone number for our database
        full_phone = normalize_phone_number(phone, country_code)

        # Find the OTP session with matching code
        try:
            otp_session = OTPSession.objects.filter(
                phone_number=full_phone,
                otp_code=otp_code,
                is_used=False
            ).order_by('-created_at').first()

            if not otp_session:
                return JsonResponse({'error': 'Invalid OTP code or session not found. Please request a new OTP.'}, status=400)

            if otp_session.is_expired():
                return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)

            # OTP verification successful
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

            cookie_age = getattr(settings, 'OTP_SESSION_COOKIE_AGE', 86400)
            response.set_cookie(
                'verified_phone',
                full_phone,
                max_age=cookie_age,
                httponly=False,  # Allow JavaScript access for form pre-fill
                samesite='Strict'
            )

            return response

        except Exception as e:
            return JsonResponse({'error': 'Verification failed'}, status=500)

    except Exception as e:
        return JsonResponse({'error': f'CopyCode verification error: {str(e)}'}, status=500)



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

            # Check if phone is manually set to inactive
            if not verified_phone.is_active:
                return JsonResponse({'error': 'Phone verification is inactive. Please verify again.'}, status=403)

            if verified_phone.is_expired():
                # Mark as inactive and return error
                verified_phone.is_active = False
                verified_phone.save()
                return JsonResponse({'error': 'Phone verification expired. Please verify again.'}, status=403)
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

            # Log the calculation for analytics
            CalculationLog.objects.create(
                phone_number=verified_phone.phone_number,
                brand=calculation_data['brand'],
                model=calculation_data['model'],
                variant=calculation_data['variant'],
                year=calculation_data['year'],
                user_mileage=calculation_data.get('user_mileage'),
                estimated_price=result_data.get('estimated_market_price'),
                final_price=result_data.get('adjusted_price'),
                total_reduction_percent=result_data.get('total_reduction_percentage', 0),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

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