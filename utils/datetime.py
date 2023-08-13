from datetime import datetime

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def parse_date_string(date_string):
    return datetime.fromisoformat(date_string.replace('Z', '+00:00'))

def format_date_string(date_obj):
    return date_obj.strftime(DATE_FORMAT)

def convert_string_to_datetime(date_string):
    try:
        datetime_object = datetime.strptime(date_string, DATE_FORMAT)
        return datetime_object
    except ValueError:
        print("Error: Unable to parse the date string.")
        return None