# Configurações do Bot iBot
import os
import json
from dotenv import load_dotenv

load_dotenv()

def load_channel_ids():
    """Carrega IDs dos canais do arquivo JSON ou retorna valores padrão"""
    try:
        if os.path.exists('channel_config.json'):
            with open('channel_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar channel_config.json: {e}")
    
    # Retorna valores das variáveis de ambiente como fallback
    return {
        "ticket_channel_id": int(os.getenv("TICKET_CHANNEL_ID", "0")),
        "ticket_category_id": int(os.getenv("TICKET_CATEGORY_ID", "0")),
        "log_channel_id": int(os.getenv("LOG_CHANNEL_ID", "0")),
        "announcements_channel_id": int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID", "0")),
        "accounts_channel_id": int(os.getenv("ACCOUNTS_CHANNEL_ID", "0"))
    }

# Carregar IDs dinamicamente
_channel_config = load_channel_ids()

# Token do bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "seu_token_aqui")

# IDs de configuração (carregados dinamicamente de channel_config.json)
TICKET_CHANNEL_ID = _channel_config.get("ticket_channel_id", 0)
TICKET_CATEGORY_ID = _channel_config.get("ticket_category_id", 0)
LOG_CHANNEL_ID = _channel_config.get("log_channel_id", 0)
ANNOUNCEMENTS_CHANNEL_ID = _channel_config.get("announcements_channel_id", 0)
ACCOUNTS_CHANNEL_ID = _channel_config.get("accounts_channel_id", 0)
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
