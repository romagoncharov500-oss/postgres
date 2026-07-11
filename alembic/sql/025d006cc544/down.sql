-- Удаляем внешний ключ
ALTER TABLE sales.orders 
    DROP CONSTRAINT processed_by_ref;

-- Удаляем колонку
ALTER TABLE sales.orders 
    DROP COLUMN processed_by;