"""
Helper utilities for Jules Dev Kit
"""

from datetime import datetime


def format_datetime(iso_string):
    """Format ISO datetime string for display."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except (ValueError, AttributeError):
        return iso_string or 'Unknown'


def truncate_text(text, max_length):
    """Truncate text with ellipsis if too long."""
    if not text:
        return ""
    return text[:max_length] + "..." if len(text) > max_length else text
