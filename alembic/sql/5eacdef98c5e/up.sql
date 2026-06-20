-- 1. Выдаем права на использование самих схем (иначе роли в них не зайдут)
GRANT USAGE ON SCHEMA catalog TO catalog_manager, sales_manager;
GRANT USAGE ON SCHEMA sales TO sales_manager;

-- 2. catalog_manager: любые операции в catalog (все существующие таблицы)
GRANT ALL ON ALL TABLES IN SCHEMA catalog TO catalog_manager;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA catalog 
    GRANT ALL ON TABLES TO catalog_manager;

-- 3. sales_manager: любые операции в sales (все существующие таблицы)
GRANT ALL ON ALL TABLES IN SCHEMA sales TO sales_manager;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA sales 
    GRANT ALL ON TABLES TO sales_manager;

-- 4. sales_manager: чтение из catalog (текущие таблицы)
GRANT SELECT ON ALL TABLES IN SCHEMA catalog TO sales_manager;

-- 5. Будущие таблицы в catalog должны быть доступны на чтение ВСЕМ (включая sales_manager)
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA catalog 
    GRANT SELECT ON TABLES TO PUBLIC;