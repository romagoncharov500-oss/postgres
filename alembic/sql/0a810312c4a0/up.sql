CREATE TABLE catalog.cities (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO catalog.cities (name) VALUES
    ('Москва'),
    ('Санкт-Петербург'),
    ('Новосибирск'),
    ('Екатеринбург'),
    ('Казань'),
    ('Нижний Новгород'),
    ('Челябинск'),
    ('Самара'),
    ('Омск'),
    ('Ростов-на-Дону'),
    ('Красноярск'),
    ('Воронеж'),
    ('Пермь'),
    ('Уфа'),
    ('Волгоград');
    
ALTER TABLE catalog.warehouses ADD COLUMN city_name_ref TEXT;

UPDATE catalog.warehouses SET city_name_ref = city; 

ALTER TABLE catalog.warehouses DROP COLUMN city;

ALTER TABLE catalog.warehouses RENAME COLUMN city_name_ref TO city;

ALTER TABLE catalog.warehouses
    ADD CONSTRAINT warehouse_city_ref 
    FOREIGN KEY (city)
    REFERENCES catalog.cities (name);
