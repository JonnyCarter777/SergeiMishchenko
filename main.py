import random
from random import randrange
import datetime
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from sql import insert_user_into_db, insert_match_into_db, check_db_link, create_db_link

with open('bot_token.txt', 'r') as file:
    bot_token = file.readline()
with open('app_token.txt', 'r') as file:
    app_token = file.readline()


vk_session = vk_api.VkApi(token=bot_token)
longpoll = VkLongPoll(vk_session)


def write_msg(user_id, message, attachment='0'):
    vk_session.method('messages.send', {'user_id': user_id,
                                        'message': message,
                                        'random_id': randrange(10 ** 7),
                                        'attachment': attachment})


def get_user_info(user_id):
    """Takes user_id as an integer, returns user_info as a dictionary"""
    user_info = {}
    url = 'https://api.vk.com/method/users.get'
    params = {
        'user_ids': user_id,
        'access_token': app_token,
        'v': 5.131,
        'fields': 'first_name, last_name, bdate, sex, city, movies, music'
    }
    if requests.get(url, params=params).json().get('response'):
        for key, value in requests.get(url, params=params).json().get('response')[0].items():
            if key == 'city':
                user_info[key] = value['id']
            else:
                user_info[key] = value
    else:
        return False
    return user_info


def check_user_info_missing(user_info):
    """Takes user_info as a dictionary, returns keys missing in user_info as a list"""
    info_missing = []
    for item in ['bdate', 'sex', 'city', 'movies', 'music']:
        if not user_info.get(item):
            info_missing.append(item)
        if user_info['bdate'].count('.') != 2:
            info_missing.append('bdate')
    return info_missing


def translate_field(field):
    """Takes a string in English, returns it in Russian also as a string"""
    dictionary = {
        'bdate': 'ваша дата рождения в формате xx.xx.xxxx',
        'sex': 'ваш пол (1 - женский, 2 - мужской)',
        'city': 'ваш город',
        'movies': 'ваш любимый фильм',
        'music': 'ваша любимая музыка'
    }
    translation = dictionary[field]
    return translation


def get_age(date):
    """Takes a date of birth as a string in a xx.xx.xxxx format,
    returns corresponding age as of current day as an integer"""
    return datetime.datetime.now().year - int(date[-4:])


def get_additional_information(user_id, field):
    """Takes user_id as a dictionary to send a message and a field to require as a string,
    returns an answer as a string """
    write_msg(user_id, f'''Пожалуйста, сообщите следующие данные о себе:\n{translate_field(field)}''')
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                return event.text


def find_matches(user_info):
    """Takes user_info as a dictionary, returns other users infos as a list of dictionaries"""
    url = 'https://api.vk.com/method/users.search'
    params = {
        'age_from': user_info['age'] - 3,
        'age_to': user_info['age'] + 3,
        'sex': 3 - user_info['sex'],
        'city': user_info['city'],
        'status': 6,
        'has_photo': 1,
        'count': 1000,
        'access_token': app_token,
        'v': 5.131
    }
    if requests.get(url, params=params).json().get('response'):
        return requests.get(url, params=params).json().get('response').get('items')


def choose_match(matches, user_id):
    """Takes users infos as a list of dictionaries and user_id as an integer,
    makes some additional checks and filters for suitability,
    returns a random but suitable user_info as a dictionary"""
    filter_success = False
    random_choice = {}
    while not filter_success:
        random_choice = random.choice(matches)
        if get_photos(random_choice['id'])\
                and not random_choice['is_closed']\
                and random_choice['id'] != user_id\
                and check_db_link(random_choice, user_id):
            filter_success = True
    return random_choice


def get_photos(user_id):
    """Takes user_id as an integer, returns 3 photos data as a dictionary"""
    url = 'https://api.vk.com/method/photos.get'
    params = {
        'owner_id': user_id,
        'album_id': 'profile',
        'extended': '1',
        'access_token': app_token,
        'v': 5.131
    }
    response = requests.get(url, params=params).json().get('response')
    if response:
        if response.get('count') < 3:
            return False
        top_photos = sorted(response.get('items'), key=lambda x: x['likes']['count']
                            + x['comments']['count'], reverse=True)[:3]
        photo_data = {'user_id': top_photos[0]['owner_id'], 'photo_ids': []}
        for photo in top_photos:
            photo_data['photo_ids'].append(photo['id'])
        return photo_data


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                user_info = get_user_info(event.user_id)
                write_msg(event.user_id, f'''Привет, {user_info['first_name']}!
Подберём вам пару через VKinder?
Сейчас проверим, достаточно ли мы о вас знаем.''')
                info_missing = check_user_info_missing(user_info)
                while info_missing:
                    additional_info = get_additional_information(event.user_id, info_missing[0])
                    user_info[info_missing[0]] = additional_info
                    info_missing.pop(0)
                user_info['age'] = get_age(user_info['bdate'])
                insert_user_into_db(user_info)
                write_msg(event.user_id, '''Информации о вас достаточно :)
Начинаем подбирать пары...''')
                matches_found = find_matches(user_info)
                match_found = choose_match(matches_found, event.user_id)
                photo_data = get_photos(match_found['id'])
                insert_match_into_db(match_found, photo_data)
                create_db_link(match_found, event.user_id)
                write_msg(event.user_id,
                          f'''Мы нашли возможную пару: {match_found['first_name']} {match_found['last_name']}
Вы можете найти этого пользователя по ссылке: vk.com/id{match_found['id']}''',
                          attachment=f"photo{photo_data['user_id']}_{photo_data['photo_ids'][0]},"
                                     f"photo{photo_data['user_id']}_{photo_data['photo_ids'][1]},"
                                     f"photo{photo_data['user_id']}_{photo_data['photo_ids'][2]}")


if __name__ == '__main__':
    main()
