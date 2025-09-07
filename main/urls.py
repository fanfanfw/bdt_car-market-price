from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('result/', views.result, name='result'),
    
    # Car data APIs
    path('api/categories/', views.get_categories, name='get_categories'),
    path('api/brands/', views.get_brands, name='get_brands'),
    path('api/models/', views.get_models, name='get_models'),
    path('api/variants/', views.get_variants, name='get_variants'),
    path('api/years/', views.get_years, name='get_years'),
    
    # OTP system APIs
    path('api/check-phone/', views.check_phone_status, name='check_phone_status'),
    path('api/send-otp/', views.send_otp, name='send_otp'),
    path('api/verify-otp/', views.verify_otp, name='verify_otp'),
    path('api/get-results/', views.get_secure_results, name='get_secure_results'),
]