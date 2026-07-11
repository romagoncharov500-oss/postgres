-- Отзываем права
REVOKE UPDATE (processed_by) ON TABLE sales.orders FROM inventory_manager;

-- Удаляем внешний ключ
ALTER TABLE sales.orders 
    DROP CONSTRAINT processed_by_ref;

-- Удаляем колонку
ALTER TABLE sales.orders 
    DROP COLUMN processed_by;
