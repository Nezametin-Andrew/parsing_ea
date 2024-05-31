from scrap.request import Request
import asyncio
from scrap.EA import EaComAuth
from scrap.config import proxy_pc, auth_proxy_pc, main_host, tg_url, admins


class Scrap:

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
        self.bocked_accounts = []
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
                print(response)
        except Exception as e:
            print(f'Sent notification error, error: {e}')

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


    async def start(self):
        await self.get_accounts()
        if self.accounts:
            await self.get_working_account()

        # ea = EaComAuth()
        # check = await ea.check_auth_acc()

        # if 'error' in check and check['error']:
        #     await ea.try_auth()
        #
        #     if ea.error is not None:
        #         print(ea.error)
        #     else:
        #         print(ea.updated_sesid)


async def main(platform):
    scrap = Scrap(platform)
    await scrap.start()


if __name__ == '__main__':
    asyncio.run(main('pc'))


