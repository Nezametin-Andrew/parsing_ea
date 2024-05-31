import json
import random
from scrap.request import Request


class BaseEaCom:

    def __init__(self, **kwargs):
        self.email = kwargs['email']
        self.access_token = kwargs['access_token']
        self.platform = 'pc' if kwargs['platform'] == '1' else 'console'
        self.sesid = kwargs['auth']
        self.error = None
        self.get_ea_data()

    def get_ea_data(self):

        """
        Загружает данные EA из файла 'ea.json' и устанавливает соответствующие атрибуты.
        :return: None
        """

        try:
            with open('ea.json', 'r') as file:
                data = json.load(file)
            for key in data:
                if key == 'transfer_headers':
                    val = data[key]
                    val['X-Ut-Sid'] = self.sesid
                    self.transfer_headers = val
                    continue
                setattr(self, key, data[key])

        except FileNotFoundError:
            print("Error: 'ea.json' file not found.")
            self.error = "FileNotFoundError"
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from 'ea.json'.")
            self.error = "JSONDecodeError"
        except Exception as e:
            print(f"Error loading EA data. Details: {str(e)}")
            self.error = e


class EaComAuth(BaseEaCom):
    """
    Class для взаимодействия с EA.

    :argument:
        email (str): Электронная почта пользователя.
        access_token (str): Токен доступа для аутентификации.
        platform (str): Платформа пользователя ('pc' или 'console').
        session_id (str): Идентификатор сессии.
    """

    DEFAULT_DATA_FOR_TRANSFER = {
        'page': 1,
        'amount_data': 50,
        'start_point': 50,
        'price': random.randrange(260, 310) * 1000
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.header_pl = 'FFA24PCC' if self.platform == 'pc' else 'FFA24PS5'
        self.updated_sesid = None
        self.transfer_headers, self.auth_code, self.personal_id, self.persona = None, None, None, None
        self.persona_id, self.code_for_auth, self.status_try_auth = None, None, None

    async def try_auth(self):

        """
        Пытается аутентифицировать пользователя.

        Этот метод выполняет несколько шагов для аутентификации пользователя,
        включая получение кода авторизации, идентификатора пользователя и сессии.
        :return: None
        """

        await self._get_auth_code()
        if self.auth_code is not None:
            await self._get_personal_id()
            if self.personal_id is not None:
                await self._get_person()
                if self.persona_id is not None:
                    await self._get_code_for_auth()
                    if self.code_for_auth is not None:
                        session_id = await self._get_session_id()
                        if session_id:
                            self.updated_sesid = session_id
                            return
        if self.error is None:
            self.error = f"Error update session id for account: {self.email}. Try update access key"

        if self.status_try_auth is None:
            self.status_try_auth = 403

    async def check_session_acc(self):

        """
        Проверка сессии для аккаунта EA
        :return: dict -> status, error = bool, bool
        """

        req = Request()
        data = await req.fetch(
            url=self.transfer_link.format(**self.DEFAULT_DATA_FOR_TRANSFER),
            headers=self.transfer_headers
        )
        if req.status_code == 401:
            return {'error': 'session is blocked', 'status': False}
        if req.status_code == 200:
            return {'error': False, 'status': True}

    async def _get_auth_code(self):

        """
        Получает код авторизации для пользователя.
        :return: None
        """

        try:
            link, params = self.data_auth['first_link'], self.data_auth['first_params']
            params['access_token'] = self.access_token
            req = Request()
            data = await req.fetch(url=link, params=params)

            if isinstance(data, str):
                data = json.loads(data)

            if req.status_code == 200:
                if 'code' in data:
                    self.auth_code = data['code']
            else:
                self.status_try_auth = req.status_code
                if 'error_description' in data:
                    self.error = data['error_description']
        except Exception as e:
            print(f"Error get auth code, errors: {str(e)}")
            self.error = e

    async def _get_code_for_auth(self):
        """
        Получает код авторизации для получения индификатора сессии
        :return: None
        """

        try:
            req = Request()
            link, params = self.data_auth['four_link'], self.data_auth['four_params']
            params['access_token'] = self.access_token
            data = await req.fetch(link, params=params)
            if isinstance(data, str):
                data = json.loads(data)
            if "code" in data:
                self.code_for_auth = data['code']
        except Exception as e:
            self.error = e
            print(f"Error get code for auth: {str(e)}")

    async def _get_personal_id(self):

        """
        Получает информацию о пользователе, включая игровые персонажи.
        :return: None
        """

        try:
            req = Request()
            link, headers = self.data_auth['second_link'], self.data_auth['second_headers']
            headers['Authorization'] = headers['Authorization'].format(access_token=self.access_token)
            data = await req.fetch(link, headers=headers)
            if req.status_code == 200:
                if 'pid' in data:
                    if 'pidId' in data['pid']:
                        self.personal_id = data['pid']['pidId']
        except Exception as e:
            print(f"Error get personal id, error: {str(e)}")
            self.error = e

    async def _get_person(self):

        """
        Получает информацию о пользователе.

        Этот метод использует личный идентификатор и код авторизации для получения
        информации о пользователе, включая его игровые персонажи. Если у пользователя
        несколько персонажей, выбирается первый с пустым состоянием.
        :return: None
        """

        try:
            req = Request()
            link, headers, params = (
                self.data_auth['third_link'], self.data_auth['third_headers'], self.data_auth['third_params']
            )
            headers['Easw-Session-Data-Nucleus-Id'] = headers['Easw-Session-Data-Nucleus-Id'].format(
                personal_id=self.personal_id
            )
            headers['Nucleus-Access-Code'] = headers['Nucleus-Access-Code'].format(auth_code=self.auth_code)
            data = await req.fetch(url=link, headers=headers, params=params)
            if req.status_code == 200:
                if 'userAccountInfo' in data:
                    if 'personas' in data['userAccountInfo']:
                        if len(data['userAccountInfo']['personas']) > 1:
                            for person in data['userAccountInfo']['personas']:
                                if 'userState' in person:
                                    if person['userState'] is None:
                                        self.persona_id = person['personaId']
                        else:
                            self.persona_id = data['userAccountInfo']['personas'][0]['personaId']
        except Exception as e:
            print(f"Error get person, error: {str(e)}")
            self.error = e

    async def _get_session_id(self):

        """
        Получает идентификатор сессии.
        :return: str
        """

        try:
            req = Request()
            link, headers, params = (
                self.data_auth['post_link'], self.data_auth['post_headers'], self.data_auth['post_params']
            )
            params['gameSku'], params['nucleusPersonaId'] = self.header_pl, self.persona_id
            params['identification']['authCode'] = self.code_for_auth
            data = await req.post_data(link, headers=headers, data=params)

            if isinstance(data, str):
                data = json.loads(data)

            if req.status_code == 200:
                if 'sid' in data:
                    return data['sid']
            return False
        except Exception as e:
            self.error = e
            print(e)
            return False