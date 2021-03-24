from flask import Flask, jsonify, abort, make_response, request
from dateutil.parser import parse
from misc import app, db
import json


@app.route('/orders', methods=['POST'])
def import_orders():
    content = request.json
    # если content - не словарь
    # проверка, нет ли в базе айдишников
    if not content or 'data' not in content:
        abort(400, 'Invalid request body')
    data = content['data']
    orders_ids, bad_orders_ids = [], []
    for order in data:
        if not isinstance(order['order_id'], int) \
            or not isinstance(order['weight'], (int, float)) \
            or not isinstance(order['region'], int) \
            or not isinstance(order['delivery_hours'], list) \
            or not all(map(lambda x: isinstance(x, str),
                           order['delivery_hours'])):
            bad_orders_ids.append({'id': order['order_id']})
        else:
            orders_ids.append({'id': order['order_id']})
    if bad_orders_ids:
        abort(400, {'orders': bad_orders_ids})
    # check if successed
    db.insert_orders(data)
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
