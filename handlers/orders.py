from flask import Flask, jsonify, abort, make_response, request
from dateutil.parser import parse
from misc import app, db
import json
import re
import datetime
from collections import defaultdict


COURIER_TYPE_CAPACITY = {
    'foot': 10,
    'bike': 15,
    'car': 50
}


def check_input_json(content):
    if not content or not isinstance(content, dict):
        abort(400, 'Invalid request body')


def valid_time(hours_min: str):
    matching = re.match(r'^(\d\d:\d\d)-(\d\d:\d\d)$', hours_min.strip())
    if matching is None or len(matching.groups()) != 2:
        return False

    # проверить, что второй член больше первого
    for t in matching.groups():
        try:
            datetime.datetime.strptime(t, '%H:%M')
        except ValueError:
            return False
    return True


def validate_order(order: dict):
    if not isinstance(order, dict):
        return {"order": "is not JSON object"}

    bad_fields = {}

    order_id = order['order_id']
    if not isinstance(order_id, int):
        bad_fields['order_id'] = 'is not integer'
    elif order_id < 1:
        bad_fields['order_id'] = 'is not positive number'
    elif db.check_order(order_id):
        bad_fields['order_id'] = 'already in database'

    if 'weight' not in order:
        bad_fields['weight'] = 'missing field'
    else:
        weight = order['weight']
        if not isinstance(weight, (int, float)):
            bad_fields['weight'] = 'is not number'
        elif weight < 0.01:
            bad_fields['weight'] = 'less than 0.01'
        elif weight > 50:
            bad_fields['weight'] = 'more than 50'

    if 'region' not in order:
        bad_fields['region'] = 'missing field'
    else:
        region = order['region']
        if not isinstance(region, int):
            bad_fields['region'] = 'is not integer'
        elif region < 1:
            bad_fields['region'] = 'is not positive number'

    if 'delivery_hours' not in order:
        bad_fields['delivery_hours'] = 'missing field'
    else:
        delivery_hours = order['delivery_hours']
        if not isinstance(delivery_hours, list):
            bad_fields['delivery_hours'] = 'is not array'
        # расширить до выдачи индексов некорректных элементов
        elif not all(map(lambda x: isinstance(x, str), delivery_hours)):
            bad_fields['delivery_hours'] = 'not all elements are strings'
        elif not all(map(lambda x: valid_time(x), delivery_hours)):
            bad_fields['delivery_hours'] = 'not all elements are in the correct time format'

    # только когда все поля корректные
    if len(order) > 4:
        bad_fields['has_extra_fields'] = True

    if bad_fields:
        bad_fields['id'] = order_id
    return bad_fields


@app.route('/orders', methods=['POST'])
def import_orders():
    content = request.json
    check_input_json(content)

    #  `data` есть всегда
    # if 'data' not in content:
    #     abort(400, 'data not in request body')

    data = content['data']

    bad_orders = []
    for order in data:
        bad_fields = validate_order(order)
        if bad_fields:
            bad_orders.append(bad_fields)

    if bad_orders:
        abort(400, {'orders': bad_orders})

    # check if successed
    orders_ids = db.insert_orders(data)
    return jsonify(orders=orders_ids), 201


@app.route('/orders/assign', methods=['POST'])
def assign_orders():
    content = request.json
    check_input_json(content)

    if 'courier_id' not in content:
        abort(400, 'Bad request')
    courier_id = content['courier_id']

    if not db.check_courier(courier_id):
        abort(400, 'Bad request')

    courier_info = db.get_courier(courier_id)

    courier_id = courier_info['courier_id']
    courier_type = courier_info['courier_type']
    max_weight = COURIER_TYPE_CAPACITY[courier_type]
    regions = courier_info['regions']
    working_hours = courier_info['working_hours']

    relevant_orders, date_tz = db.find_relevant_orders(courier_id, max_weight, regions, working_hours)
    if not relevant_orders:
        return jsonify(orders=[])

    return jsonify(orders=relevant_orders, assign_time=str(date_tz).replace(' ', 'T').replace('+00:00', 'Z')), 201


def valid_tz(dt):
    try:
        parse(dt)
    except ValueError:
        return False
    return True


@app.route('/orders/complete', methods=['POST'])
def mark_as_completed():
    content = request.json
    check_input_json(content)
    if 'courier_id' not in content \
            or 'order_id' not in content \
            or 'complete_time' not in content:
        abort(400, 'Bad request')

    if not isinstance(content['courier_id'], int) \
            or not isinstance(content['order_id'], int) \
            or not isinstance(content['complete_time'], str) \
            or not valid_tz(content['complete_time']):
        abort(400, 'Bad request')

    courier_id = content['courier_id']
    order_id = content['order_id']
    complete_time = parse(content['complete_time'])

    correct_order = db.check_order_assignment(courier_id, order_id)
    if not correct_order:
        abort(400, 'Bad request')

    # если complete_time позже assign_time
    db.mark_as_completed(courier_id, order_id, complete_time)
    return jsonify(order_id=order_id)
