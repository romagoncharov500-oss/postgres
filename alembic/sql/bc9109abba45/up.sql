ALTER TABLE sales.orders 
    ADD COLUMN created_by INTEGER NOT NULL 
    DEFAULT (SELECT id FROM auth.users WHERE role = 'sales_manager' LIMIT 1);

ALTER TABLE sales.orders 
    ADD CONSTRAINT created_by_ref FOREIGN KEY (created_by) REFERENCES auth.users (id);

ALTER TABLE sales.orders 
    ALTER COLUMN created_by DROP DEFAULT;