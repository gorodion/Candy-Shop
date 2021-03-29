import mysql.connector as connector
from mysql.connector.errors import Error
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE
import json
import re
import datetime
from constants import COURIER_FIELDS, COURIER_TYPE_CAPACITY, REQUIRED_COURIER_FIELDS


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

    def check_courier(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT COUNT(*) FROM couriers WHERE id={courier_id}')
        return self.curr.fetchone()[0]

    def insert_couriers(self, couriers):
        self.check_connection()

        couriers_ids = []
        query = '''
            INSERT INTO
                couriers (id, courier_type, regions, working_hours)
            VALUES 
                (%s, %s, %s, %s)
        '''
        for courier in couriers:
            self.curr.execute(
                query,
                (
                    courier['courier_id'],
                    courier['courier_type'],
                    json.dumps(courier['regions']),
                    json.dumps([x.strip() for x in courier['working_hours']])
                )
            )
            couriers_ids.append({'id': courier['courier_id']})
        self.conn.commit()
        return couriers_ids

    @staticmethod
    def map_courier_info(courier_values):
        courier_info = dict(zip(COURIER_FIELDS, courier_values))
        for json_field in ('regions', 'working_hours'):
            courier_info[json_field] = json.loads(courier_info[json_field])
        return courier_info

    # without reconnect
    # transaction is still ongoing
    def find_irrelevant_orders(self, courier_id):
        # select updated courier_info
        self.curr.execute(
            f'''
            SELECT id, courier_type, regions, working_hours
            FROM couriers
            WHERE id={courier_id}
            '''
        )
        courier_values = self.curr.fetchone()
        courier_info = self.map_courier_info(courier_values)

        # case when regions or working_hours fields are empty
        if not courier_info['regions'] or not courier_info['working_hours']:
            self.curr.execute(
                f'''
                UPDATE orders
                SET
                    courier_id=NULL,
                    assign_time=NULL
                WHERE
                    courier_id={courier_id} AND
                    complete_time IS NULL
                '''
            )
            return courier_info

        # updating by weight and region
        self.curr.execute(
            f'''
            UPDATE orders
            SET
                courier_id=NULL,
                assign_time=NULL
            WHERE
                courier_id={courier_id} AND
                complete_time IS NULL AND
                (
                    weight>{COURIER_TYPE_CAPACITY[courier_info['courier_type']]} OR
                    region NOT IN ({', '.join(map(str, courier_info['regions']))})
                )
            '''
        )

        # updating by working_hours
        query = f'''
            SELECT id, delivery_hours
            FROM orders
            WHERE
                courier_id={courier_id} AND
                complete_time IS NULL
        '''
        self.curr.execute(query)
        res0 = self.curr.fetchall()
        working_hours = courier_info['working_hours']

        res1 = []
        for (id, delivery_hours) in res0:
            delivery_hours = json.loads(delivery_hours)
            intersect = any(self.intervals_intersect(i, j)
                            for i in working_hours
                            for j in delivery_hours)
            if not intersect:
                res1.append(id)
        if res1:
            print(f'''
                UPDATE
                    orders
                SET
                    courier_id=NULL,
                    assign_time=NULL
                WHERE
                    id IN ({', '.join(map(str, res1))})
                ''')
            self.curr.execute(
                f'''
                UPDATE
                    orders
                SET
                    courier_id=NULL,
                    assign_time=NULL
                WHERE
                    id IN ({', '.join(map(str, res1))})
                '''
            )
        return courier_info

    def patch_courier(self, courier_id, content):
        self.check_connection()

        query = f'''
            UPDATE
                couriers
            SET
                courier_type=IF(%s, %s, courier_type),
                regions=IF(%s, %s, regions),
                working_hours=IF(%s, %s, working_hours)
            WHERE
                id=%s
            '''
        self.curr.execute(
            query,
            (
                'courier_type' in content, content.get('courier_type'),
                'regions' in content, json.dumps(content.get('regions')),
                'working_hours' in content, json.dumps(content.get('working_hours')),
                courier_id
            )
        )

        courier_info = self.find_irrelevant_orders(courier_id)
        self.conn.commit()
        return courier_info

    def calculate_rating(self, courier_id):
        self.curr.execute(
            f'''
            SELECT *
            FROM orders
            WHERE courier_id={courier_id} AND complete_time IS NOT NULL
            '''
        )
        res = self.curr.fetchall()
        rating = 0
        return rating

    def get_courier(self, courier_id):
        self.check_connection()
        self.curr.execute(f'SELECT * FROM couriers WHERE id={courier_id}')
        courier_values = self.curr.fetchone()
        if courier_values is None:
            return courier_values

        courier_info = self.map_courier_info(courier_values)
        courier_info['rating'] = self.calculate_rating(courier_id)

        return courier_info

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

    @staticmethod
    def extract_interval_ends(interval: str):
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
                region IN ({', '.join(map(str, regions))}) AND
                courier_id IS NULL
        '''
        self.curr.execute(query)
        # result without working_hours
        res0 = self.curr.fetchall()

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

    # also returns assign_time
    def check_order_assignment(self, courier_id, order_id):
        self.check_connection()
        query = f'''
            SELECT
                COUNT(*), assign_time
            FROM
                orders
            WHERE
                id={order_id} AND
                courier_id={courier_id}
        '''
        self.curr.execute(query)
        return self.curr.fetchone()

    def mark_as_completed(self, courier_id, order_id, complete_time):
        self.check_connection()
        self.curr.execute(f'''
            SELECT COUNT(*) FROM orders 
            WHERE id={order_id} AND courier_id={courier_id} AND complete_time IS NULL''')
        not_marked = self.curr.fetchone()[0]

        if not_marked:
            self.curr.execute(
                f'''
                UPDATE couriers 
                SET earnings = earnings + 500 * (CASE 
                    WHEN courier_type='foot' THEN 2
                    WHEN courier_type='bike' THEN 5
                    WHEN courier_type='car' THEN 9
                    END)
                WHERE id={courier_id}
                '''
            )
        self.curr.execute(
            f'''
            UPDATE orders
            SET complete_time='{str(complete_time)}'
            WHERE id={order_id} AND courier_id={courier_id}
            '''
        )
        self.conn.commit()
