import re

def parse_owner_agent_response(text: str) -> str:
    """
    Парсит ответ пользователя, чтобы определить, собственник он или агент.
    Возвращает 'owner', 'agent' или 'pending' (если не ясно).
    """
    text_lower = text.lower()

    owner_keywords = ["собственник", "хозяин", "я", "моя", "моё", "прямая продажа", "без посредников", "без агентов"]
    agent_keywords = ["агент", "риелтор", "посредник", "брокер", "сотрудник агентства", "помогу продать", "комиссия"]

    # Проверка на прямое подтверждение собственника
    for keyword in owner_keywords:
        if keyword in text_lower:
            # Избегаем ложных срабатываний, если рядом есть "не" или "нет"
            if re.search(rf"(?<!не\s)(?<!нет\s)\b{keyword}\b", text_lower):
                return "owner"
    
    # Проверка на прямое подтверждение агента
    for keyword in agent_keywords:
        if keyword in text_lower:
            return "agent"

    # Если есть "нет" или "не", но нет прямого подтверждения
    if "нет" in text_lower or "не" in text_lower:
        if "не собственник" in text_lower or "я не хозяин" in text_lower:
            return "agent" # Или 'not_owner', но пока схлопнем в agent
        if "не агент" in text_lower:
            # Если "не агент", но нет "собственник", то это "pending" или "owner"
            # Для простоты пока в 'pending'
            return "pending"
    
    # Если ответ слишком короткий или не содержит ключевых слов
    if len(text) < 5 or "что" in text_lower or "кто" in text_lower:
        return "pending" # Возможно, уточняющий вопрос или спам

    return "pending"
