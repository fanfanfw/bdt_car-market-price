"""
CopyCode API Client for WhatsApp OTP integration
"""
import requests
import json
from decouple import config
from typing import Tuple, Optional


class CopyCodeAPIError(Exception):
    """Custom exception for CopyCode API errors"""
    pass


class CopyCodeClient:
    """CopyCode API client for sending WhatsApp OTP"""

    def __init__(self):
        self.base_url = config('COPYCODE_BASE_URL', default='https://copycode.cc/api')
        self.api_token = config('COPYCODE_API_TOKEN')

        if not self.api_token:
            raise CopyCodeAPIError("COPYCODE_API_TOKEN not configured in environment")

        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def format_phone_number(self, phone: str, country_code: str) -> str:
        """
        Format phone number for CopyCode API
        CopyCode expects format: 60812341234 (without + and leading 0)
        """
        import re

        # Remove all non-digits
        cleaned_phone = re.sub(r'[^\d]', '', phone)
        country_num = re.sub(r'[^\d]', '', country_code)

        # Remove leading 0 if present
        if cleaned_phone.startswith('0'):
            cleaned_phone = cleaned_phone[1:]

        # Combine country code + phone number
        full_number = country_num + cleaned_phone

        return full_number

    def check_balance(self) -> dict:
        """
        Check account balance
        Returns: {"balance": 9768}
        """
        try:
            url = f"{self.base_url}/balance"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                raise CopyCodeAPIError(f"Balance check failed: HTTP {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            raise CopyCodeAPIError("Balance check timeout")
        except requests.exceptions.RequestException as e:
            raise CopyCodeAPIError(f"Balance check network error: {str(e)}")
        except json.JSONDecodeError:
            raise CopyCodeAPIError("Invalid JSON response from balance check")

    def send_otp(self, phone: str, country_code: str, otp_code: str) -> dict:
        """
        Send OTP code via WhatsApp

        Args:
            phone: Phone number (e.g., "812341234")
            country_code: Country code (e.g., "+60")
            otp_code: 6-digit OTP code

        Returns:
            {"message": "The code will be sent immediately to 6289525521887"}
        """
        try:
            # Format phone number
            formatted_phone = self.format_phone_number(phone, country_code)

            # Validate OTP code
            if not otp_code.isdigit() or len(otp_code) != 6:
                raise CopyCodeAPIError("OTP code must be exactly 6 digits")

            # Prepare payload
            payload = {
                "code": int(otp_code),
                "to": int(formatted_phone)
            }

            url = f"{self.base_url}/send"
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Send OTP failed: HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    if 'message' in error_detail:
                        error_msg += f" - {error_detail['message']}"
                except:
                    error_msg += f" - {response.text}"

                raise CopyCodeAPIError(error_msg)

        except requests.exceptions.Timeout:
            raise CopyCodeAPIError("Send OTP timeout")
        except requests.exceptions.RequestException as e:
            raise CopyCodeAPIError(f"Send OTP network error: {str(e)}")
        except json.JSONDecodeError:
            raise CopyCodeAPIError("Invalid JSON response from send OTP")
        except ValueError as e:
            raise CopyCodeAPIError(f"Invalid data format: {str(e)}")

    def validate_phone_format(self, phone: str, country_code: str) -> Tuple[bool, str]:
        """
        Validate phone number format for supported countries

        Returns:
            (is_valid, error_message)
        """
        import re

        # Normalize inputs
        cleaned_phone = re.sub(r'[^\d]', '', phone)
        country_num = re.sub(r'[^\d]', '', country_code)

        # Remove leading 0
        if cleaned_phone.startswith('0'):
            cleaned_phone = cleaned_phone[1:]

        if country_num == '60':
            # Malaysia: should be 8-10 digits after country code
            if not re.match(r'^\d{8,10}$', cleaned_phone):
                return False, "Invalid Malaysian phone number format (should be 8-10 digits)"
        elif country_num == '62':
            # Indonesia: should be 8-12 digits after country code
            if not re.match(r'^\d{8,12}$', cleaned_phone):
                return False, "Invalid Indonesian phone number format (should be 8-12 digits)"
        else:
            return False, f"Unsupported country code: +{country_num}. Only +60 (Malaysia) and +62 (Indonesia) are supported"

        return True, ""


# Singleton instance
copycode_client = CopyCodeClient()