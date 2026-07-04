-- ==========================================
-- TASK 2: Выдвча прав app_user на создание
-- таблиц в схеме public
-- ==========================================

GRANT CREATE ON SCHEMA public TO app_user;

-- ==========================================
-- TASK 4: Создание ролей и расширений
-- Выполняется из-под postgres
-- ==========================================

CREATE ROLE catalog_manager WITH LOGIN PASSWORD 'cmpss';
CREATE ROLE sales_manager WITH LOGIN PASSWORD 'smpss';
CREATE ROLE supervisor WITH LOGIN PASSWORD 'super';
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Auth: схема, таблица, права
CREATE SCHEMA auth;
CREATE TABLE auth.users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    CONSTRAINT role_check CHECK (role IN ('sales_manager', 'catalog_manager'))
);

-- Права на чтение схемы и таблицы для всех ролей (включая будущие)
GRANT USAGE ON SCHEMA auth TO PUBLIC;
GRANT SELECT ON auth.users TO PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA auth 
    GRANT SELECT ON TABLES TO PUBLIC;

-- Право на создание ссылок (для миграций app_user)
GRANT REFERENCES (id) ON auth.users TO app_user;

-- Тестовые пользователи
INSERT INTO auth.users (username, password, role) VALUES 
('cat_man', crypt('cmpss', gen_salt('bf')), 'catalog_manager'),
('sales_man', crypt('smpss', gen_salt('bf')), 'sales_manager'),
('new_sales_man', crypt('newsmpss', gen_salt('bf')), 'sales_manager');

-- Членство в ролях
GRANT catalog_manager TO supervisor;
GRANT sales_manager TO supervisor;

-- =====================================
-- TASK 5
-- =====================================
CREATE ROLE inventory_manager WITH LOGIN PASSWORD 'impss';
CREATE ROLE worker WITH LOGIN PASSWORD 'wpss';

ALTER TABLE auth.users DROP CONSTRAINT role_check;
ALTER TABLE auth.users ADD  CONSTRAINT role_check CHECK (role IN ('sales_manager', 'catalog_manager', 'inventory_manager', 'worker'));

INSERT INTO auth.users (username, password, role) VALUES
('invent_man', crypt('impss', gen_salt('bf')), 'inventory_manager'),
('worker', crypt('wpss', gen_salt('bf')), 'worker');