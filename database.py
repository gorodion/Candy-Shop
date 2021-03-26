import mysql.connector as connector
from mysql.connector.errors import Error
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE
import json
import re
import datetime


COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')


class CandyShopDB:
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
                    round(order['weight'], 2),
                    order['region'],
                    json.dumps(map(lambda x: x.strip(), order['delivery_hours']))
                )
            )
            orders_ids.append({'id': order['order_id']})
        self.conn.commit()
        return orders_ids

    def check_courier(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT COUNT(*) FROM couriers WHERE id={courier_id}')
        return self.curr.fetchone()[0]

    def get_courier(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT * FROM couriers WHERE id={courier_id}')
        spam = self.curr.fetchone()
        if spam is None:
            return spam

        courier_info = {}
        for field, val in zip(COURIER_FIELDS, spam):
            if field in ('regions', 'working_hours'):
                val = json.loads(val)
            courier_info[field] = val

        return courier_info

    @staticmethod
    def extract_interval_ends(interval: str):
        # проверять на ошибки?
        matching = re.match(r'^(\d\d:\d\d)-(\d\d:\d\d)$', interval.strip()).groups()
        return tuple(datetime.datetime.strptime(x, '%H:%M').time() for x in matching)

    @staticmethod
    def intervals_intersect(working_hours: str, delivery_hours: str):
        left_working, right_working = CandyShopDB.extract_interval_ends(working_hours)
        left_delivery, right_delivery = CandyShopDB.extract_interval_ends(delivery_hours)

        if left_working < left_delivery < right_working \
                or left_delivery < left_working < right_delivery:
            return True
        return False

    def find_relevant_orders(self, courier_id, max_weight, regions: tuple, working_hours):
        self.check_connection()

        # filter weight and region
        query = f'''
            SELECT
                id, delivery_hours
            FROM
                orders
            WHERE
                weight<={max_weight} AND
                region in {regions}
        '''
        self.curr.execute(query)
        # result without working_hours
        res0 = self.curr.fetchall()

        # можно избавиться
        if not res0:
            return res0, None

        # filtering by working_hours
        res1 = []
        for (id, delivery_hours) in res0:
            delivery_hours = json.loads(delivery_hours)
            intersect = any(self.intervals_intersect(i, j)
                            for i in working_hours
                            for j in delivery_hours)
            if intersect:
                res1.append({'id': id})

        if not res1:
            return res1, None
        date_tz = datetime.datetime.now(datetime.timezone.utc)
        return res1, date_tz

    # def find_relevant_orders(self, courier_id):
    #     self.check_connection()
    #     self.curr.execute(f'SELECT * FROM couriers WHERE couriers.id={courier_id}')
    #     courier_info = self.curr.fetchone()
    #     if not courier_info:
    #         return False
    #     _, courier_type, regions, working_hours, rating, earnings = courier_info
    #
    #     return self.curr.fetchone()[0]

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
