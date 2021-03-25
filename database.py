import mysql.connector as connector
from mysql.connector.errors import Error
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE
import json


class candy_shop_db():
    COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')

    def __init__(self):
        self.conn = connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE
        )
        self.curr = self.conn.cursor()

    def check_connection(self):
        if not self.conn.is_connected():
            self.conn.reconnect()

    def check_order(self, order_id):
        self.check_connection()
        self.curr.execute(f'SELECT COUNT(*) FROM orders where id={order_id}')
        return self.curr.fetchone()[0]

    def insert_orders(self, orders):
        self.check_connection()

        orders_ids = []
        for order in orders:
            self.curr.execute(
                'INSERT INTO orders VALUES (%s, %s, %s, %s, DEFAULT, DEFAULT)',
                (
                    order['order_id'],
                    order['weight'],
                    order['region'],
                    json.dumps(order['delivery_hours'])
                )
            )
            orders_ids.append({'id': order['order_id']})
        self.conn.commit()
        return orders_ids

    def get_courier(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT * FROM couriers WHERE id={courier_id}')
        spam = self.curr.fetchone()
        if spam is None:
            return spam

        res = {}
        for field, val in zip(self.COURIER_FIELDS, spam):
            if field in ('regions', 'working_hours'):
                val = json.loads(val)
            res[field] = val

        return res

    def find_relevant_orders(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT * FROM couriers WHERE couriers.id={courier_id}')
        courier_info = self.curr.fetchone()
        if not courier_info:
            return False
        _, courier_type, regions, working_hours, rating, earnings = courier_info

        return self.curr.fetchone()[0]

    def mark_as_completed(self, content):
        self.check_connection()
        courier_id = content['courier_id']
        order_id = content['order_id']
        complete_time = content['complete_time']
        # change complete_time
        query = f'''
            UPDATE 
                orders
            SET
                complete_time={complete_time}
            WHERE 
                courier_id={courier_id} AND
                order_id={order_id}
            '''
        self.curr.execute(query)
        self.conn.commit()

    # def store_db(self, item):
    #     try:
	# 		self.check_connection()
	# 		...
    #         self.conn.commit()
    #     except Error as e:
    #         print('Database problem:', e)
