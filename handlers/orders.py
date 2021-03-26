from flask import jsonify, abort, request
from dateutil.parser import parse
from misc import app, db
from .common_funcs import check_input_json, validate_interval_list


COURIER_TYPE_CAPACITY = {
    'foot': 10,
    'bike': 15,
    'car': 50
}


def validate_order(order: dict):
    if not isinstance(order, dict):
        return {"order": "type is not object"}

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

    #  `data` есть всегда и содержит список элементов
    # if 'data' not in content:
    #     abort(400, 'data not in request body')
    print(content)
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

    # разделить на несколько функций
    # searching for relevant orders + assign
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
