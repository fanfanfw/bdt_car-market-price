from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('result/', views.result, name='result'),
    
    # Car data APIs
    path('api/categories/', views.get_categories, name='get_categories'),
    path('api/brands/', views.get_brands_api, name='get_brands'),
    path('api/models/', views.get_models_api, name='get_models'),
    path('api/variants/', views.get_variants_api, name='get_variants'),
    path('api/years/', views.get_years_api, name='get_years'),
    
    # OTP system APIs
    path('api/check-phone/', views.check_phone_status, name='check_phone_status'),
    path('api/send-otp/', views.send_otp, name='send_otp'),
    path('api/verify-otp/', views.verify_otp, name='verify_otp'),
    path('api/get-results/', views.get_secure_results, name='get_secure_results'),
    path('api/check-balance/', views.check_copycode_balance, name='check_copycode_balance'),
    
    # Simplified admin configuration URLs
    path('panel/formula-config/', views.formula_config_edit, name='formula_config_edit'),
    path('panel/condition-categories/', views.condition_categories_manage, name='condition_categories_manage'),
    
    # Condition option management APIs
    path('api/condition-option/<int:option_id>/edit/', views.condition_option_edit, name='condition_option_edit'),
    path('api/condition-option/<int:option_id>/delete/', views.condition_option_delete, name='condition_option_delete'),
    path('api/condition-category/<int:category_id>/option/add/', views.condition_option_add, name='condition_option_add'),
    
    # Car data management
    path('panel/car-data/', views.car_data_view, name='car_data_view'),
    path('api/car-data/', views.car_data_api, name='car_data_api'),
    path('api/car-detail/<int:car_id>/', views.car_detail_api, name='car_detail_api'),
    
    # Verified phones management
    path('panel/verified-phones/', views.verified_phones_view, name='verified_phones_view'),
    path('api/verified-phones/', views.verified_phones_api, name='verified_phones_api'),
    path('api/verified-phone/<int:phone_id>/', views.verified_phone_detail_api, name='verified_phone_detail_api'),
    path('api/verified-phone/<int:phone_id>/toggle/', views.toggle_phone_status, name='toggle_phone_status'),
    
    # OTP sessions management
    path('panel/otp-sessions/', views.otp_sessions_view, name='otp_sessions_view'),
    path('api/otp-sessions/', views.otp_sessions_api, name='otp_sessions_api'),
    path('api/otp-session/<int:session_id>/', views.otp_session_detail_api, name='otp_session_detail_api'),
    
    # Categories management (Brand Categories System)
    path('panel/categories/', views.categories_management_view, name='categories_management_view'),
    path('api/category/create/', views.category_create, name='category_create'),
    path('api/category/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('api/category/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    path('api/category/<int:category_id>/brands/', views.category_brands_api, name='category_brands_api'),
    
    # Brand classification
    path('panel/brand-classification/', views.brand_classification_view, name='brand_classification_view'),
    path('api/brands-data/', views.brands_data_api, name='brands_data_api'),
    path('api/brand/assign/', views.assign_brand_to_category, name='assign_brand_to_category'),
    path('api/brand/reassign/', views.reassign_brand_to_category, name='reassign_brand_to_category'),
    path('api/brand/remove/', views.remove_brand_classification, name='remove_brand_classification'),
    path('api/unclassified-brands/', views.get_unclassified_brands_api, name='get_unclassified_brands_api'),
    
    # Price Tiers management
    path('panel/price-tiers/', views.price_tiers_management_view, name='price_tiers_management_view'),
    path('api/price-tier/create/', views.price_tier_create, name='price_tier_create'),
    path('api/price-tier/<int:tier_id>/edit/', views.price_tier_edit, name='price_tier_edit'),
    path('api/price-tier/<int:tier_id>/delete/', views.price_tier_delete, name='price_tier_delete'),
]