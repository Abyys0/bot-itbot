# Configurações do Bot iBot
import os
from dotenv import load_dotenv

load_dotenv()

# Token do bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "seu_token_aqui")

# IDs de configuração
TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID", "0"))  # Canal onde os tickets são criados
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))  # Categoria onde os tickets serão criados
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))  # Canal para logs
STAFF_ROLE_IDS = [int(role_id.strip()) for role_id in os.getenv("STAFF_ROLE_IDS", "0").split(",") if role_id.strip()]  # Cargos de staff para fechar tickets
GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # ID do servidor

# Prefixo do bot
BOT_PREFIX = "!"

# Cores para embeds
COLORS = {
    "info": 0x3498db,      # Azul
    "success": 0x2ecc71,   # Verde
    "error": 0xe74c3c,     # Vermelho
    "warning": 0xf39c12,   # Laranja
}
