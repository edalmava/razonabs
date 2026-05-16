from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr):
    """Filtro para obtener atributos dinámicos de un objeto."""
    return getattr(obj, attr, None)

@register.filter
def sum_time(queryset):
    return sum(item.time_taken for item in queryset)

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
