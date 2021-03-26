import mysql.connector as connector
from mysql.connector.errors import Error
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE
import json
import re
import datetime


COURIER_FIELDS = ('courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings')
ORDER_FIELDS = ('id', 'weight', 'region', 'delivery_hours', 'courier_id', 'assign_time', 'complete_time')

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
        query = f'''
            INSERT INTO
                orders (id, weight, region, delivery_hours)
            VALUES (%s, %s, %s, %s)
        '''
        for order in orders:
            self.curr.execute(
                query,
                (
                    order['order_id'],
                    round(order['weight'], 2),
                    order['region'],
                    json.dumps([x.strip() for x in order['delivery_hours']])
                )
            )
            orders_ids.append({'id': order['order_id']})
        self.conn.commit()
        return orders_ids

    # объединить с get_courier(?)
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

    def find_relevant_orders(self, courier_id, max_weight, regions, working_hours):
        self.check_connection()

        # filter weight and region
        query = f'''
            SELECT
                id, delivery_hours
            FROM
                orders
            WHERE
                weight<={max_weight} AND
                region in ({', '.join(map(str, regions))}) AND
                courier_id IS NULL
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
                res1.append(id)

        if not res1:
            return res1, None
        date_tz = datetime.datetime.now(datetime.timezone.utc)

        # выделиить в другую функцию
        # assign relevant orders
        query = f'''
            UPDATE
                orders
            SET
                courier_id={courier_id},
                assign_time='{str(date_tz)}'
            WHERE
                id IN ({', '.join(map(str, res1))})
        '''
        self.curr.execute(query)
        self.conn.commit()
        res1 = [{'id': id} for id in res1]
        return res1, date_tz

    def check_order_assignment(self, courier_id, order_id):
        self.check_connection()
        query = f'''
            SELECT
                COUNT(*)
            FROM
                orders
            WHERE
                id={order_id} AND
                courier_id={courier_id}
        '''
        self.curr.execute(query)
        return self.curr.fetchone()[0]

    def mark_as_completed(self, courier_id, order_id, complete_time):
        self.check_connection()
        # менять ли complete_time?
        query = f'''
            UPDATE 
                orders
            SET
                complete_time='{complete_time}'
            WHERE 
                courier_id={courier_id} AND
                order_id={order_id}
            '''
        self.curr.execute(query)
        self.conn.commit()
