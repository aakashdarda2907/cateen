from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    # Add these to your urlpatterns
path('addresses/', views.addresses, name='addresses'),
path('addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
path('addresses/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
path('cart/update-delivery/', views.update_delivery_option, name='update_delivery_option'),
    # Authentication routes
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Menu routes
    path('menu/', views.menu_view, name='menu'),
    # Add these URLs to your urls.py file
path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
path('cart/remove-coupon/', views.remove_coupon, name='remove_coupon'),
    # favourites
    path('toggle-favorite/<int:item_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('api/favorite-status/', views.favorite_status, name='favorite_status'),
    
    # Cart routes
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Order routes
    path('checkout/', views.checkout, name='checkout'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('orders/history/', views.order_history, name='order_history'),
    path('orders/detail/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Staff/Owner dashboard routes
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/orders/', views.order_management, name='order_management'),
    path('dashboard/orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('dashboard/analytics/', views.analytics, name='analytics'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)