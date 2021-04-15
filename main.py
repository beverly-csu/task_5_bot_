import vk_api, options, json, sqlite3, requests
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randint

data = options.option_data()

vk = vk_api.VkApi(token=data["api_key"])
vk_long_poll = VkLongPoll(vk)
connect = sqlite3.connect("db.sqlite")
cursor = connect.cursor()


def get_button(text, color):
    return {
        "action": {
            "type": "text",
            "payload": "{\"button\": \"1\"}",
            "label": text
        },
        "color": color
    }


def get_key(buttons):
    color = {
        "blue": "primary",
        "red": "negative",
        "green": "positive",
        "white": "secondary"
    }
    button_matrix = []
    for line in buttons:
        button_line = []
        for button in line:
            button_line.append(get_button(button[0], color[button[1]]))
        button_matrix.append(button_line)
    keyboard = {
        "one_time": False,
        "buttons": button_matrix
    }
    keyboard = json.dumps(keyboard, ensure_ascii=False).encode("utf-8")
    keyboard = str(keyboard.decode("utf-8"))
    return keyboard


def button_status(user_id, model="color_list"):
    request = """SELECT * FROM categories WHERE user_id LIKE (?)"""
    status = list(cursor.execute(request, (user_id,)).fetchone())
    status.remove(user_id)
    if model == "color_list":
        for index in range(len(status)):
            if status[index] == 1:
                status[index] = "blue"
            else:
                status[index] = "white"
    return status


def clear_keys(keywords):
    keywords = str(keywords)
    keywords = keywords.replace("\\", "")
    keywords = keywords.replace("'", "")
    keywords = keywords.replace("[", "")
    keywords = keywords.replace("]", "")
    keywords = keywords.replace('"', '')
    keywords = keywords.replace("(", "")
    keywords = keywords.replace(")", "")
    keywords = keywords.replace(",", "")
    return keywords


def select_keys(user_id):
    request = """SELECT * FROM keywords WHERE user_id LIKE {}""".format(user_id)
    keywords = cursor.execute(request).fetchone()[1]
    print(keywords)
    keywords = clear_keys(keywords)
    keywords = keywords.split()
    if "None" in keywords:
        keywords.remove("None")
    return keywords


def add_key(user_id, word):
    keys = select_keys(user_id)
    if word in keys:
        return "Данное слово уже есть в вашем списке"
    if "None" in keys:
        keys.remove("None")
    keys.append(word)
    request = """UPDATE keywords SET keywords="{}" WHERE user_id LIKE {}""".format(str(keys), user_id, )
    cursor.execute(request)
    connect.commit()
    return "Ключевое слово добавлено"


def del_key(user_id, word):
    keys = select_keys(user_id)
    try:
        index = keys.index(word)
        keys.pop(index)
    except ValueError:
        pass
    request = """UPDATE keywords SET keywords="{}" WHERE user_id LIKE {}""".format(str(keys), user_id, )
    cursor.execute(request)
    connect.commit()
    return "Ключевое слово удалено"


def news_print(msg_data, user_id, category):
    option = list(cursor.execute("""SELECT * FROM option WHERE user_id LIKE (?)""", (user_id,)).fetchone())
    index = categories[0].index(category)
    if option[2] != "all":
        link_gen = f"https://newsapi.org/v2/top-headlines?country={option[2]}&category={categories[0][index]}&pageSize={option[1]}&apiKey={options.option_data()['news_api_key']}"
    else:
        link_gen = f"https://newsapi.org/v2/top-headlines?category={categories[0][index]}&pageSize={option[1]}&apiKey={options.option_data()['news_api_key']}"
    answer = requests.get(link_gen)
    answer = answer.json()
    if answer["totalResults"] <= option[1]:
        count = answer["totalResults"]
        if select_state(msg_data) == "category":
            send_msg(user_id, categories[1][index], key_in_cats(msg_data, category))
        if select_state(msg_data) == "main":
            send_msg(user_id, categories[1][index], key_main())
    elif answer["totalResults"] == 0:
        return "В данный момент новостей из данной категории нет"
    else:
        if select_state(msg_data) == "category":
            send_msg(user_id, categories[1][index], key_in_cats(msg_data, category))
        if select_state(msg_data) == "main":
            send_msg(user_id, categories[1][index], key_main())
        count = option[1]
    for i in range(0, count):
        article = str(answer["articles"][i]["title"] + "\n" + answer["articles"][i]["url"])
        if select_state(msg_data) == "category":
            send_msg(msg_data["user_id"], article, key_in_cats(msg_data, category))
        if select_state(msg_data) == "main":
            send_msg(msg_data["user_id"], article, key_main())


def q_print(user_id):
    option = list(cursor.execute("""SELECT * FROM option WHERE user_id LIKE (?)""", (user_id,)).fetchone())
    keys = select_keys(user_id)
    for key in keys:
        if option[2] != "all":
            link_gen = f"https://newsapi.org/v2/top-headlines?q={key}&pageSize={option[1]}&apiKey={options.option_data()['news_api_key']}"
        else:
            link_gen = f"https://newsapi.org/v2/top-headlines?q={key}&pageSize={option[1]}&apiKey={options.option_data()['news_api_key']}"
        answer = requests.get(link_gen)
        answer = answer.json()
        if answer["totalResults"] <= option[1]:
            count = answer["totalResults"]
            send_msg(user_id, key.capitalize(), key_main())
        elif answer["totalResults"] == 0:
            return "В данный момент новостей из данной категории нет"
        else:
            send_msg(user_id, key.capitalize(), key_main())
            count = option[1]
        for i in range(0, count):
            article = str(answer["articles"][i]["title"] + "\n" + answer["articles"][i]["url"])
            send_msg(user_id, article, key_main())


def all_news_print(msg_data, user_id):
    active_cats = button_status(user_id, "values")
    if 1 not in active_cats:
        send_msg(user_id, "У вас нет активных подписок на категории", key_main())
    else:
        for cat in categories[0]:
            if active_cats[categories[0].index(cat)] == 1:
                news_print(msg_data, user_id, cat)


def create_db():
    request_users = """CREATE TABLE IF NOT EXISTS users ("user_id" INTEGER NOT NULL UNIQUE, "name" TEXT NOT NULL, "surname" TEXT, "date_reg" INTEGER, "state" TEXT NOT NULL, "temp_cat" TEXT NOT NULL, "temp_flag" TEXT NOT NULL,  PRIMARY KEY("user_id"))"""
    request_categories = """CREATE TABLE IF NOT EXISTS "categories" ("user_id" INTEGER NOT NULL UNIQUE, "business" INTEGER NOT NULL DEFAULT 0, "entertainment" INTEGER NOT NULL DEFAULT 0, "general" INTEGER NOT NULL DEFAULT 0, "health" INTEGER NOT NULL DEFAULT 0, "science" INTEGER NOT NULL DEFAULT 0, "sports" INTEGER NOT NULL DEFAULT 0, "technology" INTEGER NOT NULL DEFAULT 0, PRIMARY KEY("user_id"))"""
    request_keywords = """CREATE TABLE IF NOT EXISTS "keywords" ("user_id" INTEGER NOT NULL UNIQUE, "keywords" TEXT, PRIMARY KEY("user_id"))"""
    request_news = """CREATE TABLE IF NOT EXISTS "option" ("user_id" INTEGER NOT NULL UNIQUE, "pageSize" INTEGER NOT NULL DEFAULT 3, "country" TEXT NOT NULL DEFAULT "all", PRIMARY KEY("user_id"))"""
    cursor.execute(request_users)
    cursor.execute(request_categories)
    cursor.execute(request_keywords)
    cursor.execute(request_news)
    connect.commit()


create_db()
categories = [
    ["business", "entertainment", "general", "health", "science", "sports", "technology"],
    ["Бизнес", "Развлечения", "Популярное", "Здоровье", "Наука", "Спорт", "Технологии"]
]


def check_user(user_id):
    request = """SELECT * FROM users WHERE user_id LIKE (?)"""
    status = cursor.execute(request, (user_id,)).fetchone()
    if status is None:
        return False
    else:
        return True


def create_user(user_info):
    if not check_user(user_info["user_id"]):
        request_users = """INSERT INTO users ('user_id', 'name', 'surname', 'date_reg', 'state', 'temp_cat', 'temp_flag') VALUES (?, ?, ?, ?, ?, ?, ?)"""
        request_categories = """INSERT INTO categories ('user_id') VALUES (?)"""
        request_keywords = """INSERT INTO keywords ('user_id') VALUES (?)"""
        request_news = """INSERT INTO "option" ('user_id') VALUES (?)"""
        cursor.execute(request_users,
                       (user_info["user_id"], user_info["name"], user_info["surname"], user_info["datetime"], "main",
                        "none", "none"))
        user_id = user_info["user_id"]
        cursor.execute(request_categories, (user_id,))
        cursor.execute(request_keywords, (user_id,))
        cursor.execute(request_news, (user_id,))
        connect.commit()


def select_temp_flag(user_id):
    request = """SELECT * FROM users WHERE user_id LIKE {}""".format(user_id)
    flag = list(cursor.execute(request).fetchone())
    flag = flag[6]
    return flag


def update_temp_flag(user_id, flag):
    request = """UPDATE users SET "temp_flag"="{}" WHERE user_id LIKE {}""".format(flag, user_id)
    cursor.execute(request)
    connect.commit()


def update_state(msg_data, state):
    request = """UPDATE users SET "state"="{}" WHERE user_id LIKE {}""".format(state, msg_data["user_id"])
    cursor.execute(request)
    connect.commit()


def select_state(msg_data):
    request = """SELECT * FROM users WHERE user_id LIKE {}""".format(msg_data["user_id"])
    state = list(cursor.execute(request).fetchone())
    state = state[4]
    return state


def update_cat(msg_data, cat):
    request = """UPDATE users SET "temp_cat"="{}" WHERE user_id LIKE {}""".format(cat, msg_data["user_id"])
    cursor.execute(request)
    connect.commit()


def select_cat(msg_data):
    request = """SELECT * FROM users WHERE user_id LIKE {}""".format(msg_data["user_id"])
    cat = list(cursor.execute(request).fetchone())
    cat = cat[5]
    return cat


def category_update(user_id, category_s):
    status = button_status(user_id, "values")
    index = categories[0].index(category_s)
    if status[index] == 0:
        request = """UPDATE categories SET {}=1 WHERE user_id LIKE {}""".format(categories[0][index], user_id)
        cursor.execute(request)
        connect.commit()
        return "Подписка на категорию успешно оформлена"
    else:
        request = """UPDATE categories SET {}=0 WHERE user_id LIKE {}""".format(categories[0][index], user_id)
        cursor.execute(request)
        connect.commit()
        return "Подписка на категорию успешно отменена"


def size_edit(user_id, size):
    request = """UPDATE "option" SET pageSize={} WHERE user_id LIKE {}""".format(size, user_id)
    cursor.execute(request)
    connect.commit()
    return "Изменение сохранено"


def country_edit(user_id, country):
    request = """UPDATE "option" SET "country"="{}" WHERE user_id LIKE {}""".format(country, user_id)
    cursor.execute(request)
    connect.commit()
    return "Изменение сохранено"


def acc_info(msg_data):
    request = """SELECT * FROM users WHERE user_id LIKE {}""".format(msg_data["user_id"])
    info = list(cursor.execute(request).fetchone())
    return "Информация об аккаунте:\nИмя: " + info[1] + "\nФамилия: " + info[2] + "\nID: " + str(info[
                                                                                                     0]) + "\nДата регистрации: " + \
           info[3]


def read_msg(user_id):
    vk.method("messages.markAsRead", {"peer_id": user_id})


def send_msg(user_id, text, keyboard):
    vk.method("messages.send",
              {"user_id": user_id, "random_id": randint(0, 2147483648), "message": text, "keyboard": keyboard})


def key_in_cats(msg_data, category):
    if msg_data["text"].capitalize() in categories[1] or category in categories[0]:
        try:
            index = categories[1].index(msg_data["text"].capitalize())
        except ValueError:
            index = categories[0].index(category)
        if button_status(msg_data["user_id"], "values")[index] == 1:
            subscribe_mode = [["Отписаться от категории", "red"]]
        else:
            subscribe_mode = [["Подписаться на категорию", "green"]]
        return get_key(
            [[[str("Новости из категории: <" + categories[1][index] + ">"), "blue"]],
             subscribe_mode,
             [["Описание", "white"], ["Назад", "green"]]])


def key_main():
    return get_key(
        [
            [["Последние новости (категории)", "blue"]],
            [["Последние новости (ключевые слова)", "blue"]],
            [["Категории", "white"], ["Ключевые слова", "white"]],
            [["Настройки", "white"], ["Справка", "white"]]
        ]
    )


def key_cats(msg_data):
    key_status = button_status(msg_data["user_id"])
    return get_key(
        [[[categories[1][0], key_status[0]], [categories[1][1], key_status[1]]],
         [[categories[1][2], key_status[2]], [categories[1][3], key_status[3]]],
         [[categories[1][4], key_status[4]], [categories[1][5], key_status[5]]],
         [[categories[1][6], key_status[6]], ["Назад", "green"]]])


def key_size(msg_data):
    page_size = ["1", "2", "3", "5"]
    line = []
    request = """SELECT * FROM "option" WHERE user_id LIKE (?)"""
    option = list(cursor.execute(request, (msg_data["user_id"],)).fetchone())
    option.pop(0)
    for size in page_size:
        if int(size) == option[0]:
            line.append([size, "blue"])
        else:
            line.append([size, "white"])
    return get_key([line, [["Назад", "green"]]])


def key_country(msg_data):
    countries = ["ru", "us", "all"]
    line = []
    request = """SELECT * FROM "option" WHERE user_id LIKE (?)"""
    option = list(cursor.execute(request, (msg_data["user_id"],)).fetchone())
    option.pop(0)
    for country in countries:
        if country == option[1]:
            line.append([country, "blue"])
        else:
            line.append([country, "white"])
    line.append(["Назад", "green"])
    return get_key([line])


def key_keys():
    return get_key([
        [["Добавить", "blue"], ["Удалить", "blue"]],
        [["Посмотреть", "white"], ["Назад", "green"]],
    ])


def key_option():
    return get_key(
        [
            [["Язык поиска", "white"], ["Количество новостей", "white"]],
            [["Данные аккаунта", "blue"], ["Назад", "green"]]
        ]
    )


menu_levels = {
    "categories": "main",
    "category": "categories",
    "country": "option",
    "size": "option"
}


def main():
    subscribe_status = False
    page_size = ["1", "2", "3", "5"]
    country_list = ["ru", "us", "all"]
    for event in vk_long_poll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                user_info = vk.method("users.get", {"user_ids": event.user_id})
                msg_data = {
                    "user_id": event.user_id,
                    "text": event.text.lower(),
                    "name": user_info[0]["first_name"],
                    "surname": user_info[0]["last_name"],
                    "datetime": event.datetime
                }
                if msg_data["text"] == "начать":
                    send_msg(msg_data["user_id"], "Добро пожаловать!", key_main())
                    read_msg(msg_data["user_id"])
                    create_user(msg_data)
                try:
                    index = categories[1].index(msg_data["text"].capitalize())
                    update_cat(msg_data, categories[0][index])
                except ValueError:
                    pass
                if msg_data["text"] == "отписаться от категории":
                    string = category_update(msg_data["user_id"], select_cat(msg_data))
                    subscribe_status = True
                if select_temp_flag(msg_data["user_id"]) == "add":
                    send_msg(msg_data["user_id"], add_key(msg_data["user_id"], msg_data["text"]), key_keys())
                    update_temp_flag(msg_data["user_id"], "none")
                if select_temp_flag(msg_data["user_id"]) == "del":
                    send_msg(msg_data["user_id"], del_key(msg_data["user_id"], msg_data["text"]), key_keys())
                    update_temp_flag(msg_data["user_id"], "none")
                if msg_data["text"] == "подписаться на категорию":
                    string = category_update(msg_data["user_id"], select_cat(msg_data))
                    subscribe_status = True
                if subscribe_status:
                    send_msg(msg_data["user_id"], string, key_in_cats(msg_data, select_cat(msg_data)))
                    subscribe_status = False
                if msg_data["text"].capitalize() in categories[1]:
                    update_state(msg_data, "category")
                    send_msg(msg_data["user_id"],
                             str("Вы перешли в меню категории <" + msg_data["text"].capitalize() + ">"),
                             key_in_cats(msg_data, select_cat(msg_data)))
                if msg_data["text"] == "категории":
                    update_state(msg_data, "categories")
                    send_msg(msg_data["user_id"], "Выбирайте категории на любой вкус!", key_cats(msg_data))
                    read_msg(msg_data["user_id"])
                if msg_data["text"] == "настройки":
                    update_state(msg_data, "option")
                    send_msg(msg_data["user_id"],
                             "Вы находитесь в меню настроек",
                             key_option())
                    read_msg(msg_data["user_id"])
                if msg_data["text"] == "количество новостей":
                    update_state(msg_data, "size")
                    send_msg(msg_data["user_id"],
                             "Выберите количество новостей, которые будут показываться Вам за один запрос",
                             key_size(msg_data))
                    read_msg(msg_data["user_id"])
                if msg_data["text"] == "последние новости (категории)":
                    all_news_print(msg_data, msg_data["user_id"])
                if msg_data["text"] == "последние новости (ключевые слова)":
                    q_print(msg_data["user_id"])
                if msg_data["text"] == "ключевые слова":
                    update_state(msg_data, "keys")
                    send_msg(msg_data["user_id"], "Вы находитесь в меню редактора ключевых слов", key_keys())
                if msg_data["text"] == "добавить":
                    send_msg(msg_data["user_id"], "Введите ключевое слово", key_keys())
                    update_temp_flag(msg_data["user_id"], "add")
                if msg_data["text"] == "удалить":
                    send_msg(msg_data["user_id"], "Введите ключевое слово", key_keys())
                    update_temp_flag(msg_data["user_id"], "del")
                if msg_data["text"] == "посмотреть":
                    keys = select_keys(msg_data["user_id"])
                    string = "Ваши ключевые слова:\n"
                    for key in keys:
                        string = string + key.capitalize() + "\n"
                    send_msg(msg_data["user_id"], string, key_keys())
                if msg_data["text"] == "язык поиска":
                    update_state(msg_data, "country")
                    send_msg(msg_data["user_id"], "Выберите язык, на котором будут выводиться новости",
                             key_country(msg_data))
                    read_msg(msg_data["user_id"])
                if msg_data["text"] in page_size:
                    send_msg(msg_data["user_id"], size_edit(msg_data["user_id"], int(msg_data["text"])),
                             key_size(msg_data))
                    read_msg(msg_data["user_id"])
                if msg_data["text"] in country_list:
                    send_msg(msg_data["user_id"], country_edit(msg_data["user_id"], msg_data["text"]),
                             key_country(msg_data))
                    read_msg(msg_data["user_id"])
                if msg_data["text"] == "данные аккаунта":
                    send_msg(msg_data["user_id"], acc_info(msg_data),
                             key_option())
                    read_msg(msg_data["user_id"])
                if msg_data["text"] == "справка":
                    send_msg(msg_data["user_id"], "Данный новостной бот был разработан by beverly-csu!",
                             key_main())
                    read_msg(msg_data["user_id"])
                if msg_data["text"].startswith("новости из категории:"):
                    send_msg(msg_data["user_id"], categories[1][categories[0].index(select_cat(msg_data))],
                             key_in_cats(msg_data, select_cat(msg_data)))
                    news_print(msg_data, msg_data["user_id"], select_cat(msg_data))
                if msg_data["text"] == "назад":
                    if select_state(msg_data) == "category":
                        send_msg(msg_data["user_id"], "Вы вернулись к меню категорий.", key_cats(msg_data))
                        update_state(msg_data, "categories")
                    elif select_state(msg_data) == "categories":
                        send_msg(msg_data["user_id"], "Вы вернулись в главное меню.", key_main())
                        update_state(msg_data, "main")
                    elif select_state(msg_data) == "option":
                        send_msg(msg_data["user_id"], "Вы вернулись в главное меню.", key_main())
                        update_state(msg_data, "main")
                    elif select_state(msg_data) == "size":
                        send_msg(msg_data["user_id"], "Вы вернулись в меню настроек.", key_option())
                        update_state(msg_data, "option")
                    elif select_state(msg_data) == "country":
                        send_msg(msg_data["user_id"], "Вы вернулись в меню настроек.", key_option())
                        update_state(msg_data, "option")
                    elif select_state(msg_data) == "keys":
                        send_msg(msg_data["user_id"], "Вы вернулись в меню настроек.", key_main())
                        update_state(msg_data, "main")


if __name__ == "__main__":
    main()
