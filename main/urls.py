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
    
    # Admin pricing configuration URLs
    path('panel/pricing-config/', views.pricing_config_list, name='pricing_config_list'),
    path('panel/pricing-config/create/', views.pricing_config_create, name='pricing_config_create'),
    path('panel/pricing-config/<int:config_id>/', views.pricing_config_detail, name='pricing_config_detail'),
    path('panel/pricing-config/<int:config_id>/edit/', views.pricing_config_edit, name='pricing_config_edit'),
    path('panel/pricing-config/<int:config_id>/publish/', views.pricing_config_publish, name='pricing_config_publish'),
    path('panel/pricing-config/<int:config_id>/delete/', views.pricing_config_delete, name='pricing_config_delete'),
    path('panel/pricing-config/<int:config_id>/clone/', views.pricing_config_clone, name='pricing_config_clone'),
    
    # Condition management URLs
    path('panel/pricing-config/<int:config_id>/conditions/', views.condition_manage, name='condition_manage'),
    path('panel/pricing-config/<int:config_id>/conditions/add/', views.condition_add, name='condition_add'),
    path('panel/pricing-config/<int:config_id>/conditions/<int:condition_id>/edit/', views.condition_edit, name='condition_edit'),
    path('panel/pricing-config/<int:config_id>/conditions/<int:condition_id>/delete/', views.condition_delete, name='condition_delete'),
]