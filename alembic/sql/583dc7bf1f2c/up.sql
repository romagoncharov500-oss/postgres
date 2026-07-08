CREATE SCHEMA IF NOT EXISTS inventory;

CREATE TABLE inventory.routes (
    from_city_id int NOT NULL, 
    to_city_id int NOT NULL,
    duration interval NOT NULL,
    total_threshold numeric(10, 2) NOT NULL,
    CONSTRAINT from_city_id_ref FOREIGN KEY (from_city_id) REFERENCES catalog.cities (id),
    CONSTRAINT to_city_id_ref FOREIGN KEY (to_city_id) REFERENCES catalog.cities (id),
    CONSTRAINT routes_pk PRIMARY KEY (from_city_id, to_city_id),
    CONSTRAINT routes_different_cities CHECK (from_city_id <> to_city_id)
);

CREATE TABLE inventory.stock(
    product_id   int NOT NULL,
    warehouse_id int NOT NULL,
    quantity int NOT NULL,
    CONSTRAINT product_id_ref FOREIGN KEY (product_id) REFERENCES catalog.products (id),
    CONSTRAINT warehouse_id_ref FOREIGN KEY (warehouse_id) REFERENCES catalog.warehouses (id),
    PRIMARY KEY (product_id, warehouse_id)
);

CREATE TABLE inventory.reserves(
    id serial PRIMARY KEY,
    order_id   int NOT NULL,
    product_id int NOT NULL,
    quantity   int NOT NULL,
    CONSTRAINT order_id_ref FOREIGN KEY (order_id) REFERENCES sales.orders (id),
    CONSTRAINT product_id_ref FOREIGN KEY (product_id) REFERENCES catalog.products (id),
    CONSTRAINT reserves_order_product UNIQUE (order_id, product_id)
);

CREATE TABLE inventory.deliveries(
    order_id int NOT NULL PRIMARY KEY,
    status text DEFAULT 'planned' NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    shipped_at timestamptz,
    CONSTRAINT order_id_ref FOREIGN KEY (order_id) REFERENCES sales.orders(id),
    CONSTRAINT deliveries_status_check CHECK (status IN ('planned', 'shipping', 'shipped'))
);

CREATE TABLE inventory.delivery_items(
    order_id int NOT NULL,
    product_id  int NOT NULL,
    quantity    int NOT NULL,
    status text DEFAULT 'planned' NOT NULL,
    CONSTRAINT delivery_items_status_check CHECK (status IN ('planned', 'shipped')),
    CONSTRAINT delivery_id_ref FOREIGN KEY (order_id) REFERENCES inventory.deliveries (order_id),
    CONSTRAINT product_id_ref FOREIGN KEY (product_id) REFERENCES catalog.products (id),
    PRIMARY KEY(order_id, product_id)
);

CREATE TABLE inventory.transfers (
    id serial PRIMARY KEY,
    from_warehouse_id int NOT NULL, 
    to_warehouse_id   int NOT NULL,
    status text NOT NULL DEFAULT 'planned',
    created_at  timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at  timestamptz,
    arriving_at timestamptz,
    received_at timestamptz,
    CONSTRAINT from_warehouse_id_ref FOREIGN KEY (from_warehouse_id) REFERENCES catalog.warehouses(id),
    CONSTRAINT to_warehouse_id_ref FOREIGN KEY (to_warehouse_id) REFERENCES catalog.warehouses(id),
    CONSTRAINT transfers_status_check CHECK (status IN ('planned','shipping','in_transit','arrived','received')),
    CONSTRAINT transfers_different_warehouses CHECK (from_warehouse_id <> to_warehouse_id)
);

CREATE TABLE inventory.transfer_items (
    id serial PRIMARY KEY,
    transfer_id  int NOT NULL,
    product_id   int NOT NULL,
    quantity     int NOT NULL,
    reserve_id   int REFERENCES inventory.reserves(id),   -- nullable!
    requested_by int NOT NULL REFERENCES auth.users(id),
    status       text NOT NULL DEFAULT 'planned',
    CONSTRAINT transfer_ref FOREIGN KEY (transfer_id) REFERENCES inventory.transfers(id),
    CONSTRAINT product_ref FOREIGN KEY (product_id) REFERENCES catalog.products (id),
    CONSTRAINT reserve_ref FOREIGN KEY (reserve_id) REFERENCES inventory.reserves (id),
    CONSTRAINT transfer_items_status_check CHECK (status IN ('planned', 'shipped', 'received'))
);

-- ============ inventory_manager ============
GRANT ALL ON SCHEMA inventory TO inventory_manager;
GRANT ALL ON ALL TABLES IN SCHEMA inventory TO inventory_manager;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA inventory TO inventory_manager;

GRANT SELECT ON ALL TABLES IN SCHEMA sales TO inventory_manager;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA sales TO inventory_manager;
GRANT UPDATE (status) ON TABLE sales.orders TO inventory_manager;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA sales TO inventory_manager;

ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA inventory
GRANT ALL ON TABLES TO inventory_manager;

ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA inventory
GRANT USAGE, SELECT ON SEQUENCES TO inventory_manager;

-- ============ worker ============
GRANT USAGE ON SCHEMA inventory TO worker;
GRANT SELECT ON ALL TABLES IN SCHEMA inventory TO worker;

GRANT ALL ON TABLE inventory.stock TO worker;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA inventory TO worker;
GRANT UPDATE ON TABLE inventory.reserves TO worker;

GRANT UPDATE (status, shipped_at) ON TABLE inventory.deliveries TO worker;
GRANT UPDATE (status) ON TABLE inventory.delivery_items TO worker;

GRANT UPDATE (status, started_at, arriving_at, received_at)
    ON TABLE inventory.transfers TO worker;
GRANT UPDATE (status) ON TABLE inventory.transfer_items TO worker;
