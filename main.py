import streamlit as st
import psycopg2
import random

# ========= Настройка страницы =========
st.set_page_config(
    page_title="EnglishCard",
    page_icon="📚",
    layout="wide"
)


# ========= Работа с базой данных =========
def get_db_connection():
    """Подключение к PostgreSQL."""
    return psycopg2.connect(
        host="localhost",
        database="english_card",
        user="postgres",
        password="postgres",
        client_encoding="UTF8"
    )


def init_database():
    """Создание таблиц и начальных данных."""
    try:
        with open('init_db.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        conn.close()
    except FileNotFoundError:
        st.error("Файл init_db.sql не найден!")
    except Exception as e:
        st.error(f"Ошибка инициализации БД: {e}")


# ========= Работа с пользователями =========
def login_user(username):
    """Авторизация пользователя."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if user:
        user_id = user[0]
    else:
        cur.execute("INSERT INTO users (username) VALUES (%s) RETURNING id",
                    (username,))
        user_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    return user_id


# ========= Работа со словами =========
def get_user_words(user_id):
    """Получение слов пользователя."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, russian_word, english_word, 'common' AS word_type
                FROM common_words
        UNION ALL
        SELECT id, russian_word, english_word, 'user' AS word_type
                FROM user_words WHERE user_id = %s
    """, (user_id,))
    words = [{'id': w[0], 'russian_word': w[1], 'english_word': w[2],
              'word_type': w[3]} for w in cur.fetchall()]
    conn.close()
    return words


def add_personal_word(user_id, russian, english):
    """Добавление слова пользователя."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM user_words WHERE user_id = %s AND russian_word = %s",
        (user_id, russian))
    if cur.fetchone():
        return False
    cur.execute(
        "INSERT INTO user_words "
        "(user_id, russian_word, english_word) VALUES (%s, %s, %s)",
        (user_id, russian.lower(), english.lower()))
    conn.commit()
    conn.close()
    return True


def delete_personal_word(user_id, word_id):
    """Удаление слова пользователя."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_words WHERE user_id = %s AND id = %s",
                (user_id, word_id))
    deleted = bool(cur.rowcount)
    conn.commit()
    conn.close()
    return deleted


# ========= Статистика обучения =========
def update_stats(user_id, word_id, word_type, is_correct):
    """Обновление статистики по слову."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, correct_answers, total_attempts
        FROM learning_stats
        WHERE user_id = %s AND word_id = %s AND word_type = %s
    """, (user_id, word_id, word_type))
    stat = cur.fetchone()

    if stat:
        stat_id, correct, attempts = stat
        correct += 1 if is_correct else 0
        attempts += 1
        cur.execute("""
            UPDATE learning_stats
            SET correct_answers=%s, total_attempts=%s,
                    last_reviewed=CURRENT_TIMESTAMP
            WHERE id=%s
        """, (correct, attempts, stat_id))
    else:
        correct_val = 1 if is_correct else 0
        cur.execute("""
            INSERT INTO learning_stats
            (user_id, word_id, word_type, correct_answers, total_attempts)
            VALUES (%s, %s, %s, %s, 1)
        """, (user_id, word_id, word_type, correct_val))

    conn.commit()
    conn.close()


def get_statistics(user_id):
    """Сбор статистики пользователя."""
    stats = {}
    words = get_user_words(user_id)
    stats['total_words'] = len(words)

    conn = get_db_connection()
    cur = conn.cursor()

    # Общая статистика
    cur.execute("""
        SELECT SUM(total_attempts), SUM(correct_answers)
        FROM learning_stats
        WHERE user_id = %s
    """, (user_id,))
    attempts_row = cur.fetchone() or (0, 0)

    stats['total_attempts'] = attempts_row[0] or 0
    stats['correct_answers'] = attempts_row[1] or 0

    if stats['total_attempts'] > 0:
        stats['accuracy'] = round(stats['correct_answers'] /
                                  stats['total_attempts'] * 100)
    else:
        stats['accuracy'] = 0

    # Последние 5 попыток — исправленный запрос
    try:
        cur.execute("""
            SELECT word_type, russian_word, english_word,
                   correct_answers, total_attempts, last_reviewed
            FROM (
                SELECT ls.word_type, cw.russian_word, cw.english_word,
                       ls.correct_answers, ls.total_attempts, ls.last_reviewed
                FROM learning_stats ls
                JOIN common_words cw
                    ON ls.word_type = 'common' AND ls.word_id = cw.id
                WHERE ls.user_id = %s

                UNION ALL

                SELECT ls.word_type, uw.russian_word, uw.english_word,
                       ls.correct_answers, ls.total_attempts, ls.last_reviewed
                FROM learning_stats ls
                JOIN user_words uw
                    ON ls.word_type = 'user' AND ls.word_id = uw.id
                WHERE ls.user_id = %s
            ) AS combined_stats
            ORDER BY last_reviewed DESC
            LIMIT 5;
        """, (user_id, user_id))

        stats['last_attempts'] = [{
            "type": row[0],
            "russian_word": row[1],
            "english_word": row[2],
            "correct": row[3],
            "total": row[4],
            "date": row[5]
        } for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Ошибка при получении статистики: {e}")
        stats['last_attempts'] = []

    conn.close()
    return stats


# ========= Вспомогательные функции UI/Logic =========
def generate_options(correct_english, all_english):
    """Генерация вариантов ответа."""
    options = [correct_english]
    while len(options) < 4:
        rand_word = random.choice(all_english)
        if rand_word not in options:
            options.append(rand_word)
    random.shuffle(options)
    return options


def render_welcome():
    """Приветственное сообщение."""
    st.write("### 📚 EnglishCard — изучение английского")
    st.info("Введите своё имя в боковой панели и нажмите «Войти»!")
    st.write("**Возможности:** ")
    st.write("- Викторина на перевод слов.")
    st.write("- Добавление своих слов.")
    st.write("- Удаление слов.")
    st.write("- Статистика прогресса.")


def render_sidebar():
    """Боковая панель с авторизацией."""
    if 'user_id' not in st.session_state:
        username = st.sidebar.text_input("Ваше имя")
        if st.sidebar.button("Войти"):
            if username.strip():
                st.session_state.user_id = login_user(username.strip())
                st.session_state.username = username.strip()
                st.sidebar.success(f"Привет, {username}!")
                st.rerun()
            else:
                st.sidebar.error("Введите имя!")


def render_study_tab(words):
    """Вкладка изучения слов (Викторина)."""
    if not words:
        st.info("Добавьте слова во вкладке ➕.")
        return

    current_word = random.choice(words)
    all_english = [w['english_word'] for w in words]
    options = generate_options(current_word['english_word'], all_english)

    st.write(f"**Переведите:** {current_word['russian_word']}")

    selected_answer = st.radio("Выберите правильный перевод:", options,
                               key="quiz_answer")

    if st.button("Проверить ответ", key="check_answer"):
        is_correct = selected_answer.lower() == current_word[
            'english_word'
            ].lower()
        handle_answer(is_correct, current_word)


def handle_answer(is_correct, word):
    if is_correct:
        st.success("✅ Верно!")
    else:
        st.error(f"❌ Неправильно. Ответ: {word['english_word']}")
    update_stats(st.session_state.user_id, word['id'],
                 word['word_type'], is_correct)
    st.rerun()


def render_add_tab():
    """Вкладка добавления слов."""
    russian = st.text_input("Слово на русском")
    english = st.text_input("Перевод на английском")

    if st.button("➕ Добавить"):
        if not russian or not english:
            st.warning("Заполните оба поля!")
            return
        success = add_personal_word(st.session_state.user_id, russian, english)
        if success:
            st.success("✅ Слово добавлено!")
        else:
            st.error("❌ Уже есть такое слово.")
        st.rerun()


def render_delete_tab(words):
    """Вкладка удаления слов."""
    personal_words = [w for w in words if w['word_type'] == 'user']
    if not personal_words:
        st.info("Нет ваших слов для удаления.")
        return

    word_options = [f"{w['russian_word']} → {w['english_word']}"
                    for w in personal_words]
    selected_index = st.selectbox("Выберите слово для удаления:",
                                  range(len(word_options)),
                                  format_func=lambda x: word_options[x])
    selected_word = personal_words[selected_index]

    if st.button("🗑️ Удалить"):
        success = delete_personal_word(st.session_state.user_id,
                                       selected_word['id'])
        if success:
            st.success("✅ Удалено!")
        else:
            st.error("❌ Ошибка удаления.")
        st.rerun()


def render_stats_tab(user_id):
    """Вкладка статистики."""
    stats = get_statistics(user_id)
    st.write(f"**Всего слов:** {stats['total_words']}")
    st.write(f"**Попыток:** {stats['total_attempts']}")
    st.write(f"**Правильных:** {stats['correct_answers']}")
    st.write(f"**Точность:** {stats['accuracy']}%")

    st.subheader("Последние попытки:")
    for a in stats['last_attempts']:
        st.write(
            f"- {a['russian_word']} → {a['english_word']} "
            f"({a['correct']}/{a['total']})"
        )


def render_schema_tab():
    """Вкладка схемы БД."""
    st.code("""
CREATE TABLE users (
   id SERIAL PRIMARY KEY,
   username VARCHAR(50) UNIQUE NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE common_words (
   id SERIAL PRIMARY KEY,
   russian_word VARCHAR(50) NOT NULL,
   english_word VARCHAR(50) NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_words (
   id SERIAL PRIMARY KEY,
   user_id INTEGER REFERENCES users(id),
   russian_word VARCHAR(50) NOT NULL,
   english_word VARCHAR(50) NOT NULL,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE learning_stats (
   id SERIAL PRIMARY KEY,
   user_id INTEGER REFERENCES users(id),
   word_id INTEGER,
   word_type VARCHAR(10) CHECK (word_type IN ('common', 'user')),
   correct_answers INTEGER DEFAULT 0,
   total_attempts INTEGER DEFAULT 0,
   last_reviewed TIMESTAMP
);
""", language="sql")


# ========= Главная функция приложения =========
def main():
    st.title("📚 EnglishCard — учи английский!")

    # Инициализация БД
    init_database()

    # Боковая панель
    render_sidebar()

    # Контент в зависимости от авторизации
    if 'user_id' in st.session_state:
        words = get_user_words(st.session_state.user_id)

        tabs = st.tabs(
            ["📖 Учить", "➕ Добавить", "🗑️ Удалить", "📊 Статистика", "📄 Схема"])

        with tabs[0]: render_study_tab(words)
        with tabs[1]: render_add_tab()
        with tabs[2]: render_delete_tab(words)
        with tabs[3]: render_stats_tab(st.session_state.user_id)
        with tabs[4]: render_schema_tab()

        st.sidebar.button(
            "🚪 Выход", key="logout", on_click=lambda:
            st.session_state.pop('user_id'))

    else:
        render_welcome()


if __name__ == "__main__":
    main()
