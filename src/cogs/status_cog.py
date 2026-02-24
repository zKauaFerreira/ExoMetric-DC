import discord
from discord.ext import commands, tasks
from discord import app_commands
from src.services.exo_service import exo_service
from src.utils.ui import create_status_embed, StatusView
import os
import time

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.online_players = {} # Cache de {uuid: name}
        self.first_run = True
        self.server_online = None # Status anterior do servidor
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(seconds=15)
    async def update_loop(self):
        data = await exo_service.get_stats()
        players_data = await exo_service.get_players()
        
        is_online = (data is not None)
        embed, files = create_status_embed(data)
        view = StatusView(self.bot, exo_service, is_online=is_online)

        # Lógica de Entrada/Saída (calculada uma vez por ciclo)
        current_players = {}
        if players_data and 'players' in players_data:
            current_players = {p['uuid']: p['name'] for p in players_data['players']}
        
        new_joins = []
        new_leaves = []
        
        if not self.first_run:
            # 📥 QUEM ENTROU
            join_uuids = set(current_players.keys()) - set(self.online_players.keys())
            for uuid in join_uuids:
                new_joins.append({'uuid': uuid, 'name': current_players[uuid]})
            
            # 📤 QUEM SAIU
            leave_uuids = set(self.online_players.keys()) - set(current_players.keys())
            for uuid in leave_uuids:
                new_leaves.append({'uuid': uuid, 'name': self.online_players[uuid]})

        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            msg_info = self.bot.status_messages.get(guild_id)

            if not msg_info:
                # Auto-descoberta se não houver no DB
                channel = discord.utils.get(guild.text_channels, name='📊-status-servidor')
                if channel:
                    try:
                        async for message in channel.history(limit=20):
                            if message.author.id == self.bot.user.id and message.embeds:
                                self.bot.save_status_message(guild.id, channel.id, message.id)
                                msg_info = self.bot.status_messages.get(guild_id)
                                break
                    except: pass

            if not msg_info: continue

            try:
                channel = self.bot.get_channel(msg_info['channel_id']) or await self.bot.fetch_channel(msg_info['channel_id'])
                
                # Atualiza o Embed Principal
                try:
                    message = await channel.fetch_message(msg_info['message_id'])
                    await message.edit(embed=embed, attachments=files, view=view)
                except: pass # Mensagem original sumiu

                # --- Lógica de Notificações ---
                role_id = os.getenv("MENTION_ROLE_ID", "")
                mention = f"<@&{role_id}>" if role_id else ""
                
                notify_start = os.getenv("NOTIFY_SERVER_START", "on").lower() == "on"
                notify_stop = os.getenv("NOTIFY_SERVER_STOP", "on").lower() == "on"
                notify_login = os.getenv("NOTIFY_LOGIN", "on").lower() == "on"
                notify_logout = os.getenv("NOTIFY_LOGOUT", "on").lower() == "on"

                # 🟢 SERVIDOR LIGOU
                if self.server_online is False and is_online and notify_start:
                    online_embed = discord.Embed(title="🚀 Servidor Iniciado!", description="O servidor foi **ligado com sucesso**!", color=0x57F287, timestamp=discord.utils.utcnow())
                    if data:
                        launch_ts = int(time.time() - data.get('uptime_seconds', 0))
                        online_embed.add_field(name="⏱️ Online desde", value=f"<t:{launch_ts}:R>")
                    await channel.send(content=mention, embed=online_embed, delete_after=60)

                # 🔴 SERVIDOR DESLIGOU
                elif self.server_online is True and not is_online and notify_stop:
                    offline_embed = discord.Embed(title="🛑 Servidor Desconectado!", description="O servidor acaba de ficar **OFFLINE**.", color=0xFF4B4B, timestamp=discord.utils.utcnow())
                    await channel.send(content=mention, embed=offline_embed, delete_after=60)

                # 📥 ENTRADAS
                if notify_login:
                    for p in new_joins:
                        join_embed = discord.Embed(title="📥 Novo Jogador Online!", description=f"O jogador **{p['name']}** entrou no mundo!", color=0x2ECC71, timestamp=discord.utils.utcnow())
                        join_embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{p['uuid']}/64")
                        join_embed.add_field(name="⏱️ Hora da Entrada", value=f"<t:{int(time.time())}:R>")
                        await channel.send(content=mention, embed=join_embed, delete_after=60)

                # 📤 SAÍDAS
                if notify_logout:
                    for p in new_leaves:
                        leave_embed = discord.Embed(title="📤 Jogador Desconectado!", description=f"O jogador **{p['name']}** saiu do mundo!", color=0xE67E22, timestamp=discord.utils.utcnow())
                        leave_embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{p['uuid']}/64")
                        leave_embed.add_field(name="⏱️ Hora da Saída", value=f"<t:{int(time.time())}:R>")
                        await channel.send(content=mention, embed=leave_embed, delete_after=60)

            except: pass

        # Atualiza estados para o próximo loop
        self.online_players = current_players
        self.server_online = is_online
        self.first_run = False

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="setup", description="Configura o painel de status do ExoMetric")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild_id)
        msg_info = self.bot.status_messages.get(guild_id)
        channel = None

        # 1. Prioridade: Tentar recuperar o canal pelo ID salvo (mesmo se mudou o nome)
        if msg_info:
            channel = self.bot.get_channel(msg_info['channel_id'])
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(msg_info['channel_id'])
                except:
                    channel = None

        # 2. Se não achou por ID, tenta pelo nome padrão
        if not channel:
            channel = discord.utils.get(interaction.guild.text_channels, name='📊-status-servidor')
        
        # 3. Se ainda não achou, cria um novo
        if not channel:
            channel = await interaction.guild.create_text_channel(
                '📊-status-servidor',
                overwrites={
                    interaction.guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
                    interaction.guild.me: discord.PermissionOverwrite(send_messages=True, view_channel=True)
                }
            )

        data = await exo_service.get_stats()
        embed, files = create_status_embed(data)
        view = StatusView(self.bot, exo_service, is_online=(data is not None))

        message = None
        if msg_info:
            try:
                target_chan = self.bot.get_channel(msg_info['channel_id']) or await self.bot.fetch_channel(msg_info['channel_id'])
                message = await target_chan.fetch_message(msg_info['message_id'])
                await message.edit(embed=embed, attachments=files, view=view)
            except:
                message = None

        if not message:
            message = await channel.send(embed=embed, file=files[0] if len(files) == 1 else None, files=files if len(files) > 1 else None, view=view)
            self.bot.save_status_message(interaction.guild_id, channel.id, message.id)

        await interaction.followup.send(f"✅ Monitoramento configurado em {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
