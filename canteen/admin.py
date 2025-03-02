from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    User, 
    Category, 
    MenuItem, 
    Order, 
    OrderItem, 
    Cart, 
    CartItem, 
    PaymentInfo
)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone_number', 'user_type', 'date_joined','birth_date','is_active']
    list_filter = ['user_type', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'phone_number',]
    fieldsets = (
        ('Account Info', {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_image', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    display_image.short_description = 'Image'

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'display_image', 'is_available', 'is_featured','prep_time']
    list_filter = ['category', 'is_available', 'is_featured', 'created_at']
    search_fields = ['name', 'description']
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    display_image.short_description = 'Image'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total_amount', 'order_date', 'completed_at']
    list_filter = ['status', 'order_date', 'completed_at']
    search_fields = ['user__username', 'upi_transaction_id', 'notes']
    readonly_fields = ['order_date']
    inlines = [OrderItemInline]
    actions = ['mark_orders_as_completed']
    
    def mark_orders_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f"{updated} orders have been marked as completed.")
    mark_orders_as_completed.short_description = "Mark selected orders as completed"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total', 'item_count', 'updated_at']
    search_fields = ['user__username']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at', 'total', 'item_count']

@admin.register(PaymentInfo)
class PaymentInfoAdmin(admin.ModelAdmin):
    list_display = ['owner', 'upi_id', 'display_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['owner__username', 'upi_id', 'display_name']

# These models don't need their own admin page as they're accessed through inlines,
# but we can register them for direct access if needed
admin.site.register(OrderItem)
admin.site.register(CartItem)

from django.contrib import admin
from .models import Coupon, CouponUsage

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_value', 
                    'is_active', 'valid_from', 'valid_to', 'is_first_order_only')
    list_filter = ('is_active', 'discount_type', 'is_first_order_only')
    search_fields = ('code', 'description')
    
@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'used_at', 'discount_amount')
    list_filter = ('used_at',)
    search_fields = ('coupon__code', 'user__username')

from django.contrib import admin
from .models import DeliveryAddress

@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_type', 'address_preview', 'is_default', 'created_at')
    list_filter = ('address_type', 'is_default', 'created_at')
    search_fields = ('user__username', 'user__email', 'address')
    list_editable = ('is_default',)
    date_hierarchy = 'created_at'
    
    def address_preview(self, obj):
        """Returns a preview of the address (first 30 characters)"""
        if len(obj.address) > 30:
            return f"{obj.address[:30]}..."
        return obj.address
    
    address_preview.short_description = 'Address'
    
    def save_model(self, request, obj, form, change):
        # If setting as default, unset other defaults for this user
        if obj.is_default:
            DeliveryAddress.objects.filter(user=obj.user, is_default=True).exclude(pk=obj.pk).update(is_default=False)
        super().save_model(request, obj, form, change)
    
    # Define fieldsets for a better organization in the admin form
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Address Details', {
            'fields': ('address_type', 'address', 'is_default')
        }),
    )