import aiohttp
import json
import os
import io
import asyncio
import zipfile
import shutil
from PIL import Image

class JemsireIconFinder:
    def __init__(self, cache_dir):
        self.base_url = "https://minecraftallimages.jemsire.com"
        self.version_url = "https://raw.githubusercontent.com/TinyTank800/MinecraftAllImages/refs/heads/main/version.json"
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "jemsire_index.json")
        self.versions_dir = os.path.join(cache_dir, "versions")
        
        # Da mais nova para a mais antiga
        self.versions = ["1.21.10", "1.21.6", "1.21.5", "1.21.4", "1.20.6", "1.19.4", "1.18.2", "1.17.1", "1.16.5", "1.15.2", "1.14.4", "1.13.2"]
        self.index = {}
        self.path_cache = {} # Cache de caminhos reais para performance
        self.local_version = None
        self._ready = False

    async def initialize(self):
        """Carrega o índice e verifica se houve atualização no Github."""
        needs_rebuild = False
        
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    self.index = data.get("index", {})
                    self.local_version = data.get("version", "")
            except:
                needs_rebuild = True
        else:
            needs_rebuild = True

        print("🔍 [Jemsire] Verificando atualizações no servidor...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.version_url, timeout=10) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        remote_data = json.loads(text)
                        remote_version = remote_data.get("message", "")
                        
                        if remote_version != self.local_version:
                            print(f"🔄 [Jemsire] NOVA VERSÃO DISPONÍVEL: {remote_version}")
                            self.local_version = remote_version
                            needs_rebuild = True
                        elif not os.path.exists(self.versions_dir) or not os.listdir(self.versions_dir):
                            print("⚠️ [Jemsire] Assets locais não encontrados. Sincronizando...")
                            needs_rebuild = True
                        else:
                            print(f"✅ [Jemsire] Mirror local {self.local_version} está OK.")
            except Exception as e:
                print(f"⚠️ [Jemsire] Usando Mirror local (Offline: {e})")

        if needs_rebuild:
            await self.full_sync()
        else:
            self._ready = True

    async def build_index_from_web(self, session):
        """Reconstrói o mapeamento item->versão usando os dados oficiais da web."""
        print("📂 [Jemsire] Gerindo metadados da galeria...")
        temp_map = {}
        
        # 1. Manifest Base
        try:
            async with session.get(f"{self.base_url}/manifest.json", timeout=10) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text.strip().startswith("{"):
                        data = json.loads(text)
                        for item in data.get("images", []):
                            name = item.replace(".png", "").lower()
                            temp_map[name] = []
        except: pass

        # 2. Mudanças por versão (antigo para novo, para que o novo prevaleça no final)
        for version in reversed(self.versions):
            url = f"{self.base_url}/images/{version}/changes.json"
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if text.strip().startswith("{"):
                            data = json.loads(text)
                            items = data.get("added", []) + data.get("modified", [])
                            for item in items:
                                name = item.replace(".png", "").lower()
                                if name not in temp_map: temp_map[name] = []
                                # Adicionamos no início da lista para que vers[0] seja sempre a mais recente
                                temp_map[name].insert(0, version)
            except: pass

        final_index = {}
        for name, vers in temp_map.items():
            if vers:
                final_index[name] = vers[0]
            else:
                final_index[name] = "1.21.10" # Default
        
        return final_index

    async def full_sync(self):
        """Baixa ZIPs e constrói o índice."""
        print("🚀 [Jemsire] Iniciando sincronização completa...")
        
        if os.path.exists(self.versions_dir):
            shutil.rmtree(self.versions_dir)
        os.makedirs(self.versions_dir, exist_ok=True)

        async with aiohttp.ClientSession() as session:
            # Baixar em paralelo
            tasks = []
            sem = asyncio.Semaphore(4)

            async def download_v(v):
                async with sem:
                    url = f"{self.base_url}/images/{v}.zip"
                    print(f"📦 [Jemsire] Download: {v}.zip")
                    try:
                        async with session.get(url, timeout=300) as resp:
                            if resp.status == 200:
                                b = await resp.read()
                                with zipfile.ZipFile(io.BytesIO(b)) as z:
                                    z.extractall(os.path.join(self.versions_dir, v))
                                print(f"✅ [Jemsire] Extraído: {v}")
                    except Exception as e:
                        print(f"❌ [Jemsire] Falha em {v}: {e}")

            await asyncio.gather(*[download_v(v) for v in self.versions])
            
            # Construir índice
            self.index = await self.build_index_from_web(session)

        with open(self.cache_file, "w") as f:
            json.dump({"version": self.local_version, "index": self.index}, f)

        total_mb = sum(os.path.getsize(os.path.join(r, f)) for r, d, fs in os.walk(self.versions_dir) for f in fs) / (1024*1024)
        print(f"✨ [Jemsire] Mirror pronto! {len(self.index)} itens | {total_mb:.2f} MB")
        self._ready = True

    async def get_icon(self, item_id):
        if not self._ready:
            await self.initialize()

        clean_name = item_id.split(":")[-1].lower()
        version = self.index.get(clean_name)
        
        if not version:
            return None

        # Verificar cache de caminhos
        cache_key = f"{version}:{clean_name}"
        if cache_key in self.path_cache:
            return Image.open(self.path_cache[cache_key]).convert("RGBA")

        # Procurar o arquivo
        v_dir = os.path.join(self.versions_dir, version)
        if not os.path.exists(v_dir):
            return None

        # Busca recursiva para lidar com pastas aninhadas nos ZIPs
        for root, _, files in os.walk(v_dir):
            filename = f"{clean_name}.png"
            if filename in files:
                full_path = os.path.join(root, filename)
                self.path_cache[cache_key] = full_path
                try:
                    return Image.open(full_path).convert("RGBA")
                except:
                    pass
        
        return None

    async def download_icon(self, item_id, local_path):
        img = await self.get_icon(item_id)
        if img: return img
        return None
