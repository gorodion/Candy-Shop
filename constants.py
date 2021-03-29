COURIER_TYPES = ('foot', 'bike', 'car')
REQUIRED_COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours')
PATCH_COURIER_FIELDS = ('courier_type', 'regions', 'working_hours')
COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')

COURIER_TYPE_CAPACITY = {
    'foot': 10,
    'bike': 15,
    'car': 50
}

REQUIRED_ORDER_FIELDS = ('order_id', 'weight', 'region', 'delivery_hours')