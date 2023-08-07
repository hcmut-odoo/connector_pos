from datetime import datetime

def parse_date_string(date_string):
    return datetime.fromisoformat(date_string.replace('Z', '+00:00'))

def format_date_string(date_obj):
    return date_obj.strftime('%Y-%m-%d %H:%M:%S')