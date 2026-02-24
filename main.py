import asyncio
import os
from dotenv import load_dotenv
from src.structures.bot import ExoBot

# Carregar variáveis de ambiente
load_dotenv()

async def main():
    bot = ExoBot()
    
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "SEU_TOKEN_AQUI":
        print("❌ ERRO: DISCORD_TOKEN não configurado no arquivo .env!")
        return

    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot desligado.")
