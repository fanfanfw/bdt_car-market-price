from django.db import models
from django.utils import timezone
from datetime import timedelta


class Category(models.Model):
    """Category reference table"""
    name = models.CharField(max_length=100, unique=True)
    reduction_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Reduction percentage for this category (0-100%)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name


class BrandCategory(models.Model):
    """Brand to category mapping table"""
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brand_categories'
        unique_together = [['brand', 'category']]

    def __str__(self):
        return f"{self.brand} - {self.category.name}"


# CarStandard, CarUnified, and PriceHistoryUnified models removed
# These tables will be accessed via FastAPI endpoints only


class VerifiedPhone(models.Model):
    """Phone verification tracking for OTP system"""
    phone_number = models.CharField(
        max_length=15, 
        unique=True,
        help_text='Phone number with country code (+60xxxxxxxxx or +62xxxxxxxxx)'
    )
    verified_at = models.DateTimeField(
        auto_now_add=True,
        help_text='First time verified'
    )
    last_accessed = models.DateTimeField(
        auto_now=True,
        help_text='Last time accessed'
    )
    access_count = models.PositiveIntegerField(
        default=1,
        help_text='Number of times accessed'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether phone is still active'
    )
    user_agent = models.TextField(
        blank=True, 
        null=True,
        help_text='Browser/device info'
    )
    ip_address = models.GenericIPAddressField(
        blank=True, 
        null=True,
        help_text='Last IP address'
    )

    class Meta:
        db_table = 'verified_phones'
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['phone_number'], name='verified_ph_phone_n_317bb1_idx'),
            models.Index(fields=['verified_at'], name='verified_ph_verifie_13dc2c_idx'),
            models.Index(fields=['last_accessed'], name='verified_ph_last_ac_1c534c_idx'),
            models.Index(fields=['is_active'], name='verified_ph_is_acti_852b26_idx'),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.verified_at.strftime('%Y-%m-%d')}"

    def is_expired(self):
        """Check if phone verification has expired"""
        from django.conf import settings
        expiry_days = getattr(settings, 'PHONE_VERIFICATION_EXPIRY_DAYS', 30)
        expiry_date = self.verified_at + timedelta(days=expiry_days)
        return timezone.now() > expiry_date

    def extend_expiry(self):
        """Extend the expiry by updating verified_at to now"""
        self.verified_at = timezone.now()
        self.is_active = True
        self.save()


class OTPSession(models.Model):
    """Temporary OTP sessions (1 minute validity)"""
    phone_number = models.CharField(max_length=15)
    verification_id = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'otp_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['verification_id']),
            models.Index(fields=['is_used']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.verification_id} - {self.created_at}"

    def is_expired(self):
        """Check if OTP has expired (1 minute)"""
        expiry_time = self.created_at + timedelta(minutes=1)
        return timezone.now() > expiry_time

    def is_valid(self):
        """Check if OTP is still valid and unused"""
        return not self.is_used and not self.is_expired()


# Simplified Pricing Configuration Models

class MileageConfiguration(models.Model):
    """Layer 1: Mileage-based reduction configuration"""
    
    # Mileage calculation parameters
    threshold_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.0,
        help_text="Mileage threshold percentage (e.g., 10 = every 10% excess)"
    )
    reduction_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.0,
        help_text="Reduction percentage per threshold (e.g., 2 = 2% reduction)"
    )
    max_reduction_cap = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.0,
        help_text="Maximum reduction percentage cap for Layer 1 (Mileage)"
    )
    layer2_max_cap = models.DecimalField(
        max_digits=5, decimal_places=2, default=70.0,
        help_text="Maximum reduction percentage cap for Layer 2 (Conditions)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mileage_configurations'

    def __str__(self):
        return f"Mileage Config: {self.reduction_percent}% per {self.threshold_percent}% (cap: {self.max_reduction_cap}%)"

    def calculate_reduction(self, user_mileage, avg_mileage):
        """Calculate Layer 1 reduction percentage"""
        if user_mileage <= avg_mileage:
            return 0.0
        
        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
        reduction = (mileage_diff_percent / float(self.threshold_percent)) * float(self.reduction_percent)
        
        # Apply cap
        return min(reduction, float(self.max_reduction_cap))


class VehicleConditionCategory(models.Model):
    """Layer 2: Fixed vehicle condition categories"""
    
    CATEGORY_CHOICES = [
        ('exterior_condition', 'Exterior Condition'),
        ('interior_condition', 'Interior Condition'),
        ('mechanical_condition', 'Mechanical Condition'),
        ('accident_history', 'Accident History'),
        ('service_history', 'Service History'),
        ('number_of_owners', 'Number of Owners'),
        ('tires_brakes', 'Tires & Brakes'),
        ('modifications', 'Modifications'),
        ('market_demand', 'Market Demand'),
        ('brand_category', 'Brand Category'),
        ('price_tier', 'Price Tier'),
    ]
    
    category_key = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_condition_categories'
        ordering = ['order', 'display_name']

    def __str__(self):
        return self.display_name


class ConditionOption(models.Model):
    """Options for each condition category"""
    category = models.ForeignKey(VehicleConditionCategory, on_delete=models.CASCADE, related_name='options')
    
    label = models.CharField(max_length=100, help_text="Display label (e.g., 'Excellent', 'Good')")
    reduction_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Reduction percentage for this option"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'condition_options'
        ordering = ['category__order', 'order']
        unique_together = [['category', 'label']]

    def __str__(self):
        return f"{self.category.display_name}: {self.label} (-{self.reduction_percentage}%)"


class PriceTier(models.Model):
    """Price tier configuration for automatic price-based categorization"""
    name = models.CharField(max_length=100, unique=True, help_text="Tier name (e.g., 'Budget', 'Mid-range', 'Premium')")
    min_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Minimum price for this tier (RM)")
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Maximum price for this tier (RM), leave blank for unlimited")
    reduction_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Reduction percentage for this price tier (0-100%)")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'price_tiers'
        ordering = ['order', 'min_price']

    def __str__(self):
        if self.max_price:
            return f"{self.name} (RM {self.min_price:,.0f} - RM {self.max_price:,.0f})"
        else:
            return f"{self.name} (RM {self.min_price:,.0f}+)"

    def price_range_display(self):
        """Display formatted price range"""
        if self.max_price:
            return f"RM {self.min_price:,.0f} - RM {self.max_price:,.0f}"
        else:
            return f"RM {self.min_price:,.0f}+"

    @classmethod
    def get_tier_for_price(cls, price):
        """Get the appropriate price tier for a given price"""
        try:
            price = float(price)
            tiers = cls.objects.filter(is_active=True).order_by('min_price')

            for tier in tiers:
                if price >= float(tier.min_price):
                    if tier.max_price is None or price <= float(tier.max_price):
                        return tier

            # If no tier matches, return None
            return None
        except (ValueError, TypeError):
            return None


class CalculationLog(models.Model):
    """Track all price calculations for analytics"""
    phone_number = models.CharField(max_length=15, help_text='Phone number of user who made calculation')
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    variant = models.CharField(max_length=200)
    year = models.PositiveIntegerField()
    user_mileage = models.PositiveIntegerField(null=True, blank=True)
    estimated_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_reduction_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'calculation_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['brand', 'model']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.brand} {self.model} ({self.created_at.date()})"

    @classmethod
    def get_today_count(cls):
        """Get count of calculations made today"""
        today = timezone.now().date()
        return cls.objects.filter(created_at__date=today).count()
