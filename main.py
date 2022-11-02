import random
from random import randrange
import datetime
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType


with open('bot_token.txt', 'r') as file:
    bot_token = file.readline()
with open('app_token.txt', 'r') as file:
    app_token = file.readline()
with open('photo_token.txt', 'r') as file:
    photo_token = file.readline()

vk_session = vk_api.VkApi(token=bot_token)
longpoll = VkLongPoll(vk_session)


def write_msg(user_id, message, attachment=0):
    vk_session.method('messages.send', {'user_id': user_id,
                                        'message': message,
                                        'random_id': randrange(10 ** 7),
                                        'attachment': attachment})


def get_user_info(user_id):
    user_info = {}
    url = 'https://api.vk.com/method/users.get'
    params = {
        'user_ids': user_id,
        'access_token': app_token,
        'v': 5.131,
        'fields': 'first_name, last_name, bdate, sex, city, relation, movies, music'
    }
    if requests.get(url, params=params).json().get('response'):
        for key, value in requests.get(url, params=params).json().get('response')[0].items():
            if key == 'city':
                user_info[key] = value['id']
            else:
                user_info[key] = value
    else:
        return False
    # print(user_info)
    return user_info


def check_user_info_missing(user_id):
    info_missing = []
    user_info = get_user_info(user_id)
    for item in ['bdate', 'sex', 'city', 'movies', 'music']:
        if not user_info.get(item):
            info_missing.append(item)
        if user_info['bdate'].count('.') != 2:
            info_missing.append('bdate')
    return info_missing


def translate_fields(fields: list):
    dictionary = {
        'bdate': 'Возраст в формате xx.xx.xxxx',
        'sex': 'Пол (1 - женский, 2 - мужской)',
        'city': 'Город',
        'movies': 'Любимый фильм',
        'music': 'Любимая музыка'
    }
    translation = []
    for field in fields:
        translation.append(dictionary[field])
    return translation


def get_age(date):
    return datetime.datetime.now().year - int(date[-4:])


def get_additional_information(user_id):
    info_missing = check_user_info_missing(user_id)
    missing_fields_translated = translate_fields(info_missing)
    fields_to_require = ''
    for field in missing_fields_translated:
        fields_to_require += f'{field}. '
    write_msg(user_id, f'''Похоже, мы мало о вас знаем.
    Пожалуйста, сообщите через запятую следующие данные:
    {fields_to_require}''')
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                return [text.strip() for text in event.text.split(',')]


def find_matches(user_info: dict):
    url = 'https://api.vk.com/method/users.search'
    params = {
        'age_from': user_info['age'] - 5,
        'age_to': user_info['age'] + 5,
        'sex': 3 - user_info['sex'],
        'city': user_info['city'],
        'status': 6,
        'has_photo': 1,
        'access_token': app_token,
        'v': 5.131
        }
    if requests.get(url, params=params).json().get('response'):
        print(requests.get(url, params=params).json().get('response'))
        return requests.get(url, params=params).json().get('response').get('items')



def choose_match(matches: list):
    filter_success = False
    random_choice = {}
    while not filter_success:
        random_choice = random.choice(matches)
        if get_photos(random_choice['id']) and not random_choice['is_closed']:
            filter_success = True
            print('success')
    return random_choice




def get_photos(user_id):
    url = 'https://api.vk.com/method/photos.getAll'
    params = {
        'owner_id': user_id,
        'extended': '1',
        'access_token': photo_token,
        'v': 5.131
    }
    response = requests.get(url, params=params).json().get('response')
    if response:
        if response.get('count') < 3:
            return False
        top_photos = sorted(response.get('items'), key=lambda x: x['likes']['count'], reverse=True)[:3]
        return True



def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                user_info = get_user_info(event.user_id)
                write_msg(event.user_id, f'''Привет, {user_info['first_name']}!
                Сейчас подберём вам пару через VKinder.''')
                info_missing = check_user_info_missing(event.user_id)
                if info_missing:
                    info_provided = dict(zip(info_missing, get_additional_information(event.user_id)))
                    user_info.update(info_provided)
                user_info['age'] = get_age(user_info['bdate'])
                print(user_info)
                write_msg(event.user_id, '''Информации о вас достаточно :)
                Начинаем подбирать пары......''')
                matches_found = find_matches(user_info)
                match_found = choose_match(matches_found)
                write_msg(event.user_id, f'''Мы нашли возможную пару: {match_found['first_name']} {match_found['last_name']}
Вы можете найти этого пользователя по ссылке: vk.com/id{match_found['id']}''')


main()