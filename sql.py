import sqlalchemy
import psycopg2


DSN = 'postgresql://postgres:Gliese-581@localhost:5432/Vkinder'
engine = sqlalchemy.create_engine(DSN)
connection = engine.connect()


def insert_user_into_db(user):
    """User as a dictionary"""
    if not connection.execute(f"SELECT id FROM users WHERE id = {user['id']};").fetchone():
        connection.execute(f"INSERT INTO users (id, first_name, last_name, sex, bdate, city)"
                           f"VALUES ({user['id']}, \'{user['first_name']}\',"
                           f"\'{user['last_name']}\', {user['sex']},"
                           f"\'{'-'.join(user['bdate'].split('.')[::-1])}\', {user['city']});")
    #     print('User successfully added to db')
    # else:
    #     print(f"User with id {user['id']} already in db")


def insert_match_into_db(user, photo_data):
    """User as a dictionary, photo_data as a dictionary"""
    if not connection.execute(f"SELECT id FROM matches WHERE id = {user['id']};").fetchone():
        connection.execute(f"INSERT INTO matches (id, first_name, last_name, top_photo_1, top_photo_2, top_photo_3)"
                           f"VALUES ({user['id']}, \'{user['first_name']}\',"
                           f"\'{user['last_name']}\', {photo_data['photo_ids'][0]},"
                           f"{photo_data['photo_ids'][1]}, {photo_data['photo_ids'][2]});")
    #     print('Match successfully added to db')
    # else:
    #     print(f"Match with id {user['id']} already in db")


def check_db_link(match, user_id):
    """Match as a dictionary, user_id as an integer"""
    if connection.execute(f'''SELECT user_id
    FROM matches_to_users
    WHERE user_id = {user_id} and match_id = {match['id']};''').fetchone():
        # print('Link already in db')
        return False
    # print('No link in db yet')
    return True


def create_db_link(match, user_id):
    """Match as a dictionary, user_id as an integer"""
    if connection.execute(f'''SELECT user_id
    FROM matches_to_users
    WHERE user_id = {user_id} and match_id = {match['id']};''').fetchone():
        # print('Link already in db')
        return False
    connection.execute(f"INSERT INTO matches_to_users (user_id, match_id) VALUES ({user_id}, {match['id']});")
    # print('Link successfully added to db')
    return True
