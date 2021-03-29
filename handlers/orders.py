from flask import jsonify, abort, request
from dateutil.parser import parse
from dateutil.tz import tzutc
from misc import app, db
from constants import REQUIRED_ORDER_FIELDS, COURIER_TYPE_CAPACITY
from .common_funcs import validate_interval_list


def validate_order(order: dict):
    bad_fields = {}

    # всегда есть
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
        validate_interval_list(delivery_hours, bad_fields, key='delivery_hours')

    if set(order.keys()) - set(REQUIRED_ORDER_FIELDS):
        bad_fields['has_extra_fields'] = True

    if bad_fields:
        bad_fields['id'] = order_id
    return bad_fields


@app.route('/orders', methods=['POST'])
def import_orders():
    content = request.json
    data = content['data']

    bad_orders = []
    for order in data:
        bad_fields = validate_order(order)
        if bad_fields:
            bad_orders.append(bad_fields)

    if bad_orders:
        abort(400, {'orders': bad_orders})

    orders_ids = db.insert_orders(data)
    return jsonify(orders=orders_ids), 201


@app.route('/orders/assign', methods=['POST'])
def assign_orders():
    content = request.json

    if 'courier_id' not in content:
        abort(400, 'Bad request')
    courier_id = content['courier_id']

    courier_info = db.get_courier(courier_id)

    if courier_info is None:
        abort(400, 'Bad request')

    courier_id = courier_info['courier_id']
    courier_type = courier_info['courier_type']
    max_weight = COURIER_TYPE_CAPACITY[courier_type]
    regions = courier_info['regions']
    working_hours = courier_info['working_hours']

    if not regions or not working_hours:
        return jsonify(orders=[])

    # searching for relevant orders + assign
    relevant_orders, date_tz = db.find_relevant_orders(courier_id, max_weight, regions, working_hours)
    if not relevant_orders:
        return jsonify(orders=[])

    return jsonify(orders=relevant_orders, assign_time=str(date_tz).replace(' ', 'T').replace('+00:00', 'Z'))


def valid_tz(dt):
    try:
        parse(dt)
    except ValueError:
        return False
    return True


@app.route('/orders/complete', methods=['POST'])
def mark_as_completed():
    content = request.json

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

    correct_order, assign_time = db.check_order_assignment(courier_id, order_id)
    if not correct_order:
        abort(400, 'Bad request')

    assign_time = assign_time.replace(tzinfo=tzutc())
    if assign_time > complete_time:
        abort(400, 'Bad request')

    db.mark_as_completed(courier_id, order_id, complete_time)
    return jsonify(order_id=order_id)
