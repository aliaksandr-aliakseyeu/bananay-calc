import re
import unicodedata

# Таблица транслитерации кириллицы
CYRILLIC_TRANSLITERATION = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
}


def slugify(text: str, max_length: int = 100) -> str:
    """
    Преобразует текст в slug (URL-friendly строку).

    Args:
        text: Исходный текст
        max_length: Максимальная длина slug

    Returns:
        Slug строка

    Examples:
        >>> slugify("Быстрое питание")
        'bystroe-pitanie'
        >>> slugify("Кафе & Рестораны")
        'kafe-restorany'
    """
    if not text:
        return ""
    result = ""
    for char in text:
        if char in CYRILLIC_TRANSLITERATION:
            result += CYRILLIC_TRANSLITERATION[char]
        else:
            result += char
    result = unicodedata.normalize('NFKD', result)
    result = result.encode('ascii', 'ignore').decode('ascii')
    result = result.lower()
    result = re.sub(r'[^\w\s-]', '', result)
    result = re.sub(r'[-\s]+', '-', result)
    result = result.strip('-')

    if len(result) > max_length:
        result = result[:max_length].rstrip('-')

    return result
