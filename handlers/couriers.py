from flask import jsonify, request, abort
from misc import app, db
from .common_funcs import check_input_json, validate_interval_list

COURIER_TYPES = ('foot', 'bike', 'car')


def validate_courier(courier: dict):
    if not isinstance(courier, dict):
        return {"courier": "type is not object"}

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
        if not isinstance(courier_type, str):
            bad_fields['courier_type'] = 'is not string'
        elif courier_type not in COURIER_TYPES:
            bad_fields['courier_type'] = 'invalid courier type'

    if 'regions' not in courier:
        bad_fields['regions'] = 'missing field'
    else:
        regions = courier['regions']
        if not isinstance(regions, list):
            bad_fields['regions'] = 'is not an array'
        elif not all(map(lambda x: isinstance(x, int) and x > 0, regions)):
            bad_fields['regions'] = 'not all elements are integers'

    if 'working_hours' not in courier:
        bad_fields['working_hours'] = 'missing_field'
    else:
        working_hours = courier['working_hours']
        validate_interval_list(working_hours, bad_fields, key='working_hours')

    # только когда все поля корректные
    if len(courier) > 4:
        bad_fields['has_extra_fields'] = True

    if bad_fields:
        bad_fields['id'] = courier_id
    return bad_fields


@app.route('/couriers', methods=['POST'])
def import_couriers():
    content = request.json
    check_input_json(content)

    #  `data` есть всегда и содержит список элементов
    # if 'data' not in content:
    #     abort(400, 'data not in request body')
    data = content['data']

    bad_couriers = []
    for courier in data:
        bad_fields = validate_courier(courier)
        if bad_fields:
            bad_couriers.append(bad_fields)

    if bad_couriers:
        abort(400, {'couriers': bad_couriers})

    # check if successed
    couriers_ids = db.insert_couriers(data)
    return jsonify(couriers=couriers_ids), 201


# @app.route('/couriers/<int:courier_id>', methods=['GET'])
# def get_courier(courier_id):
#     res = db.get_courier(courier_id)
#     if not res:
#         abort(404)
#     if res['rating'] == 0:
#         res.pop('rating')
#     return jsonify(res)

# @app.route('/couriers/<int:courier_id>', methods=['GET'])
# def get_courier(courier_id):
#     if not db.check_courier(courier_id):
#         abort(404)
#     return jsonify(courier=db.get_courier(courier_id))
