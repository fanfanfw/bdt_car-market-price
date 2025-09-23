# Import all views to maintain backward compatibility
from .public import index, result
from .api import (
    get_categories, get_brands_api, get_models_api, get_variants_api, get_years_api,
    car_data_api, car_detail_api
)
from .auth import (
    check_phone_status, send_otp, verify_otp, get_secure_results, check_copycode_balance
)
from .admin import (
    CustomAdminLoginView, admin_dashboard_view, admin_logout_view,
    formula_config_edit, condition_categories_manage, condition_option_edit,
    condition_option_add, condition_option_delete, car_data_view,
    verified_phones_view, verified_phones_api, verified_phone_detail_api,
    toggle_phone_status, otp_sessions_view, otp_sessions_api,
    otp_session_detail_api, categories_management_view, category_create,
    category_edit, category_delete, category_brands_api, brand_classification_view,
    brands_data_api, assign_brand_to_category, reassign_brand_to_category,
    remove_brand_classification, get_unclassified_brands_api,
    price_tiers_management_view, price_tier_create, price_tier_edit, price_tier_delete
)
from .utils import (
    get_mileage_config, get_car_statistics, get_client_ip,
    normalize_phone_number, generate_otp, is_staff_user,
    export_verified_phones, export_otp_sessions
)

# Maintain backward compatibility
__all__ = [
    # Public views
    'index', 'result',

    # API views
    'get_categories', 'get_brands_api', 'get_models_api', 'get_variants_api',
    'get_years_api', 'car_data_api', 'car_detail_api',

    # Auth views
    'check_phone_status', 'send_otp', 'verify_otp', 'get_secure_results', 'check_copycode_balance',

    # Admin views
    'CustomAdminLoginView', 'admin_dashboard_view', 'admin_logout_view',
    'formula_config_edit', 'condition_categories_manage', 'condition_option_edit',
    'condition_option_add', 'condition_option_delete', 'car_data_view',
    'verified_phones_view', 'verified_phones_api', 'verified_phone_detail_api',
    'toggle_phone_status', 'otp_sessions_view', 'otp_sessions_api',
    'otp_session_detail_api', 'categories_management_view', 'category_create',
    'category_edit', 'category_delete', 'category_brands_api', 'brand_classification_view',
    'brands_data_api', 'assign_brand_to_category', 'reassign_brand_to_category',
    'remove_brand_classification', 'get_unclassified_brands_api',
    'price_tiers_management_view', 'price_tier_create', 'price_tier_edit', 'price_tier_delete',

    # Utilities
    'get_mileage_config', 'get_car_statistics', 'get_client_ip',
    'normalize_phone_number', 'generate_otp', 'is_staff_user',
    'export_verified_phones', 'export_otp_sessions'
]