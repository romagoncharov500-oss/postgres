-- 1. Удаляем внешний ключ
ALTER TABLE sales.orders DROP CONSTRAINT IF EXISTS created_by_ref;

-- 2. Удаляем колонку
ALTER TABLE sales.orders DROP COLUMN IF EXISTS created_by;