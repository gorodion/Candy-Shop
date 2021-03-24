DROP TABLE IF EXISTS couriers;
CREATE TABLE couriers (
	id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
	courier_type ENUM('foot', 'bike', 'car') NOT NULL,
	regions JSON NOT NULL,
	working_hours JSON NOT NULL,
	rating FLOAT NOT NULL DEFAULT 0,
	earnings INT NOT NULL DEFAULT 0
);

INSERT INTO
	couriers (id, courier_type, regions, working_hours)
VALUES
	(1, 'foot', '[3, 4, 5]', '["13:00", "20:00"]'),
	(2, 'car', '[2, 3, 5]', '["9:00", "21:00"]'),
	(3, 'bike', '[1, 3, 4]', '["10:00", "16:00"]'),
	(4, 'bike', '[2, 4]', '["15:00", "20:00"]');

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
	id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
	weight DOUBLE NOT NULL,
	region INT NOT NULL,
	delivery_hours JSON NOT NULL,
	courier_id BIGINT UNSIGNED,
	complete_time DATETIME,
	FOREIGN KEY (courier_id)
		REFERENCES couriers (id)
);

INSERT INTO 
	orders (id, weight, region, delivery_hours)
VALUES
	(1, 3, 5, '["15:30", "16:30"]'),
	(2, 0.5, 2, '["12:00", "13:00"]'),
	(3, 1, 3, '["15:00", "16:00"]')
