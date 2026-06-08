from dataclasses import dataclass
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from psycopg.rows import class_row
from rich.panel import Panel
from rich.table import Table

from console import console, render_error
from db import get_conn
from commands import command, CATEGORY_PRODUCT_CATEGORIES
from validators import ChoiceValidator, NonEmptyValidator, YesNoValidator

categories = [
    "Бытовая техника",
    "Компьютеры",
    "Ноутбуки",
    "Телефоны",
    "Коммутация",
    "Аккумуляторы",
    "Телевизоры",
]

name_completer = WordCompleter(categories, ignore_case=True, sentence=True)
name_validator = ChoiceValidator(
    categories, message="Город должен быть из списка. Используйте Tab для автодополнения."
)

@dataclass
class Category:
    id: int
    name: str

def _render_category(category) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_column("Поле", style="bold cyan", width=15)
    table.add_column("Значение", style="white")

    table.add_row("ID", str(category.id))
    table.add_row("Категория", category.name)

    panel = Panel(
        table,
        expand=False,
        title=f"[bold green]Категория #{category.id}[/bold green]",
        border_style="green",
    )

    console.print(panel)

@command("list categories", "список всех категорий", CATEGORY_PRODUCT_CATEGORIES)
def list_product_categories()-> None:
    conn = get_conn()
    table = Table(title="Категории", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Категория", style="green", min_width=20)

    with conn.cursor(row_factory=class_row(Category)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories")
        category: list[Category] = cur.fetchall()

    for category in category:
        table.add_row(
            str(category.id),
            category.name,
        )
    console.print(table)

@command("show category", "информация о складе", CATEGORY_PRODUCT_CATEGORIES)
def show_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Category)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: Category | None = cur.fetchone()

    if category is None:
        render_error(f"Категория с ID {_id} не найдена")
        return

    _render_category(category)

@command("add category", "добавить категорию (интерактивно)", CATEGORY_PRODUCT_CATEGORIES)
def add_product_category() -> None:
    conn = get_conn()
    name = prompt("Категория: ", validator=name_validator, completer=name_completer).strip()
    conn.execute(
        "INSERT INTO catalog.product_categories (name) VALUES (%s)",
        (name,)
    )
    
    console.print(f"[green]Категория {name} добавлена [/green]")

@command("edit category", "редактировать категорию", CATEGORY_PRODUCT_CATEGORIES)
def edit_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Category)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: Category | None = cur.fetchone()

    if category is None:
        render_error(f"Категория с ID {_id} не найден")
        return

    name = prompt(
        "Категория: ",
        default=category.name,
        validator=name_validator,
        completer=name_completer,
    ).strip()
    
    conn.execute(
        """UPDATE catalog.product_categories SET name = %s
        WHERE id = %s""",
        (name, _id),
    )
    
    console.print(f"[green]Категория {name} обновлена [/green]")
    


@command("delete category", "удалить склад", CATEGORY_PRODUCT_CATEGORIES)
def delete_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Category)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        category: Category | None = cur.fetchone()

    if category is None:
        render_error(f"Категория с ID {_id} не найдена")
        return

    _render_category(category)

    answer = prompt("Вы уверены? (y/n, д/н): ", validator=YesNoValidator())

    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM catalog.product_categories WHERE id = %s", (_id,))        
        console.print(f"[green]Категория {category.name} удалена [/green]")
        
