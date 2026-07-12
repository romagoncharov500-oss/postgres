from dataclasses import dataclass

from prompt_toolkit import prompt
from psycopg.rows import class_row
from rich.table import Table

from db import get_conn
from console import console

from commands import command, CATEGORY_WAREHOUSES
from auth import ROLE_INVENTORY_MANAGER


@dataclass
class WarehouseStockRow:
    product_name: str
    total_quantity: int
    available_quantity: int
    reserve_quantity: int


@dataclass
class ProductStockRow:
    warehouse_name: str
    total_quantity: int
    available_quantity: int
    reserve_quantity: int


def _create_stock_table(title: str, first_column: str) -> Table:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column(first_column, style="dim", width=50, justify="left")
    table.add_column("Общее количество", style="green", min_width=15, justify="right")
    table.add_column("Доступно", style="yellow", min_width=10, justify="right")
    table.add_column("Резерв", style="magenta", min_width=10, justify="right")
    return table


@command(
    "view warehouse stock",
    "Просмотр всех товаров на всех складах",
    CATEGORY_WAREHOUSES,
    [ROLE_INVENTORY_MANAGER],
)
def view_warehouse_stock() -> None:
    query = """
        SELECT
            p.name                                     AS product_name,
            COALESCE(s_agg.total_quantity, 0) +
            COALESCE(r_agg.reserve_quantity, 0)           AS total_quantity,
            COALESCE(s_agg.total_quantity, 0)           AS available_quantity,
            COALESCE(r_agg.reserve_quantity, 0)         AS reserve_quantity
        FROM catalog.products p
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS total_quantity
            FROM inventory.stock
            GROUP BY product_id
        ) s_agg ON s_agg.product_id = p.id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS reserve_quantity
            FROM inventory.reserves
            GROUP BY product_id
        ) r_agg ON r_agg.product_id = p.id
        ORDER BY p.name;
    """
    conn = get_conn()
    with conn.cursor(row_factory=class_row(WarehouseStockRow)) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    table = _create_stock_table("Остатки по складам", "Продукт")
    for row in rows:
        table.add_row(
            row.product_name,
            str(row.total_quantity),
            str(row.available_quantity),
            str(row.reserve_quantity),
        )
    console.print(table)


@command(
    "view product stock",
    "Просмотр остатков продукта на складах",
    CATEGORY_WAREHOUSES,
    [ROLE_INVENTORY_MANAGER],
)
def view_product_stock() -> None:
    product_id = prompt("Введите ID продукта: ").strip()
    if not product_id.isdigit():
        console.print("[red]ID должен быть числом[/red]")
        return

    query = """
        SELECT
            c.name || ', ' || w.address        AS warehouse_name,
            COALESCE(s.quantity, 0)    +
            COALESCE(r_agg.reserve_qty, 0)     AS total_quantity,
            COALESCE(s.quantity, 0)            AS available_quantity,
            COALESCE(r_agg.reserve_qty, 0)     AS reserve_quantity
        FROM catalog.warehouses w
        JOIN catalog.cities c ON c.id = w.city_id
        LEFT JOIN inventory.stock s ON s.warehouse_id = w.id AND s.product_id = %s
        LEFT JOIN (
            SELECT o.warehouse_id, SUM(r.quantity) AS reserve_qty
            FROM inventory.reserves r
            JOIN sales.orders o ON o.id = r.order_id
            WHERE r.product_id = %s
            GROUP BY o.warehouse_id
        ) r_agg ON r_agg.warehouse_id = w.id
        ORDER BY available_quantity DESC, warehouse_name;
    """
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductStockRow)) as cur:
        cur.execute(query, (int(product_id), int(product_id)))
        rows = cur.fetchall()

    if not rows:
        console.print("[yellow]Продукт не найден или отсутствует на складах[/yellow]")
        return

    table = _create_stock_table(f"Остатки продукта #{product_id} по складам", "Склад")
    for row in rows:
        table.add_row(
            row.warehouse_name,
            str(row.total_quantity),
            str(row.available_quantity),
            str(row.reserve_quantity),
        )
    console.print(table)