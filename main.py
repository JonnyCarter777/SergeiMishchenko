from random import randrange
import datetime
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType


with open('bot_token.txt', 'r') as file:
    bot_token = file.readline()
with open('app_token.txt', 'r') as file:
    app_token = file.readline()

vk_session = vk_api.VkApi(token=bot_token)
longpoll = VkLongPoll(vk_session)


def write_msg(user_id, message):
    vk_session.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': randrange(10 ** 7),})


def get_user_info(user_id):
    user_info = {}
    url = 'https://api.vk.com/method/users.get'
    params = {
        'user_ids': user_id,
        'access_token': app_token,
        'v': 5.131,
        'fields': 'first_name, last_name, bdate, sex, city, relation'
    }
    if requests.get(url, params=params).json().get('response'):
        # print(requests.get(url, params=params).json().get('response'))
        for key, value in requests.get(url, params=params).json().get('response')[0].items():
            user_info[key] = value
    else:
        return False
    #print(user_info)
    return user_info


def get_age(user_id):
    user_info = get_user_info(user_id)
    if 'bdate' in user_info.keys() and user_info['bdate'].count('.') == 2:
        return datetime.datetime.now().year - int(user_info['bdate'][-4:])
    else:
        return 'Неизвестна точная дата рождения!'


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                incoming_message = event.text
                if incoming_message.lower() == "привет":
                    write_msg(event.user_id, f'''Привет, {get_user_info(event.user_id)['first_name']}!
                    Введи имя пользователя или его ID в ВК,
                    чтобы мы подобрали ему пару через VKinder''')
                else:
                    if get_user_info(event.text):
                        write_msg(event.user_id, f'''Подбираем пары для пользователя
                        {get_user_info(incoming_message)['first_name']} {get_user_info(incoming_message)['last_name']}''')
                    else:
                        write_msg(event.user_id, 'Ошибка, нет такого пользователя!')


main()