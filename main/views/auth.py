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
from decouple import config

from ..models import VerifiedPhone, OTPSession, CalculationLog
from .utils import (
    format_phone_number_for_message_central, normalize_phone_number,
    get_client_ip, get_car_statistics
)


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
@require_http_methods(["POST"])
def send_otp(request):
    """Send OTP to phone number using Message_Central API"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        country_code = data.get('country_code', '+60')

        if not phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)

        # Format phone number for Message_Central API
        country_code_formatted, mobile_number = format_phone_number_for_message_central(phone, country_code)

        if not country_code_formatted or not mobile_number:
            return JsonResponse({'error': 'Invalid phone number format. Use +62 for Indonesia or +60 for Malaysia'}, status=400)

        # Create normalized full phone number for our database
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

        # Get Message_Central API configuration from environment
        auth_token = config('MESSAGE_CENTRAL_AUTH_TOKEN', default=None)
        customer_id = config('MESSAGE_CENTRAL_CUSTOMER_ID', default=None)

        if not auth_token or not customer_id:
            return JsonResponse({'error': 'Message_Central API configuration not found'}, status=500)

        # Call Message_Central API to send OTP
        try:
            url = f"https://cpaas.messagecentral.com/verification/v3/send?countryCode={country_code_formatted}&customerId={customer_id}&flowType=WHATSAPP&mobileNumber={mobile_number}"

            headers = {
                'authToken': auth_token
            }

            response = requests.post(url, headers=headers, data={}, timeout=30)
            response_data = response.json()

            if response.status_code == 200 and response_data.get('responseCode') == 200:
                # Success - get verificationId from response
                verification_id = response_data.get('data', {}).get('verificationId')

                if not verification_id:
                    return JsonResponse({'error': 'No verification ID received from Message_Central'}, status=500)

                # Clean up old OTP sessions for this phone
                OTPSession.objects.filter(phone_number=full_phone, is_used=False).update(is_used=True)

                # Create new OTP session with verificationId
                otp_session = OTPSession.objects.create(
                    phone_number=full_phone,
                    verification_id=verification_id,
                    ip_address=get_client_ip(request)
                )

                return JsonResponse({
                    'success': True,
                    'message': f'OTP sent to {full_phone} via WhatsApp',
                    'verification_id': verification_id,
                    'expires_in': 60  # seconds
                })
            else:
                # Error from Message_Central
                error_message = response_data.get('message', 'Failed to send OTP')
                return JsonResponse({'error': f'Message_Central Error: {error_message}'}, status=400)

        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Request timeout. Please try again.'}, status=500)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'API error: {str(e)}'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """Verify OTP using Message_Central API and mark phone as verified"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        otp_code = data.get('otp')
        country_code = data.get('country_code', '+60')

        if not phone or not otp_code:
            return JsonResponse({'error': 'Phone number and OTP required'}, status=400)

        # Validate OTP code format (should be 4 digits)
        if not otp_code or not otp_code.isdigit() or len(otp_code) != 4:
            return JsonResponse({'error': 'OTP code must be 4 digits'}, status=400)

        # Format phone number for Message_Central API
        country_code_formatted, mobile_number = format_phone_number_for_message_central(phone, country_code)

        if not country_code_formatted or not mobile_number:
            return JsonResponse({'error': 'Invalid phone number format. Use +62 for Indonesia or +60 for Malaysia'}, status=400)

        # Create normalized full phone number for our database
        full_phone = normalize_phone_number(phone, country_code)

        # Find the OTP session with verificationId
        try:
            otp_session = OTPSession.objects.filter(
                phone_number=full_phone,
                is_used=False
            ).order_by('-created_at').first()

            if not otp_session:
                return JsonResponse({'error': 'No active OTP session found. Please request a new OTP.'}, status=400)

            if otp_session.is_expired():
                return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)

            # Get verificationId from our session
            verification_id = otp_session.verification_id

            # Get Message_Central API configuration from environment
            auth_token = config('MESSAGE_CENTRAL_AUTH_TOKEN', default=None)
            customer_id = config('MESSAGE_CENTRAL_CUSTOMER_ID', default=None)

            if not auth_token or not customer_id:
                return JsonResponse({'error': 'Message_Central API configuration not found'}, status=500)

            # Call Message_Central API to validate OTP
            try:
                url = f"https://cpaas.messagecentral.com/verification/v3/validateOtp?countryCode={country_code_formatted}&mobileNumber={mobile_number}&verificationId={verification_id}&customerId={customer_id}&code={otp_code}"

                headers = {
                    'authToken': auth_token
                }

                response = requests.get(url, headers=headers, timeout=30)
                response_data = response.json()

                if response.status_code == 200 and response_data.get('responseCode') == 200:
                    # Check verification status
                    verification_status = response_data.get('data', {}).get('verificationStatus')

                    if verification_status == 'VERIFICATION_COMPLETED':
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
                    else:
                        # OTP verification failed
                        return JsonResponse({'error': 'Invalid OTP code. Please try again.'}, status=400)
                else:
                    # Error from Message_Central
                    error_message = response_data.get('message', 'OTP verification failed')
                    return JsonResponse({'error': f'Verification Error: {error_message}'}, status=400)

            except requests.exceptions.Timeout:
                return JsonResponse({'error': 'Request timeout. Please try again.'}, status=500)
            except requests.exceptions.RequestException as e:
                return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
            except Exception as e:
                return JsonResponse({'error': f'API error: {str(e)}'}, status=500)

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