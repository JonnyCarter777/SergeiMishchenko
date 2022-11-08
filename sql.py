import sqlalchemy
import psycopg2


DSN = 'postgresql://postgres:Gliese-581@localhost:5432/mydb'
engine = sqlalchemy.create_engine(DSN)
connection = engine.connect()


def create_db():
    initial_connection = psycopg2.connect(
        database="postgres",
        user='postgres',
        password='Gliese-581',
        host='localhost',
        port='5432'
    )
    initial_connection.autocommit = True
    cursor = initial_connection.cursor()
    sql = 'CREATE database mydb;'
    try:
        cursor.execute(sql)
    except psycopg2.ProgrammingError:
        print("Already exists")
    initial_connection.close()


def create_tables():
    connection.execute('''
    CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    first_name varchar(40) NOT NULL,
    last_name varchar(40) NOT NULL,
    sex integer NOT NULL,
    bdate date NOT NULL,
    city integer NOT NULL	
    );
    ''')
    connection.execute('''
    CREATE TABLE IF NOT EXISTS matches (
    id integer PRIMARY KEY,
    first_name varchar(40) NOT NULL,
    last_name varchar(40) NOT NULL,
    top_photo_1 integer NOT NULL,
    top_photo_2 integer NOT NULL,
    top_photo_3 integer NOT NULL
    );
    ''')
    connection.execute('''
    CREATE TABLE IF NOT EXISTS matches_to_users (
    user_id INTEGER REFERENCES users (id),
    match_id INTEGER REFERENCES matches (id),
    CONSTRAINT pk1 PRIMARY KEY (user_id, match_id)
    );
    ''')
    

def insert_user_into_db(user):
    """User as a dictionary"""
    if not connection.execute(f"SELECT id FROM users WHERE id = {user['id']};").fetchone():
        connection.execute(f"INSERT INTO users (id, first_name, last_name, sex, bdate, city)"
                           f"VALUES ({user['id']}, \'{user['first_name']}\',"
                           f"\'{user['last_name']}\', {user['sex']},"
                           f"\'{'-'.join(user['bdate'].split('.')[::-1])}\', {user['city']});")



def insert_match_into_db(user, photo_data):
    """User as a dictionary, photo_data as a dictionary"""
    if not connection.execute(f"SELECT id FROM matches WHERE id = {user['id']};").fetchone():
        connection.execute(f"INSERT INTO matches (id, first_name, last_name, top_photo_1, top_photo_2, top_photo_3)"
                           f"VALUES ({user['id']}, \'{user['first_name']}\',"
                           f"\'{user['last_name']}\', {photo_data['photo_ids'][0]},"
                           f"{photo_data['photo_ids'][1]}, {photo_data['photo_ids'][2]});")



def check_db_link(match, user_id):
    """Match as a dictionary, user_id as an integer"""
    if connection.execute(f'''SELECT user_id
    FROM matches_to_users
    WHERE user_id = {user_id} and match_id = {match['id']};''').fetchone():
        return False
    return True


def create_db_link(match, user_id):
    """Match as a dictionary, user_id as an integer"""
    if connection.execute(f'''SELECT user_id
    FROM matches_to_users
    WHERE user_id = {user_id} and match_id = {match['id']};''').fetchone():
        # print('Link already in db')
        return False
    connection.execute(f"INSERT INTO matches_to_users (user_id, match_id) VALUES ({user_id}, {match['id']});")
    return True
