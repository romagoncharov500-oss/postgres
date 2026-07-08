ALTER TABLE catalog.warehouses DROP CONSTRAINT IF EXISTS warehouse_city_ref;
DELETE FROM catalog.cities;
DROP TABLE IF EXISTS catalog.cities CASCADE;