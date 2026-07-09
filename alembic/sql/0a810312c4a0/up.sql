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
    
ALTER TABLE catalog.warehouses ADD COLUMN city_id_ref INTEGER;

UPDATE catalog.warehouses SET city_id_ref = c.id FROM catalog.cities c WHERE c.name = city; 

ALTER TABLE catalog.warehouses DROP COLUMN city;

ALTER TABLE catalog.warehouses RENAME COLUMN city_id_ref TO city_id;

ALTER TABLE catalog.warehouses
    ADD CONSTRAINT warehouse_city_ref 
    FOREIGN KEY (city_id)
    REFERENCES catalog.cities (id);
