"""
FastAPI Client Service for Django
===============================

HTTP client untuk komunikasi dengan FastAPI backend.
Mengganti direct database access dengan API calls.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
import json

logger = logging.getLogger(__name__)

# Configuration
FASTAPI_BASE_URL = getattr(settings, 'FASTAPI_BASE_URL', 'http://localhost:8000/api')
DJANGO_SECRET_KEY = getattr(settings, 'DJANGO_SECRET_KEY', 'django-unlimited-access')
REQUEST_TIMEOUT = getattr(settings, 'API_REQUEST_TIMEOUT', 30)

class FastAPIClient:
    """HTTP client for FastAPI communication"""
    
    def __init__(self):
        self.base_url = FASTAPI_BASE_URL
        self.headers = {
            'Content-Type': 'application/json',
            'X-Django-Key': DJANGO_SECRET_KEY
        }
        self.timeout = REQUEST_TIMEOUT
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to FastAPI with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.ConnectionError:
            logger.error(f"FastAPI connection failed: {url}")
            raise APIConnectionError(f"Cannot connect to FastAPI at {url}")
        
        except requests.exceptions.Timeout:
            logger.error(f"FastAPI request timeout: {url}")
            raise APITimeoutError(f"Request timeout for {url}")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"FastAPI HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise APINotFoundError("Resource not found")
            elif e.response.status_code >= 500:
                raise APIServerError("FastAPI server error")
            else:
                raise APIClientError(f"HTTP {e.response.status_code}: {e.response.text}")
        
        except Exception as e:
            logger.error(f"Unexpected API error: {str(e)}")
            raise APIError(f"Unexpected error: {str(e)}")
    
    def get_brands(self) -> List[str]:
        """Get all brands"""
        cache_key = "fastapi_brands"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        result = self._make_request('GET', '/django/brands')
        cache.set(cache_key, result, 300)  # Cache for 5 minutes
        return result
    
    def get_models(self, brand: str) -> List[str]:
        """Get models for specific brand"""
        cache_key = f"fastapi_models_{brand}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        result = self._make_request('GET', '/django/models', params={'brand': brand})
        cache.set(cache_key, result, 300)
        return result
    
    def get_variants(self, brand: str, model: str) -> List[str]:
        """Get variants for specific brand and model"""
        cache_key = f"fastapi_variants_{brand}_{model}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        result = self._make_request('GET', '/django/variants', params={
            'brand': brand,
            'model': model
        })
        cache.set(cache_key, result, 300)
        return result
    
    def get_years(self, brand: str, model: str, variant: str) -> List[int]:
        """Get years for specific brand, model, and variant"""
        cache_key = f"fastapi_years_{brand}_{model}_{variant}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        result = self._make_request('GET', '/django/years', params={
            'brand': brand,
            'model': model,
            'variant': variant
        })
        cache.set(cache_key, result, 300)
        return result
    
    def get_car_records(
        self,
        draw: int = 1,
        start: int = 0,
        length: int = 10,
        search: Optional[str] = None,
        order_column: Optional[str] = None,
        order_direction: str = "asc",
        source_filter: Optional[str] = None,
        year_filter: Optional[str] = None,
        price_filter: Optional[str] = None,
        brand_filter: Optional[str] = None,
        model_filter: Optional[str] = None,
        variant_filter: Optional[str] = None,
        year_value: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get car records for DataTables"""
        params = {
            'draw': draw,
            'start': start,
            'length': length,
            'order_direction': order_direction
        }
        
        if search:
            params['search'] = search
        if order_column:
            params['order_column'] = order_column
        if source_filter:
            params['source_filter'] = source_filter
        if year_filter:
            params['year_filter'] = year_filter
        if price_filter:
            params['price_filter'] = price_filter
        if brand_filter:
            params['brand_filter'] = brand_filter
        if model_filter:
            params['model_filter'] = model_filter
        if variant_filter:
            params['variant_filter'] = variant_filter
        if year_value:
            params['year_value'] = year_value
        
        return self._make_request('GET', '/django/cars', params=params)
    
    def get_car_detail(self, car_id: int, source: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed car information"""
        params = {'source': source} if source else None
        kwargs = {'params': params} if params else {}
        return self._make_request('GET', f'/django/car/{car_id}', **kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        cache_key = "fastapi_statistics"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        result = self._make_request('GET', '/django/statistics')
        cache.set(cache_key, result, 60)  # Cache for 1 minute
        return result
    
    def get_today_count(self) -> int:
        """Get today's data count"""
        result = self._make_request('GET', '/django/today-count')
        return result.get('count', 0)
    
    def get_price_estimation(
        self,
        brand: str,
        model: str,
        variant: str,
        year: int,
        mileage: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get price estimation for car"""
        params = {
            'brand': brand,
            'model': model,
            'variant': variant,
            'year': year
        }
        
        if mileage:
            params['mileage'] = mileage
        
        return self._make_request('POST', '/django/price-estimation', params=params)
    
    def get_brand_car_counts(self) -> Dict[str, int]:
        """Get car counts for all brands in bulk"""
        return self._make_request('GET', '/django/brand-car-counts')


# Custom Exception Classes
class APIError(Exception):
    """Base API error"""
    pass

class APIConnectionError(APIError):
    """Connection to FastAPI failed"""
    pass

class APITimeoutError(APIError):
    """Request timeout"""
    pass

class APINotFoundError(APIError):
    """Resource not found"""
    pass

class APIClientError(APIError):
    """Client error (4xx)"""
    pass

class APIServerError(APIError):
    """Server error (5xx)"""
    pass


# Global client instance
api_client = FastAPIClient()

# Convenience functions
def get_brands() -> List[str]:
    """Get all brands"""
    return api_client.get_brands()

def get_models(brand: str) -> List[str]:
    """Get models for specific brand"""
    return api_client.get_models(brand)

def get_variants(brand: str, model: str) -> List[str]:
    """Get variants for specific brand and model"""
    return api_client.get_variants(brand, model)

def get_years(brand: str, model: str, variant: str) -> List[int]:
    """Get years for specific brand, model, and variant"""
    return api_client.get_years(brand, model, variant)

def get_car_records(**kwargs) -> Dict[str, Any]:
    """Get car records for DataTables"""
    return api_client.get_car_records(**kwargs)

def get_car_detail(car_id: int, source: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed car information"""
    return api_client.get_car_detail(car_id, source)

def get_statistics() -> Dict[str, Any]:
    """Get dashboard statistics"""
    return api_client.get_statistics()

def get_today_count() -> int:
    """Get today's data count"""
    return api_client.get_today_count()

def get_price_estimation(**kwargs) -> Dict[str, Any]:
    """Get price estimation for car"""
    return api_client.get_price_estimation(**kwargs)

def get_unique_brands() -> List[str]:
    """Get all unique brands from cars_unified"""
    try:
        # We can reuse get_brands since it gets from cars_standard 
        # which should have same brands as cars_unified
        return api_client.get_brands()
    except APIError:
        return []

def get_brand_car_count(**kwargs) -> int:
    """Get car count for specific brand"""
    return api_client.get_brand_car_count(**kwargs)

def get_brand_car_counts() -> Dict[str, int]:
    """Get car counts for all brands in bulk"""
    return api_client.get_brand_car_counts()

def brand_exists(brand: str) -> bool:
    """Check if brand exists in cars_unified"""
    try:
        brands = api_client.get_brands()
        return brand in brands
    except APIError:
        return False
