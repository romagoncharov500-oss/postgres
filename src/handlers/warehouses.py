from dataclasses import dataclass

from prompt_toolkit import prompt
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from console import console, render_error
from db import get_conn
from validators import NonEmptyValidator, YesNoValidator
from commands import command, CATEGORY_WAREHOUSES
from auth import ROLE_CATALOG_MANAGER, ALL_ROLES
from cities import city_validator, city_completer, _get_city_name, _get_city_id


@dataclass
class Warehouse:
    id: int
    city_id: int
    address: str
    label: str | None
    is_central: bool


def _get_central_warehouse() -> Warehouse:
    conn = get_conn()
    cur = conn.cursor(row_factory=class_row(Warehouse))
    cur.execute("SELECT * FROM catalog.warehouses WHERE is_central")
    warehouse: Warehouse = cur.fetchone()
    return warehouse


def _update_central() -> None:
    conn = get_conn()
    central_warehouse = _get_central_warehouse()
    conn.execute("UPDATE catalog.warehouses SET is_central = %s WHERE id = %s", (False, central_warehouse.id))
    

def _render_warehouse(warehouse: Warehouse) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(warehouse.id))
    table.add_row("Город", _get_city_name(warehouse.city_id))
    table.add_row("Адрес", warehouse.address)
    table.add_row("Метка", warehouse.label or "")
    table.add_row("Центральный", str(warehouse.is_central))

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Склад #{warehouse.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)


@command("list warehouses", "список всех складов", CATEGORY_WAREHOUSES, ALL_ROLES)
def list_warehouses() -> None:
    conn = get_conn()
    table = Table(title="Склады", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Город", style="green", min_width=20)
    table.add_column("Адрес", style="yellow", min_width=30)
    table.add_column("Метка", style="magenta", min_width=15)
    table.add_column("Центральный", style="magenta", min_width=15)

    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses")
        warehouses: list[Warehouse] = cur.fetchall()

    for warehouse in warehouses:
        table.add_row(
            str(warehouse.id),
            _get_city_name(warehouse.city_id),
            warehouse.address,
            warehouse.label or "",
            str(warehouse.is_central)
        )
    console.print(table)


@command("show warehouse", "информация о складе", CATEGORY_WAREHOUSES, ALL_ROLES)
def show_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return

    _render_warehouse(warehouse)


@command("add warehouse", "добавить склад (интерактивно)", CATEGORY_WAREHOUSES, [ROLE_CATALOG_MANAGER])
def add_warehouse() -> None:
    conn = get_conn()
    city = prompt("Город: ", validator=city_validator, completer=city_completer).strip()
    address = prompt("Адрес: ", validator=NonEmptyValidator()).strip()
    label = prompt("Метка (необязательно): ").strip() or None
    is_central = True

    city_id = _get_city_id(city)

    if _get_central_warehouse():
        is_central = prompt("Центральный: ", validator=YesNoValidator()).strip() 
        if YesNoValidator.is_yes(is_central):
            _update_central()

    conn.execute(
            "INSERT INTO catalog.warehouses (city, address, label, is_central) VALUES (%s, %s, %s, %s)",
            (city_id, address, label, is_central),
    )

    if label:
        console.print(f"[green]Склад в городе {city} ({label}) добавлен [/green]")
    else:
        console.print(f"[green]Склад в городе {city} добавлен [/green]")


@command("edit warehouse", "редактировать склад", CATEGORY_WAREHOUSES, [ROLE_CATALOG_MANAGER])
def edit_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return
    
    city = prompt(
        "Город: ",
        default=warehouse.city,
        validator=city_validator,
        completer=city_completer,
    ).strip()
    city_id = _get_city_id(city)

    address = prompt(
        "Адрес: ", default=warehouse.address, validator=NonEmptyValidator()
    ).strip()
    label = (
        prompt("Метка (необязательно): ", default=warehouse.label or "").strip() or None
    )

    if not warehouse.is_central: 
        is_central = (
            prompt("Центральный склад: ", validator=YesNoValidator())
        )
        if YesNoValidator.is_yes(is_central):
            _update_central()
    else:
        is_central = "TRUE"

    conn.execute(
        """UPDATE catalog.warehouses SET city = %s, address = %s, label = %s, is_central = %s
        WHERE id = %s""",
        (city_id, address, label, is_central, _id),
    )
        
    if label:
        console.print(f"[green]Склад в городе {city} ({label}) обновлен [/green]")
    else:
        console.print(f"[green]Склад в городе {city} обновлен [/green]")


@command("delete warehouse", "удалить склад", CATEGORY_WAREHOUSES, [ROLE_CATALOG_MANAGER])
def delete_warehouse(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Warehouse)) as cur:
        cur.execute("SELECT * FROM catalog.warehouses WHERE id = %s", (_id,))
        warehouse: Warehouse | None = cur.fetchone()

    if warehouse is None:
        render_error(f"Склад с ID {_id} не найден")
        return
    
    if not warehouse.is_central:
        _render_warehouse(warehouse)

        answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())
        city_name = _get_city_name(warehouse.city_id)
        if YesNoValidator.is_yes(answer):
            conn.execute("DELETE FROM catalog.warehouses WHERE id = %s", (_id,))
            if warehouse.label:
                console.print(
                    f"[green]Склад в городе {city_name} ({warehouse.label}) удален [/green]"
                )
            else:
                console.print(f"[green]Склад в городе {city_name} удален [/green]")
    else:
        console.print(f"[bold red]Склад ID: {_id} является центральным. Чтобы удалить его - назначте центральным другой склад. [/bold red]")