COURIER_TYPES = ('foot', 'bike', 'car')
REQUIRED_COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours')
COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')

REQUIRED_ORDER_FIELDS = ('order_id', 'weight', 'region', 'delivery_hours')
ORDER_FIELDS = ('order_id', 'weight', 'region', 'delivery_hours', 'courier_id', 'assign_time', 'complete_time')
