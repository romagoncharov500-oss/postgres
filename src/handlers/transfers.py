from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from psycopg.rows import class_row
from psycopg.errors import SerializationFailure
from rich.table import Table

from console import console, render_error
from db import get_conn
from validators import PositiveIntValidator, YesNoValidator, ChoiceValidator
from commands import command, CATEGORY_TRANSFERS
from auth import ROLE_INVENTORY_MANAGER
from auth import auth_user
from users import get_user
from cities import _get_city_name
from handlers.warehouses import Warehouse
from handlers.routes import _get_existing_routes


@dataclass
class Transfer:
    id: int
    from_warehouse_id: int
    to_warehouse_id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    arriving_at: Optional[datetime] = None
    received_at: Optional[datetime] = None


@dataclass
class TransferItem:
    id: int
    transfer_id: int
    product_id: int
    quantity: int
    reserve_id: Optional[int] = None
    requested_by: Optional[int] = None
    status: str = "planned"


@dataclass
class StockRow:
    product_id: int
    product_name: str
    total_quantity: int
    available_quantity: int


def _get_warehouses_by_city(city_id: int) -> list[Warehouse]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute(
            "SELECT * FROM catalog.warehouses WHERE city_id = %s ORDER BY id",
            (city_id,),
        )
        return cur.fetchall()


def _warehouse_display(wh: Warehouse) -> str:
    label = f" ({wh.label})" if wh.label else ""
    return f"{_get_city_name(wh.city_id)}, {wh.address}{label}"


def _select_city(prompt_text: str) -> Optional[str]:
    """Выбор города из списка."""
    routes = _get_existing_routes()
    cities = sorted({_get_city_name(r.from_city_id) for r in routes})
    if not cities:
        render_error("Нет доступных маршрутов.")
        return None
    completer = WordCompleter(cities, ignore_case=True, sentence=True)
    validator = ChoiceValidator(cities)
    return prompt(prompt_text, completer=completer, validator=validator).strip()


def _get_stock_for_warehouse(warehouse_id: int) -> list[StockRow]:
    conn = get_conn()
    query = """
        SELECT p.id AS product_id, p.name AS product_name,
               COALESCE(s.quantity, 0)::int AS total_quantity,
               (COALESCE(s.quantity, 0) - COALESCE(r_agg.reserve_qty, 0))::int AS available_quantity
        FROM catalog.products p
        LEFT JOIN inventory.stock s ON s.product_id = p.id AND s.warehouse_id = %s
        LEFT JOIN (
            SELECT r.product_id, SUM(r.quantity) AS reserve_qty
            FROM inventory.reserves r
            JOIN sales.orders o ON o.id = r.order_id
            WHERE o.warehouse_id = %s
            GROUP BY r.product_id
        ) r_agg ON r_agg.product_id = p.id
        WHERE COALESCE(s.quantity, 0) > 0
        ORDER BY p.name
    """
    with conn.cursor(row_factory=class_row(StockRow)) as cur:
        cur.execute(query, (warehouse_id, warehouse_id))
        return cur.fetchall()


def _get_or_create_planned_transfer(from_wh: int, to_wh: int) -> Optional[int]:
    """Внутри транзакции с LOCK TABLE. Ищет или создаёт planned transfer."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM inventory.transfers
               WHERE from_warehouse_id = %s AND to_warehouse_id = %s AND status = 'planned'
               FOR UPDATE""",
            (from_wh, to_wh),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            """INSERT INTO inventory.transfers (from_warehouse_id, to_warehouse_id, status)
               VALUES (%s, %s, 'planned') RETURNING id""",
            (from_wh, to_wh),
        )
        return cur.fetchone()[0]


def _get_my_transfers() -> list[Transfer]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Transfer)) as cur:
        cur.execute(
            """SELECT DISTINCT t.id, t.from_warehouse_id, t.to_warehouse_id,
                      t.status, t.created_at, t.started_at, t.arriving_at, t.received_at
               FROM inventory.transfers t
               JOIN inventory.transfer_items ti ON ti.transfer_id = t.id
               WHERE t.status = 'planned' AND ti.requested_by = %s
               ORDER BY t.id""",
            (auth_user().id,),
        )
        return cur.fetchall()


def _get_transfer_items(transfer_id: int) -> list[TransferItem]:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(TransferItem)) as cur:
        cur.execute(
            "SELECT * FROM inventory.transfer_items WHERE transfer_id = %s ORDER BY product_id",
            (transfer_id,),
        )
        return cur.fetchall()


def _get_city_id_by_warehouse(warehouse_id: int) -> int:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT city_id FROM catalog.warehouses WHERE id = %s", (warehouse_id,))
        row = cur.fetchone()
        return row[0] if row else 0


# ===================== КОМАНДЫ =====================


@command(
    "add transfer items",
    "добавить товары в перемещение (интерактивно)",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def add_transfer_items() -> None:
    # 1. Выбор маршрута
    routes = _get_existing_routes()
    if not routes:
        render_error("Нет маршрутов.")
        return

    from_cities = sorted({_get_city_name(r.from_city_id) for r in routes})
    from_completer = WordCompleter(from_cities, ignore_case=True, sentence=True)
    from_validator = ChoiceValidator(from_cities)

    from_city = prompt("Город отправления: ", completer=from_completer, validator=from_validator).strip()
    from_city_id = None
    for r in routes:
        if _get_city_name(r.from_city_id) == from_city:
            from_city_id = r.from_city_id
            break

    to_cities = sorted({
        _get_city_name(r.to_city_id) for r in routes if r.from_city_id == from_city_id
    })
    to_completer = WordCompleter(to_cities, ignore_case=True, sentence=True)
    to_validator = ChoiceValidator(to_cities)
    to_city = prompt("Город назначения: ", completer=to_completer, validator=to_validator).strip()
    to_city_id = None
    for r in routes:
        if r.from_city_id == from_city_id and _get_city_name(r.to_city_id) == to_city:
            to_city_id = r.to_city_id
            break

    # 2. Выбор складов в городах
    from_warehouses = _get_warehouses_by_city(from_city_id)
    to_warehouses = _get_warehouses_by_city(to_city_id)
    if not from_warehouses or not to_warehouses:
        render_error("В одном из городов нет складов.")
        return

    wh_from_opts = {_warehouse_display(w): w for w in from_warehouses}
    wh_to_opts = {_warehouse_display(w): w for w in to_warehouses}
    wh_completer = WordCompleter(list(wh_from_opts.keys()), ignore_case=True)

    from_input = prompt("Склад отправления: ", completer=wh_completer).strip()
    from_wh = wh_from_opts.get(from_input)
    if not from_wh:
        render_error("Склад не распознан.")
        return

    to_completer = WordCompleter(list(wh_to_opts.keys()), ignore_case=True)
    to_input = prompt("Склад получения: ", completer=to_completer).strip()
    to_wh = wh_to_opts.get(to_input)
    if not to_wh:
        render_error("Склад не распознан.")
        return

    # 3. Цикл добавления товаров
    while True:
        stock = _get_stock_for_warehouse(from_wh.id)
        if not stock:
            render_error("На складе отправления нет товаров.")
            return

        stock_opts = {
            f"{s.product_name} (ID: {s.product_id}) — доступно: {s.available_quantity}": s
            for s in stock
        }
        s_completer = WordCompleter(list(stock_opts.keys()), ignore_case=True)

        prod_input = prompt("Товар: ", completer=s_completer).strip()
        sel = stock_opts.get(prod_input)
        if not sel or sel.available_quantity <= 0:
            render_error("Товар недоступен.")
            continue

        qty_str = prompt(f"Количество (до {sel.available_quantity}): ", validator=PositiveIntValidator()).strip()
        qty = int(qty_str)
        if qty > sel.available_quantity:
            render_error(f"Доступно только {sel.available_quantity}.")
            continue

        console.print(f"\n[bold]Добавление:[/bold] {sel.product_name} x {qty}")
        confirm = prompt("Подтвердить? (y/n): ", validator=YesNoValidator())
        if YesNoValidator.is_no(confirm):
            continue

        conn = get_conn()
        try:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                conn.execute("LOCK TABLE inventory.transfers IN EXCLUSIVE MODE")

                transfer_id = _get_or_create_planned_transfer(from_wh.id, to_wh.id)

                with conn.cursor(row_factory=class_row(Transfer)) as cur:
                    cur.execute(
                        "SELECT * FROM inventory.transfers WHERE id = %s FOR UPDATE",
                        (transfer_id,),
                    )
                    tr = cur.fetchone()
                if not tr or tr.status != "planned":
                    render_error("Перемещение уже не в статусе 'planned'.")
                    return

                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, quantity FROM inventory.transfer_items
                           WHERE transfer_id = %s AND requested_by = %s AND product_id = %s
                           FOR UPDATE""",
                        (transfer_id, auth_user().id, sel.product_id),
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            "UPDATE inventory.transfer_items SET quantity = quantity + %s WHERE id = %s",
                            (qty, existing[0]),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO inventory.transfer_items
                               (transfer_id, product_id, quantity, requested_by, status)
                               VALUES (%s, %s, %s, %s, 'planned')""",
                            (transfer_id, sel.product_id, qty, auth_user().id),
                        )
                    cur.execute(
                        "UPDATE inventory.stock SET quantity = quantity - %s WHERE product_id = %s AND warehouse_id = %s",
                        (qty, sel.product_id, from_wh.id),
                    )
        except SerializationFailure:
            render_error("Ошибка: другой менеджер изменяет данные. Попробуйте снова.")
            continue

        console.print(f"[green]Добавлено: {sel.product_name} x {qty} в перемещение ID: {transfer_id}.[/green]")

        if YesNoValidator.is_no(prompt("Добавить ещё? (y/n): ", validator=YesNoValidator())):
            break


@command(
    "remove transfer items",
    "удалить товары из перемещения (интерактивно)",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def remove_transfer_items() -> None:
    my_transfers = _get_my_transfers()
    if not my_transfers:
        render_error("Нет перемещений с вашими товарами.")
        return

    tr_opts = {}
    for t in my_transfers:
        fc = _get_city_id_by_warehouse(t.from_warehouse_id)
        tc = _get_city_id_by_warehouse(t.to_warehouse_id)
        label = f"ID: {t.id} — {_get_city_name(fc)} → {_get_city_name(tc)}"
        tr_opts[label] = t

    t_completer = WordCompleter(list(tr_opts.keys()), ignore_case=True)
    tr_input = prompt("Перемещение: ", completer=t_completer).strip()
    sel_tr = tr_opts.get(tr_input)
    if not sel_tr:
        render_error("Не распознано.")
        return

    while True:
        items = [i for i in _get_transfer_items(sel_tr.id) if i.requested_by == auth_user().id]
        if not items:
            render_error("Нет ваших товаров в этом перемещении.")
            return

        item_opts = {}
        for i in items:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM catalog.products WHERE id = %s", (i.product_id,))
                row = cur.fetchone()
                name = row[0] if row else f"ID {i.product_id}"
            item_opts[f"{name} (ID: {i.product_id}) — {i.quantity} шт."] = i

        i_completer = WordCompleter(list(item_opts.keys()), ignore_case=True)
        i_input = prompt("Товар: ", completer=i_completer).strip()
        sel_item = item_opts.get(i_input)
        if not sel_item:
            render_error("Не распознан.")
            continue

        qty_str = prompt(f"Количество для удаления (до {sel_item.quantity}): ", validator=PositiveIntValidator()).strip()
        qty = int(qty_str)
        if qty > sel_item.quantity:
            render_error(f"Доступно только {sel_item.quantity}.")
            continue

        confirm = prompt(f"Удалить {qty} шт.? (y/n): ", validator=YesNoValidator())
        if YesNoValidator.is_no(confirm):
            continue

        conn = get_conn()
        try:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

                with conn.cursor(row_factory=class_row(Transfer)) as cur:
                    cur.execute(
                        "SELECT * FROM inventory.transfers WHERE id = %s FOR UPDATE",
                        (sel_tr.id,),
                    )
                    tr = cur.fetchone()
                if not tr or tr.status != "planned":
                    render_error("Перемещение уже не в статусе 'planned'.")
                    return

                with conn.cursor() as cur:
                    if qty >= sel_item.quantity:
                        cur.execute("DELETE FROM inventory.transfer_items WHERE id = %s", (sel_item.id,))
                    else:
                        cur.execute(
                            "UPDATE inventory.transfer_items SET quantity = quantity - %s WHERE id = %s",
                            (qty, sel_item.id),
                        )
                    cur.execute(
                        "UPDATE inventory.stock SET quantity = quantity + %s WHERE product_id = %s AND warehouse_id = %s",
                        (qty, sel_item.product_id, sel_tr.from_warehouse_id),
                    )
        except SerializationFailure:
            render_error("Ошибка: другой менеджер изменяет данные. Попробуйте снова.")
            continue

        pname = item_opts[i_input].split(" —")[0]
        console.print(f"[green]Удалено: {qty} шт. из перемещения ID: {sel_tr.id}.[/green]")

        if YesNoValidator.is_no(prompt("Удалить ещё? (y/n): ", validator=YesNoValidator())):
            break


@command(
    "list transfers planned all",
    "список всех планируемых перемещений",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def list_transfers_planned_all() -> None:
    conn = get_conn()
    query = """
        SELECT t.id, t.from_warehouse_id, t.to_warehouse_id,
               p.id AS product_id, p.name AS product_name,
               ti.quantity, ti.requested_by, ti.reserve_id
        FROM inventory.transfers t
        JOIN inventory.transfer_items ti ON ti.transfer_id = t.id
        JOIN catalog.products p ON p.id = ti.product_id
        WHERE t.status = 'planned'
        ORDER BY t.from_warehouse_id, t.to_warehouse_id, t.id, p.name
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        console.print("[yellow]Нет планируемых перемещений.[/yellow]")
        return

    table = Table(title="Планируемые перемещения", header_style="bold cyan")
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Маршрут", style="green", min_width=30)
    table.add_column("Товар", style="yellow", min_width=30)
    table.add_column("Добавил", style="magenta", width=15)
    table.add_column("Кол-во", style="cyan", width=8, justify="right")
    table.add_column("Заказ", style="blue", width=8, justify="right")

    from itertools import groupby

    for (from_wh, to_wh), group in groupby(rows, key=lambda r: (r[1], r[2])):
        fc = _get_city_id_by_warehouse(from_wh)
        tc = _get_city_id_by_warehouse(to_wh)
        route_str = f"{_get_city_name(fc)} → {_get_city_name(tc)}"

        for row in group:
            user = get_user(row[6])
            order_id = ""
            if row[7]:
                with conn.cursor() as cur2:
                    cur2.execute("SELECT order_id FROM inventory.reserves WHERE id = %s", (row[7],))
                    r = cur2.fetchone()
                    if r:
                        order_id = str(r[0])
            table.add_row(
                str(row[0]), route_str,
                f"{row[4]} (ID: {row[3]})",
                user.username, str(row[5]), order_id,
            )

    console.print(table)


@command(
    "start shipping",
    "начать отгрузку перемещения",
    CATEGORY_TRANSFERS,
    [ROLE_INVENTORY_MANAGER],
)
def start_shipping(transfer_id: str) -> None:
    tid = int(transfer_id)
    conn = get_conn()

    with conn.cursor(row_factory=class_row(Transfer)) as cur:
        cur.execute("SELECT * FROM inventory.transfers WHERE id = %s", (tid,))
        tr = cur.fetchone()

    if not tr:
        render_error(f"Перемещение ID: {tid} не найдено.")
        return
    if tr.status != "planned":
        render_error(f"Статус '{tr.status}'. Отгрузить можно только 'planned'.")
        return

    confirm = prompt(f"Начать отгрузку ID: {tid}? (y/n): ", validator=YesNoValidator())
    if YesNoValidator.is_no(confirm):
        return

    conn.execute("UPDATE inventory.transfers SET status = 'shipping' WHERE id = %s", (tid,))
    console.print(f"[green]Перемещение ID: {tid} → 'shipping'.[/green]")