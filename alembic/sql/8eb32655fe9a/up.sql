CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE sales.orders (
    id serial PRIMARY KEY,
    status text DEFAULT 'unpublished' NOT NULL,
    total_amount decimal(10, 2) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    warehouse_id integer NOT NULL,
    CONSTRAINT status_check CHECK (status IN ('unpublished', 'new', 'processing', 'pending', 'packing', 'shipped')),
    CONSTRAINT warehouse_ref FOREIGN KEY (warehouse_id) REFERENCES catalog.warehouses (id)
);

CREATE TABLE sales.order_items (
    id serial PRIMARY KEY,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    price decimal(10, 2) NOT NULL,
    -- Ссылка на заказ в схеме sales
    CONSTRAINT order_ref FOREIGN KEY (order_id) REFERENCES sales.orders (id) ON DELETE CASCADE,
    -- Ссылка на товар в схеме catalog
    CONSTRAINT product_ref FOREIGN KEY (product_id) REFERENCES catalog.products (id)
);