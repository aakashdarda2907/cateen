from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('staff', 'Canteen Staff'),
        ('owner', 'Canteen Owner'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    # Fix reverse accessor conflict
    groups = models.ManyToManyField(
        Group,
        related_name="canteen_user_groups",  # Unique related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="canteen_user_permissions",  # Unique related_name
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='menu_items')
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    prep_time = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'),
        ('pending', 'Order Placed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),  # Changed from on_delivery
        ('delivered', 'Delivered'),  # New status for when delivery is complete
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    DELIVERY_CHOICES = (
        ('dine_in', 'Dine In'),
        ('delivery', 'Delivery'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='dine_in')
    delivery_address = models.ForeignKey('DeliveryAddress', on_delete=models.SET_NULL, null=True, blank=True)
    delivery_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_date = models.DateTimeField(default=timezone.now)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    upi_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.get_status_display()}"
    
    def mark_as_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Price at time of order
    
    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"
    
    @property
    def subtotal(self):
        return self.price * self.quantity

class Cart(models.Model):
    DELIVERY_CHOICES = (
        ('dine_in', 'Dine In'),
        ('delivery', 'Delivery'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='dine_in')
    delivery_address = models.ForeignKey('DeliveryAddress', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def discount(self):
        if not self.coupon:
            return 0
        return self.coupon.calculate_discount(self.total)
    
    @property
    def delivery_charge(self):
        return 10 if self.delivery_type == 'delivery' else 0
    
    @property
    def final_total(self):
        return self.total - self.discount + self.delivery_charge
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ('cart', 'menu_item')
    
    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"
    
    @property
    def subtotal(self):
        return self.menu_item.price * self.quantity

class PaymentInfo(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    upi_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.display_name} - {self.upi_id}"
    
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Make sure a user can only favorite an item once
        unique_together = ('user', 'menu_item')

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_one_time_use = models.BooleanField(default=False)
    is_first_order_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.code
    
    def is_valid(self, user, cart_total):
        now = timezone.now()
        
        # Check if coupon is active
        if not self.is_active:
            return False, "This coupon is not active"
            
        # Check validity period
        if self.valid_to and now > self.valid_to:
            return False, "This coupon has expired"
        
        if now < self.valid_from:
            return False, "This coupon is not valid yet"
            
        # Check minimum order value
        if cart_total < self.min_order_value:
            return False, f"Minimum order amount of ₹{self.min_order_value} required"
            
        # Check if first order only
        if self.is_first_order_only:
            if user.orders.filter(status='completed').exists():
                return False, "This coupon is for first orders only"
                
        # Check if user has already used one-time coupon
        if self.is_one_time_use:
            if CouponUsage.objects.filter(coupon=self, user=user).exists():
                return False, "You have already used this coupon"
                
        return True, "Coupon applied successfully"
        
    def calculate_discount(self, cart_total):
        if self.discount_type == 'percentage':
            discount = (cart_total * self.discount_value) / 100
            # Apply max discount cap if specified
            if self.max_discount and discount > self.max_discount:
                return self.max_discount
            return discount
        else:  # fixed discount
            return min(self.discount_value, cart_total)  # Don't exceed cart total


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_usages', null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        unique_together = ('coupon', 'user', 'order')
        
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code} for ₹{self.discount_amount}"
    
class DeliveryAddress(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('class1', 'Class 1'),
        ('class2', 'Class 2'),
        ('class3', 'Class 3'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES)
    address = models.TextField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_address_type_display()}: {self.address[:20]}..."
        
    def save(self, *args, **kwargs):
        # If this is set as default, unset other defaults for this user
        if self.is_default:
            DeliveryAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class KitchenStatus(models.Model):
    is_open = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name_plural = "Kitchen Status"
    
    @classmethod
    def get_status(cls):
        status, created = cls.objects.get_or_create(id=1)
        return status
    
