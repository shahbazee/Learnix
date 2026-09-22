"""
Custom template tags and filters for courses and curriculum tracking.
SRS Section 11.2.
"""

from django import template
from django.utils.safestring import mark_safe
import math

register = template.Library()


@register.filter(name="format_duration")
def format_duration(seconds: int) -> str:
    """
    Converts raw seconds into human-readable duration (e.g. 1h 45m or 14m).
    """
    if not seconds:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    return f"{minutes}m"


@register.simple_tag
def calculate_progress_badge(completed_count: int, total_count: int) -> str:
    """
    Calculates completion percentage and returns a colored HTML badge.
    """
    if not total_count or total_count == 0:
        pct = 0
    else:
        pct = int(math.floor((completed_count / total_count) * 100))

    if pct == 100:
        color_class = "bg-emerald-50 text-emerald-700 border border-emerald-200"
    elif pct >= 50:
        color_class = "bg-cyan-50 text-cyan-700 border border-cyan-200"
    elif pct > 0:
        color_class = "bg-violet-50 text-violet-700 border border-violet-200"
    else:
        color_class = "bg-slate-100 text-slate-600 border border-slate-200"

    html = f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold font-mono {color_class}">{pct}% Done</span>'
    return mark_safe(html)


@register.filter(name="times")
def times(number):
    """Returns range for rendering star ratings in templates."""
    try:
        return range(int(number))
    except (ValueError, TypeError):
        return range(0)


@register.filter(name="two_digits")
def two_digits(value):
    """Formats an integer or string with a leading zero (e.g. 1 -> '01')."""
    try:
        return f"{int(value):02d}"
    except (ValueError, TypeError):
        return value


@register.filter(name="preview_count")
def preview_count(module):
    """Counts previewable lessons in a course module."""
    if hasattr(module, 'lessons'):
        return module.lessons.filter(is_preview=True).count()
    return 0


@register.filter(name="original_price")
def original_price(price):
    """Calculates strike-through price (default ~2x for 50% discount presentation)."""
    try:
        val = float(price)
        if val <= 0:
            return "$199"
        # round up to integer for clean display e.g. 89 -> 178
        return f"${int(val * 2)}"
    except (ValueError, TypeError):
        return "$199"

