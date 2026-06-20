-- 1. Откатываем права на использование схем
REVOKE USAGE ON SCHEMA catalog FROM catalog_manager, sales_manager;
REVOKE USAGE ON SCHEMA sales FROM sales_manager;

-- 2. Откатываем права на существующие таблицы в catalog
REVOKE ALL ON ALL TABLES IN SCHEMA catalog FROM catalog_manager;
REVOKE SELECT ON ALL TABLES IN SCHEMA catalog FROM sales_manager;

-- 3. Откатываем права на существующие таблицы в sales
REVOKE ALL ON ALL TABLES IN SCHEMA sales FROM sales_manager;

-- 4. Откатываем ALTER DEFAULT PRIVILEGES для catalog (ALL для catalog_manager)
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA catalog 
    REVOKE ALL ON TABLES FROM catalog_manager;

-- 5. Откатываем ALTER DEFAULT PRIVILEGES для sales (ALL для sales_manager)
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA sales 
    REVOKE ALL ON TABLES FROM sales_manager;

-- 6. Откатываем ALTER DEFAULT PRIVILEGES для catalog (SELECT для PUBLIC)
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA catalog 
    REVOKE SELECT ON TABLES FROM PUBLIC;