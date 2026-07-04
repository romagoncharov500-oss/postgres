from dataclasses import dataclass
from decimal import Decimal
import time

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from commands import command, CATEGORY_ROUTES
from auth import ROLE_INVENTORY_MANAGER, ROLE_WORKER

from db import get_conn
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table
from cities import _get_city_name, _get_city_id
from validators import NonEmptyValidator, YesNoValidator, ChoiceValidator, TimeValidator
from console import console, render_error


@dataclass
class Route:
    from_city_id: int
    to_city_id: int
    duration: time
    total_threshold: Decimal


def _render_route(route: Route) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("Из города", _get_city_name(route.from_city_id))
    table.add_row("В город", _get_city_name(route.to_city_id))
    table.add_row("За время", str(route.duration))
    table.add_row("Порог", str(route.total_threshold))

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Маршрут {_get_city_name(route.from_city_id)} -> {_get_city_name(route.to_city_id)}[/bold green]",
        border_style="green",
    )

    console.print(panel)


def _get_existing_routes() -> list[Route]:
    """Возвращает все существующие маршруты."""
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Route)) as cur:
        cur.execute("SELECT from_city_id, to_city_id, duration, total_threshold FROM inventory.routes")
        return cur.fetchall()


def _get_available_city_pairs() -> list[tuple[str, str]]:
    """
    Возвращает список пар (from_city, to_city), которые ещё не используются в маршрутах.
    Один SQL-запрос с CROSS JOIN и NOT IN.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c1.name AS from_city, c2.name AS to_city
            FROM catalog.cities c1
            CROSS JOIN catalog.cities c2
            WHERE c1.id <> c2.id
              AND (c1.id, c2.id) NOT IN (
                SELECT from_city_id, to_city_id FROM inventory.routes
              )
            ORDER BY c1.name, c2.name
            """
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def _select_route() -> Route | None:
    """
    Интерактивный выбор существующего маршрута через два выпадающих списка.
    Возвращает Route или None, если маршрутов нет.
    """
    routes = _get_existing_routes()
    if not routes:
        render_error("Нет ни одного маршрута")
        return None

    # Уникальные города отправления среди существующих маршрутов
    from_cities = sorted({_get_city_name(r.from_city_id) for r in routes})
    from_completer = WordCompleter(from_cities, ignore_case=True, sentence=True)
    from_validator = ChoiceValidator(from_cities, message="Выберите город из списка. Используйте Tab для автодополнения.")

    from_city_str = prompt(
        "Город отправления: ",
        completer=from_completer,
        validator=from_validator,
    ).strip()

    from_city_id = _get_city_id(from_city_str)

    # Города назначения для выбранного города отправления
    to_cities = sorted({
        _get_city_name(r.to_city_id)
        for r in routes
        if r.from_city_id == from_city_id
    })
    to_completer = WordCompleter(to_cities, ignore_case=True, sentence=True)
    to_validator = ChoiceValidator(to_cities, message="Выберите город из списка. Используйте Tab для автодополнения.")

    to_city_str = prompt(
        "Город назначения: ",
        completer=to_completer,
        validator=to_validator,
    ).strip()

    to_city_id = _get_city_id(to_city_str)

    # Ищем маршрут по составному ключу
    for r in routes:
        if r.from_city_id == from_city_id and r.to_city_id == to_city_id:
            return r

    render_error("Маршрут не найден")
    return None


@command("list routes", "список всех маршрутов", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER, ROLE_WORKER])
def list_routes() -> None:
    conn = get_conn()
    table = Table(title="Маршруты", show_header=True, header_style="bold cyan")

    table.add_column("Из города", style="dim", min_width=20)
    table.add_column("В город", style="green", min_width=20)
    table.add_column("За время", style="yellow", min_width=15)
    table.add_column("Порог", style="magenta", min_width=15)

    with conn.cursor(row_factory=class_row(Route)) as cur:
        cur.execute("SELECT from_city_id, to_city_id, duration, total_threshold FROM inventory.routes")
        routes: list[Route] = cur.fetchall()

    for route in routes:
        table.add_row(
            _get_city_name(route.from_city_id),
            _get_city_name(route.to_city_id),
            str(route.duration),
            str(route.total_threshold or ""),
        )
    console.print(table)


@command("show route", "информация о маршруте", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER, ROLE_WORKER])
def show_route() -> None:
    route = _select_route()
    if route is None:
        return
    _render_route(route)


@command("add route", "добавить маршрут (интерактивно)", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def add_route() -> None:
    conn = get_conn()

    # Получаем свободные пары городов одним SQL-запросом
    available_pairs = _get_available_city_pairs()
    if not available_pairs:
        render_error("Нет доступных пар городов для создания маршрута. Все возможные маршруты уже существуют.")
        return

    # Уникальные города отправления среди доступных пар
    from_cities = sorted({pair[0] for pair in available_pairs})
    from_completer = WordCompleter(from_cities, ignore_case=True, sentence=True)

    from_city_str = prompt(
        "Из города: ",
        completer=from_completer,
    ).strip()

    # Города назначения для выбранного города отправления
    to_cities = sorted({
        pair[1] for pair in available_pairs if pair[0] == from_city_str
    })
    to_completer = WordCompleter(to_cities, ignore_case=True, sentence=True)

    to_city_str = prompt(
        "В город: ",
        completer=to_completer,
    ).strip()

    duration = prompt("Длительность: ", validator=TimeValidator()).strip()
    total_threshold = prompt("Порог: ", validator=NonEmptyValidator()).strip()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO inventory.routes (from_city_id, to_city_id, duration, total_threshold) VALUES (%s, %s, %s, %s)",
            (_get_city_id(from_city_str), _get_city_id(to_city_str), duration, total_threshold),
        )

    console.print(f"[green]Маршрут {from_city_str} -> {to_city_str} добавлен [/green]")


@command("edit route", "редактировать маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def edit_route() -> None:
    route = _select_route()
    if route is None:
        return

    _render_route(route)

    duration = prompt(
        "Длительность: ", default=str(route.duration), validator=TimeValidator()
    ).strip()
    total_threshold = (
        prompt("Порог: ", default=str(route.total_threshold), validator=NonEmptyValidator()).strip()
    )

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE inventory.routes
               SET duration = %s, total_threshold = %s
               WHERE from_city_id = %s AND to_city_id = %s""",
            (duration, total_threshold, route.from_city_id, route.to_city_id),
        )

    console.print(
        f"[green]Маршрут {_get_city_name(route.from_city_id)} -> {_get_city_name(route.to_city_id)} обновлён [/green]"
    )


@command("delete route", "удалить маршрут", CATEGORY_ROUTES, [ROLE_INVENTORY_MANAGER])
def delete_route() -> None:
    route = _select_route()
    if route is None:
        return

    _render_route(route)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn = get_conn()
        conn.execute(
            "DELETE FROM inventory.routes WHERE from_city_id = %s AND to_city_id = %s",
            (route.from_city_id, route.to_city_id),
        )
        console.print(
            f"[green]Маршрут {_get_city_name(route.from_city_id)} -> {_get_city_name(route.to_city_id)} удалён [/green]"
        )
    else:
        console.print(
            f"[bold red]Маршрут {_get_city_name(route.from_city_id)} -> {_get_city_name(route.to_city_id)} НЕ был удалён [/bold red]"
        )