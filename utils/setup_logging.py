import sys
import logging
import pytz
from pytz.tzinfo import BaseTzInfo
from datetime import datetime



def setup_logging(log_to_file: bool, level: int, timezone: BaseTzInfo) -> None:
    '''Настройка логгирования под конкретный часовой пояс'''
    logging.Formatter.converter = lambda *args: datetime.now(tz=timezone).timetuple()
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_to_file:
        log_file_name = 'bot_log.log'
        handlers.append(logging.FileHandler(log_file_name))
    
    format = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(funcName)s: %(message)s'
    logging.basicConfig(
        level=level,
        format=format,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True,
    )

LOG_TO_FILE = False
LEVEL = logging.INFO
TIMEZONE: BaseTzInfo = pytz.timezone('Europe/Moscow')

setup_logging(log_to_file=LOG_TO_FILE, level=LEVEL, timezone=TIMEZONE)