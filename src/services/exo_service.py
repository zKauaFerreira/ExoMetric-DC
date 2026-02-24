import aiohttp
import os

class ExoMetricService:
    def __init__(self):
        self.api_url = os.getenv("API_URL")
        self.api_token = os.getenv("API_TOKEN")

    async def get_stats(self):
        async with aiohttp.ClientSession() as session:
            try:
                params = {"token": self.api_token}
                async with session.get(self.api_url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
        return None

    async def get_players(self):
        async with aiohttp.ClientSession() as session:
            try:
                params = {"token": self.api_token}
                async with session.get(f"{self.api_url}/players", params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
        return None

exo_service = ExoMetricService()
