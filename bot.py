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
import logging
import asyncio

# Keep-alive e painel web integrado
from flask import Flask, jsonify, request, send_from_directory
import threading
import os

# Flask app que serve tanto keep-alive quanto painel
app = Flask(__name__)
bot_instance = None

# Keep-alive endpoints
@app.route('/')
def home():
    return "Bot iBot está online! 🤖"

@app.route('/health')
def health():
    return "OK"

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Criando o bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
ticket_manager = TicketManager(bot)
backup_manager = BackupManager()
loja_builder = LojaBuilder(bot)

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
        await self.view_instance.process_close(interaction, self.reason.value)


class AddMemberModal(discord.ui.Modal, title="Adicionar Membro"):
    """Modal para adicionar um membro ao ticket"""
    
    member_id = discord.ui.TextInput(
        label="ID do Membro",
        style=discord.TextStyle.short,
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    def __init__(self, view_instance):
        super().__init__()
        self.view_instance = view_instance
    
    async def on_submit(self, interaction: discord.Interaction):
        """Quando o modal é enviado"""
        await self.view_instance.process_add_member(interaction, self.member_id.value)

# ==================== VIEWS (Botões) ====================

class BuyAccountView(discord.ui.View):
    """View com botão de compra de conta"""
    
    def __init__(self, account_id: str):
        super().__init__(timeout=None)
        self.account_id = account_id
    
    @discord.ui.button(label="Comprar Conta", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para comprar conta - abre ticket automaticamente"""
        
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
            # Cria ticket automaticamente para compra
            channel, result_msg = await create_ticket_channel(
                guild, 
                interaction.user, 
                f"Interesse em comprar conta - ID: {self.account_id}"
            )
            
            if channel:
                # Envia mensagem efêmera para o usuário
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="✅ Ticket de Compra Criado",
                        description=f"Seu ticket para compra da conta foi criado com sucesso!\n\nAcesse: {channel.mention}\n\nNossa equipe entrará em contato em breve.",
                        color=COLORS["success"]
                    ),
                    ephemeral=True
                )
                
                # Envia mensagem no ticket sobre a conta
                await channel.send(
                    embed=discord.Embed(
                        title="🛒 Interesse em Compra de Conta",
                        description=f"O usuário {interaction.user.mention} está interessado na conta **{self.account_id}**.\n\nNossa equipe irá ajudá-lo com o processo de compra.",
                        color=COLORS["info"]
                    )
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
            ticket_number = ticket_info.get("ticket_number", "?")
            
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
        
        # Fecha o ticket
        ticket_manager.close_ticket(self.ticket_id, interaction.user.id)
        
        # Obtém informações completas do ticket
        ticket_info = ticket_manager.get_ticket(self.ticket_id)
        ticket_number = ticket_info.get("ticket_number", "?")
        ticket_creator_id = ticket_info.get("user_id")
        ticket_creator = guild.get_member(ticket_creator_id)
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

async def create_ticket_channel(guild, user, reason="Ticket criado via painel"):
    """Função independente para criar um canal de ticket"""
    try:
        # Verifica se o usuário já tem um ticket aberto
        user_id = user.id
        for ticket_id, ticket_info in ticket_manager.tickets.items():
            if ticket_info["user_id"] == str(user_id) and ticket_info["status"] == "open":
                return None, f"Usuário {user.display_name} já possui um ticket aberto!"
        
        # Cria o ticket no manager
        ticket_data = ticket_manager.create_ticket(str(user_id), reason)
        if not ticket_data:
            return None, "Erro ao criar ticket no sistema"
            
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
        embed_ticket = discord.Embed(
            title=f"🎫 Ticket #{ticket_number}",
            description=f"Olá {user.mention}!\n\nObrigado por abrir um ticket. Nossa equipe de suporte entrará em contato em breve.",
            color=COLORS["info"]
        )
        embed_ticket.add_field(name="Status", value="🟢 Aberto", inline=False)
        embed_ticket.add_field(name="Criado por", value=user.mention, inline=False)
        embed_ticket.add_field(name="Motivo", value=reason, inline=False)
        embed_ticket.set_footer(text=f"Ticket ID: {ticket_id}")
        
        await channel.send(embed=embed_ticket, view=TicketPanelView(bot, ticket_id, user.id))
        
        # Envia log
        await send_log(
            f"✅ Novo ticket criado",
            f"**Ticket:** #{ticket_number}\n**Usuário:** {user.mention}\n**Canal:** {channel.mention}\n**Motivo:** {reason}",
            COLORS["success"]
        )
        
        logger.info(f"🎫 Ticket #{ticket_number} criado para {user.display_name} via painel - Canal: {channel.name}")
        
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


# ==================== COMANDOS ====================

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


@bot.command(name="nova_loja")
@commands.has_permissions(administrator=True)
async def nova_loja(ctx, confirmar: str = None):
    """Cria uma loja profissional do zero (APAGA TUDO EXCETO CARGOS!)"""
    
    # Aviso de segurança
    if confirmar != "CONFIRMAR":
        embed = discord.Embed(
            title="⚠️ ATENÇÃO - COMANDO DESTRUTIVO!",
            description="""
            **Este comando irá:**
            ❌ Deletar TODAS as categorias
            ❌ Deletar TODOS os canais (texto e voz)
            ✅ Manter todos os cargos
            ✅ Criar estrutura profissional de loja Roblox
            ✅ Configurar painéis automaticamente
            
            **ANTES DE USAR:**
            1️⃣ Faça um backup: `!backup_loja`
            2️⃣ Se não gostar, restaure: `!restaurar_backup <arquivo> confirmar`
            
            **⚠️ ESTA AÇÃO NÃO PODE SER DESFEITA SEM BACKUP!**
            
            Para confirmar, use:
            `!nova_loja CONFIRMAR`
            """,
            color=0xff0000
        )
        embed.set_footer(text="⚠️ LEIA COM ATENÇÃO ANTES DE CONFIRMAR!")
        await ctx.send(embed=embed)
        return
    
    # Verificar se há backup recente
    backups = backup_manager.list_backups()
    has_recent_backup = False
    
    if backups:
        from datetime import datetime, timedelta
        latest_backup = backups[-1]
        backup_date = datetime.fromisoformat(latest_backup['created_at'])
        if datetime.now() - backup_date < timedelta(days=1):
            has_recent_backup = True
    
    if not has_recent_backup:
        embed = discord.Embed(
            title="⚠️ AVISO: SEM BACKUP RECENTE!",
            description="""
            Você não tem um backup recente (últimas 24h).
            
            **É ALTAMENTE RECOMENDADO fazer um backup antes!**
            
            Deseja continuar mesmo assim?
            • `!backup_loja` - Criar backup primeiro (RECOMENDADO)
            • `!nova_loja CONFIRMAR FORCAR` - Continuar sem backup (NÃO RECOMENDADO)
            """,
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Mensagem de progresso inicial
    progress_embed = discord.Embed(
        title="🏗️ Criando Nova Loja Profissional...",
        description="""
        **Progresso:**
        ⏳ Fase 1: Limpando servidor...
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
def api_close_ticket(ticket_id):
    """API: Fecha um ticket"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Fechado via painel web')
        
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
            ticket_manager.close_ticket(ticket_id, reason)
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
def api_get_tickets():
    """API: Lista todos os tickets"""
    try:
        tickets = ticket_manager.get_all_tickets()
        return jsonify({'success': True, 'tickets': tickets}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINTS PARA PAINEL WEB ====================

@app.route('/api/stats', methods=['GET'])
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

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    """Retorna todos os tickets"""
    try:
        tickets = ticket_manager.get_all_tickets()
        return jsonify({'success': True, 'tickets': tickets}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/notify', methods=['POST'])
def notify_staff_panel(ticket_id):
    """Notifica staff via painel"""
    return api_notify_staff(ticket_id)

@app.route('/api/ticket/<ticket_id>/add-member', methods=['POST']) 
def add_member_panel(ticket_id):
    """Adiciona membro via painel"""
    return api_add_member(ticket_id)

@app.route('/api/ticket/<ticket_id>/close', methods=['POST'])
def close_ticket_panel(ticket_id):
    """Fecha ticket via painel"""
    return api_close_ticket(ticket_id)

@app.route('/api/tickets/reset', methods=['POST'])
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

@app.route('/api/ticket/create', methods=['POST'])
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
                
                # View com botão de compra
                view = BuyAccountView(data['id'])
                
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

def run_web_server():
    """Executa o servidor web em thread separada"""
    app.run(host='0.0.0.0', port=8080, debug=False)

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
