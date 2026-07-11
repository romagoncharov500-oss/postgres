-- Добавляем колонку processed_by (nullable — не все заказы обработаны)
ALTER TABLE sales.orders 
    ADD COLUMN processed_by INTEGER;

-- Добавляем внешний ключ на auth.users
ALTER TABLE sales.orders 
    ADD CONSTRAINT processed_by_ref FOREIGN KEY (processed_by) REFERENCES auth.users (id);