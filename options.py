import os
import json

data = {
    "api_key": "dcf2cd99608ced960aacd96f208241e43934c006ee3927c8a4cb3426c4a4c3758e7b37bd20edb3ee5ff24",
    "news_api_key": ""
}


def option_exist():
    for file in os.listdir():
        if file == "data.json":
            return True


def option_data():
    if option_exist():
        with open("data.json", "r") as file:
            return json.load(file)
    else:
        print("Файл настроек был сконфигурирован автоматически.")
        data["api_key"] = input("Введите API ключ для платформы: ")
        data["news_api_key"] = input("Введите API ключ для платформы новостей: ")
        with open("data.json", "w+") as file:
            json.dump(data, file)
        return data
