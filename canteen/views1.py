import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
# Remove this import to avoid conflict
# from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import Coupon, CouponUsage, DeliveryAddress, Favorite, User, Category, MenuItem, Order, OrderItem, Cart, CartItem, PaymentInfo
from django.db.models import Sum
from django.db.models.functions import TruncMonth

# Home page view
def home(request):
    featured_items = MenuItem.objects.filter(is_featured=True, is_available=True)[:6]
    categories = Category.objects.filter(is_active=True)[:4]
    
    context = {
        'featured_items': featured_items,
        'categories': categories,
    }
    return render(request, 'canteen/home.html', context)

# Auth views
def register_view(request):
    if request.method == 'POST':
        # Get form data directly from request.POST
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        birth_date = request.POST.get('birth_date')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validate data
        errors = []
        
        if User.objects.filter(username=username).exists():
            errors.append("Username already exists")
        
        if User.objects.filter(email=email).exists():
            errors.append("Email already registered")
            
        if password != password_confirm:
            errors.append("Passwords do not match")
            
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'canteen/register.html')
        
        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.phone_number = phone_number
        user.birth_date = birth_date
        user.user_type = 'student'  # Default to student
        user.save()
        
        # Create a cart for the new user
        Cart.objects.create(user=user)
        
        # Log the user in
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect('home')
    
    return render(request, 'canteen/register.html')



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Use authenticate with your custom User model
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Direct access to user_type from your custom User model
            if user.user_type == 'student':
                return redirect('menu')
            elif user.user_type in ['staff', 'owner']:
                return redirect('dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'canteen/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

# Menu related views
def menu_view(request):
    categories = Category.objects.filter(is_active=True)
    
    # Filter by category if specified
    category_id = request.GET.get('category')
    if category_id:
        menu_items = MenuItem.objects.filter(
            category_id=category_id, 
            is_available=True
        ).order_by('category', 'name')
    else:
        menu_items = MenuItem.objects.filter(
            is_available=True
        ).order_by('category', 'name')
    
    # Birthday message logic
    birthday_message = None
    birthday_person = None
    
    # Check if user is logged in
    if request.user.is_authenticated:
        today = datetime.now().date()
        
        # Get all users with birthdays today
        birthday_users = User.objects.filter(
            birth_date__day=today.day,
            birth_date__month=today.month
        )
        
        if birthday_users.exists():
            # Get the first birthday person (you could extend this for multiple birthdays)
            birthday_person = birthday_users.first()
            
            # Check if current user is the birthday person
            if request.user.id == birthday_person.id:
                birthday_message = f"Happy birthday {birthday_person.username} : Lets have a party today :)!"
            else:
                birthday_message = f"Today is {birthday_person.username}'s birthday! get a party from them! - here is their number - {birthday_person.phone_number}"
    
    context = {
        'categories': categories,
        'menu_items': menu_items,
        'selected_category': category_id,
        'birthday_message': birthday_message,
        
    }
    return render(request, 'canteen/menu.html', context)

# Cart related views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

@login_required
def view_cart(request):
    if request.user.is_anonymous:
        return redirect('login')  # Ensure users are logged in before proceeding
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    payment_info = PaymentInfo.objects.filter(is_active=True).first()
    
    # Get user's saved addresses
    addresses = DeliveryAddress.objects.filter(user=request.user).order_by('-is_default')

    # For first-time users, check if there's a "first order" coupon
    is_first_time = not Order.objects.filter(user=request.user, status='completed').exists()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'payment_info': payment_info,
        'is_first_time': is_first_time,
        'addresses': addresses,
        'delivery_choices': Cart.DELIVERY_CHOICES,
    }
    return render(request, 'canteen/cart.html', context)

@login_required
@require_POST
def add_to_cart(request, item_id):
    menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get the quantity from the POST data
    quantity = int(request.POST.get('quantity', 1))
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        menu_item=menu_item,
    )
    
    if created:
        # Set initial quantity for new item
        cart_item.quantity = quantity
    else:
        # Add the selected quantity to existing item
        cart_item.quantity += quantity
    
    cart_item.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"{menu_item.name} added to cart",
            'cart_count': cart.item_count,
        })
    
    messages.success(request, f"{menu_item.name} added to cart")
    return redirect('menu')

@login_required
@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    action = request.POST.get('action')
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return redirect('view_cart')
    
    cart_item.save()
    return redirect('view_cart')

@login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    
    messages.success(request, "Item removed from cart")
    return redirect('view_cart')

# Order related views
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.warning(request, "Your cart is empty. Add items before checkout.")
        return redirect('menu')
    
    payment_info = PaymentInfo.objects.filter(is_active=True).first()
    if not payment_info:
        messages.error(request, "Payment information is not available. Please try again later.")
        return redirect('view_cart')
    
    if request.method == 'POST':
        upi_transaction_id = request.POST.get('upi_transaction_id')
        notes = request.POST.get('notes', '')
        
        # Validate UPI transaction ID
        if not upi_transaction_id:
            messages.error(request, "Please enter your UPI transaction ID")
            return render(request, 'canteen/checkout.html', {
                'cart': cart,
                'cart_items': cart_items,
                'payment_info': payment_info,
            })
            
        # Validate delivery address for delivery orders
        if cart.delivery_type == 'delivery' and not cart.delivery_address:
            messages.error(request, "Please select a delivery address")
            return redirect('view_cart')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=cart.total,
            discount=cart.discount,
            delivery_type=cart.delivery_type,
            delivery_address=cart.delivery_address,
            delivery_charge=cart.delivery_charge,
            total_amount=cart.final_total,
            coupon=cart.coupon,
            upi_transaction_id=upi_transaction_id,
            notes=notes,
            status='pending'  # Initially pending until verified
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.menu_item,
                quantity=cart_item.quantity,
                price=cart_item.menu_item.price
            )
        
        # Record coupon usage if a coupon was applied
        if cart.coupon:
            CouponUsage.objects.create(
                coupon=cart.coupon,
                user=request.user,
                order=order,
                discount_amount=cart.discount
            )
            # Remove the coupon from the cart
            cart.coupon = None
            cart.save()
        
        # Clear the cart
        cart_items.delete()
        
        # Reset delivery options
        cart.delivery_type = 'dine_in'
        cart.delivery_address = None
        cart.save()
        
        messages.success(request, "Order placed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'payment_info': payment_info,
    }
    return render(request, 'canteen/checkout.html', context)
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'canteen/order_confirmation.html', context)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'canteen/order_history.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'canteen/order_detail.html', context)

# Staff/Owner Dashboard views
@login_required
def dashboard(request):
    # Check if user is staff or owner
    if request.user.user_type not in ['staff', 'owner']:
        messages.error(request, "You don't have permission to access the dashboard.")
        return redirect('home')
    
    # Get today's date
    today = timezone.now().date()
    
    # Get counts and statistics
    pending_orders = Order.objects.filter(
        status__in=['pending', 'preparing', 'ready']
    ).count()
    
    today_orders = Order.objects.filter(
        order_date__date=today
    ).count()
    
    today_sales = Order.objects.filter(
        order_date__date=today,
        status='completed'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # For owner only: get more detailed stats
    if request.user.user_type == 'owner':
        # Get monthly sales for the last 6 months
    
        # Correct way to get monthly sales data
        monthly_sales = Order.objects.filter(
            status='completed'
        ).annotate(
            month=TruncMonth('order_date')
        ).values('month').annotate(
            amount=Sum('total_amount')
        ).order_by('month')
        # Get top 5 popular items
        popular_items = OrderItem.objects.values(
            'menu_item__name'
        ).annotate(
            count=Sum('quantity')
        ).order_by('-count')[:5]
    else:
        monthly_sales = []
        popular_items = []
    formatted_monthly_sales = []
    for data in monthly_sales:
        formatted_monthly_sales.append({
                'month_name': data['month'].strftime('%B %Y'),
                'amount': float(data['amount'])
            })
        
        context['monthly_sales'] = formatted_monthly_sales
    
    context = {
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'today_sales': today_sales,
        'monthly_sales': monthly_sales,
        'popular_items': popular_items,
        'is_owner': request.user.user_type == 'owner',
    }
    return render(request, 'canteen/dashboard.html', context)

# In views.py - order_management function update
@login_required
def order_management(request):
    # Check if user is staff or owner
    if request.user.user_type not in ['staff', 'owner']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get recent orders that are not completed or cancelled
    active_orders = Order.objects.filter(
        status__in=['pending', 'preparing', 'ready', 'out_for_delivery', 'delivered']
    ).order_by('order_date')
    
    # Get recently completed orders (last 12 hours)
    recent_time = timezone.now() - timedelta(hours=12)
    recent_completed = Order.objects.filter(
        status__in=['completed', 'cancelled'],
        completed_at__gte=recent_time
    ).order_by('-completed_at')
    
    context = {
        'active_orders': active_orders,
        'recent_completed': recent_completed,
    }
    return render(request, 'canteen/order_management.html', context)

@login_required
@require_POST
def update_order_status(request, order_id):
    # Check if user is staff or owner
    if request.user.user_type not in ['staff', 'owner']:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    # Get the available status choices from the model
    valid_statuses = [status[0] for status in Order.STATUS_CHOICES]
    
    if new_status in valid_statuses:
        order.status = new_status
        
        # If marking as completed or delivered, set completed_at time
        if new_status in ['completed', 'delivered'] and not order.completed_at:
            order.completed_at = timezone.now()
            
        order.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Order status updated to {order.get_status_display()}'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': f'Invalid status: {new_status}. Valid statuses are: {", ".join(valid_statuses)}'
    }, status=400)@login_required
def analytics(request):
    # Only allow owner access
    if request.user.user_type != 'owner':
        messages.error(request, "Only canteen owners can access analytics.")
        return redirect('dashboard')
    
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)
        
    if end_date_param:
        try:
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get orders within date range
    orders = Order.objects.filter(
        order_date__date__gte=start_date,
        order_date__date__lte=end_date,
        status='completed'
    )
    
    # Sales by day
    sales_by_day = orders.extra({
        'day': "strftime(order_date, 'YYYY-MM-DD')"
    }).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    # Top selling items
    top_items = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'menu_item__name', 
        'menu_item__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_quantity')[:10]
    
    # Sales by category
    sales_by_category = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'menu_item__category__name'
    ).annotate(
        total=Sum('price'),
        item_count=Sum('quantity')
    ).order_by('-total')
    
    # Average order value
    avg_order = orders.aggregate(
        avg_value=Avg('total_amount')
    )['avg_value'] or 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_orders': orders.count(),
        'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'avg_order_value': avg_order,
        'sales_by_day': sales_by_day,
        'top_items': top_items,
        'sales_by_category': sales_by_category,
    }
    return render(request, 'canteen/analytics.html', context)

@login_required
@require_POST
def toggle_favorite(request, item_id):
    menu_item = get_object_or_404(MenuItem, id=item_id)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        menu_item=menu_item
    )
    
    # If favorite already existed, delete it (toggle behavior)
    if not created:
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True
        
    return JsonResponse({
        'status': 'success',
        'is_favorite': is_favorite
    })

@login_required
def favorites_view(request):
    # Get user's favorite menu items
    favorite_items = MenuItem.objects.filter(
        favorite__user=request.user
    ).order_by('category', 'name')
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'categories': categories,
        'menu_items': favorite_items,
        'is_favorites_page': True
    }
    return render(request, 'canteen/menu.html', context)

@login_required
def favorite_status(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    # Get item IDs from request
    data = json.loads(request.body)
    item_ids = data.get('item_ids', [])
    
    # Get user's favorites for these items
    favorite_ids = Favorite.objects.filter(
        user=request.user,
        menu_item_id__in=item_ids
    ).values_list('menu_item_id', flat=True)
    
    return JsonResponse({
        'success': True,
        'favorites': list(favorite_ids)
    })

@login_required
@require_POST
def apply_coupon(request):
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    
    if not coupon_code:
        messages.error(request, "Please enter a coupon code")
        return redirect('view_cart')
    
    try:
        coupon = Coupon.objects.get(code=coupon_code)
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid coupon code")
        return redirect('view_cart')
    
    # Get user's cart
    cart = get_object_or_404(Cart, user=request.user)
    
    # Validate the coupon
    is_valid, message = coupon.is_valid(request.user, cart.total)
    
    if is_valid:
        cart.coupon = coupon
        cart.save()
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('view_cart')

@login_required
def remove_coupon(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart.coupon = None
    cart.save()
    messages.success(request, "Coupon removed")
    return redirect('view_cart')

@login_required
def addresses(request):
    addresses = DeliveryAddress.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    if request.method == 'POST':
        address_type = request.POST.get('address_type')
        address = request.POST.get('address')
        is_default = request.POST.get('is_default') == 'on'
        
        if address and address_type:
            DeliveryAddress.objects.create(
                user=request.user,
                address_type=address_type,
                address=address,
                is_default=is_default
            )
            messages.success(request, "Address added successfully")
            return redirect('addresses')
        else:
            messages.error(request, "Please provide all required information")
    
    context = {
        'addresses': addresses,
    }
    return render(request, 'canteen/addresses.html', context)

@login_required
@require_POST
def delete_address(request, address_id):
    address = get_object_or_404(DeliveryAddress, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully")
    return redirect('addresses')

@login_required
@require_POST
def set_default_address(request, address_id):
    address = get_object_or_404(DeliveryAddress, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated")
    return redirect('addresses')

@login_required
@require_POST
def update_delivery_option(request):
    cart = get_object_or_404(Cart, user=request.user)
    delivery_type = request.POST.get('delivery_type')
    
    if delivery_type not in dict(Cart.DELIVERY_CHOICES):
        messages.error(request, "Invalid delivery option")
        return redirect('view_cart')
    
    cart.delivery_type = delivery_type
    
    # If delivery option is 'delivery', set the delivery address
    if delivery_type == 'delivery':
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(DeliveryAddress, id=address_id, user=request.user)
            cart.delivery_address = address
        else:
            # If no address is selected, but user has a default address, use that
            default_address = DeliveryAddress.objects.filter(user=request.user, is_default=True).first()
            if default_address:
                cart.delivery_address = default_address
    else:
        # If dine in, clear the delivery address
        cart.delivery_address = None
    
    cart.save()
    messages.success(request, f"Delivery option updated to {dict(Cart.DELIVERY_CHOICES)[delivery_type]}")
    return redirect('view_cart')