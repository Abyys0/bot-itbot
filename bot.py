import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from config import (
    BOT_TOKEN, TICKET_CHANNEL_ID, TICKET_CATEGORY_ID, LOG_CHANNEL_ID, 
    STAFF_ROLE_IDS, GUILD_ID, BOT_PREFIX, COLORS
)
from ticket_manager import TicketManager
import logging
import asyncio

# Keep-alive para evitar hibernação no Render
try:
    from keep_alive import keep_alive
    keep_alive()
except ImportError:
    pass  # Se não tiver Flask instalado, ignora (desenvolvimento local)

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

class TicketCreateView(discord.ui.View):
    """View para criar um novo ticket"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para criar um novo ticket"""
        
        # Verifica se o usuário já tem um ticket aberto
        user_id = interaction.user.id
        for ticket_id, ticket_info in ticket_manager.tickets.items():
            if ticket_info["user_id"] == user_id and ticket_info["status"] == "open":
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description="Você já possui um ticket aberto!",
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
                return
        
        # Cria o ticket
        ticket_number = ticket_manager.get_next_ticket_number()
        ticket_id = ticket_manager.create_ticket(user_id, ticket_number)
        
        # Obtem o servidor
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
        
        # Obtém os cargos de staff necessários
        staff_roles = [guild.get_role(role_id) for role_id in STAFF_ROLE_IDS]
        staff_roles = [role for role in staff_roles if role is not None]  # Filtra roles válidas
        
        # Cria o canal de ticket
        try:
            # Obtém a categoria onde os tickets devem ser criados
            category = guild.get_channel(TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Erro",
                        description="Categoria de tickets não encontrada!",
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
                return
            
            # Permissões padrão: sem acesso
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    view_channel=False
                ),
                interaction.user: discord.PermissionOverwrite(
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
            
            # Cria o canal com permissões restritas
            channel = await guild.create_text_channel(
                name=f"ticket-{ticket_number}",
                overwrites=overwrites,
                category=category,  # Cria na categoria especificada
                topic=f"Ticket #{ticket_number} - Aberto por {interaction.user.mention}"
            )
            
            # Atualiza o ticket com o channel ID
            ticket_manager.set_ticket_channel(ticket_id, channel.id)
            
            # Envia mensagem no canal do ticket
            embed_ticket = discord.Embed(
                title=f"🎫 Ticket #{ticket_number}",
                description=f"Olá {interaction.user.mention}!\n\nObrigado por abrir um ticket. Nossa equipe de suporte entrará em contato em breve.",
                color=COLORS["info"]
            )
            embed_ticket.add_field(name="Status", value="🟢 Aberto", inline=False)
            embed_ticket.add_field(name="Criado por", value=interaction.user.mention, inline=False)
            embed_ticket.set_footer(text=f"Ticket ID: {ticket_id}")
            
            await channel.send(embed=embed_ticket, view=TicketPanelView(bot, ticket_id, interaction.user.id))
            
            # Envia mensagem efêmera para o usuário
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Ticket Criado",
                    description=f"Seu ticket foi criado com sucesso!\n\nAcesse: {channel.mention}",
                    color=COLORS["success"]
                ),
                ephemeral=True
            )
            
            # Envia log
            await send_log(
                f"✅ Novo ticket criado",
                f"**Ticket:** #{ticket_number}\n**Usuário:** {interaction.user.mention}\n**Canal:** {channel.mention}",
                COLORS["success"]
            )
            
            logger.info(f"Ticket #{ticket_number} criado por {interaction.user} ({interaction.user.id})")
        
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
    logger.info(f"Bot conectado como {bot.user}")
    
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
    """Função principal para executar o bot com auto-restart"""
    if not BOT_TOKEN or BOT_TOKEN == "seu_token_aqui":
        print("❌ ERRO: BOT_TOKEN não configurado!")
        print("Configure o arquivo .env com seu token do Discord")
        return
    
    if GUILD_ID == 0 or TICKET_CHANNEL_ID == 0 or LOG_CHANNEL_ID == 0 or not STAFF_ROLE_IDS:
        print("❌ ERRO: IDs de configuração não definidos!")
        print("Configure corretamente o arquivo .env com:")
        print("  - GUILD_ID (ID do servidor Discord)")
        print("  - TICKET_CHANNEL_ID (ID do canal para criar tickets)")
        print("  - LOG_CHANNEL_ID (ID do canal para logs)")
        print("  - STAFF_ROLE_IDS (IDs dos cargos de staff, separados por vírgula)")
        return
    
    print("🚀 Iniciando bot iBot...")
    
    # Loop de auto-restart em caso de erro
    while True:
        try:
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
