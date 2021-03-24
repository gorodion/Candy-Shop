from flask import jsonify, request, abort
from misc import app, db

COURIER_TYPES = ('foot', 'bike', 'car')
COURIER_COLS = ('id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')


def courier_to_json(courier):
    return {
            'courier_id': courier.courier_id,
            'courier_type': courier.courier_type,
            'regions': courier.regions,
            'working_hours': courier.working_hours
        }


# @app.route('/couriers', methods=['GET'])
# def get_couriers():
#     return jsonify({'couriers': list(map(courier_to_json, couriers))})

@app.route('/couriers/<int:courier_id>', methods=['GET'])
def get_courier(courier_id):
    res = db.get_courier(courier_id)
    if not res:
        abort(404)
    if res['rating'] == 0:
        res.pop('rating')
    return jsonify(res)


@app.route('/couriers', methods=['POST'])
def import_couriers():
    if not request.json:
        abort(400)
    if not isinstance(request.json, list):
        abort(400)

    couriers = []
    courier_ids = []
    bad_courier_ids = []
    code = 201

    for courier in request.json:
        # условие проверки айди в базе
        # все ли поля пристуствуют
        # нет ли лишних полей
        if not isinstance(courier['courier_id'], int) \
            or courier['courier_type'] not in COURIER_TYPES \
            or not isinstance(courier['regions'], list) \
            or not all(isinstance(x, int) for x in courier['regions']) \
            or not isinstance(courier['working_hours'], list) \
            or not all(isinstance(x, str) and '-' in x
                       for x in courier['working_hours']):
            bad_courier_ids.append(courier['courier_id'])
            code = 400
        elif code != 400:
            # добавление в базу с транзакцией
            couriers.append(courier)
            courier_ids.append(courier['courier_id'])

    # if code != 400:
        # couriers_list.append(couriers)
    return jsonify(couriers=courier_ids), 201
    # else:
    #     abort(400, {'validation_error': bad_courier_ids})




# @app.route('/couriers/<int:courier_id>', methods=['GET'])
# def get_courier(courier_id):
    # for courier in couriers:
    #     if courier.courier_id == courier_id:
    #         return jsonify(courier=courier_to_json(courier))
    # abort(404)
