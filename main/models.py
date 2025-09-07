from django.db import models


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
