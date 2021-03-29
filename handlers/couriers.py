from flask import jsonify, request, abort
from misc import app, db
from .common_funcs import validate_interval_list
from constants import COURIER_TYPES, REQUIRED_COURIER_FIELDS, PATCH_COURIER_FIELDS


# adding errors to bad_fields is done inplace
def validate_courier_type(courier_type, bad_fields):
    if not isinstance(courier_type, str):
        bad_fields['courier_type'] = 'is not string'
    elif courier_type not in COURIER_TYPES:
        bad_fields['courier_type'] = 'invalid courier type'


def validate_regions(regions, bad_fields):
    if not isinstance(regions, list):
        bad_fields['regions'] = 'is not an array'
    elif not all(map(lambda x: isinstance(x, int) and x > 0, regions)):
        bad_fields['regions'] = 'not all elements are positive integers'


def validate_courier(courier: dict):
    bad_fields = {}

    # есть всегда
    courier_id = courier['courier_id']
    if not isinstance(courier_id, int):
        bad_fields['courier_id'] = 'is not integer'
    elif courier_id < 1:
        bad_fields['courier_id'] = 'is not positive number'
    elif db.check_courier(courier_id):
        bad_fields['courier_id'] = 'already in database'

    if 'courier_type' not in courier:
        bad_fields['courier_type'] = 'missing field'
    else:
        courier_type = courier['courier_type']
        validate_courier_type(courier_type, bad_fields)

    if 'regions' not in courier:
        bad_fields['regions'] = 'missing field'
    else:
        regions = courier['regions']
        validate_regions(regions, bad_fields)

    if 'working_hours' not in courier:
        bad_fields['working_hours'] = 'missing_field'
    else:
        working_hours = courier['working_hours']
        validate_interval_list(working_hours, bad_fields, key='working_hours')

    if set(courier.keys()) - set(REQUIRED_COURIER_FIELDS):
        bad_fields['has_extra_fields'] = True

    if bad_fields:
        bad_fields['id'] = courier_id
    return bad_fields


@app.route('/couriers', methods=['POST'])
def import_couriers():
    content = request.json
    data = content['data']

    bad_couriers = []
    for courier in data:
        bad_fields = validate_courier(courier)
        if bad_fields:
            bad_couriers.append(bad_fields)

    if bad_couriers:
        abort(400, {'couriers': bad_couriers})

    couriers_ids = db.insert_couriers(data)
    return jsonify(couriers=couriers_ids), 201


@app.route('/couriers/<int:courier_id>', methods=['PUT'])
def patch_courier(courier_id):
    content = request.json

    if not db.check_courier(courier_id):
        abort(404)

    if set(content.keys()) - set(PATCH_COURIER_FIELDS):
        abort(400, 'Bad request')

    bad_fields = {}
    if 'courier_type' in content:
        courier_type = content['courier_type']
        validate_courier_type(courier_type, bad_fields)
    if 'regions' in content:
        regions = content['regions']
        validate_regions(regions, bad_fields)
    if 'working_hours' in content:
        working_hours = content['working_hours']
        validate_interval_list(working_hours, bad_fields, key='working_hours')
    if bad_fields:
        abort(400, 'Bad request')

    result = db.patch_courier(courier_id, content)
    return jsonify(result)


@app.route('/couriers/<int:courier_id>', methods=['GET'])
def get_courier(courier_id):
    courier_info = db.get_courier(courier_id)
    if courier_info is None:
        abort(404)
    if courier_info['rating'] == 0:
        courier_info.pop('rating')
    return jsonify(courier_info)
