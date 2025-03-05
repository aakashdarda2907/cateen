from django import template
from django.db.models import Q

register = template.Library()

@register.filter
def is_beverage_order(order_items):
    """
    Check if order contains any beverage items
    
    Args:
        order_items (QuerySet): A QuerySet of OrderItem objects
    
    Returns:
        bool: True if the order contains any beverage items, False otherwise
    """
    return order_items.filter(
        Q(menu_item__category__name__icontains='beverage') | 
        Q(menu_item__category__name__icontains='drinks')
    ).exists()