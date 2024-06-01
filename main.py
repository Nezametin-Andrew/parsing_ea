import json
import random
import sys
import time
from scrap.request import Request
import asyncio
from scrap.EA import EaComAuth, EaComApi
from scrap.config import proxy_pc, auth_proxy_pc, main_host, tg_url, admins, server_pc


class Parsing:

    def __init__(self, account: dict):
        self.account = account
        self.platform = 'pc' if account['platform'] == '1' else 'console'
        self.start_point, self.amount_data = 50, 50
        self.processed_ids, self.players, self.sent_data = set(), {}, []
        self.min_time, self.max_time = 3520, 3900
        self.get_players()
        self.error = None

    async def main_loop(self):
        while True:
            ea = EaComApi(**self.account)
            data, status_code = await ea.get_data(amount_data=self.amount_data, start_point=self.start_point)

            if status_code == 200:
                await self.parsing_json(data)
                time.sleep(random.randint(7, 9))
            self.start_point += self.amount_data

    async def parsing_json(self, data):
        if isinstance(data, str):
            data = json.loads(data)
        if 'auctionInfo' in data:
            for item in data['auctionInfo']:
                asset_id, resource_id, expires, rare_flag = (
                    item['itemData']['assetId'], item['itemData']['resourceId'], item['expires'],
                    item['itemData'].get('rareflag', '')
                )
                if resource_id not in self.processed_ids and self.min_time < int(expires) < self.max_time:
                    self.sent_data.append(
                        {
                            'player_id': asset_id,
                            'player_name': self.players[asset_id],
                            'price': item['buyNowPrice'],
                            'expires': expires,
                            'rating': item['itemData']['rating'],
                            'platform': self.platform,
                            'resource_id': resource_id,
                            'rare_flag': rare_flag
                        })
                    self.processed_ids.add(resource_id)

                self.sent_data = self.split_list(self.sent_data)
                await self.check_actual_price()
                self.sent_data = []

    async def check_actual_price(self):
        try:
            req = Request()
            tasks = [req.post_data(server_pc, data=data) for data in self.sent_data]
            responses = await asyncio.gather(*tasks)
            [print(response) for response in responses]
        except Exception as e:
            print(e)
            self.error = e

    def split_list(self, input_list) -> list:
        if not isinstance(input_list, list):
            raise ValueError("Input must be a list")

        if not input_list:
            return []
        result = []

        for i in range(0, len(input_list), 5):
            result.append(input_list[i:i + 5])

        return result

    def get_players(self):
        try:
            with open('players.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
            for key, val in data.items():
                for player in val:
                    self.players[player['id']] = str(player['f']) + " " + str(player['l'])

        except FileNotFoundError:
            print("Error: 'ea.json' file not found.")
            self.error = "FileNotFoundError"
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from 'ea.json'.")
            self.error = "JSONDecodeError"
        except Exception as e:
            print(f"Error loading EA data. Details: {str(e)}")
            self.error = e


class MainProcess:

    SETTINGS = {
        'pc': {
            'host_recv': '',
            'proxy': proxy_pc,
            'proxy_auth': auth_proxy_pc
        },
        'console': {
            'host_recv': '',
            'proxy': None,
            'proxy_auth': None
        }
    }

    def __init__(self, platform='console'):
        self.platform = platform
        self.key_platform = '2' if platform == 'console' else '1'
        self.settings = self.SETTINGS[platform]
        self.host = main_host
        self.working_accounts = []
        self.update_accounts = []
        self.accounts = []

    async def get_accounts(self):
        self.accounts = await Request().fetch(url=self.host, params={'platform': self.key_platform, 'blocked': False})

    async def notification_admin(self, err, email):
        req = Request()
        try:
            for ids in admins:
                response = await req.post_data(
                    tg_url,
                    data={'chat_id': ids, 'text': f'Error check accounts {email}\nError: {err}'}
                )
        except Exception as e:
            print(f'Sent notification error, error: {e}')

    async def update_data_acc(self):
        for acc in self.update_accounts:
            req = Request()
            url = f'{self.host}{acc["id"]}/'
            data = await req.update_data(url=url, data=acc)

    async def get_working_account(self):

        """
        Пробуем получить рабочий аккаунт
        :return:
        """

        for acc in self.accounts:
            ea = EaComAuth(**acc)
            check = await ea.check_session_acc()

            if 'error' in check and check['error']:
                await ea.try_auth()

                if ea.error is not None:
                    await self.notification_admin(err=ea.error, email=acc['email'])
                    acc['blocked'] = True
                    self.update_accounts.append(acc)
                    continue
                elif ea.updated_sesid is not None:
                    acc['auth'] = ea.updated_sesid
                    self.update_accounts.append(acc)
            self.working_accounts.append(acc)
            break

    async def start(self):
        print('Старт программы')
        print('Получаю аккунты...')
        await self.get_accounts()
        if self.accounts:
            print('Проверка аккаунтов...')
            await self.get_working_account()
        else:
            print('Не удалось получить рабочий аккаунт.')

        if self.update_accounts:
            print('Обновление данных аккаунтов...')
            await self.update_data_acc()

        if self.working_accounts:
            print('Запускаю парсинг...')
            start = Parsing(self.working_accounts[0])
            await start.main_loop()
        print('Завершение программы через 90 сек.')
        time.sleep(90)
        sys.exit(1)


async def main(platform):
    scrap = MainProcess(platform)
    await scrap.start()


if __name__ == '__main__':
    asyncio.run(main('pc'))


