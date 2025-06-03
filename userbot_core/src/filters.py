import re
from userbot_core.src import config

def is_ad_message(text: str, channel_keywords: list = None) -> bool:
    """
    Проверяет, является ли сообщение объявлением о продаже недвижимости.
    Использует список ключевых слов.
    """
    if channel_keywords is None:
        channel_keywords = config.DEFAULT_KEYWORDS

    text_lower = text.lower()
    
    # Простая проверка на наличие хотя бы одного ключевого слова
    found_keyword = False
    for keyword in channel_keywords:
        if keyword.lower() in text_lower:
            found_keyword = True
            break
    
    if not found_keyword:
        return False
    
    # Можно добавить более сложные регулярные выражения для цен, площади и т.д.
    # Например, наличие числовых значений, похожих на цену или площадь.
    if re.search(r'\b\d{2,7}\s*(₽|руб|млн|тыс|k|m|м2|м²)\b', text_lower):
        return True
    
    if "собственник" in text_lower or "продавец" in text_lower or "без комиссии" in text_lower:
        return True

    return False
