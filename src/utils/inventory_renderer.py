import discord
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
import asyncio
from src.utils.jemsire_finder import JemsireIconFinder

# Baseado na pasta atual: raiz/src/utils/inventory_renderer.py
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
# Nova pasta para ícones de interface para não ser confundida com cache de itens
UI_DIR = os.path.join(ASSETS_DIR, "ui")
os.makedirs(UI_DIR, exist_ok=True)

SCALE = 4
ORIGINAL_WIDTH = 176
ORIGINAL_HEIGHT = 166
SLOT_STEP = 18

CHAR_BOX_X = 26
CHAR_BOX_Y = 8
CHAR_BOX_W = 51
CHAR_BOX_H = 72

class InventoryRenderer:
    def __init__(self):
        self.session = None
        self.bg_path = os.path.join(ASSETS_DIR, "inventory_bg.png")
        self.jemsire = JemsireIconFinder(ASSETS_DIR)
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            await self.jemsire.initialize()
            await self._ensure_ui_icons()
            self._initialized = True

    async def _ensure_ui_icons(self):
        """Garante que os ícones de slots (silhuetas) existam."""
        base_url = "https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.17.1/items"
        icon_urls = {
            "helmet": f"{base_url}/empty_armor_slot_helmet.png",
            "chestplate": f"{base_url}/empty_armor_slot_chestplate.png",
            "leggings": f"{base_url}/empty_armor_slot_leggings.png",
            "boots": f"{base_url}/empty_armor_slot_boots.png",
            "shield": f"{base_url}/empty_armor_slot_shield.png"
        }
        
        session = await self.get_session()
        for name, url in icon_urls.items():
            path = os.path.join(UI_DIR, f"empty_{name}.png")
            # Se não existe ou é o placeholder de 85 bytes que eu criei antes
            if not os.path.exists(path) or os.path.getsize(path) < 100:
                print(f"📥 [Renderer] Baixando silhueta: {name}")
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(path, "wb") as f:
                                f.write(content)
                except Exception as e:
                    print(f"⚠️ [Renderer] Erro ao baixar silhueta {name}: {e}")
                    # Fallback final: transparente se falhar o download
                    if not os.path.exists(path):
                        Image.new("RGBA", (16, 16), (0,0,0,0)).save(path)

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_item_icon(self, item_id):
        await self.initialize()
        img = await self.jemsire.get_icon(item_id)
        if img:
            return img

        clean_name = item_id.split(":")[-1].lower()
        if clean_name != "air":
            print(f"🏮 [Renderer] AVISO: {clean_name} não encontrado localmente.")
        return None

    async def fetch_empty_icon(self, slot_type):
        path = os.path.join(UI_DIR, f"empty_{slot_type}.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    async def fetch_player_body(self, uuid):
        url = f"https://mc-heads.net/body/{uuid}/400" 
        session = await self.get_session()
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        except: return None

    async def render(self, player_data):
        print(f"🆕 [Renderer] Renderizando Dossiê: {player_data.get('name')}")
        await self.initialize()

        # 1. Preparar fundo e corpo
        if os.path.exists(self.bg_path):
            bg_full = Image.open(self.bg_path).convert("RGBA")
            bg = bg_full.crop((0, 0, ORIGINAL_WIDTH, ORIGINAL_HEIGHT))
        else:
            bg = Image.new("RGBA", (ORIGINAL_WIDTH, ORIGINAL_HEIGHT), (60, 60, 60, 255))
        
        final_img = bg.resize((ORIGINAL_WIDTH * SCALE, ORIGINAL_HEIGHT * SCALE), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(final_img)
        
        try:
            # Tentar carregar fonte, senão default
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            count_font = ImageFont.truetype(font_path, 22)
        except:
            count_font = ImageFont.load_default()

        body = await self.fetch_player_body(player_data['uuid'])
        if body:
            target_h = int(CHAR_BOX_H * SCALE * 0.95)
            ratio = target_h / body.height
            target_w = int(body.width * ratio)
            body_hd = body.resize((target_w, target_h), Image.Resampling.LANCZOS)
            bx, by, bw, bh = CHAR_BOX_X*SCALE, CHAR_BOX_Y*SCALE, CHAR_BOX_W*SCALE, CHAR_BOX_H*SCALE
            pos_x = bx + (bw - target_w) // 2
            pos_y = by + (bh - target_h) // 2
            final_img.paste(body_hd, (pos_x, pos_y), body_hd)

        async def draw_item(item, ox, oy, empty_type=None):
            rx, ry = ox * SCALE, oy * SCALE
            
            # Se vazio, tentar desenhar ícone de "slot" (ex: sombra do capacete)
            if (not item or item.get('id') == "minecraft:air"):
                if empty_type:
                    e_icon = await self.fetch_empty_icon(empty_type)
                    if e_icon:
                        e_rendered = e_icon.resize((16 * SCALE, 16 * SCALE), Image.Resampling.NEAREST)
                        final_img.paste(e_rendered, (rx, ry), e_rendered)
                return

            icon = await self.fetch_item_icon(item['id'])
            if icon:
                # print(f"📍 [Renderer] Desenhando {item['id']} em {ox},{oy}")
                target_size = 16 * SCALE
                # Redimensionar usando filtro apropriado
                if icon.width <= 32: # Pixel art
                    icon_rendered = icon.resize((target_size, target_size), Image.Resampling.NEAREST)
                else: # HD Jemsire
                    icon_rendered = icon.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
                final_img.paste(icon_rendered, (rx, ry), icon_rendered)
                
                # Desenhar quantidade se > 1
                count = item.get('count', 1)
                if count > 1:
                    txt = str(count)
                    tw = draw.textlength(txt, font=count_font)
                    tx = rx + (16 * SCALE) - tw - 4
                    ty = ry + (16 * SCALE) - 24
                    # Sombra
                    draw.text((tx + 2, ty + 2), txt, fill=(0, 0, 0, 180), font=count_font)
                    draw.text((tx, ty), txt, fill=(255, 255, 255, 255), font=count_font)

        # 2. Renderizar Slots
        # Armor
        armor_map = {39: "helmet", 38: "chestplate", 37: "leggings", 36: "boots"}
        for slot_id, slot_name in armor_map.items():
            item = next((a for a in player_data.get('armor', []) if a and a.get('slot') == slot_id), None)
            y = 8 + (39 - slot_id) * SLOT_STEP
            await draw_item(item, 8, y, empty_type=slot_name)

        # Off-hand
        await draw_item(player_data.get('off_hand'), 77, 62, empty_type="shield")

        # Main Inventory
        for row in range(3):
            for col in range(9):
                slot_id = 9 + row * 9 + col
                item = next((i for i in player_data.get('main_inventory', []) if i and i.get('slot') == slot_id), None)
                await draw_item(item, 8 + col * SLOT_STEP, 84 + row * SLOT_STEP)

        # Hotbar
        for col in range(9):
            item = next((i for i in player_data.get('hotbar', []) if i and i.get('slot') == col), None)
            await draw_item(item, 8 + col * SLOT_STEP, 142)

        output = io.BytesIO()
        final_img.save(output, format="PNG")
        output.seek(0)
        
        print(f"🏁 [Renderer] Dossiê de {player_data.get('name')} ok.")
        return discord.File(fp=output, filename=f"inventory_{player_data['name']}.png")

renderer = InventoryRenderer()
