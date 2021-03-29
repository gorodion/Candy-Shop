from flask import abort
import re
import datetime


def valid_time(hours_min: str):
    matching = re.match(r'^(\d\d:\d\d)-(\d\d:\d\d)$', hours_min.strip())
    if matching is None or len(matching.groups()) != 2:
        return False

    left, right = matching.groups()
    try:
        left = datetime.datetime.strptime(left, '%H:%M').time()
        right = datetime.datetime.strptime(right, '%H:%M').time()
    except ValueError:
        return False

    return left < right


# adding errors to bad_fields inplace
def validate_interval_list(interval_list, bad_fields: dict, key):
    if not isinstance(interval_list, list):
        bad_fields[key] = 'is not array'
    elif not all(map(lambda x: isinstance(x, str), interval_list)):
        bad_fields[key] = 'not all elements are strings'
    elif not all(map(lambda x: valid_time(x), interval_list)):
        bad_fields[key] = 'not all elements are in the correct time format'
