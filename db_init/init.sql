-- Таблица для настроек бота (например, приветственное сообщение, ID админ-канала)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO settings (key, value) VALUES
('welcome_message', 'Здравствуйте! Подскажите, вы собственник квартиры или агент?')
ON CONFLICT (key) DO NOTHING;

-- Таблица для Telegram аккаунтов (userbot-ов)
CREATE TABLE IF NOT EXISTS user_accounts (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    session_string TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для мониторируемых каналов
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL, -- ID канала (-100xxxxxx)
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    keywords TEXT DEFAULT '', -- Ключевые слова для фильтрации, разделенные запятыми
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для всех обработанных сообщений из каналов
CREATE TABLE IF NOT EXISTS processed_messages (
    id SERIAL PRIMARY KEY,
    message_telegram_id BIGINT NOT NULL,
    channel_telegram_id BIGINT NOT NULL REFERENCES channels(telegram_id),
    message_text TEXT NOT NULL,
    message_hash TEXT UNIQUE NOT NULL, -- Хеш текста для дедупликации
    author_telegram_id BIGINT,
    author_username TEXT,
    original_link TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_message_in_channel UNIQUE (message_telegram_id, channel_telegram_id)
);

-- Таблица для пользователей, с которыми бот вступил в диалог
CREATE TYPE contact_status AS ENUM ('pending', 'owner', 'agent', 'blacklisted', 'error');

CREATE TABLE IF NOT EXISTS contacted_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    status contact_status DEFAULT 'pending',
    first_contact_message_id BIGINT,
    last_contact_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    dialog_history JSONB DEFAULT '[]', -- История диалога (опционально)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для подтвержденных собственников (лидов)
CREATE TABLE IF NOT EXISTS owner_leads (
    id SERIAL PRIMARY KEY,
    contacted_user_id INTEGER NOT NULL REFERENCES contacted_users(id),
    original_message_id INTEGER NOT NULL REFERENCES processed_messages(id),
    owner_response_text TEXT NOT NULL,
    found_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
