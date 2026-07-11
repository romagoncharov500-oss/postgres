from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import prompt
from psycopg.rows import class_row
from psycopg.errors import SerializationFailure
from rich.table import Table
from rich.panel import Panel

from console import console, render_error
from db import get_conn
from validators import ChoiceValidator, PositiveIntValidator, YesNoValidator
from commands import command, CATEGORY_ORDERS
from auth import ROLE_SALES_MANAGER, ROLE_INVENTORY_MANAGER
from handlers.order_items import add_item, _get_order_items_info, _create_order_item_info_table
from handlers.warehouses import _get_warehouse_location
from auth import auth_user
from users import get_user


valid_statuses = [
    "unpublished", 
    "new", 
    "processing",
    "pending",
    "packing",
    "shipped",
]

status_completer = WordCompleter(valid_statuses, ignore_case=True, sentence=True)
status_validator = ChoiceValidator(
    valid_statuses, message="Статуст должен быть из списка."
)


@dataclass
class Order:
    id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    warehouse_id: int
    created_by: int
    processed_by: Optional[int] = None


def _get_order(_id: int) -> Order | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE id = %s", (_id,))
        order = cur.fetchone()

    if order is None:
        render_error(f"Заказ с ID {_id} не найден.")

    return order


def _has_unpublished_status(_order : Order) -> bool:
    if _order.status != "unpublished":
        render_error(f"Заказ ID: {_order.id} уже опубликован (статус: '{_order.status}'). Изменения запрещены.")
        return False
    else:
        return True


def _create_orders_table() -> Table:
    table = Table(title="Заказы", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Статус", style="green", min_width=20)
    table.add_column("Общая сумма", style="yellow", min_width=30)
    table.add_column("Создан", style="magenta", min_width=15)
    table.add_column("Склад", style="magenta", min_width=15)
    table.add_column("Создал", style="magenta", min_width=15)

    return table


def _render_order(order: Order) -> None:
    # Основная информация о заказе
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Поле", style="bold cyan", width=20)
    info_table.add_column("Значение", style="white")

    warehouse_location = _get_warehouse_location(order.warehouse_id)
    created_by_user = get_user(order.created_by)
    created_at_str = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else ""

    info_table.add_row("ID", str(order.id))
    info_table.add_row("Статус", order.status)
    info_table.add_row("Общая сумма", f"{order.total_amount:.2f}")
    info_table.add_row("Создан", created_at_str)
    info_table.add_row("Склад отгрузки", f"{warehouse_location} (ID: {order.warehouse_id})")
    info_table.add_row("Создал", created_by_user.username)

    order_panel = Panel(
        info_table,
        expand=False,
        title=f"[bold green]Заказ ID: {order.id}[/bold green]",
        border_style="green",
    )
    console.print(order_panel)

    # Позиции заказа
    items = _get_order_items_info(order.id)
    if not items:
        console.print("[yellow]Позиции заказа не найдены[/yellow]")
        return

    items_table = _create_order_item_info_table()
    for item in items:
        items_table.add_row(
            item.product_name,
            f"{item.price:.2f}",
            str(item.quantity),
            item.item_status,
        )
    console.print(items_table)


@command("list orders", "список всех заказов", CATEGORY_ORDERS, [ROLE_SALES_MANAGER, ROLE_INVENTORY_MANAGER])
def list_orders() -> None:
    conn = get_conn()
    table = _create_orders_table()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders")
        orders: list[Order] = cur.fetchall()

    for order in orders:
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            str(order.created_at),
            str(order.warehouse_id),
            get_user(order.created_by).username
        )
    console.print(table)
        

def _list_orders_by_status(status: str) -> None:
    conn = get_conn()
    table = _create_orders_table()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE status = %s", (status,))
        orders: list[Order] = cur.fetchall()

    for order in orders:
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            str(order.created_at),
            str(order.warehouse_id),
            get_user(order.created_by).username
        )
    console.print(table)


@command("list orders new", "просмотр новых заказов", CATEGORY_ORDERS, [ROLE_INVENTORY_MANAGER])
def list_orders_new() -> None:
    _list_orders_by_status("new")


@command("list orders processing", "просмотр заказов в обработке", CATEGORY_ORDERS, [ROLE_INVENTORY_MANAGER])
def list_orders_processing() -> None:
    _list_orders_by_status("processing")


@command("list orders my", "мои заказы", CATEGORY_ORDERS, [ROLE_INVENTORY_MANAGER])
def list_orders_my() -> None:
    conn = get_conn()
    table = _create_orders_table()

    with conn.cursor(row_factory=class_row(Order)) as cur:
        cur.execute("SELECT * FROM sales.orders WHERE processed_by = %s", (auth_user().id,))
        orders: list[Order] = cur.fetchall()

    for order in orders:
        table.add_row(
            str(order.id),
            order.status,
            str(order.total_amount),
            str(order.created_at),
            str(order.warehouse_id),
            get_user(order.created_by).username
        )
    console.print(table)



@command("show orders", "информация о заказах", CATEGORY_ORDERS, [ROLE_SALES_MANAGER, ROLE_INVENTORY_MANAGER])
def show_order(_id: str) -> None:
    order = _get_order(int(_id))
    if order is None:
        return
    else:
        _render_order(order)

    
@command("add order", "добавить новый заказ", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def add_order() -> None:
    warehouse_id_str = prompt("ID склада для отгрузки: ", validator=PositiveIntValidator())
    warehouse_id = int(warehouse_id_str)

    status = "unpublished"

    conn = get_conn()
    # Создаем заказ и сразу получаем его новый ID через RETURNING
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sales.orders (status, total_amount, warehouse_id, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
            (status, 0.00, warehouse_id, auth_user().id) # total_amount изначально 0, пересчитается при добавлении товаров
        )
        new_order_id = cur.fetchone()[0]

    console.print(f"[green] Заказ ID: {new_order_id} успешно создан.[/green]")
    conn.commit()
    # Интерактивное предложение добавить товары сразу
    add_items_now = prompt("Добавить товары в этот заказ прямо сейчас?", validator=YesNoValidator())
    if YesNoValidator.is_yes(add_items_now):
        add_item(str(new_order_id))


@command("edit order", "изменить статус или склад заказа", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def edit_order(_id: str) -> None:
    conn = get_conn()
    order_id = int(_id)
    order = _get_order(order_id)

    if order is None:
        return

    if not _has_unpublished_status(order):
        return
    
    console.print(f"Редактирование заказа ID: {order.id} (текущий статус: {order.status}, склад: {order.warehouse_id})")

    new_warehouse_str = prompt(
        "Новый ID склада (отображен текущий): ",
        validator=PositiveIntValidator(),
        default=str(order.warehouse_id)
    ).strip()
    
    conn.execute("UPDATE sales.orders SET warehouse_id = %s WHERE id = %s", (new_warehouse_str, order_id))
    console.print(f"[green] Заказ ID: {order.id} успешно обновлен.[/green]")


@command("publish order", "опубликовать заказ (сменить статус на new)", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def publish_order(_id: str) -> None:

    order_id = int(_id)

    order = _get_order(order_id)
    if order is None:
        return

    # Проверяем, можно ли публиковать этот заказ
    if order.status != "unpublished":
        render_error(f"Заказ ID: {order_id} уже имеет статус '{order.status}'. Публикация возможна только для статуса 'unpublished'.")
        return

    # Меняем статус на 'new'
    conn = get_conn()
    conn.execute(
        "UPDATE sales.orders SET status = %s WHERE id = %s",
        ("new", order_id)
    )
    
    console.print(f"[green] Заказ ID: {order_id} успешно опубликован (статус изменен на 'new').[/green]")


@command("delete order", "удалить заказ", CATEGORY_ORDERS, [ROLE_SALES_MANAGER])
def delete_order(_id: str) -> None:
    conn = get_conn()
    order_id = int(_id)
    order = _get_order(order_id)

    if order is None:
        return
    
    if not _has_unpublished_status(order):
        return

    confirm = prompt(f"Вы уверены, что хотите удалить заказ ID: {_id} и все товары в нем? (y/n): ", validator=YesNoValidator())
    if YesNoValidator.is_no(confirm):
        console.print("[yellow]Удаление отменено.[/yellow]")
        return

    # Благодаря ON DELETE CASCADE в миграции, order_items удалятся автоматически!
    conn.execute("DELETE FROM sales.orders WHERE id = %s", (_id,))
    console.print(f"[green] Заказ ID: {_id} и все его позиции успешно удалены.[/green]")


@command("mark order processing", "взять заказ в обработку", CATEGORY_ORDERS, [ROLE_INVENTORY_MANAGER])
def mark_order_processing(_id: str) -> None:
    order_id = int(_id)

    # 1. Быстрая проверка снаружи транзакции (обычное чтение, без блокировки)
    order = _get_order(order_id)
    if order is None:
        return

    if order.status != "new":
        render_error(
            f"Заказ ID: {order_id} имеет статус '{order.status}'. "
            "В обработку можно взять только заказ со статусом 'new'."
        )
        return

    # Показываем информацию о заказе
    _render_order(order)

    # Запрашиваем подтверждение
    confirm = prompt(
        f"Взять заказ ID: {order_id} в обработку? (y/n): ",
        validator=YesNoValidator()
    )
    if YesNoValidator.is_no(confirm):
        console.print("[yellow]Операция отменена.[/yellow]")
        return

    # 2. Транзакция с REPEATABLE READ — защита от гонки
    conn = get_conn()
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

            with conn.cursor(row_factory=class_row(Order)) as cur:
                cur.execute(
                    "SELECT * FROM sales.orders WHERE id = %s",
                    (order_id,)
                )
                order = cur.fetchone()

                # Повторная проверка — теперь под изоляцией
                if order is None or order.status != "new":
                    render_error("Заказ уже обработан другим менеджером.")
                    return

                cur.execute(
                    "UPDATE sales.orders SET status = %s, processed_by = %s WHERE id = %s",
                    ("processing", auth_user().id, order_id)
                )
            # COMMIT автоматически при выходе из with

    except SerializationFailure:
        render_error(
            "Не удалось обработать заказ: другой менеджер опередил вас. "
            "Попробуйте снова."
        )
        return

    console.print(f"[green] Заказ ID: {order_id} взят в обработку пользователем {auth_user().username}.[/green]")
