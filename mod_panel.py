import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption
import json
import os
from datetime import datetime, timedelta
import asyncio

class PunishmentManager:
    """Gerenciador de punições do servidor"""
    
    def __init__(self):
        self.punishments_file = "punishments.json"
        self.punishments = self.load_punishments()
    
    def load_punishments(self):
        """Carrega histórico de punições"""
        if os.path.exists(self.punishments_file):
            with open(self.punishments_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_punishments(self):
        """Salva histórico de punições"""
        with open(self.punishments_file, 'w', encoding='utf-8') as f:
            json.dump(self.punishments, f, indent=2, ensure_ascii=False)
    
    def add_punishment(self, guild_id: int, user_id: int, punishment_type: str, reason: str, moderator_id: int, duration: str = None):
        """Adiciona uma punição ao histórico"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.punishments:
            self.punishments[guild_key] = {}
        
        if user_key not in self.punishments[guild_key]:
            self.punishments[guild_key][user_key] = []
        
        punishment = {
            "type": punishment_type,
            "reason": reason,
            "moderator_id": moderator_id,
            "timestamp": datetime.utcnow().isoformat(),
            "duration": duration
        }
        
        self.punishments[guild_key][user_key].append(punishment)
        self.save_punishments()
    
    def get_user_punishments(self, guild_id: int, user_id: int):
        """Obtém o histórico de punições de um usuário"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.punishments and user_key in self.punishments[guild_key]:
            return self.punishments[guild_key][user_key]
        return []

# Instância global
punishment_manager = PunishmentManager()

# ==================== MODALS ====================

class BanModal(Modal, title="🔨 Banir Usuário"):
    user_id = TextInput(
        label="ID do Usuário",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    reason = TextInput(
        label="Motivo",
        style=discord.TextStyle.paragraph,
        placeholder="Digite o motivo do banimento...",
        required=True,
        max_length=500
    )
    
    delete_days = TextInput(
        label="Deletar mensagens (dias)",
        placeholder="0-7 dias",
        required=False,
        default="0",
        max_length=1
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            delete_days_int = int(self.delete_days.value) if self.delete_days.value else 0
            
            if delete_days_int < 0 or delete_days_int > 7:
                delete_days_int = 0
            
            user = await interaction.guild.fetch_member(user_id)
            await interaction.guild.ban(user, reason=self.reason.value, delete_message_days=delete_days_int)
            
            # Registrar punição
            punishment_manager.add_punishment(
                interaction.guild.id, user_id, "ban", 
                self.reason.value, interaction.user.id
            )
            
            embed = discord.Embed(
                title="✅ Usuário Banido",
                description=f"**Usuário:** {user.mention} ({user.name})\n**Motivo:** {self.reason.value}\n**Moderador:** {interaction.user.mention}",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para banir este usuário!", ephemeral=True)

class KickModal(Modal, title="👢 Expulsar Usuário"):
    user_id = TextInput(
        label="ID do Usuário",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    reason = TextInput(
        label="Motivo",
        style=discord.TextStyle.paragraph,
        placeholder="Digite o motivo da expulsão...",
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            user = await interaction.guild.fetch_member(user_id)
            await interaction.guild.kick(user, reason=self.reason.value)
            
            punishment_manager.add_punishment(
                interaction.guild.id, user_id, "kick",
                self.reason.value, interaction.user.id
            )
            
            embed = discord.Embed(
                title="✅ Usuário Expulso",
                description=f"**Usuário:** {user.mention} ({user.name})\n**Motivo:** {self.reason.value}\n**Moderador:** {interaction.user.mention}",
                color=0xf39c12
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para expulsar este usuário!", ephemeral=True)

class WarnModal(Modal, title="⚠️ Avisar Usuário"):
    user_id = TextInput(
        label="ID do Usuário",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    reason = TextInput(
        label="Motivo",
        style=discord.TextStyle.paragraph,
        placeholder="Digite o motivo do aviso...",
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            user = await interaction.guild.fetch_member(user_id)
            
            punishment_manager.add_punishment(
                interaction.guild.id, user_id, "warn",
                self.reason.value, interaction.user.id
            )
            
            # Enviar DM para o usuário
            try:
                embed_dm = discord.Embed(
                    title="⚠️ Você recebeu um aviso",
                    description=f"**Servidor:** {interaction.guild.name}\n**Motivo:** {self.reason.value}\n**Moderador:** {interaction.user.name}",
                    color=0xf39c12
                )
                await user.send(embed=embed_dm)
            except:
                pass
            
            embed = discord.Embed(
                title="✅ Aviso Registrado",
                description=f"**Usuário:** {user.mention} ({user.name})\n**Motivo:** {self.reason.value}\n**Moderador:** {interaction.user.mention}",
                color=0xf39c12
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)

class ClearModal(Modal, title="🗑️ Limpar Mensagens"):
    amount = TextInput(
        label="Quantidade (1-100)",
        placeholder="Digite a quantidade de mensagens...",
        required=True,
        max_length=3
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 1 or amount > 100:
                await interaction.response.send_message("❌ Quantidade deve ser entre 1 e 100!", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            deleted = await interaction.channel.purge(limit=amount)
            
            await interaction.followup.send(f"✅ {len(deleted)} mensagens deletadas!", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Número inválido!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para deletar mensagens!", ephemeral=True)

class UserInfoModal(Modal, title="ℹ️ Informações do Usuário"):
    user_id = TextInput(
        label="ID do Usuário",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            user = await interaction.guild.fetch_member(user_id)
            
            # Obter punições
            punishments = punishment_manager.get_user_punishments(interaction.guild.id, user_id)
            punishment_count = len(punishments)
            
            embed = discord.Embed(
                title=f"ℹ️ Informações de {user.name}",
                color=0x3498db
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="📛 Nome", value=user.name, inline=True)
            embed.add_field(name="🆔 ID", value=user.id, inline=True)
            embed.add_field(name="📅 Entrou em", value=f"<t:{int(user.joined_at.timestamp())}:F>", inline=False)
            embed.add_field(name="📆 Conta criada em", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=False)
            embed.add_field(name="🎭 Cargos", value=f"{len(user.roles)-1} cargos", inline=True)
            embed.add_field(name="⚠️ Punições", value=f"{punishment_count} registros", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)

# ==================== VIEWS (Botões) ====================

class ModPanelView(View):
    """View principal do painel de moderação"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Punições", style=discord.ButtonStyle.danger, emoji="🔨", row=0)
    async def punishments_button(self, interaction: discord.Interaction, button: Button):
        """Abre menu de punições"""
        view = PunishmentsView()
        await interaction.response.send_message("🔨 Selecione o tipo de punição:", view=view, ephemeral=True)
    
    @discord.ui.button(label="Ferramentas", style=discord.ButtonStyle.primary, emoji="🔧", row=0)
    async def tools_button(self, interaction: discord.Interaction, button: Button):
        """Abre menu de ferramentas"""
        view = ToolsView()
        await interaction.response.send_message("🔧 Selecione a ferramenta:", view=view, ephemeral=True)
    
    @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary, emoji="⚙️", row=0)
    async def admin_button(self, interaction: discord.Interaction, button: Button):
        """Abre menu admin"""
        view = AdminView()
        await interaction.response.send_message("⚙️ Painel Administrativo:", view=view, ephemeral=True)
    
    @discord.ui.button(label="AutoMod", style=discord.ButtonStyle.success, emoji="🤖", row=1)
    async def automod_button(self, interaction: discord.Interaction, button: Button):
        """Configurações de AutoMod"""
        embed = discord.Embed(
            title="🤖 AutoMod",
            description="**Status:** Ativo ✅\n\n**Proteções Ativas:**\n• Anti-Spam\n• Anti-Raid\n• Filtro de Palavrões\n• Anti-Links\n• Anti-Mention Spam",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Estatísticas", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def stats_button(self, interaction: discord.Interaction, button: Button):
        """Mostra estatísticas"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title="📊 Estatísticas do Servidor",
            color=0x9b59b6
        )
        embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
        embed.add_field(name="💬 Canais", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 Cargos", value=len(guild.roles), inline=True)
        embed.add_field(name="😀 Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="📅 Criado", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Ajuda", style=discord.ButtonStyle.secondary, emoji="❓", row=1)
    async def help_button(self, interaction: discord.Interaction, button: Button):
        """Mostra ajuda"""
        embed = discord.Embed(
            title="❓ Ajuda - Painel de Moderação",
            description="**Funções disponíveis:**",
            color=0x3498db
        )
        embed.add_field(
            name="🔨 Punições",
            value="Ban, Kick, Mute, Warn - Aplicar punições aos usuários",
            inline=False
        )
        embed.add_field(
            name="🔧 Ferramentas",
            value="Clear, Info, Histórico - Ferramentas de moderação",
            inline=False
        )
        embed.add_field(
            name="⚙️ Admin",
            value="Config, Stats, Logs - Painel administrativo",
            inline=False
        )
        embed.add_field(
            name="🤖 AutoMod",
            value="Sistema automático de moderação",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PunishmentsView(View):
    """View para punições"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BanModal())
    
    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(KickModal())
    
    @discord.ui.button(label="Mute", style=discord.ButtonStyle.danger, emoji="🔇")
    async def mute_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔇 Função Mute em breve!", ephemeral=True)
    
    @discord.ui.button(label="Warn", style=discord.ButtonStyle.secondary, emoji="⚠️")
    async def warn_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WarnModal())

class ToolsView(View):
    """View para ferramentas"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ClearModal())
    
    @discord.ui.button(label="Info", style=discord.ButtonStyle.primary, emoji="ℹ️")
    async def info_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(UserInfoModal())
    
    @discord.ui.button(label="Histórico", style=discord.ButtonStyle.secondary, emoji="📜")
    async def history_button(self, interaction: discord.Interaction, button: Button):
        modal = HistoryModal()
        await interaction.response.send_modal(modal)

class HistoryModal(Modal, title="📜 Ver Histórico"):
    user_id = TextInput(
        label="ID do Usuário",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            punishments = punishment_manager.get_user_punishments(interaction.guild.id, user_id)
            
            if not punishments:
                await interaction.response.send_message("✅ Usuário sem punições registradas!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📜 Histórico de Punições",
                description=f"**Total:** {len(punishments)} registros",
                color=0xe74c3c
            )
            
            for i, p in enumerate(punishments[-5:], 1):  # Últimos 5
                moderator = f"<@{p['moderator_id']}>"
                timestamp = datetime.fromisoformat(p['timestamp'])
                embed.add_field(
                    name=f"{i}. {p['type'].upper()}",
                    value=f"**Motivo:** {p['reason']}\n**Mod:** {moderator}\n**Data:** <t:{int(timestamp.timestamp())}:R>",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)

class AdminView(View):
    """View para admin"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Config", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def config_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="⚙️ Configurações",
            description="**Configurações do Servidor**\n\nUse os comandos para ajustar as configurações.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Logs", style=discord.ButtonStyle.primary, emoji="📋")
    async def logs_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📋 Logs do Servidor",
            description="**Sistema de Logs Ativo**\n\nTodos os eventos estão sendo registrados.",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_mod_panel(channel: discord.TextChannel):
    """Envia o painel de moderação no canal"""
    embed = discord.Embed(
        title="🛡️ Painel de Moderação",
        description="Bem-vindo ao painel de moderação!\n\nSelecione uma categoria abaixo para acessar as ferramentas de moderação.",
        color=0x5865f2
    )
    
    embed.add_field(
        name="🔨 Punições",
        value="Ban, Kick, Mute, Warn",
        inline=True
    )
    
    embed.add_field(
        name="🔧 Ferramentas",
        value="Clear, Info, Histórico",
        inline=True
    )
    
    embed.add_field(
        name="⚙️ Admin",
        value="Config, Stats, Logs",
        inline=True
    )
    
    embed.set_footer(text=f"Moderador: {channel.guild.name}")
    embed.set_thumbnail(url=channel.guild.icon.url if channel.guild.icon else None)
    
    view = ModPanelView()
    await channel.send(embed=embed, view=view)
