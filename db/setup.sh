#!/bin/bash
# Скрипт инициализации БД
# Использование: ./db/setup.sh

echo "Выполняю инициализацию БД..."
psql -h 127.0.0.1 -p 5432 -U postgres -d inventorydb -f db/init.sql
echo "Готово!"