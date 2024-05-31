from scrap.request import Request
import asyncio
from scrap.EA import EaComAuth
from scrap.config import proxy_pc, auth_proxy_pc, main_host


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

    async def get_accounts(self):
        data = await Request().fetch(url=self.host, params={'platform': self.key_platform})
        print(f"Received data: {data}")
        return data

    async def start(self):
        data = await self.get_accounts()
        ea = EaComAuth(**data[0])
        check = await ea.check_auth_acc()

        if 'error' in check and check['error']:
            await ea.try_auth()

            if ea.error is not None:
                print(ea.error)
            else:
                print(ea.updated_sesid)


async def main(platform):
    scrap = Scrap(platform)
    await scrap.start()


if __name__ == '__main__':
    asyncio.run(main('pc'))


