import os
from dotenv import load_dotenv


load_dotenv()

main_host = os.getenv('MAIN_HOST')
proxy_pc = os.getenv('PROXY_PC')
auth_proxy_pc = tuple(os.getenv('AUTH_PROXY_PC').split(':'))
