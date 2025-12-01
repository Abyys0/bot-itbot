import json
import os
from datetime import datetime
import discord
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Gerenciador de backups do servidor Discord"""
    
    def __init__(self, backup_folder="backups"):
        self.backup_folder = backup_folder
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
    
    async def create_backup(self, guild: discord.Guild):
        """Cria um backup completo do servidor"""
        try:
            backup_data = {
                "backup_info": {
                    "guild_name": guild.name,
                    "guild_id": guild.id,
                    "created_at": datetime.now().isoformat(),
                    "member_count": guild.member_count,
                    "owner_id": guild.owner_id
                },
                "roles": await self._backup_roles(guild),
                "categories": await self._backup_categories(guild),
                "channels": await self._backup_channels(guild),
                "emojis": await self._backup_emojis(guild),
                "guild_settings": await self._backup_guild_settings(guild)
            }
            
            # Salva o backup em arquivo JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{guild.name}_{timestamp}.json"
            filepath = os.path.join(self.backup_folder, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Backup criado: {filename}")
            return True, filename, backup_data
        
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return False, None, str(e)
    
    async def _backup_roles(self, guild: discord.Guild):
        """Faz backup dos cargos"""
        roles_data = []
        for role in guild.roles:
            if role.name != "@everyone":  # Pula o cargo padrão
                roles_data.append({
                    "name": role.name,
                    "id": role.id,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "position": role.position,
                    "permissions": role.permissions.value
                })
        return roles_data
    
    async def _backup_categories(self, guild: discord.Guild):
        """Faz backup das categorias"""
        categories_data = []
        for category in guild.categories:
            # Backup de permissões
            overwrites = {}
            for target, overwrite in category.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[f"role_{target.id}"] = {
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value
                    }
            
            categories_data.append({
                "name": category.name,
                "id": category.id,
                "position": category.position,
                "overwrites": overwrites
            })
        return categories_data
    
    async def _backup_channels(self, guild: discord.Guild):
        """Faz backup dos canais"""
        channels_data = []
        
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue  # Categorias já foram salvas
            
            # Backup de permissões
            overwrites = {}
            for target, overwrite in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[f"role_{target.id}"] = {
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value
                    }
            
            channel_data = {
                "name": channel.name,
                "id": channel.id,
                "type": str(channel.type),
                "position": channel.position,
                "category_id": channel.category.id if channel.category else None,
                "overwrites": overwrites
            }
            
            # Dados específicos por tipo
            if isinstance(channel, discord.TextChannel):
                channel_data.update({
                    "topic": channel.topic,
                    "slowmode_delay": channel.slowmode_delay,
                    "nsfw": channel.nsfw
                })
            elif isinstance(channel, discord.VoiceChannel):
                channel_data.update({
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit
                })
            
            channels_data.append(channel_data)
        
        return channels_data
    
    async def _backup_emojis(self, guild: discord.Guild):
        """Faz backup dos emojis"""
        emojis_data = []
        for emoji in guild.emojis:
            emojis_data.append({
                "name": emoji.name,
                "id": emoji.id,
                "animated": emoji.animated,
                "url": str(emoji.url)
            })
        return emojis_data
    
    async def _backup_guild_settings(self, guild: discord.Guild):
        """Faz backup das configurações gerais"""
        return {
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
            "banner_url": str(guild.banner.url) if guild.banner else None,
            "description": guild.description,
            "verification_level": str(guild.verification_level),
            "default_notifications": str(guild.default_notifications),
            "explicit_content_filter": str(guild.explicit_content_filter),
            "afk_timeout": guild.afk_timeout,
            "afk_channel_id": guild.afk_channel.id if guild.afk_channel else None,
            "system_channel_id": guild.system_channel.id if guild.system_channel else None
        }
    
    def list_backups(self):
        """Lista todos os backups disponíveis"""
        try:
            backups = []
            for filename in os.listdir(self.backup_folder):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.backup_folder, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        backups.append({
                            "filename": filename,
                            "guild_name": data["backup_info"]["guild_name"],
                            "created_at": data["backup_info"]["created_at"],
                            "member_count": data["backup_info"]["member_count"]
                        })
            return backups
        except Exception as e:
            logger.error(f"Erro ao listar backups: {e}")
            return []
    
    def load_backup(self, filename):
        """Carrega um backup específico"""
        try:
            filepath = os.path.join(self.backup_folder, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar backup: {e}")
            return None
    
    async def restore_backup(self, guild: discord.Guild, backup_data: dict, options: dict = None):
        """
        Restaura um backup
        options: {
            'restore_roles': True,
            'restore_channels': True,
            'restore_categories': True,
            'delete_existing': False
        }
        """
        if options is None:
            options = {
                'restore_roles': True,
                'restore_channels': True,
                'restore_categories': True,
                'delete_existing': False
            }
        
        results = {
            "success": True,
            "errors": [],
            "restored": {
                "roles": 0,
                "categories": 0,
                "channels": 0
            }
        }
        
        try:
            # Restaurar cargos
            if options.get('restore_roles'):
                role_map = {}  # Mapeia IDs antigos para novos
                for role_data in sorted(backup_data['roles'], key=lambda x: x['position']):
                    try:
                        # Verifica se o cargo já existe
                        existing_role = discord.utils.get(guild.roles, name=role_data['name'])
                        if existing_role and not options.get('delete_existing'):
                            role_map[role_data['id']] = existing_role.id
                            continue
                        
                        new_role = await guild.create_role(
                            name=role_data['name'],
                            color=discord.Color(role_data['color']),
                            hoist=role_data['hoist'],
                            mentionable=role_data['mentionable'],
                            permissions=discord.Permissions(role_data['permissions'])
                        )
                        role_map[role_data['id']] = new_role.id
                        results['restored']['roles'] += 1
                    except Exception as e:
                        results['errors'].append(f"Erro ao restaurar cargo '{role_data['name']}': {str(e)}")
            
            # Restaurar categorias
            if options.get('restore_categories'):
                category_map = {}
                for cat_data in sorted(backup_data['categories'], key=lambda x: x['position']):
                    try:
                        existing_cat = discord.utils.get(guild.categories, name=cat_data['name'])
                        if existing_cat and not options.get('delete_existing'):
                            category_map[cat_data['id']] = existing_cat.id
                            continue
                        
                        new_cat = await guild.create_category(name=cat_data['name'])
                        category_map[cat_data['id']] = new_cat.id
                        results['restored']['categories'] += 1
                    except Exception as e:
                        results['errors'].append(f"Erro ao restaurar categoria '{cat_data['name']}': {str(e)}")
            
            # Restaurar canais
            if options.get('restore_channels'):
                for chan_data in sorted(backup_data['channels'], key=lambda x: x['position']):
                    try:
                        existing_chan = discord.utils.get(guild.channels, name=chan_data['name'])
                        if existing_chan and not options.get('delete_existing'):
                            continue
                        
                        category = None
                        if chan_data.get('category_id') and chan_data['category_id'] in category_map:
                            category = guild.get_channel(category_map[chan_data['category_id']])
                        
                        if 'text' in chan_data['type']:
                            await guild.create_text_channel(
                                name=chan_data['name'],
                                category=category,
                                topic=chan_data.get('topic'),
                                slowmode_delay=chan_data.get('slowmode_delay', 0),
                                nsfw=chan_data.get('nsfw', False)
                            )
                        elif 'voice' in chan_data['type']:
                            await guild.create_voice_channel(
                                name=chan_data['name'],
                                category=category,
                                bitrate=chan_data.get('bitrate', 64000),
                                user_limit=chan_data.get('user_limit', 0)
                            )
                        
                        results['restored']['channels'] += 1
                    except Exception as e:
                        results['errors'].append(f"Erro ao restaurar canal '{chan_data['name']}': {str(e)}")
        
        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Erro geral na restauração: {str(e)}")
            logger.error(f"Erro ao restaurar backup: {e}")
        
        return results
