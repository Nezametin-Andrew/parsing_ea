import os
from dotenv import load_dotenv
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


platform = 'console'
load_dotenv()

main_host = os.getenv('MAIN_HOST')
proxy = os.getenv('PROXY_PC') if platform == 'pc' else os.getenv('PROXY_CONSOLE')
auth_proxy = os.getenv('AUTH_PROXY')
tg_token = os.getenv('TELEGRAM_TOKEN')
admins = tuple(os.getenv('ADMINS').split(','))
tg_url = f'https://api.telegram.org/bot{tg_token}/sendMessage'
server = os.getenv('SERVER_PC') if platform == 'pc' else os.getenv('SERVER_CONSOLE')
setting_parser = os.getenv('HOST_PARSING_DATA')
