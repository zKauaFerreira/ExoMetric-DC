import discord
from discord import Embed, ButtonStyle, ui, File
from datetime import datetime, timedelta, timezone
import os
import time

# Fuso Horário Brasil (GMT-3)
TZ_OFFSET = timezone(timedelta(hours=-3))
from src.utils.inventory_renderer import renderer

# Caminhos locais para os ícones
# Baseado na pasta atual: raiz/src/utils/ui.py
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

def format_bytes(size):
    if not size: return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def create_player_dossier_embed(p, inv_file_name_placeholder=None):
    embed = Embed(title=f"🛡️ Dossiê: {p['name']}", color=0x3498DB)
    embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{p.get('uuid')}/64")
    
    if inv_file_name_placeholder:
        embed.set_image(url=f"attachment://{inv_file_name_placeholder}")

    # Cálculo do Timestamp UTC absoluto (time.time() é o mais seguro)
    login_ts = int(time.time() - p.get('online_seconds', 0))

    # Status Vital
    health = p.get('health', 0)
    food = p.get('food', 0)
    sat = p.get('saturation', 0)
    
    embed.add_field(
        name="❤️ Vitalidade", 
        value=f"```ansi\n\u001b[1;31mVida:\u001b[0m\n{health:.1f}/20\n\u001b[1;33mFome:\u001b[0m\n{food}/20\n\u001b[1;36mSat:\u001b[0m\n{sat:.1f}\n```", 
        inline=True
    )

    # Progressão e Sessão
    lvl = p.get('level', 0)
    gm = p.get('gamemode', 'SURVIVAL').capitalize()
    ping = p.get('ping', 0)
    
    embed.add_field(
        name="📊 Atributos", 
        value=f"```ansi\n\u001b[1;35mNível:\u001b[0m\n{lvl}\n\u001b[1;32mModo:\u001b[0m\n{gm}\n\u001b[1;34mPing:\u001b[0m\n{ping}ms\n```", 
        inline=True
    )

    # Localização Detalhada
    dim = p.get('dimension', '???').split(':')[-1].replace('_', ' ').capitalize()
    coords = f"`X:{int(p.get('x',0))} Y:{int(p.get('y',0))} Z:{int(p.get('z',0))}`"
    
    embed.add_field(
        name="📍 Localização & Sessão", 
        value=f"🌍 **Dimensão:** `{dim}`\n🎯 **Coords:** {coords}\n⏱️ **Logado:** <t:{login_ts}:R>", 
        inline=False
    )
    
    return embed

def create_status_embed(data):
    files = []
    if not data:
        embed = Embed(title="🔴 ExoMetric - Offline", color=0xFF4B4B)
        embed.description = "⚠️ O servidor Minecraft não está respondendo."
        return embed, files

    net_in = format_bytes(data.get('network_rx_bytes', 0))
    net_out = format_bytes(data.get('network_tx_bytes', 0))
    cpu = data.get('cpu_percent', 0)
    ram_used = format_bytes(data.get('memory_bytes', 0))
    
    # Cálculos de Tempo (UTC absoluto via time.time)
    now_ts = time.time()
    launch_timestamp = int(now_ts - data.get('uptime_seconds', 0))
    world_day = data.get('world_day', 0)

    embed = Embed(
        title="⏳ Painel de Status",
        description=f"\n🖥️ **Host:**\n```\n{os.getenv('SERVER_HOST', 'SEU_IP_AQUI')}\n```",
        color=0x57F287
    )

    embed.add_field(name="⚙️ RECURSOS", value=f"```ansi\n\u001b[1;33mCPU:\u001b[0m {cpu}%\n\u001b[1;34mRAM:\u001b[0m {ram_used}\n```", inline=True)
    embed.add_field(name="📡 CONEXÃO", value=f"```ansi\n\u001b[1;32mIn:\u001b[0m {net_in}/s\n\u001b[1;31mOut:\u001b[0m {net_out}/s\n```", inline=True)
    embed.add_field(name="👥 JOGADORES", value=f"```ansi\n\u001b[1;36mOnline:\u001b[0m {data.get('players_online', 0)}\n```", inline=False)
    
    # Formatação do Tempo Online para o Bloco ANSI
    uptime_sec = int(now_ts - launch_timestamp)
    if uptime_sec < 3600:
        uptime_fmt = f"{uptime_sec//60}m"
    elif uptime_sec < 86400:
        uptime_fmt = f"{uptime_sec//3600}h {(uptime_sec%3600)//60}m"
    else:
        uptime_fmt = f"{uptime_sec//86400}d {(uptime_sec%86400)//3600}h"

    embed.add_field(name="📅 MUNDO", value=f"```ansi\n\u001b[1;35mDIA:\u001b[0m {world_day}\n```", inline=True)
    embed.add_field(name="⏱️ SERVIDOR", value=f"```ansi\n\u001b[1;32mON:\u001b[0m {uptime_fmt}\n```", inline=True)
    
    updated_at = datetime.now(TZ_OFFSET).strftime("%H:%M:%S")
    embed.set_footer(text=f"🟢 Último Update: {updated_at}")
    return embed, files

def create_world_embed(data):
    time = data.get('world_time', 0)
    hours = (time // 1000 + 6) % 24
    minutes = (time % 1000) * 60 // 1000
    
    embed = Embed(title="🌐 Detalhes do Mundo Minecraft", color=0x9B59B6)
    
    # Seed em destaque total
    seed = data.get('world_seed', 'N/A')
    url = f"https://www.chunkbase.com/apps/biome-finder#seed={seed}&platform=java_1_21_5&dimension=overworld"
    embed.add_field(name="🌍 Seed", value=f"[🗺️ Ver no Chunkbase]({url})\n```\n{seed}\n```", inline=False)
    
    # Outros dados em blocos simples
    embed.add_field(name="📅 Dia", value=f"`{data.get('world_day', 0)}`", inline=True)
    embed.add_field(name="⏰ Hora Local", value=f"`{hours:02d}:{minutes:02d}`", inline=True)
    embed.add_field(name="📦 Chunks", value=f"`{data.get('loaded_chunks', 0)} carregados`", inline=True)
    
    diff = str(data.get('difficulty', 'Normal')).upper()
    embed.add_field(name="⚔️ Dificuldade", value=f"`{diff}`", inline=True)
    
    clima = "Chovendo" if data.get('is_raining') else "Céu Limpo"
    embed.add_field(name="🌧️ Clima", value=f"`{clima}`", inline=True)
    
    # Informação extra: Armazenamento
    disco = format_bytes(data.get('disk_bytes', 0))
    embed.add_field(name="💽 Armazenamento", value=f"`{disco}`", inline=True)
    
    return embed

def create_performance_embed(data):
    ram_pct = (data.get('heap_used_bytes', 0) / data.get('heap_max_bytes', 1)) * 100
    bar = "🟩" * int(ram_pct/10) + "⬛" * (10 - int(ram_pct/10))
    embed = Embed(title="⚡ Métricas de Performance", color=0xE67E22)
    embed.add_field(name="🚀 TPS", value=f"`{data.get('tps', 0):.2f}`", inline=True)
    embed.add_field(name="🕒 MSPT", value=f"`{data.get('mspt', 0):.2f}ms`", inline=True)
    embed.add_field(name="💾 Java Heap", value=f"{bar} ({ram_pct:.1f}%)\n`{format_bytes(data.get('heap_used_bytes', 0))} / {format_bytes(data.get('heap_max_bytes', 0))}`", inline=False)
    return embed

# --- Views de Resposta Efêmera ---

class WorldRefreshView(ui.View):
    def __init__(self, service):
        super().__init__(timeout=120)
        self.service = service

    @ui.button(label="Atualizar", emoji="🔄", style=ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        data = await self.service.get_stats()
        await interaction.edit_original_response(embed=create_world_embed(data))

class PerfRefreshView(ui.View):
    def __init__(self, service):
        super().__init__(timeout=120)
        self.service = service

    @ui.button(label="Atualizar", emoji="🔄", style=ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        data = await self.service.get_stats()
        await interaction.edit_original_response(embed=create_performance_embed(data))

class PlayerRefreshView(ui.View):
    def __init__(self, service, uuid):
        super().__init__(timeout=120)
        self.service = service
        self.uuid = uuid

    @ui.button(label="Atualizar Inventário", emoji="🔄", style=ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        data = await self.service.get_players()
        p = next((x for x in data['players'] if x['uuid'] == self.uuid), None)
        if not p:
            await interaction.followup.send("❌ Jogador saiu do servidor.", ephemeral=True)
            return
        
        inv_file = await renderer.render(p)
        p_embed = create_player_dossier_embed(p, inv_file.filename)
        await interaction.edit_original_response(embed=p_embed, attachments=[inv_file], view=self)

# --- View Principal ---

class StatusView(ui.View):
    def __init__(self, bot, service, is_online=True):
        super().__init__(timeout=None)
        self.bot = bot
        self.service = service
        
        if not is_online:
            for item in self.children[:]:
                if getattr(item, 'custom_id', '') != "persistent:refresh":
                    self.remove_item(item)

    @ui.button(label="Atualizar", emoji="🔄", style=ButtonStyle.primary, custom_id="persistent:refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        data = await self.service.get_stats()
        embed, files = create_status_embed(data)
        # Atualiza a view para esconder os botões se cair ou voltar
        new_view = StatusView(self.bot, self.service, is_online=(data is not None))
        await interaction.edit_original_response(embed=embed, attachments=files, view=new_view)

    @ui.button(emoji="🌐", style=ButtonStyle.secondary, custom_id="persistent:world")
    async def world_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = await self.service.get_stats()
        await interaction.followup.send(embed=create_world_embed(data), view=WorldRefreshView(self.service), ephemeral=True)

    @ui.button(emoji="⚡", style=ButtonStyle.secondary, custom_id="persistent:perf")
    async def perf_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = await self.service.get_stats()
        await interaction.followup.send(embed=create_performance_embed(data), view=PerfRefreshView(self.service), ephemeral=True)

    @ui.button(emoji="👥", style=ButtonStyle.secondary, custom_id="persistent:players")
    async def players_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = await self.service.get_players()
        if not data or not data.get('players'):
            await interaction.followup.send("🚫 Nenhum jogador online no momento.", ephemeral=True)
            return

        select = ui.Select(
            placeholder="Selecione um jogador...",
            options=[discord.SelectOption(label=p['name'], description=f"Ping: {p['ping']}ms", value=p['uuid'], emoji="👤") for p in data['players'][:25]]
        )

        async def select_callback(inter: discord.Interaction):
            try:
                await inter.response.defer()
                uuid = select.values[0]
                p = next((x for x in data['players'] if x['uuid'] == uuid), None)
                if not p:
                    await inter.followup.send("❌ Jogador não encontrado.", ephemeral=True)
                    return

                inv_file = await renderer.render(p)
                p_embed = create_player_dossier_embed(p, inv_file.filename)
                
                await inter.edit_original_response(content="", embed=p_embed, attachments=[inv_file], view=PlayerRefreshView(self.service, uuid))
            except Exception as e:
                print(f"❌ Erro: {e}")
                await inter.followup.send(f"❌ Erro ao gerar inventário.", ephemeral=True)

        select.callback = select_callback
        inspect_view = ui.View(timeout=60)
        inspect_view.add_item(select)
        await interaction.followup.send("🔍 **Inspetor de Jogadores**", view=inspect_view, ephemeral=True)
