import os
import datetime
import telegram
import requests
import logging
import sys

from dotenv import load_dotenv
import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    level=logging.INFO)


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Проверяем отправку сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            'Бот успешно отправил сообщение '
            + message + ' в чат ' + TELEGRAM_CHAT_ID
        )
    except telegram.error.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Проверяем ответ API."""
    try:
        timestamp = current_timestamp or int(datetime.time())
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        message = f'Сайт не отвечает {error}'
    if response.status_code != 200:
        message = f'Ошибочный статус ответа по API: {response.status_code}'
        raise exceptions.CheckResponseStatusException(message)
    return response.json()


def check_response(response):
    """Проверка ответа сайта."""
    if not isinstance(response, dict):
        raise TypeError('Тип не словарь.')
    homeworks = response['homeworks']
    if 'homeworks' not in response:
        raise KeyError('Ключ не найден.')
    if not isinstance(homeworks, list):
        raise TypeError('Тип не список.')
    if not homeworks:
        error = f'Список {homeworks} пуст'
        raise exceptions.EmptyValueException(error)
    logging.info('Статус домашней работы.')
    return homeworks


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('Тип не словарь.')
    if 'homework_name' not in homework:
        raise KeyError('Ключ не найден.')
    if 'status' not in homework:
        raise KeyError('Ключ не найден.')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        error = (
            f'Недокументированный статус домашней работы,'
            f'обнаруженный в ответе API: {homework_status}.'
        )
        raise exceptions.UnknownStatusException(error)
    if homework_name is None:
        error = (
            f'Нет такого имени в списке {homework_name}'
        )
        raise exceptions.UnknownNameException(error)
    verdict = homework_status
    logging.info('Получен новый статус.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие необходимых переменных."""
    if not PRACTICUM_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная: PRACTICUM_TOKEN.'
            'Программа принудительно остановлена.'
        )
        return False
    if not TELEGRAM_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная: TELEGRAM_TOKEN.'
            'Программа принудительно остановлена.'
        )
        return False
    if not TELEGRAM_CHAT_ID:
        logging.critical(
            'Отсутствует обязательная переменная: TELEGRAM_CHAT_ID.'
            'Программа принудительно остановлена.'
        )
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = 'Необходимые переменные отсутствуют.'
        logging.error(error, exc_info=True)
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(datetime.timedelta() - 30 * 24 * 60 * 60)
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message != status:
                send_message(bot, message)
                status = message
            current_timestamp = current_timestamp
            datetime.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Ошибка при запросе к основному API: {error}')
        finally:
            datetime.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
