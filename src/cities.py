from db import get_conn
from validators import ChoiceValidator
from prompt_toolkit.completion import WordCompleter


def _load_cities() -> tuple[dict[str, int], dict[int, str]]:
    """Загружает все города из БД и возвращает два словаря: name->id и id->name."""
    conn = get_conn()
    name_to_id: dict[str, int] = {}
    id_to_name: dict[int, str] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM catalog.cities ORDER BY id")
        for row in cur.fetchall():
            city_id, city_name = row[0], row[1]
            name_to_id[city_name] = city_id
            id_to_name[city_id] = city_name
    return name_to_id, id_to_name


city_name_to_id, city_id_to_name = _load_cities()

cities = list(city_name_to_id.keys())

city_completer = WordCompleter(cities, ignore_case=True, sentence=True)

city_validator = ChoiceValidator(
    cities, message="Город должен быть из списка. Используйте Tab для автодополнения."
)


def _get_city_name(city_id: int) -> str:
    """Возвращает название города по его ID."""
    return city_id_to_name[city_id]


def _get_city_id(city_name: str) -> int:
    """Возвращает ID города по его названию."""
    return city_name_to_id[city_name]