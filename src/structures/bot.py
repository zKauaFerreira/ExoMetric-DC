import discord
from discord.ext import commands
import asyncio
from src.utils.persistence import load_data, save_data

class ExoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = False
        intents.message_content = False
        
        # Prefix apenas como fallback, o foco são Comandos Slash
        super().__init__(command_prefix="!", intents=intents)
        
        data = load_data()
        self.status_messages = data.get('status_messages', {})

    def save_status_message(self, guild_id, channel_id, message_id):
        self.status_messages[str(guild_id)] = {
            "channel_id": channel_id,
            "message_id": message_id
        }
        data = load_data()
        data['status_messages'] = self.status_messages
        save_data(data)

    async def setup_hook(self):
        # Imports locais para evitar circularidade
        from src.utils.ui import StatusView
        from src.services.exo_service import exo_service
        from src.utils.inventory_renderer import renderer
        
        # Inicializar Assets proativamente
        asyncio.create_task(renderer.initialize())
        await self.load_extension("src.cogs.status_cog")
        
        # Registrar views persistentes para os botões funcionarem sempre
        self.add_view(StatusView(self, exo_service))
        
        # Sincronização manual via comando é melhor que no boot
        print("✅ Bot configurado e pronto para ligar.")

    async def on_ready(self):
        print(f"🤖 Bot online: {self.user}")
        print("💡 Se os comandos slash não aparecerem, use um comando de sync ou aguarde a propagação.")
