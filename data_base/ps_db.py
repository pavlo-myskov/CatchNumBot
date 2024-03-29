import psycopg2 as ps
from prettytable import PrettyTable, from_db_cursor
import datetime
from functools import wraps

import logging
import logging.config

logging.config.fileConfig('logging/logging.conf',
                          disable_existing_loggers=False)
log = logging.getLogger("db")


class BotDB:
    # __instance = None

    # def __new__(cls, *args, **kwargs):
    #     '''
    #     pattern Singleton
    #     Обеспечевает создания одного и только одного екзепляра класса
    #     Если объект None, тоесть он пока не существует, паттерн создает новый екземпляр.
    #     Если объект уже существует то при создании попытке создания нового екземпляра всегда будет
    #     возвращать и использовать уже существующий объект
    #     :return object
    #     '''
    #     if cls.__instance is None:
    #         cls.__instance = super().__new__(cls)
    #     return cls.__instance

    def __init__(self, DB_URL):
        """
        Проверяет коннект к бд, ловит ошибки. Создает объекты бд и курсора. Создает, если еще не созданы таблицы бд
        """
        try:
            log.debug('Trying to connect to the database')
            conn = ps.connect((DB_URL), sslmode='require')
        except TypeError or ps.ProgrammingError:
            log.error('Failed connection to the database or incorrect URL')
            return
        cursor = conn.cursor()
        self.conn, self.cursor = conn, cursor

        cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT, "
                       "last_name TEXT, join_date TIMESTAMP, bug_text TEXT)")

        cursor.execute('''CREATE TABLE IF NOT EXISTS game_stat(user_id BIGINT PRIMARY KEY, max_num INTEGER,
                        win_count INTEGER, win_count_for_stat INTEGER, max_num_for_stat INTEGER,
                        game_over_count INTEGER, last_win_date TIMESTAMP, last_over_date TIMESTAMP)''')

        cursor.execute("CREATE TABLE IF NOT EXISTS usage(user_id BIGINT PRIMARY KEY, welcome_count INTEGER, "
                       "start_game_count INTEGER, info_count INTEGER, help_count INTEGER, pidkazka_count INTEGER, "
                       "progress_count INTEGER, rating_count INTEGER, reset_count INTEGER, cancel_count INTEGER)")

        conn.commit()

        log.info('Successful connection to the database')

        '''
    def user_exists(self, user_id):
        """Проверяем, есть ли юзер в базе"""
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        return bool(self.cursor.fetchone())
        '''

# adding new user-----------------
    def add_usage(self, user_id: int) -> None:
        """
        Добавляет юзера в бд - счетчик, если он еще не добавлен
        :param user_id: telegram id юзера
        :return: None
        """
        self.cursor.execute(f"SELECT user_id FROM usage WHERE user_id = {user_id}")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO usage (user_id, welcome_count, start_game_count, info_count, "
                                "help_count, pidkazka_count, progress_count, rating_count, reset_count, "
                                "cancel_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (user_id, 0, 0, 0, 0, 0, 0, 0, 0, 0))
            self.cursor.execute("INSERT INTO game_stat (user_id, max_num, win_count, win_count_for_stat, "
                                "max_num_for_stat, game_over_count) VALUES (%s, %s, %s, %s, %s, %s) ",
                                (user_id, 10, 0, 0, 0, 0))
        self.conn.commit()

    def add_user(self, message):
        """Добавляем юзера в базу"""
        user_id = message.from_user.id
        self.cursor.execute(f"SELECT user_id FROM users WHERE user_id = {user_id}")
        if not self.cursor.fetchone():
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            username = message.from_user.username
            full_name = message.from_user.full_name
            self.cursor.execute('''INSERT INTO users (user_id, username, first_name, last_name , join_date)
                                VALUES (%s,%s,%s,%s,%s)''',
                                (user_id, username, first_name, last_name, datetime.datetime.now()))
            self.add_usage(user_id)
            log.info(f"The user: '{user_id} - {first_name}' has been added to DB")
        self.conn.commit()
# adding new user-----------------

# update_game_stat-----------------
    def update_win_count(self, user_id):
        """Обновляем данные в базе"""
        self.cursor.execute("UPDATE game_stat SET win_count = win_count + 1 WHERE user_id = %s", (user_id,))
        return self.conn.commit()

    def update_win_count_for_stat(self, user_id):
        """Обновляем данные в базе"""
        self.cursor.execute("UPDATE game_stat SET win_count_for_stat = win_count_for_stat + 1 WHERE user_id = %s",
                            (user_id,))
        return self.conn.commit()

    def update_max_num(self, user_id):
        """Обновляем данные в базе"""
        self.cursor.execute("UPDATE game_stat SET max_num = max_num * 2 WHERE user_id = %s", (user_id,))
        return self.conn.commit()

    def update_max_num_for_stat(self, user_id, max_num):
        """Обновляем данные в базе"""
        self.cursor.execute("UPDATE game_stat SET max_num_for_stat = %s WHERE user_id = %s", (max_num, user_id,))
        return self.conn.commit()

    def update_game_over_count(self, user_id):
        """Обновляем данные в базе"""
        self.cursor.execute("UPDATE game_stat SET game_over_count = game_over_count + 1 WHERE user_id = %s", (user_id,))
        return self.conn.commit()

    def update_last_win_date(self, user_id):
        self.cursor.execute('UPDATE game_stat SET last_win_date = now() WHERE user_id = %s', (user_id,))
        return self.conn.commit()

    def update_last_over_date(self, user_id):
        self.cursor.execute('UPDATE game_stat SET last_over_date = now() WHERE user_id = %s', (user_id,))
        return self.conn.commit()
# update_game_stat-----------------

# update_usage---------------------
    # decorator
    def usage_counter(self, func):
        '''
        Функция считает использования юзером декорироваемого хендлера и сохраняет значения в БД
        '''
        @wraps(func)
        def wraper(*args, **kwargs):
            result = func(*args, **kwargs)
            user_id = args[0]['from']['id']
            counter_name = func.__name__.replace('process_', '').replace('_command', '') + '_count'
            self.cursor.execute(f"UPDATE usage SET {counter_name} = {counter_name} + 1 WHERE user_id= %s",
                                (user_id,))
            self.conn.commit()
            return result
        return wraper

    def update_usage_counter(self, user_id: int, func: str):
        '''
        Cчитает использования юзером хендлера и сохраняет значения в БД

        :param int user_id: telegram id юзера
        :param str func: название вызванного хендлера
        '''
        self.add_usage(user_id)  # Добавляет юзера в таблицу-счетчик, если он еще не добавлен
        if func in {'welcome', 'start_game', 'info',
                    'help', 'pidkazka', 'progress',
                    'rating', 'reset', 'cancel'}:
            counter_name = func + '_count'
            self.cursor.execute(f"UPDATE usage SET {counter_name} = {counter_name} + 1 WHERE user_id = %s",
                                (user_id,))
            return self.conn.commit()

# update_usage---------------------

# reset---------------------
    def reset_values(self, user_id):
        """Сброс данных в базе"""
        self.cursor.execute("UPDATE game_stat SET max_num = 10 WHERE user_id = %s", (user_id,))
        self.cursor.execute("UPDATE game_stat SET win_count = 0 WHERE user_id = %s", (user_id,))
        return self.conn.commit()
# reset---------------------

# get data---------------------
    def get_user_name(self, user_id: int):
        """Достаем first_name юзера в базе по его user_id"""
        self.cursor.execute("SELECT first_name, username FROM users WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()

    def get_users(self):
        """Достаем first_name юзера в базе по его user_id"""
        self.cursor.execute("SELECT user_id, first_name, username FROM users")
        return self.cursor.fetchall()

    def get_max_num(self, user_id):
        """Достаем max_num с базы по user_id"""
        self.cursor.execute("SELECT max_num FROM game_stat WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()[0]

    def get_max_num_for_stat(self, user_id):
        """Достаем max_num с базы по user_id"""
        self.cursor.execute("SELECT max_num_for_stat FROM game_stat WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()[0]

    def get_win_count(self, user_id):
        """Достаем user_win с базы по user_id"""
        self.cursor.execute("SELECT win_count FROM game_stat WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()[0]

    def get_rating(self, message):
        """Достаем значения c разных таблиц с БД и формируем 2 списка с кортежами(users, win_count).
        Через цикл формируем словарь: first_name получаем с users, win_count берем с game_stat.
        Выводим в таблице с сортировкой по к-стве выиграшей.
        Чтобы таблица не встала криво в телеге выводим через:
        f'<pre>{db.get_rating()}</pre>', parse_mode=types.ParseMode.HTML
        """
        table = PrettyTable()
        table.field_names = ["--Ігрок--", "--Рівень--"]

        self.cursor.execute("SELECT user_id, first_name FROM users")
        users = self.cursor.fetchall()
        self.cursor.execute("SELECT user_id, win_count FROM game_stat")
        win_count = self.cursor.fetchall()
        rait_dict = {}
        # в цикле сравниваем `id`, если одинаковые - в словарь добавляем ключ как `first_name` с `users`,
        # `value` как `win_count` с `game_stat`
        for i in users:
            for j in win_count:
                if i[0] == j[0]:
                    rait_dict[i[1]] = j[1]
        # пример словаря на выходе: {'Pasha': 5, 'Ivan': 2}
        log.info(f'Юзер {message.from_user.first_name} запросил рейтинг:\n {rait_dict}')
        # формируем таблицу в prettytable для вывода юзеру в чат с сортировкой по лвл
        for i in rait_dict:
            if rait_dict[i] == 0:
                continue
            else:
                table.add_row([i, rait_dict[i]])
        table.sortby = "--Рівень--"     # сортировка таблицы по заголовку колонки
        table.reversesort = True
        return(table)

        self.cursor.execute("SELECT first_name, user_win FROM users ORDER BY user_win")
        users = from_db_cursor(self.cursor)
        return(users)
        # или вывод данных с БД прямо в таблицу
        # нужен импорт:   from prettytable import from_db_cursor
        # https://zetcode.com/python/prettytable/  - инфа по prettytable

    def get_stat(self):
        '''Получаем с timestamp с базы дату в указаном формате функцией to_char()'''
        self.cursor.execute("SELECT first_name, TO_CHAR(DATE, 'DD/MM/YY HH24:MI') FROM users")
        dates = from_db_cursor(self.cursor)
        return(dates)

    def set_bug_message(self, message):
        """Записываем bug_message от юзера с команды /bug в базу по user_id даного юзера"""
        user_id = message.from_user.id
        bug_text = message.text
        self.cursor.execute('UPDATE users SET bug_text = %s WHERE user_id = %s', (bug_text, user_id,))
        return self.conn.commit()

    def get_bug_text(self, user_id_bag_message):
        """Достаем bug_text от юзера по user_id и отправляем админу"""
        user_id = user_id_bag_message
        self.cursor.execute("SELECT bug_text FROM users WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()

    # def get_stat(self):
    #     # self.cursor.execute("SELECT first_name, date :: timestamp::date from users")
    #     x = PrettyTable()
    #     x.field_names = ["ЮЗЕР", "дата"]
    #     self.cursor.execute("SELECT first_name FROM users")
    #     users = self.cursor.fetchone()
    #     self.cursor.execute("SELECT date :: timestamp::date FROM users")
    #     dates = self.cursor.fetchone()
    #     self.cursor.execute("SELECT date_part('hour', date::TIMESTAMP) FROM users")
    #     hours = self.cursor.fetchall()
    #     self.cursor.execute("SELECT date_part('minute', date::TIMESTAMP) FROM users")
    #     minutes = self.cursor.fetchall()

    #     for name in users:
    #         for date in dates:
    #             x.add_row(name, date)

    #     log.info(x)
        # log.info(date)

        '''
    def get_rating(self):
        self.cursor.execute("SELECT username, user_win FROM users ORDER BY user_win")
        users = self.cursor.fetchall()
        return(users)
        top_text = ["NAME LVL"]
        for user in users:
            data = [f"{user[0]}|{user[1]}"]
            textpath = '\n'.join(data)
            top_text.append(textpath)
        text = '\n'.join(top_text)
        return text
        '''

    def close_connect(self):
        self.cursor.close()
        self.conn.close()
