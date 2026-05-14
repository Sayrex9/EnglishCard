-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
   id SERIAL PRIMARY KEY,
   username VARCHAR(50) UNIQUE NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Общий словарь слов (для всех пользователей)
CREATE TABLE IF NOT EXISTS common_words (
   id SERIAL PRIMARY KEY,
   russian_word VARCHAR(50) NOT NULL,
   english_word VARCHAR(50) NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Персональные слова пользователя
CREATE TABLE IF NOT EXISTS user_words (
   id SERIAL PRIMARY KEY,
   user_id INTEGER REFERENCES users(id),
   russian_word VARCHAR(50) NOT NULL,
   english_word VARCHAR(50) NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Статистика обучения по каждому слову и пользователю
CREATE TABLE IF NOT EXISTS learning_stats (
   id SERIAL PRIMARY KEY,
   user_id INTEGER REFERENCES users(id),
   word_id INTEGER,
   word_type VARCHAR(10) CHECK (word_type IN ('common', 'user')),
   correct_answers INTEGER DEFAULT 0,
   total_attempts INTEGER DEFAULT 0,
   last_reviewed TIMESTAMP
);

-- Начальные общие слова (10 штук)
INSERT INTO common_words (russian_word, english_word)
SELECT 'красный', 'red' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='красный');
INSERT INTO common_words (russian_word, english_word)
SELECT 'синий', 'blue' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='синий');
INSERT INTO common_words (russian_word, english_word)
SELECT 'зелёный', 'green' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='зелёный');
INSERT INTO common_words (russian_word, english_word)
SELECT 'жёлтый', 'yellow' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='жёлтый');
INSERT INTO common_words (russian_word, english_word)
SELECT 'дом', 'house' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='дом');
INSERT INTO common_words (russian_word, english_word)
SELECT 'книга', 'book' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='книга');
INSERT INTO common_words (russian_word, english_word)
SELECT 'стол', 'table' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='стол');
INSERT INTO common_words (russian_word, english_word)
SELECT 'кошка', 'cat' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='кошка');
INSERT INTO common_words (russian_word, english_word)
SELECT 'собака', 'dog' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='собака');
INSERT INTO common_words (russian_word, english_word)
SELECT 'человек', 'person' WHERE NOT EXISTS (SELECT 1 FROM common_words WHERE russian_word='человек');