import json
import random
import sys
import time

from scrap.request import Request
import asyncio
from scrap.EA import EaComAuth, EaComApi
from scrap.config import main_host, tg_url, admins, server, logger, setting_parser, platform


class Parsing:

    CODE_SLEEP = [429, 512, 521, 426,]
    CODE_AUTH = [401]

    def __init__(self, account: dict):
        self.account = account
        self.platform = 'pc' if account['platform'] == '1' else 'console'
        self.platform_id = account['platform']
        self.page, self.amount_data = 1, 30
        self.getting_data, self.try_get_data, self.border_reload = 0, 0, 15
        self.processed_ids, self.players, self.sent_data = set(), {}, []
        self.min_time, self.max_time = 3420, 3900
        self.get_players()
        self.error = None
        self.flag = None

    async def main_loop(self):
        await self.set_settings_parse()
        while True:

            ea = EaComApi(**self.account)
            logger.info(
                f'Попытка получить данные с EA, количество запрашеваеммых данных: {self.amount_data},'
                f' страница: {self.page}'
            )
            data, status_code = await ea.get_data(amount_data=self.amount_data, start_point=self.page * self.amount_data)
            logger.info(f'Статус ответа от ЕА: {status_code}')
            if status_code == 200:
                await self.parsing_json(data)
                time.sleep(random.randint(7, 9))

            if status_code in self.CODE_SLEEP:

                if self.error in [True]:
                    return {'status': 'error', 'error': 'Authentication Required for account'}

                time.sleep(120)
                await self.set_settings_parse()
                self.error = True
                continue

            if status_code in self.CODE_AUTH:
                return {'status': 'error', 'error': 'Authentication Required for account'}

            await self.control_parsing()

    async def control_parsing(self):

        if self.getting_data and self.page != self.border_reload and self.try_get_data != 3:
            self.page += 1
            self.getting_data = 0
            self.try_get_data = 0
        elif self.page == self.border_reload or self.try_get_data == 3 and self.flag is not None:
            self.page = 1
            self.getting_data = 0
            await self.set_settings_parse()
            if self.try_get_data == 3:
                self.flag = True
        else:
            if self.page > 5:
                self.page -= 5
            else:
                self.page = 1
            self.flag = None

    async def parsing_json(self, data):
        if isinstance(data, str):
            data = json.loads(data)

        if 'auctionInfo' in data:
            logger.info(f'Количество полученных данных от EA: {len(data["auctionInfo"])}')
            self.getting_data = len(data['auctionInfo'])
            for item in data['auctionInfo']:
                asset_id, resource_id, expires, rare_flag = (
                    item['itemData']['assetId'], item['itemData']['resourceId'], item['expires'],
                    item['itemData'].get('rareflag', '')
                )
                if resource_id not in self.processed_ids and self.min_time < int(expires) < self.max_time:
                    if asset_id not in self.players:
                        continue
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
            tasks = [req.post_data(server, data=data) for data in self.sent_data]
            responses = await asyncio.gather(*tasks)
            [logger.info(response) for response in responses]
        except Exception as e:
            logger.error(e)
            self.error = e

    async def set_settings_parse(self):
        try:
            req = Request()
            data = await req.fetch(setting_parser, params={'platform': self.platform_id})
            settings = [d for d in data if data['platform'] == self.platform_id][0]
            self.border_reload, self.amount_data = settings['border_reload'], settings['amount_data']
        except Exception as e:
            logger.error(f"Error getting data for parse, error: {e}")

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
            logger.error("Error: 'ea.json' file not found.")
            self.error = "FileNotFoundError"
        except json.JSONDecodeError:
            logger.error("Error: Failed to decode JSON from 'ea.json'.")
            self.error = "JSONDecodeError"
        except Exception as e:
            logger.error(f"Error loading EA data. Details: {str(e)}")
            self.error = e


class MainProcess:

    def __init__(self, platform='console'):
        self.platform = platform
        self.key_platform = '2' if platform == 'console' else '1'
        self.host = main_host
        self.working_accounts = []
        self.update_accounts = []
        self.accounts = []
        self.reload = False

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
            logger.error(f'Sent notification error, error: {e}')

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
        logger.info('Старт программы')
        logger.info('Получаю аккунты...')
        await self.get_accounts()
        if self.accounts:
            logger.info('Проверка аккаунтов...')
            await self.get_working_account()
        else:
            logger.info('Не удалось получить рабочий аккаунт.')

        if self.update_accounts:
            logger.info('Обновление данных аккаунтов...')
            await self.update_data_acc()

        if self.working_accounts:
            logger.info('Запускаю парсинг...')
            start = Parsing(self.working_accounts[0])
            response = await start.main_loop()
            if 'error' in response and not self.reload:
                await self.start()
                self.reload = True
            else:
                await self.notification_admin(err=response['error'], email=self.accounts[0]['email'])
        logger.info('Завершение программы через 90 сек.')
        time.sleep(90)
        sys.exit(1)


async def main(platform):
    scrap = MainProcess(platform)
    await scrap.start()


if __name__ == '__main__':
    asyncio.run(main(platform))


