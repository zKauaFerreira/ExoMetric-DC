import discord
from exo_inventory import InventoryRenderer as ExoRenderer

class InventoryRenderer:
    def __init__(self):
        self._exo = ExoRenderer()
        self._initialized = False

    async def initialize(self):
        """Inicializa o motor de renderização da biblioteca exo-inventory."""
        if not self._initialized:
            await self._exo.initialize()
            self._initialized = True

    async def render(self, player_data):
        """
        Gera a imagem de inventário do jogador usando a biblioteca exo-inventory.
        Retorna um objeto discord.File.
        """
        if not self._initialized:
            await self.initialize()

        # A biblioteca já retorna um objeto discord.File
        file = await self._exo.render_player(player_data)
        
        # Ajusta o filename se necessário (opcional, pois a lib usa "render.png" por padrão)
        name = player_data.get('name', 'player')
        file.filename = f"inventory_{name}.png"
        
        return file

    async def close(self):
        """Fecha a sessão da biblioteca."""
        await self._exo.close()

# Instância única para ser importada pelos outros módulos
renderer = InventoryRenderer()
