CREATE TABLE couriers (
	id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
	courier_type ENUM('foot', 'bike', 'car') NOT NULL,
	regions JSON NOT NULL,
	working_hours JSON NOT NULL,
	rating FLOAT NOT NULL DEFAULT 0,
	earnings INT NOT NULL DEFAULT 0
);

CREATE TABLE orders (
	id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
	weight DOUBLE NOT NULL,
	region INT NOT NULL,
	delivery_hours JSON NOT NULL,
	courier_id BIGINT UNSIGNED,
	assign_time DATETIME,
	complete_time DATETIME,
	FOREIGN KEY (courier_id)
		REFERENCES couriers (id)
);

