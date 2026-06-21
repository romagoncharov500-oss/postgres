-- 1. Добавляем колонку как NULLABLE (без DEFAULT)
ALTER TABLE sales.orders 
    ADD COLUMN created_by INTEGER;

-- 2. Заполняем существующие записи ID пользователя с ролью sales_manager
UPDATE sales.orders SET created_by = (SELECT id FROM auth.users WHERE role = 'sales_manager' LIMIT 1);

-- 3. Делаем колонку NOT NULL (теперь все строки заполнены)
ALTER TABLE sales.orders 
    ALTER COLUMN created_by SET NOT NULL;

-- 4. Добавляем внешний ключ
ALTER TABLE sales.orders 
    ADD CONSTRAINT created_by_ref FOREIGN KEY (created_by) REFERENCES auth.users (id);