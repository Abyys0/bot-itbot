"""
APIs de Moderação para o Painel Web
"""
from flask import jsonify, request
import discord
import asyncio
from datetime import datetime, timedelta
import logging
from api_auth import require_api_token

logger = logging.getLogger(__name__)

def register_moderation_routes(app, bot_instance_getter):
    """Registra todas as rotas de moderação no Flask app"""
    
    @app.route('/api/moderation/ban', methods=['POST'])
    @require_api_token
    def api_ban():
        """API para banir usuário"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            user_id = int(data.get('user_id'))
            reason = data.get('reason')
            delete_days = int(data.get('delete_days', 0))
            
            async def do_ban():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    user = await guild.fetch_member(user_id)
                    await guild.ban(user, reason=reason, delete_message_days=delete_days)
                    
                    # Registrar punição
                    from mod_panel import punishment_manager
                    punishment_manager.add_punishment(
                        guild.id, user_id, "ban", reason, guild.me.id
                    )
                    
                    return True, f"Usuário {user.name} banido"
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_ban(), loop)
            success, message = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/kick', methods=['POST'])
    @require_api_token
    def api_kick():
        """API para expulsar usuário"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            user_id = int(data.get('user_id'))
            reason = data.get('reason')
            
            async def do_kick():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    user = await guild.fetch_member(user_id)
                    await guild.kick(user, reason=reason)
                    
                    from mod_panel import punishment_manager
                    punishment_manager.add_punishment(
                        guild.id, user_id, "kick", reason, guild.me.id
                    )
                    
                    return True, f"Usuário {user.name} expulso"
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_kick(), loop)
            success, message = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/warn', methods=['POST'])
    @require_api_token
    def api_warn():
        """API para avisar usuário"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            user_id = int(data.get('user_id'))
            reason = data.get('reason')
            
            async def do_warn():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    user = await guild.fetch_member(user_id)
                    
                    from mod_panel import punishment_manager
                    punishment_manager.add_punishment(
                        guild.id, user_id, "warn", reason, guild.me.id
                    )
                    
                    # Tentar enviar DM
                    try:
                        embed = discord.Embed(
                            title="⚠️ Você recebeu um aviso",
                            description=f"**Servidor:** {guild.name}\n**Motivo:** {reason}",
                            color=0xf39c12
                        )
                        await user.send(embed=embed)
                    except:
                        pass
                    
                    return True, f"Aviso registrado para {user.name}"
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_warn(), loop)
            success, message = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/timeout', methods=['POST'])
    @require_api_token
    def api_timeout():
        """API para aplicar timeout"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            user_id = int(data.get('user_id'))
            duration = int(data.get('duration', 10))  # minutos
            reason = data.get('reason')
            
            async def do_timeout():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    user = await guild.fetch_member(user_id)
                    timeout_until = discord.utils.utcnow() + timedelta(minutes=duration)
                    await user.timeout(timeout_until, reason=reason)
                    
                    from mod_panel import punishment_manager
                    punishment_manager.add_punishment(
                        guild.id, user_id, "timeout", reason, guild.me.id, f"{duration} minutos"
                    )
                    
                    return True, f"Timeout aplicado em {user.name} por {duration} minutos"
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_timeout(), loop)
            success, message = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/clear', methods=['POST'])
    @require_api_token
    def api_clear():
        """API para limpar mensagens"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            channel_id = int(data.get('channel_id'))
            amount = int(data.get('amount', 10))
            
            async def do_clear():
                try:
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        return False, "Canal não encontrado", 0
                    
                    deleted = await channel.purge(limit=amount)
                    return True, f"{len(deleted)} mensagens deletadas", len(deleted)
                except Exception as e:
                    return False, str(e), 0
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_clear(), loop)
            success, message, deleted = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message, 'deleted': deleted})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/userinfo', methods=['GET'])
    @require_api_token
    def api_user_info():
        """API para obter informações do usuário"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            user_id = int(request.args.get('user_id'))
            
            async def get_info():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    user = await guild.fetch_member(user_id)
                    
                    from mod_panel import punishment_manager
                    punishments = punishment_manager.get_user_punishments(guild.id, user_id)
                    
                    user_data = {
                        'name': user.name,
                        'id': user.id,
                        'joined_at': user.joined_at.strftime("%d/%m/%Y %H:%M"),
                        'created_at': user.created_at.strftime("%d/%m/%Y %H:%M"),
                        'roles': len(user.roles) - 1,
                        'punishments': len(punishments)
                    }
                    
                    return True, user_data
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(get_info(), loop)
            success, result = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'user': result})
            else:
                return jsonify({'success': False, 'error': result})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/serverinfo', methods=['GET'])
    @require_api_token
    def api_server_info():
        """API para obter informações do servidor"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            async def get_info():
                try:
                    from config import GUILD_ID
                    guild = bot.get_guild(GUILD_ID)
                    if not guild:
                        return False, "Servidor não encontrado"
                    
                    server_data = {
                        'name': guild.name,
                        'members': guild.member_count,
                        'channels': len(guild.channels),
                        'roles': len(guild.roles),
                        'emojis': len(guild.emojis),
                        'boosts': guild.premium_subscription_count
                    }
                    
                    return True, server_data
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(get_info(), loop)
            success, result = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'server': result})
            else:
                return jsonify({'success': False, 'error': result})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/lock', methods=['POST'])
    @require_api_token
    def api_lock_channel():
        """API para trancar/destrancar canal"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            data = request.get_json()
            channel_id = int(data.get('channel_id'))
            lock = data.get('lock', True)
            
            async def do_lock():
                try:
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        return False, "Canal não encontrado"
                    
                    overwrite = channel.overwrites_for(channel.guild.default_role)
                    overwrite.send_messages = not lock
                    await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
                    
                    action = "trancado" if lock else "destrancado"
                    return True, f"Canal {action}"
                except Exception as e:
                    return False, str(e)
            
            loop = bot.loop
            future = asyncio.run_coroutine_threadsafe(do_lock(), loop)
            success, message = future.result(timeout=10)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/history', methods=['GET'])
    @require_api_token
    def api_user_history():
        """API para obter histórico de punições"""
        try:
            bot = bot_instance_getter()
            if not bot:
                return jsonify({'success': False, 'error': 'Bot não conectado'}), 503
            
            user_id = int(request.args.get('user_id'))
            
            from config import GUILD_ID
            from mod_panel import punishment_manager
            
            punishments = punishment_manager.get_user_punishments(GUILD_ID, user_id)
            
            # Formatar punições
            formatted = []
            for p in punishments:
                formatted.append({
                    'type': p['type'],
                    'reason': p['reason'],
                    'timestamp': datetime.fromisoformat(p['timestamp']).strftime("%d/%m/%Y %H:%M"),
                    'moderator': f"Moderador ID: {p['moderator_id']}"
                })
            
            return jsonify({'success': True, 'punishments': formatted})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/moderation/stats', methods=['GET'])
    @require_api_token
    def api_mod_stats():
        """API para estatísticas de moderação"""
        try:
            from config import GUILD_ID
            from mod_panel import punishment_manager
            
            guild_key = str(GUILD_ID)
            stats = {'bans': 0, 'kicks': 0, 'warns': 0, 'timeouts': 0}
            
            if guild_key in punishment_manager.punishments:
                for user_punishments in punishment_manager.punishments[guild_key].values():
                    for p in user_punishments:
                        if p['type'] == 'ban':
                            stats['bans'] += 1
                        elif p['type'] == 'kick':
                            stats['kicks'] += 1
                        elif p['type'] == 'warn':
                            stats['warns'] += 1
                        elif p['type'] == 'timeout':
                            stats['timeouts'] += 1
            
            return jsonify({'success': True, 'stats': stats})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
