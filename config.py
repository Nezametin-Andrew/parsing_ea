import os
from dotenv import load_dotenv


load_dotenv()

main_host = os.getenv('MAIN_HOST')
proxy_pc = os.getenv('PROXY_PC')
auth_proxy_pc = tuple(os.getenv('AUTH_PROXY_PC').split(':'))
tg_token = os.getenv('TELEGRAM_TOKEN')
admins = tuple(os.getenv('ADMINS').split(','))
tg_url = f'https://api.telegram.org/bot{tg_token}/sendMessage'