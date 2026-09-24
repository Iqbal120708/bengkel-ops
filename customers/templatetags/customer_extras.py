from django import template

register = template.Library()

STATUS_COLORS = {
    "NEW": "bg-blue-100 text-blue-700",
    "ACTIVE": "bg-green-100 text-green-700",
    "INACTIVE": "bg-red-100 text-red-700",
}

STATUS_DOTS = {
    "NEW": "bg-blue-500",
    "ACTIVE": "bg-green-500",
    "INACTIVE": "bg-red-500",
}


@register.filter
def status_badge_class(status):
    return STATUS_COLORS.get(status, "bg-gray-100 text-gray-700")


@register.filter
def status_dot_class(status):
    return STATUS_DOTS.get(status, "bg-gray-400")