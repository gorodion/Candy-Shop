from flask import Flask, jsonify, abort, make_response, request
from dateutil.parser import parse
from misc import app, db
import json
import re
from datetime import datetime
from collections import defaultdict


ORDER_JSON_FIELDS = ('delivery_hours',)


def check_input_json(content):
    if not content or not isinstance(content, dict):
        abort(400, 'Invalid request body')


def valid_time(hours_min: str):
    matching = re.match(r'(\d\d:\d\d)-(\d\d:\d\d)', hours_min)
    if matching is None or len(matching.groups()) != 2:
        return False

    # второй член больше первого
    for t in matching.groups():
        try:
            datetime.strptime(t, '%H:%M')
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
    # возвращать айдишники
    orders_ids = db.insert_orders(data)
    return jsonify(orders=orders_ids), 201

@app.route('/orders/assign', methods=['POST'])
def assign_orders():
    content = request.json
    if not content or 'courier_id' not in content:
        abort(400, 'Invalid request body')
    courier_id = content['courier_id']
    courier_info = db.find_relevant_orders(courier_id)
    if not courier_info:
        abort(400, 'Bad request')

    db.find_relevant(courier_id)
    return jsonify()


def valid_tz(dt):
    try:
        parse(dt)
    except ValueError:
        return False
    return True


@app.route('/orders/complete', methods=['POST'])
def mark_as_completed():
    content = request.json
    if not content:
        abort(400, 'Invalid request body')

    if 'courier_id' not in content \
        or 'order_id' not in content \
        or 'complete_time' not in content:
        abort(400, 'There is no any keys')

    if not isinstance(content['courier_id'], int) \
        or not isinstance(content['order_id'], int) \
        or not isinstance(content['complete_time'], str) \
        or not valid_tz(content['complete_time']):
        abort(400, 'Bad request')
    db.mark_as_completed(content)
    return jsonify(order_id=content['courier_id'])
