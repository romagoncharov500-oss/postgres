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

ALTER TABLE catalog.warehouses
    ADD CONSTRAINT warehouse_city_ref 
    FOREIGN KEY (city)
    REFERENCES catalog.cities (name)
