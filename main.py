import random
from random import randrange
import datetime
import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from sql import insert_user_into_db, insert_match_into_db, check_db_link, create_db_link, create_db, create_tables


with open('bot_token.txt', 'r') as file:
    bot_token = file.readline()
with open('app_token.txt', 'r') as file:
    app_token = file.readline()


vk_session = vk_api.VkApi(token=bot_token)
vk_session2 = vk_api.VkApi(token=app_token)
longpoll = VkLongPoll(vk_session)


def get_user_info(user_id):
    """Takes user_id as an integer, returns user_info as a dictionary"""
    user_info = {}
    try:
        response = vk_session.method('users.get', {'user_id': user_id,
                                                   'v': 5.131,
                                                   'fields': 'first_name, last_name, bdate, sex, city'})
        if response:
            for key, value in response[0].items():
                # если response не пустой, то [0] по-любому есть(?)
                if key == 'city':
                    user_info[key] = value['id']
                else:
                    user_info[key] = value
        else:
            write_msg(user_id, f'''Извините, что-то пошло не так.''')
            return False

    except vk_api.exceptions.ApiError as e:
        write_msg(user_id, f'''Извините, что-то пошло не так.''')
        print(f'Error! {e}')
    return user_info


def write_msg(user_id, message, attachment='0'):
    vk_session.method('messages.send', {'user_id': user_id,
                                        'message': message,
                                        'random_id': randrange(10 ** 7),
                                        'attachment': attachment})


def check_user_info_missing(user_info):
    """Takes user_info as a dictionary, returns keys missing in user_info as a list"""
    info_missing = []
    for item in ['bdate', 'sex', 'city']:
        if not user_info.get(item):
            info_missing.append(item)
    if user_info['bdate'].count('.') != 2:
        info_missing.append('bdate')
    return info_missing


def get_additional_information(user_id, field):
    """Takes user_id as an integer to send a message and a field to require as a string,
    returns an answer as a string """
    write_msg(user_id, f'''Пожалуйста, сообщите следующие данные о себе:\n{translate_field(field)}''')
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                if field == 'city':
                    return get_city_id(user_id, event.text)
                elif field == 'bdate':
                    if event.text.count('.') != 2 or '.' in event.text[-4:]:
                        write_msg(user_id, 'Неверный формат даты! Попробуйте ещё')
                        return False
                    return event.text
                elif field == 'sex':
                    return int(event.text)


def get_city_id(user_id, city):
    """Takes user_id as an integer to send a message if not success and a city as a string,
    returns city_id as an integer"""
    try:
        response = vk_session.method('database.getCities', {'v': 5.131,
                                                            'q': city})
        if response:
            if response.get('items'):
                city_id = response.get('items')[0].get('id')
                return city_id
            write_msg(user_id, 'К сожалению, мы не нашли такого города...')
            return False
        write_msg(user_id, 'Упс, что-то пошло не так...')
        return False
    except vk_api.exceptions.ApiError as e:
        write_msg(user_id, f'''Извините, что-то пошло не так.''')
        print(f'Error! {e}')


def translate_field(field):
    """Takes a string in English, returns it in Russian also as a string"""
    dictionary = {
        'bdate': 'ваша дата рождения в формате xx.xx.xxxx',
        'sex': 'ваш пол (1 - женский, 2 - мужской)',
        'city': 'ваш город'
    }
    translation = dictionary[field]
    return translation


def get_age(date):
    """Takes a date of birth as a string in a xx.xx.xxxx format,
    returns corresponding age as of current day as an integer"""
    return datetime.datetime.now().year - int(date[-4:])


def find_matches(user_info):
    """Takes user_info as a dictionary, returns other users infos as a list of dictionaries"""
    try:
        response = vk_session2.method('users.search', {
                                      'age_from': user_info['age'] - 3,
                                      'age_to': user_info['age'] + 3,
                                      'sex': 3 - user_info['sex'],
                                      'city': user_info['city'],
                                      'city_id': user_info['city'],
                                      'status': 6,
                                      'has_photo': 1,
                                      'count': 1000,
                                      'v': 5.131})
        if response:
            if response.get('items'):
                return response.get('items')
            write_msg(user_info['id'], 'Упс, что-то пошло не так')
            return False
        write_msg(user_info['id'], 'Упс, мы никого не нашли')
        return False
    except vk_api.exceptions.ApiError as e:
        write_msg(user_info['id'], f'''Извините, что-то пошло не так.''')
        print(f'Error! {e}')


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
    try:
        response = vk_session2.method('photos.get', {'owner_id': user_id,
                                                     'album_id': 'profile',
                                                     'extended': '1',
                                                     'v': 5.131})
        if response.get('count'):
            if response.get('count') < 3:
                return False
            top_photos = sorted(response.get('items'), key=lambda x: x['likes']['count']
                                + x['comments']['count'], reverse=True)[:3]
            photo_data = {'user_id': top_photos[0]['owner_id'], 'photo_ids': []}
            for photo in top_photos:
                photo_data['photo_ids'].append(photo['id'])
            return photo_data
        return False
    except vk_api.exceptions.ApiError as e:
        print(f'Error! {e}')


def main():
    create_db()
    create_tables()
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                user_info = get_user_info(event.user_id)
                if not user_info:
                    continue
                write_msg(event.user_id, f'''Привет, {user_info['first_name']}!
Подберём вам пару через VKinder?''')
                info_missing = check_user_info_missing(user_info)
                while info_missing:
                    additional_info = get_additional_information(event.user_id, info_missing[0])
                    if not additional_info:
                        continue
                    user_info[info_missing[0]] = additional_info
                    info_missing.pop(0)
                user_info['age'] = get_age(user_info['bdate'])
                insert_user_into_db(user_info)
                write_msg(event.user_id, '''Информации о вас достаточно :)
Начинаем подбирать пары...''')
                matches_found = find_matches(user_info)
                if not matches_found:
                    write_msg(event.user_id, 'Упс, мы никого не нашли')
                    continue
                approval = '+'
                while approval.lower() in ['+', 'да']:
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
                    write_msg(event.user_id, 'Показать ещё?\nСтавьте плюсик или \"да\"')
                    for new_event in longpoll.listen():
                        if new_event.type == VkEventType.MESSAGE_NEW:
                            if new_event.to_me:
                                approval = new_event.text
                                break


if __name__ == '__main__':
    main()
