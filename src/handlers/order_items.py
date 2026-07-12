from dataclasses import dataclass
from decimal import Decimal

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import choice
from psycopg.rows import class_row, scalar_row
from rich.table import Table

from console import console, render_error
from db import get_conn
from validators import PositiveIntValidator, YesNoValidator
from commands import command, CATEGORY_ITEMS
from auth import ROLE_SALES_MANAGER
from handlers.products import Product


@dataclass
class Item:
    order_id: int
    product_id: int
    quantity: int
    price: Decimal


@dataclass
class OrderItemInfo:
    product_name: str
    price: Decimal
    quantity: int
    item_status: str


def _get_order_items_info(order_id: int) -> list[OrderItemInfo]:
    query = """
        SELECT
            p.name AS product_name,
            oi.price,
            oi.quantity,
            CASE
                WHEN di.status = 'shipped' THEN 'отгружено'
                WHEN di.status = 'planned' THEN 'запланирована отгрузка'
                WHEN r.id IS NOT NULL AND r.quantity >= oi.quantity THEN 'в резерве'
                WHEN ti.id IS NOT NULL THEN
                    'в пути из ' || COALESCE(c_wh.name || ', ' || w.address, '?') ||
                    CASE
                        WHEN t.arriving_at IS NOT NULL
                        THEN ', ожидается ' || to_char(t.arriving_at, 'DD.MM.YYYY HH24:MI')
                        ELSE ''
                    END
                ELSE 'ожидает обработки'
            END AS item_status
        FROM sales.order_items oi
        JOIN catalog.products p ON p.id = oi.product_id
        LEFT JOIN inventory.reserves r
            ON r.order_id = oi.order_id AND r.product_id = oi.product_id
        LEFT JOIN inventory.delivery_items di
            ON di.order_id = oi.order_id AND di.product_id = oi.product_id
        LEFT JOIN inventory.transfer_items ti
            ON ti.reserve_id = r.id
        LEFT JOIN inventory.transfers t
            ON t.id = ti.transfer_id
        LEFT JOIN catalog.warehouses w
            ON w.id = t.from_warehouse_id
        LEFT JOIN catalog.cities c_wh
            ON c_wh.id = w.city_id
        WHERE oi.order_id = %s
        ORDER BY oi.product_id;
    """
    conn = get_conn()
    with conn.cursor(row_factory=class_row(OrderItemInfo)) as cur:
        cur.execute(query, (order_id,))
        return cur.fetchall()


def _create_order_item_info_table() -> Table:
    table = Table(title="Позиции заказа", show_header=True, header_style="bold cyan")

    table.add_column("Продукт", style="dim", width=15, justify="right")
    table.add_column("Цена", style="green", min_width=20)
    table.add_column("Количество", style="yellow", min_width=10)
    table.add_column("Статус", style="magenta", min_width=20)

    return table


def _get_availible_products(_order_id: int) -> list[Product]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        # Один запрос: выбираем продукты, которых нет в подзапросе для данного заказа
        cur.execute(
            """
            SELECT * 
            FROM catalog.products 
            WHERE id NOT IN (
                SELECT product_id 
                FROM sales.order_items 
                WHERE order_id = %s
            )
            """,
            (_order_id,)
        )
        return cur.fetchall()
    
    
def _get_order_items(order_id: int) -> list[Item]:
    """Получает список товаров конкретного заказа с названиями."""
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Item)) as cur:
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s", (order_id,))
        return cur.fetchall()
    
    
def _update_order_total(order_id: int) -> None:
    """Пересчитывает total_amount заказа на основе его order_items."""
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Item)) as cur:   
        cur.execute("SELECT * FROM sales.order_items WHERE order_id = %s", (order_id,))
        items: list[Item] = cur.fetchall()

    total_amount_updated = Decimal('0.00')
    for item in items:
        total_amount_updated += item.quantity * item.price

    conn.execute("UPDATE sales.orders SET total_amount = %s WHERE id = %s", (total_amount_updated, order_id,))


def _choose_order_item(order_id: int) -> Item:
    items = _get_order_items(order_id)
    if not items:
        render_error(f"В заказе ID: {order_id} нет товаров для редактирования.")
        return

    options = []
    for item in items:
        display_text = f"Товар (ID продукта: {item.product_id}) | Кол-во: {item.quantity} | Цена: {item.price}"
        options.append((str(item.id), display_text))

    item_id_to_edit = choice(
        message=f"Выберите позицию для редактирования в заказе ID: {order_id}:",
        options=options,
        show_frame=True
    )
    
    return item_id_to_edit


@command("add item", "добавить товары к заказу (интерактивно)", CATEGORY_ITEMS, [ROLE_SALES_MANAGER])
def add_item(_id: str) -> None:
    order_id = int(_id)

    while True:
        products = _get_availible_products(order_id)

        if not products:
            render_error("Каталог товаров пуст или все возможные товары уже были добавлены в заказ. Невозможно добавить позицию.")
            return

        completion_mapping = {}
        for p in products:
            display_name = f"{p.name} (ID: {p.id}, sku: {p.sku}, Цена: {p.price})"
            completion_mapping[display_name] = p

        completer = WordCompleter(list(completion_mapping.keys()), ignore_case=True)

        console.print("\n[bold cyan]--- Добавление товара в заказ ---[/bold cyan]")
        
        # Выбор товара через автокомплит
        product_input = prompt(
            "Введите название товара (начните вводить для подсказки): ",
            completer=completer
        )
        if product_input not in completion_mapping:
            render_error("Товар не распознан. Пожалуйста, выберите вариант из выпадающего списка.")
            continue

        item_to_add = completion_mapping[product_input]

        # Ввод количества с валидацией
        quantity_str = prompt("Введите количество: ", validator=PositiveIntValidator())

        conn = get_conn()
        with conn.cursor() as cur:
                # Вставляем order_id, product_id, quantity и ЦЕНУ на момент покупки
            cur.execute("INSERT INTO sales.order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                    (_id, item_to_add.id, quantity_str, item_to_add.price,))
            
        console.print(f"[green] Товар '{product_input}' (кол-во: {quantity_str}) успешно добавлен в заказ {_id}.[/green]")
    
        add_more = prompt("Добавить еще один товар в этот заказ?", validator=YesNoValidator())
        if YesNoValidator.is_no(add_more):
            _update_order_total(order_id)
            console.print("[bold blue]Добавление товаров завершено.[/bold blue]")
            break


@command("edit item", "изменить количество товара в заказе", CATEGORY_ITEMS, [ROLE_SALES_MANAGER])
def edit_item(_id: str) -> None:
    order_id = int(_id)

    item_to_edit = _choose_order_item(order_id)
    if item_to_edit is None:
        render_error("Не был выбран товар для редактирования заказа")
        return
    
    new_quantity_str = prompt("Введите новое количество: ", validator=PositiveIntValidator())
    new_quantity = int(new_quantity_str)

    conn = get_conn()
    conn.execute(
        "UPDATE sales.order_items SET quantity = %s WHERE order_id = %s AND product_id = %s",
        (new_quantity, item_to_edit.order_id, item_to_edit.product_id,)
    )
    _update_order_total(order_id)
    console.print(f"[green] Количество успешно обновлено на {new_quantity} для позиции в заказе ID: {order_id}.[/green]")
    

@command("delete item", "удалить товар из заказа", CATEGORY_ITEMS, [ROLE_SALES_MANAGER])
def delete_item(_id: str) -> None:
    order_id = int(_id)
 
    item_to_delete = _choose_order_item(order_id)
    if item_to_delete is None:
        render_error("Не был выбран товар для удаления из заказа")
        return
    
    conn = get_conn()
    conn.execute(
        "DELETE FROM sales.order_items WHERE order_id = %s AND product_id = %s",
        (item_to_delete.order_id, item_to_delete.product_id,)
    )
    _update_order_total(order_id)
    console.print(f"[green] Товар успешно удален из заказа ID: {order_id}.[/green]")
