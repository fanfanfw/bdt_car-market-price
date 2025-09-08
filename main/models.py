from django.db import models
from django.utils import timezone
from datetime import timedelta


class Category(models.Model):
    """Category reference table"""
    name = models.CharField(max_length=100, unique=True)
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


class CarStandard(models.Model):
    """Reference table for standardized car data"""
    brand_norm = models.CharField(max_length=100)
    model_group_norm = models.CharField(max_length=100)
    model_norm = models.CharField(max_length=100)
    variant_norm = models.CharField(max_length=100)
    model_group_raw = models.CharField(max_length=100, null=True, blank=True)
    model_raw = models.CharField(max_length=100, null=True, blank=True)
    variant_raw = models.CharField(max_length=100, null=True, blank=True)
    variant_raw2 = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cars_standard'
        indexes = [
            models.Index(fields=['brand_norm', 'model_norm', 'variant_norm']),
        ]

    def __str__(self):
        return f"{self.brand_norm} {self.model_norm} {self.variant_norm}"


class CarUnified(models.Model):
    """Unified car data from multiple sources"""
    SOURCE_CHOICES = [
        ('carlistmy', 'CarlistMY'),
        ('mudahmy', 'MudahMY'),
    ]
    
    # Reference to standard car and category
    cars_standard = models.ForeignKey(CarStandard, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    
    # Source information
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    listing_url = models.TextField()
    
    # Car details (normalized from both sources)
    condition = models.CharField(max_length=50, null=True, blank=True)
    brand = models.CharField(max_length=100)
    model_group = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100)
    variant = models.CharField(max_length=100, null=True, blank=True)
    
    # Car specifications
    year = models.IntegerField(null=True, blank=True)
    mileage = models.IntegerField(null=True, blank=True)
    transmission = models.CharField(max_length=50, null=True, blank=True)
    seat_capacity = models.CharField(max_length=10, null=True, blank=True)
    engine_cc = models.CharField(max_length=50, null=True, blank=True)
    fuel_type = models.CharField(max_length=50, null=True, blank=True)
    
    # Pricing
    price = models.IntegerField(null=True, blank=True)
    
    # Location and contact
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Additional info
    information_ads = models.TextField(null=True, blank=True)
    images = models.TextField(null=True, blank=True)  # JSON field for image URLs
    
    # Status tracking
    status = models.CharField(max_length=20, default='active')
    ads_tag = models.CharField(max_length=50, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)
    sold_at = models.DateTimeField(null=True, blank=True)
    last_status_check = models.DateTimeField(null=True, blank=True)
    information_ads_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cars_unified'
        indexes = [
            models.Index(fields=['source', 'listing_url']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['price']),
            models.Index(fields=['year']),
            models.Index(fields=['last_scraped_at']),
            models.Index(fields=['information_ads_date']),
        ]
        unique_together = [['source', 'listing_url']]

    def __str__(self):
        return f"{self.source}: {self.brand} {self.model} - {self.price}"


class PriceHistoryUnified(models.Model):
    """Unified price history from multiple sources"""
    # Source information
    source = models.CharField(max_length=20, choices=CarUnified.SOURCE_CHOICES, default='carlistmy')
    
    # Price tracking
    old_price = models.IntegerField(null=True, blank=True)
    new_price = models.IntegerField()
    
    # Source reference for tracking
    listing_url = models.TextField()
    
    # Timestamps
    changed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'price_history_unified'
        indexes = [
            models.Index(fields=['listing_url', 'changed_at']),
            models.Index(fields=['changed_at']),
        ]
        unique_together = [['listing_url', 'changed_at']]

    def __str__(self):
        return f"{self.source} - {self.listing_url} - {self.old_price} → {self.new_price}"


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
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'otp_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['otp_code']),
            models.Index(fields=['is_used']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.otp_code} - {self.created_at}"

    def is_expired(self):
        """Check if OTP has expired (1 minute)"""
        expiry_time = self.created_at + timedelta(minutes=1)
        return timezone.now() > expiry_time

    def is_valid(self):
        """Check if OTP is still valid and unused"""
        return not self.is_used and not self.is_expired()


# Configuration Models for Dynamic Pricing System

class PricingConfiguration(models.Model):
    """Main configuration container with versioning"""
    version = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100, help_text="Configuration name for identification")
    description = models.TextField(blank=True, null=True)
    
    # Status
    is_draft = models.BooleanField(default=True, help_text="True = Draft, False = Published")
    is_active = models.BooleanField(default=False, help_text="Currently active configuration")
    
    # Layer caps
    layer1_max_reduction = models.DecimalField(max_digits=5, decimal_places=2, default=15.0, 
                                              help_text="Maximum reduction percentage for Layer 1 (Mileage)")
    layer2_max_reduction = models.DecimalField(max_digits=5, decimal_places=2, default=70.0,
                                              help_text="Maximum reduction percentage for Layer 2 (Conditions)")
    total_max_reduction = models.DecimalField(max_digits=5, decimal_places=2, default=85.0,
                                             help_text="Maximum total reduction percentage")
    
    # Audit fields
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_configs')
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_configs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pricing_configurations'
        ordering = ['-version']

    def __str__(self):
        status = "Published" if not self.is_draft else "Draft"
        active = " (Active)" if self.is_active else ""
        return f"v{self.version} - {self.name} [{status}]{active}"

    def publish(self, user=None):
        """Publish this configuration and deactivate others"""
        if self.is_draft:
            # Deactivate all other active configs
            PricingConfiguration.objects.filter(is_active=True).update(is_active=False)
            
            # Activate this config
            self.is_draft = False
            self.is_active = True
            self.published_at = timezone.now()
            if user:
                self.updated_by = user
            self.save()

    def get_total_conditions_max(self):
        """Calculate theoretical maximum from all conditions"""
        return sum(cond.get_max_percentage() for cond in self.layer2_conditions.all())


class Layer1Configuration(models.Model):
    """Layer 1: Mileage-based reduction configuration"""
    config = models.OneToOneField(PricingConfiguration, on_delete=models.CASCADE, related_name='layer1_config')
    
    # Mileage calculation parameters
    mileage_threshold_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.0,
                                                   help_text="Mileage threshold percentage (e.g., 10 = every 10% excess)")
    reduction_per_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=2.0,
                                                 help_text="Reduction percentage per threshold (e.g., 2 = 2% reduction)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'layer1_configurations'

    def __str__(self):
        return f"Layer 1 Config v{self.config.version}: {self.reduction_per_threshold}% per {self.mileage_threshold_percent}%"

    def calculate_reduction(self, user_mileage, avg_mileage):
        """Calculate Layer 1 reduction percentage"""
        if user_mileage <= avg_mileage:
            return 0.0
        
        mileage_diff_percent = ((user_mileage - avg_mileage) / avg_mileage) * 100
        reduction = (mileage_diff_percent / float(self.mileage_threshold_percent)) * float(self.reduction_per_threshold)
        
        # Apply cap
        max_reduction = float(self.config.layer1_max_reduction)
        return min(reduction, max_reduction)


class Layer2Condition(models.Model):
    """Layer 2: Condition assessment categories"""
    config = models.ForeignKey(PricingConfiguration, on_delete=models.CASCADE, related_name='layer2_conditions')
    
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Exterior Condition')")
    field_name = models.CharField(max_length=50, help_text="Form field name (auto-generated)")
    icon_class = models.CharField(max_length=50, default='fas fa-cog', help_text="Font Awesome icon class")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'layer2_conditions'
        ordering = ['order', 'name']
        unique_together = [['config', 'field_name']]

    def __str__(self):
        return f"{self.name} (v{self.config.version})"

    def save(self, *args, **kwargs):
        # Auto-generate field_name from name
        if not self.field_name:
            import re
            self.field_name = re.sub(r'[^a-zA-Z0-9]', '_', self.name.lower()).strip('_')
        super().save(*args, **kwargs)

    def get_max_percentage(self):
        """Get maximum reduction percentage from all options"""
        return max((option.percentage for option in self.options.all()), default=0)


class ConditionOption(models.Model):
    """Options for each condition (radio button choices)"""
    condition = models.ForeignKey(Layer2Condition, on_delete=models.CASCADE, related_name='options')
    
    label = models.CharField(max_length=100, help_text="Display label (e.g., 'Excellent', 'Good')")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Reduction percentage")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'condition_options'
        ordering = ['order']
        unique_together = [['condition', 'label']]

    def __str__(self):
        return f"{self.label} (-{self.percentage}%)"


class ConfigurationHistory(models.Model):
    """History log for configuration changes"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('published', 'Published'),
        ('deactivated', 'Deactivated'),
        ('deleted', 'Deleted'),
    ]
    
    config = models.ForeignKey(PricingConfiguration, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, null=True)
    
    # Snapshot of key data
    snapshot_data = models.JSONField(default=dict, help_text="JSON snapshot of configuration")
    
    # Audit fields
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'configuration_history'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.config.name} v{self.config.version} - {self.get_action_display()} by {self.user}"
