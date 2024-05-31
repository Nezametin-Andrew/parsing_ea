import httpx


class Request:

    def __init__(self):
        self.status_code = None
        self.headers = None

    async def fetch(
            self, url: str, headers: dict = {}, params: dict = {},
            proxy: str = None, proxy_auth: tuple = None) -> object:

        async with httpx.AsyncClient(proxies=proxy, verify=False, auth=proxy_auth) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                self.status_code = response.status_code
                self.headers = response.headers
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    try:
                        resp = response.json()
                        return resp
                    except httpx.HTTPStatusError as e:
                        print(f"HTTP Status error: {e}")
                    except Exception as e:
                        print(f"Error parsing JSON response: {e}")
                        return None
                else:
                    try:
                        text = response.text
                        return text
                    except Exception as e:
                        print(f"Error reading text response: {e}")
                        return None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None

    async def post_data(self, url: str, headers: dict = {}, data: dict = {}, proxy: str = None, proxy_auth: tuple = None):
        async with httpx.AsyncClient(proxies=proxy, verify=False, auth=proxy_auth) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                self.status_code = response.status_code
                self.headers = response.headers
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    try:
                        resp = response.json()
                        return resp
                    except httpx.HTTPStatusError as e:
                        print(f"HTTP Status error: {e}")
                    except Exception as e:
                        print(f"Error parsing JSON response: {e}")
                        return None
                else:
                    try:
                        text = response.text
                        return text
                    except Exception as e:
                        print(f"Error reading text response: {e}")
                        return None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None
