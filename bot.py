import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# --- Завантаження токена ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Файли бази ---
USERS_FILE = "database/users.json"
SECTIONS_FILE = "database/sections.json"
TASKS_FILE = "database/tasks.json"

# --- Ролі ---
ROLES = [
    "👒 Тьотя Розробник",
    "🧼 Клін",
    "✍️ Переклад",
    "🖋 Ред",
    "🧩 Тайп",
    "👁 Бета"
]

# --- Порядок етапів ---
ROLE_ORDER = ["✍️ Переклад", "🧼 Клін", "🖋 Ред", "🧩 Тайп", "👁 Бета"]

# ---------- Робота з базами ----------
def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(file, data):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_users(): return load_data(USERS_FILE)
def save_users(data): save_data(USERS_FILE, data)
def load_sections(): return load_data(SECTIONS_FILE)
def save_sections(data): save_data(SECTIONS_FILE, data)
def load_tasks(): return load_data(TASKS_FILE)
def save_tasks(data): save_data(TASKS_FILE, data)

# ---------- Меню ----------
def build_main_menu(roles: list) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📋 Мої задачі")],
        [KeyboardButton(text="🎭 Мої ролі")]
    ]
    if "👒 Тьотя Розробник" in roles:
        buttons.append([KeyboardButton(text="➕ Панель Тьоті Розробника")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def build_roles_keyboard() -> ReplyKeyboardMarkup:
    role_btns = [KeyboardButton(text=r) for r in ROLES]
    grid = [role_btns[i:i+2] for i in range(0, len(role_btns), 2)]
    grid.append([KeyboardButton(text="✅ Готово")])
    return ReplyKeyboardMarkup(keyboard=grid, resize_keyboard=True)

def build_admin_panel() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🆕 Додати розділ")],
        [KeyboardButton(text="⬅️ Назад у меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- Стан адміна ---
admin_states = {}

# ---------- /start ----------
@dp.message(Command("start"))
async def start_command(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {"roles": [], "tasks": []}
        save_users(users)

    roles = users[user_id].get("roles", [])
    if roles:
        menu = build_main_menu(roles)
        await message.answer(f"Вітаю знову! 👋\nТвої ролі: {', '.join(roles)}", reply_markup=menu)
    else:
        kb = build_roles_keyboard()
        await message.answer("Хто ти? 👀\n(Можеш вибрати кілька ролей, потім натисни ✅ Готово)", reply_markup=kb)

# ---------- Перегляд ролей ----------
@dp.message(F.text == "🎭 Мої ролі")
async def show_roles(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)
    roles = users.get(user_id, {}).get("roles", [])
    if not roles:
        await message.answer("Поки що ролей немає. Обери нижче та додай 😉")
    else:
        await message.answer(f"Твої ролі: {', '.join(roles)}")

# ---------- Перегляд задач ----------
@dp.message(F.text == "📋 Мої задачі")
async def show_tasks(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)
    user_roles = users.get(user_id, {}).get("roles", [])
    tasks = load_tasks()

    # створюємо клавіатуру
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Завершити")],
            [KeyboardButton(text="⬅️ Назад у меню")]
        ],
        resize_keyboard=True
    )

    # фільтруємо задачі
    my_tasks = [t for t in tasks.values() if t["role"] in user_roles and t["status"] == "в роботі"]

    if not my_tasks:
        await message.answer("Наразі в тебе немає активних задач 😊", reply_markup=kb)
        return

    # групуємо задачі за тайтлом
    grouped = {}
    for t in my_tasks:
       grouped.setdefault((t["title"], t["role"]), []).append(t)


    text = "📋 *Твої активні задачі:*\n\n"

    for title, items in grouped.items():
        # збираємо глави
        chapters = ", ".join(sorted([t["chapter"] for t in items]))
        roles = ", ".join(sorted({t["role"] for t in items}))
        text += f"{roles} — *{title}*, глави {chapters}\n\n"

    await message.answer(text.strip(), parse_mode="Markdown", reply_markup=kb)



# ---------- Панель розробника ----------
@dp.message(F.text == "➕ Панель Тьоті Розробника")
async def open_admin_panel(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)
    roles = users.get(user_id, {}).get("roles", [])
    if "👒 Тьотя Розробник" not in roles:
        await message.answer("У тебе немає доступу до панелі 🛑")
        return
    admin_menu = build_admin_panel()
    await message.answer("👒 Панель Тьоті Розробника відкрита. Обери дію:", reply_markup=admin_menu)

# --- Додати розділ ---
def build_manhwa_keyboard(sections):
    buttons = [[KeyboardButton(text=title)] for title in sections.keys()]
    buttons.append([KeyboardButton(text="➕ Нова манхва")])
    buttons.append([KeyboardButton(text="⬅️ Назад у меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message(F.text == "🆕 Додати розділ")
async def choose_manhwa(message: Message):
    user_id = str(message.from_user.id)
    sections = load_sections()
    admin_states[user_id] = {"step": "choose_title"}
    keyboard = build_manhwa_keyboard(sections)
    await message.answer("Оберіть манхву або створіть нову:", reply_markup=keyboard)

# --- Створення нової манхви ---
@dp.message(F.text == "➕ Нова манхва")
async def start_new_manhwa(message: Message):
    user_id = str(message.from_user.id)
    admin_states[user_id] = {"step": "new_title"}
    await message.answer("Вкажи назву нової манхви 📖")

@dp.message(lambda m: str(m.from_user.id) in admin_states and admin_states[str(m.from_user.id)]["step"] == "new_title")
async def new_manhwa_title(message: Message):
    user_id = str(message.from_user.id)
    admin_states[user_id]["title"] = message.text
    admin_states[user_id]["step"] = "chapters"
    await message.answer("Тепер номер(и) глав 🔢 (наприклад 1,2,3)")

# --- Вибір існуючої манхви ---
@dp.message(lambda m: str(m.from_user.id) in admin_states and admin_states[str(m.from_user.id)]["step"] == "choose_title")
async def existing_manhwa(message: Message):
    user_id = str(message.from_user.id)
    title = message.text.strip()
    admin_states[user_id] = {"step": "chapters", "title": title}
    await message.answer(f"Додати глави для *{title}* 🔢 (наприклад: 12,13,14)", parse_mode="Markdown")

# --- Додавання глав ---
@dp.message(lambda m: str(m.from_user.id) in admin_states and admin_states[str(m.from_user.id)]["step"] == "chapters")
async def add_chapters(message: Message):
    user_id = str(message.from_user.id)
    title = admin_states[user_id]["title"]

    # 🔢 Підтримка діапазонів глав (01-10, 5-12, 7,9 і т.д.)
    raw_input = message.text.replace(" ", "")
    parsed = []
    for part in raw_input.split(","):
        if "-" in part:
            start, end = part.split("-")
            try:
                start_i = int(start)
                end_i = int(end)
                # ✅ определяем минимальную длину для выравнивания — не менее 2 символов
                width = max(2, len(start))
                parsed.extend([str(i).zfill(width) for i in range(start_i, end_i + 1)])
            except ValueError:
                continue
        elif part:
            # ✅ тоже выравниваем каждое значение до 2 символов
            try:
                parsed.append(str(int(part)).zfill(2))
            except ValueError:
                continue

    new_chapters = parsed

    sections = load_sections()
    if title not in sections:
        sections[title] = []

    existing = set(sections[title])
    duplicates = [ch for ch in new_chapters if ch in existing]
    unique_new = [ch for ch in new_chapters if ch not in existing]

    if not unique_new:
        await message.answer(
            f"ℹ️ Усі введені глави вже є у *{title}*.",
            parse_mode="Markdown"
        )
        return

    sections[title].extend(unique_new)
    save_sections(sections)

    admin_states[user_id]["step"] = "start_stage"
    admin_states[user_id]["chapters"] = unique_new

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔰 З нуля"), KeyboardButton(text="🔁 Продовження")]],
        resize_keyboard=True
    )

    msg = f"✅ Додано до *{title}*: глави {', '.join(unique_new)}"
    if duplicates:
        msg += f"\n⚠️ Пропущено (вже існували): {', '.join(duplicates)}"
    msg += "\n\nЗвідки починаємо роботу?"

    await message.answer(msg, parse_mode="Markdown", reply_markup=keyboard)


# --- Вибір типу старту ---
@dp.message(lambda m: str(m.from_user.id) in admin_states and admin_states[str(m.from_user.id)]["step"] == "start_stage")
async def choose_start_type(message: Message):
    user_id = str(message.from_user.id)
    if message.text == "🔰 З нуля":
        start_index = 0
    elif message.text == "🔁 Продовження":
        admin_states[user_id]["step"] = "choose_role_start"
        kb = [[KeyboardButton(text=r)] for r in ROLE_ORDER]
        await message.answer("З якого етапу починаємо?", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return
    else:
        return

    title = admin_states[user_id]["title"]
    chapters = admin_states[user_id]["chapters"]
    create_tasks(title, chapters, start_index)

    await finish_task_creation(message, title, chapters)

# --- Вибір ролі початку при продовженні ---
@dp.message(lambda m: str(m.from_user.id) in admin_states and admin_states[str(m.from_user.id)]["step"] == "choose_role_start")
async def choose_role_start(message: Message):
    user_id = str(message.from_user.id)
    if message.text not in ROLE_ORDER:
        return
    start_index = ROLE_ORDER.index(message.text)
    title = admin_states[user_id]["title"]
    chapters = admin_states[user_id]["chapters"]
    create_tasks(title, chapters, start_index)
    await finish_task_creation(message, title, chapters)

# === Створення початкових задач (Переклад + Клін) ===
def create_tasks(title, chapters, start_index=0):
    """
    Створює задачі для першої ролі ROLE_ORDER[start_index].
    Якщо це Переклад — одразу створює і Клін для тих самих глав.
    Далі етапи додаються автоматично після завершення (Ред, Тайп, Бета).
    """
    tasks = load_tasks()
    next_id = max([int(k) for k in tasks.keys()] + [0]) + 1

    first_role = ROLE_ORDER[start_index]  # Напр. "✍️ Переклад" або "🧼 Клін"

    for ch in chapters:
        # Завжди створюємо задачу для поточної ролі
        tasks[str(next_id)] = {
            "title": title,
            "chapter": ch,
            "role": first_role,
            "status": "в роботі"
        }
        next_id += 1

        # Якщо стартуємо з Перекладу — одразу створюємо задачу для Кліну
        if first_role == "✍️ Переклад":
            tasks[str(next_id)] = {
                "title": title,
                "chapter": ch,
                "role": "🧼 Клін",
                "status": "в роботі"
            }
            next_id += 1

    save_tasks(tasks)


# === Завершення процесу створення задач ===
async def finish_task_creation(message, title, chapters):
    user_id = str(message.from_user.id)

    # 🧹 Очистимо стан — завершуємо процес додавання
    if user_id in admin_states:
        admin_states.pop(user_id)

    # ⚙️ Після створення задач повертаємо в меню Тьоті Розробника
    admin_menu = build_admin_panel()
    await message.answer(
        f"✅ Задачі створено для *{title}*, глави {', '.join(chapters)}.\n\n"
        f"Можеш одразу додати інший розділ або повернутись у меню ⬅️",
        parse_mode="Markdown",
        reply_markup=admin_menu
    )

# --- Завершення задач з вибором ролі ---
user_finish_state = {}

def build_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад у меню")]],
        resize_keyboard=True
    )

@dp.message(F.text == "✅ Завершити")
async def start_finish_process(message: Message):
    """Початок процесу завершення — обираємо роль."""
    user_id = str(message.from_user.id)
    users = load_users()
    user_roles = users.get(user_id, {}).get("roles", [])

    if not user_roles:
        await message.answer("У тебе немає жодної ролі 😢")
        return

    buttons = [[KeyboardButton(text=r)] for r in user_roles]
    buttons.append([KeyboardButton(text="⬅️ Назад у меню")])
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    user_finish_state[user_id] = {"step": "choose_role"}
    await message.answer("✨ Яку роль ти завершила?", reply_markup=kb)


@dp.message(lambda m: str(m.from_user.id) in user_finish_state and user_finish_state[str(m.from_user.id)]["step"] == "choose_role")
async def choose_role_to_finish(message: Message):
    """Користувач вибирає роль, яку завершив."""
    user_id = str(message.from_user.id)
    role = message.text.strip()

    if role == "⬅️ Назад у меню":
        user_finish_state.pop(user_id, None)
        users = load_users()
        roles = users.get(user_id, {}).get("roles", [])
        menu = build_main_menu(roles)
        await message.answer("Повертаємось до головного меню ⬅️", reply_markup=menu)
        return

    users = load_users()
    if role not in users.get(user_id, {}).get("roles", []):
        await message.answer("❌ Це не твоя роль. Обери іншу або повернись у меню.")
        return

    # зберігаємо роль у стані
    user_finish_state[user_id]["role"] = role
    user_finish_state[user_id]["step"] = "choose_title"

    tasks = load_tasks()
    active_titles = sorted({t["title"] for t in tasks.values() if t["status"] == "в роботі" and t["role"] == role})

    if not active_titles:
        kb = build_back_keyboard()
        await message.answer(f"🔹 Немає активних задач для ролі {role}.", reply_markup=kb)
        return

    buttons = [[KeyboardButton(text=title)] for title in active_titles]
    buttons.append([KeyboardButton(text="⬅️ Назад у меню")])
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer(f"📚 Обери тайтл, який ти завершила для ролі {role}:", reply_markup=kb)


@dp.message(lambda m: str(m.from_user.id) in user_finish_state and user_finish_state[str(m.from_user.id)]["step"] == "choose_title")
async def choose_title_to_finish(message: Message):
    """Після вибору ролі — обираємо тайтл."""
    user_id = str(message.from_user.id)
    title = message.text.strip()

    if title == "⬅️ Назад у меню":
        user_finish_state.pop(user_id, None)
        users = load_users()
        roles = users.get(user_id, {}).get("roles", [])
        menu = build_main_menu(roles)
        await message.answer("Повертаємось до головного меню ⬅️", reply_markup=menu)
        return

    role = user_finish_state[user_id]["role"]
    tasks = load_tasks()
    available = [t for t in tasks.values() if t["title"] == title and t["status"] == "в роботі" and t["role"] == role]

    if not available:
        kb = build_back_keyboard()
        await message.answer("❌ Не знайдено активних задач із такою назвою для цієї ролі.", reply_markup=kb)
        return

    user_finish_state[user_id]["title"] = title
    user_finish_state[user_id]["step"] = "choose_chapters"

    kb = build_back_keyboard()
    await message.answer(
        f"✨ Які глави завершені для ролі {role}? (напиши номери через кому або діапазон: 01-05,07,09)",
        reply_markup=kb
    )
def create_next_stage(tasks, title, chapter, next_role):
    """Створює наступну задачу, якщо її ще немає."""
    exists = any(
        t["title"] == title and t["chapter"] == chapter and t["role"] == next_role
        for t in tasks.values()
    )
    if not exists:
        next_id = str(max([int(k) for k in tasks.keys()] + [0]) + 1)
        tasks[next_id] = {
            "title": title,
            "chapter": chapter,
            "role": next_role,
            "status": "в роботі"
        }

@dp.message(lambda m: str(m.from_user.id) in user_finish_state and user_finish_state[str(m.from_user.id)]["step"] == "choose_chapters")
async def choose_chapters_to_finish(message: Message):
    """Користувач вводить номери завершених глав."""
    user_id = str(message.from_user.id)
    title = user_finish_state[user_id]["title"]
    role = user_finish_state[user_id]["role"]

    raw_input = message.text.replace(" ", "")
    done_chapters = []
    for part in raw_input.split(","):
        if "-" in part:
            try:
                start, end = part.split("-")
                start_i = int(start)
                end_i = int(end)
                width = max(2, len(start))
                done_chapters.extend([str(i).zfill(width) for i in range(start_i, end_i + 1)])
            except ValueError:
                continue
        elif part:
            try:
                done_chapters.append(str(int(part)).zfill(2))
            except ValueError:
                continue

    # ⬇️ ТУТ НЕ ПОВИННО БУТИ ВІДСТУПУ!
    tasks = load_tasks()
    count = 0
    done_list = []  # Збираємо сюди всі завершені глави

    for t in list(tasks.values()):
        if (
            t["title"] == title
            and t["chapter"] in done_chapters
            and t["status"] == "в роботі"
            and t["role"] == role
        ):
            t["status"] = "готово"
            done_list.append(t["chapter"])


    # === Логіка створення наступних етапів ===
    for chapter in done_list:
        # 1️⃣ Якщо готовий Переклад → створюємо Ред
        if role == "✍️ Переклад":
            create_next_stage(tasks, title, chapter, "🖋 Ред")

        # 2️⃣ Якщо готовий Клін → перевіряємо чи вже є готовий Ред, тоді створюємо Тайп
        elif role == "🧼 Клін":
            red_done = any(
                tt["title"] == title and tt["chapter"] == chapter and tt["role"] == "🖋 Ред" and tt["status"] == "готово"
                for tt in tasks.values()
            )
            if red_done:
                create_next_stage(tasks, title, chapter, "🧩 Тайп")

        # 3️⃣ Якщо готовий Ред → перевіряємо чи вже є готовий Клін, тоді створюємо Тайп
        elif role == "🖋 Ред":
            clean_done = any(
                tt["title"] == title and tt["chapter"] == chapter and tt["role"] == "🧼 Клін" and tt["status"] == "готово"
                for tt in tasks.values()
            )
            if clean_done:
                create_next_stage(tasks, title, chapter, "🧩 Тайп")

        # 4️⃣ Якщо готовий Тайп → створюємо Бету
        elif role == "🧩 Тайп":
            create_next_stage(tasks, title, chapter, "👁 Бета")

        # 5️⃣ Бета — фінальний етап, фіксуємо завершення
        elif role == "👁 Бета":
            completed_file = "database/completed.json"

            # Завантажуємо існуючі завершені дані
            if os.path.exists(completed_file):
                with open(completed_file, "r", encoding="utf-8") as f:
                    try:
                        completed = json.load(f)
                    except json.JSONDecodeError:
                        completed = {}
            else:
                completed = {}

            if title not in completed:
                completed[title] = []

            new_completed = []
            for ch in done_chapters:
                if ch not in completed[title]:
                    completed[title].append(ch)
                    new_completed.append(ch)

            with open(completed_file, "w", encoding="utf-8") as f:
                json.dump(completed, f, indent=2, ensure_ascii=False)

    save_tasks(tasks)
    user_finish_state.pop(user_id, None)

    users = load_users()
    roles = users.get(user_id, {}).get("roles", [])
    menu = build_main_menu(roles)

    if done_list:
        await message.answer(
            f"✅ Завершено ({len(done_list)}) для ролі {role}: *{title}* — глави {', '.join(done_list)}.\n"
            f"➡️ Наступні етапи створено автоматично (якщо умови виконані).",
            parse_mode="Markdown",
            reply_markup=menu
        )
    else:
        await message.answer(
            "❌ Не знайдено збігів або ці глави вже були завершені.",
            reply_markup=menu
        )



# --- Обробка натискання "Назад у меню" ---
@dp.message(F.text == "⬅️ Назад у меню")
async def back_to_menu_global(message: Message):
    user_id = str(message.from_user.id)

    # Очистити стани, якщо були
    if user_id in admin_states:
        admin_states.pop(user_id, None)
    if 'user_finish_state' in globals() and user_id in user_finish_state:
        user_finish_state.pop(user_id, None)

    users = load_users()
    roles = users.get(user_id, {}).get("roles", [])
    menu = build_main_menu(roles)

    await message.answer("Повертаємось до головного меню ⬅️", reply_markup=menu)


# --- Вибір ролей ---
@dp.message()
async def handle_roles(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)
    text = message.text

    if text == "✅ Готово":
        roles = users.get(user_id, {}).get("roles", [])
        if not roles:
            await message.answer("Спочатку вибери хоча б одну роль 😉")
            return
        menu = build_main_menu(roles)
        await message.answer("Ролі збережено ✅\nОсь твоє меню:", reply_markup=menu)
        return

    if text in ROLES:
        if user_id not in users:
            users[user_id] = {"roles": [], "tasks": []}
        if text not in users[user_id]["roles"]:
            users[user_id]["roles"].append(text)
            save_users(users)
            await message.answer(f"Додано роль: {text} ✅")
        else:
            await message.answer(f"Ти вже маєш роль {text} 😉")
        return


# --- Запуск ---
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
