import discord
import asyncio
import logging

logger = logging.getLogger(__name__)

class LojaBuilder:
    """Construtor de loja profissional para Roblox"""
    
    def __init__(self, bot):
        self.bot = bot
        self.created_channels = {}
        self.created_roles = {}
        
    async def create_professional_shop(self, guild: discord.Guild):
        """Cria uma loja profissional do zero"""
        
        results = {
            "success": True,
            "errors": [],
            "created": {
                "categories": 0,
                "channels": 0,
                "messages": 0
            }
        }
        
        try:
            # Fase 1: Deletar canais e categorias existentes
            logger.info("🗑️ Fase 1: Limpando servidor...")
            await self._clean_server(guild, results)
            
            # Fase 2: Criar estrutura
            logger.info("🏗️ Fase 2: Criando estrutura...")
            await self._create_structure(guild, results)
            
            # Fase 3: Configurar painéis
            logger.info("📝 Fase 3: Configurando painéis...")
            await self._setup_panels(guild, results)
            
            return results
            
        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Erro fatal: {str(e)}")
            logger.error(f"Erro ao criar loja: {e}")
            return results
    
    async def _clean_server(self, guild: discord.Guild, results: dict):
        """Limpa o servidor (mantém apenas cargos)"""
        try:
            # Deletar todos os canais
            for channel in guild.channels:
                if not isinstance(channel, discord.CategoryChannel):
                    try:
                        await channel.delete(reason="Criando nova loja profissional")
                        await asyncio.sleep(0.5)  # Evitar rate limit
                    except Exception as e:
                        results['errors'].append(f"Erro ao deletar canal {channel.name}: {str(e)}")
            
            # Deletar todas as categorias
            for category in guild.categories:
                try:
                    await category.delete(reason="Criando nova loja profissional")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    results['errors'].append(f"Erro ao deletar categoria {category.name}: {str(e)}")
            
            logger.info("✅ Servidor limpo com sucesso")
            
        except Exception as e:
            results['errors'].append(f"Erro na limpeza: {str(e)}")
    
    async def _create_structure(self, guild: discord.Guild, results: dict):
        """Cria a estrutura completa da loja"""
        
        # Permissões padrão
        everyone_role = guild.default_role
        
        # ==================== CATEGORIA: 📢 INFORMAÇÕES ====================
        cat_info = await guild.create_category(
            "📢│INFORMAÇÕES",
            position=0
        )
        results['created']['categories'] += 1
        
        # Canal de boas-vindas
        ch_welcome = await guild.create_text_channel(
            "👋│boas-vindas",
            category=cat_info,
            topic="Seja bem-vindo à nossa loja! Leia as regras e divirta-se! 🎮"
        )
        await ch_welcome.set_permissions(everyone_role, send_messages=False)
        self.created_channels['welcome'] = ch_welcome
        results['created']['channels'] += 1
        
        # Canal de regras
        ch_rules = await guild.create_text_channel(
            "📜│regras",
            category=cat_info,
            topic="Regras do servidor - Leia com atenção!"
        )
        await ch_rules.set_permissions(everyone_role, send_messages=False)
        self.created_channels['rules'] = ch_rules
        results['created']['channels'] += 1
        
        # Canal de anúncios
        ch_announcements = await guild.create_text_channel(
            "📢│anúncios",
            category=cat_info,
            topic="Novidades e atualizações importantes"
        )
        await ch_announcements.set_permissions(everyone_role, send_messages=False)
        self.created_channels['announcements'] = ch_announcements
        results['created']['channels'] += 1
        
        # Canal de informações
        ch_info = await guild.create_text_channel(
            "ℹ️│informações",
            category=cat_info,
            topic="Informações úteis sobre a loja e Roblox"
        )
        await ch_info.set_permissions(everyone_role, send_messages=False)
        self.created_channels['info'] = ch_info
        results['created']['channels'] += 1
        
        # ==================== CATEGORIA: 🛒 LOJA ====================
        cat_shop = await guild.create_category(
            "🛒│LOJA",
            position=1
        )
        results['created']['categories'] += 1
        
        # Canal de contas Roblox
        ch_accounts = await guild.create_text_channel(
            "🎮│contas-roblox",
            category=cat_shop,
            topic="Contas Roblox disponíveis para compra - Clique no botão para comprar!"
        )
        await ch_accounts.set_permissions(everyone_role, send_messages=False)
        self.created_channels['accounts'] = ch_accounts
        results['created']['channels'] += 1
        
        # Canal de robux
        ch_robux = await guild.create_text_channel(
            "💎│robux",
            category=cat_shop,
            topic="Venda de Robux - Preços especiais!"
        )
        await ch_robux.set_permissions(everyone_role, send_messages=False)
        self.created_channels['robux'] = ch_robux
        results['created']['channels'] += 1
        
        # Canal de passes de jogo
        ch_passes = await guild.create_text_channel(
            "🎫│passes-e-itens",
            category=cat_shop,
            topic="Game Passes e itens especiais"
        )
        await ch_passes.set_permissions(everyone_role, send_messages=False)
        self.created_channels['passes'] = ch_passes
        results['created']['channels'] += 1
        
        # Canal de promoções
        ch_promo = await guild.create_text_channel(
            "🔥│promoções",
            category=cat_shop,
            topic="Promoções e ofertas especiais - Não perca!"
        )
        await ch_promo.set_permissions(everyone_role, send_messages=False)
        self.created_channels['promo'] = ch_promo
        results['created']['channels'] += 1
        
        # ==================== CATEGORIA: 💰 ATENDIMENTO ====================
        cat_support = await guild.create_category(
            "💰│ATENDIMENTO",
            position=2
        )
        results['created']['categories'] += 1
        
        # Canal para abrir ticket
        ch_ticket = await guild.create_text_channel(
            "📧│abrir-ticket",
            category=cat_support,
            topic="Clique no botão abaixo para abrir um ticket de atendimento"
        )
        self.created_channels['ticket'] = ch_ticket
        results['created']['channels'] += 1
        
        # Canal de proofs/avaliações
        ch_proofs = await guild.create_text_channel(
            "⭐│avaliações",
            category=cat_support,
            topic="Avaliações de clientes satisfeitos"
        )
        await ch_proofs.set_permissions(everyone_role, send_messages=False)
        self.created_channels['proofs'] = ch_proofs
        results['created']['channels'] += 1
        
        # Canal de FAQ
        ch_faq = await guild.create_text_channel(
            "❓│dúvidas-frequentes",
            category=cat_support,
            topic="Perguntas frequentes - Veja se sua dúvida está aqui!"
        )
        await ch_faq.set_permissions(everyone_role, send_messages=False)
        self.created_channels['faq'] = ch_faq
        results['created']['channels'] += 1
        
        # ==================== CATEGORIA: 💬 COMUNIDADE ====================
        cat_community = await guild.create_category(
            "💬│COMUNIDADE",
            position=3
        )
        results['created']['categories'] += 1
        
        # Canal de chat geral
        ch_chat = await guild.create_text_channel(
            "💭│chat-geral",
            category=cat_community,
            topic="Converse sobre Roblox e outros assuntos"
        )
        self.created_channels['chat'] = ch_chat
        results['created']['channels'] += 1
        
        # Canal de memes
        ch_memes = await guild.create_text_channel(
            "😂│memes",
            category=cat_community,
            topic="Compartilhe seus memes favoritos de Roblox"
        )
        self.created_channels['memes'] = ch_memes
        results['created']['channels'] += 1
        
        # Canal de mídia
        ch_media = await guild.create_text_channel(
            "📸│mídia",
            category=cat_community,
            topic="Compartilhe prints, vídeos e arte do Roblox"
        )
        self.created_channels['media'] = ch_media
        results['created']['channels'] += 1
        
        # Canal de parcerias
        ch_partner = await guild.create_text_channel(
            "🤝│parcerias",
            category=cat_community,
            topic="Interessado em parceria? Entre em contato!"
        )
        await ch_partner.set_permissions(everyone_role, send_messages=False)
        self.created_channels['partner'] = ch_partner
        results['created']['channels'] += 1
        
        # Canal de voz
        ch_voice = await guild.create_voice_channel(
            "🎤│Conversa Geral",
            category=cat_community
        )
        results['created']['channels'] += 1
        
        ch_voice2 = await guild.create_voice_channel(
            "🎮│Jogando Roblox",
            category=cat_community
        )
        results['created']['channels'] += 1
        
        # ==================== CATEGORIA: 🔧 STAFF (PRIVADA) ====================
        cat_staff = await guild.create_category(
            "🔧│STAFF",
            position=4
        )
        # Torna categoria privada (apenas staff)
        await cat_staff.set_permissions(everyone_role, read_messages=False)
        results['created']['categories'] += 1
        
        # Canal de logs
        ch_logs = await guild.create_text_channel(
            "📊│logs",
            category=cat_staff,
            topic="Logs do servidor e do bot"
        )
        self.created_channels['logs'] = ch_logs
        results['created']['channels'] += 1
        
        # Canal de comandos
        ch_commands = await guild.create_text_channel(
            "🤖│comandos",
            category=cat_staff,
            topic="Use comandos do bot aqui"
        )
        self.created_channels['commands'] = ch_commands
        results['created']['channels'] += 1
        
        # Canal de configuração
        ch_config = await guild.create_text_channel(
            "⚙️│configuração",
            category=cat_staff,
            topic="Configurações do servidor"
        )
        self.created_channels['config'] = ch_config
        results['created']['channels'] += 1
        
        logger.info(f"✅ Estrutura criada: {results['created']['categories']} categorias, {results['created']['channels']} canais")
    
    async def _setup_panels(self, guild: discord.Guild, results: dict):
        """Configura painéis e mensagens nos canais"""
        
        # Importar TicketCreateView do módulo bot
        import sys
        import os
        
        # Adicionar o diretório atual ao path se necessário
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # ==================== PAINEL: BOAS-VINDAS ====================
        if 'welcome' in self.created_channels:
            embed = discord.Embed(
                title="🎮 Bem-vindo à Melhor Loja de Roblox!",
                description="""
                Olá! Seja muito bem-vindo à nossa comunidade! 👋
                
                Aqui você encontra:
                🎮 **Contas Roblox** premium e seguras
                💎 **Robux** com os melhores preços
                🎫 **Passes e Itens** exclusivos
                🔥 **Promoções** imperdíveis
                
                📜 Leia as <#{}> antes de começar
                📧 Dúvidas? Abra um ticket em <#{}>
                ⭐ Veja nossas avaliações em <#{}>
                
                **Aproveite e boa compra!** 🛒
                """.format(
                    self.created_channels['rules'].id if 'rules' in self.created_channels else '',
                    self.created_channels['ticket'].id if 'ticket' in self.created_channels else '',
                    self.created_channels['proofs'].id if 'proofs' in self.created_channels else ''
                ),
                color=0x00ff00
            )
            embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
            embed.set_footer(text=f"Servidor: {guild.name}")
            
            await self.created_channels['welcome'].send(embed=embed)
            results['created']['messages'] += 1
        
        # ==================== PAINEL: REGRAS ====================
        if 'rules' in self.created_channels:
            embed = discord.Embed(
                title="📜 Regras do Servidor",
                description="Leia com atenção e siga todas as regras!",
                color=0xff0000
            )
            embed.add_field(
                name="1️⃣ Respeito",
                value="Respeite todos os membros. Não toleramos discriminação, ofensas ou toxicidade.",
                inline=False
            )
            embed.add_field(
                name="2️⃣ Proibido Spam",
                value="Não faça spam nos canais. Isso inclui mensagens repetidas, flood e propagandas não autorizadas.",
                inline=False
            )
            embed.add_field(
                name="3️⃣ Conteúdo Apropriado",
                value="Compartilhe apenas conteúdo apropriado. NSFW, gore e conteúdo ofensivo são proibidos.",
                inline=False
            )
            embed.add_field(
                name="4️⃣ Sem Scam",
                value="Qualquer tentativa de golpe resultará em banimento permanente.",
                inline=False
            )
            embed.add_field(
                name="5️⃣ Canais Corretos",
                value="Use os canais para seus devidos fins. Mantenha a organização!",
                inline=False
            )
            embed.add_field(
                name="6️⃣ Suporte",
                value="Para compras e suporte, abra um ticket. Não marque staff no chat.",
                inline=False
            )
            embed.add_field(
                name="⚠️ Punições",
                value="Violações podem resultar em:\n• Advertência\n• Mute temporário\n• Kick\n• Ban permanente",
                inline=False
            )
            embed.set_footer(text="Ao permanecer no servidor, você concorda com as regras.")
            
            await self.created_channels['rules'].send(embed=embed)
            results['created']['messages'] += 1
        
        # ==================== PAINEL: TICKETS ====================
        if 'ticket' in self.created_channels:
            # Criar a view manualmente sem importar do bot
            class TicketCreateView(discord.ui.View):
                def __init__(self, bot_instance):
                    super().__init__(timeout=None)
                    self.bot_instance = bot_instance
                
                @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
                async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_message(
                        "Sistema de tickets em configuração. Use o painel web para criar tickets!",
                        ephemeral=True
                    )
            
            embed = discord.Embed(
                title="📧 Sistema de Atendimento",
                description="""
                Precisa de ajuda ou quer fazer uma compra?
                Clique no botão abaixo para abrir um ticket!
                
                **O que você pode fazer no ticket:**
                💰 Comprar contas, robux ou itens
                ❓ Tirar dúvidas sobre produtos
                🔧 Reportar problemas
                📦 Solicitar suporte pós-venda
                
                **Nossa equipe responde rapidamente!**
                """,
                color=0x3498db
            )
            embed.set_footer(text="Atendimento disponível 24/7")
            
            view = TicketCreateView(self.bot)
            await self.created_channels['ticket'].send(embed=embed, view=view)
            results['created']['messages'] += 1
        
        # ==================== PAINEL: FAQ ====================
        if 'faq' in self.created_channels:
            embed = discord.Embed(
                title="❓ Perguntas Frequentes",
                description="Respostas para as dúvidas mais comuns",
                color=0xf39c12
            )
            embed.add_field(
                name="🔐 As contas são seguras?",
                value="Sim! Todas as contas são verificadas e garantimos sua segurança.",
                inline=False
            )
            embed.add_field(
                name="💳 Quais formas de pagamento?",
                value="Aceitamos PIX, transferência bancária e carteiras digitais.",
                inline=False
            )
            embed.add_field(
                name="⏱️ Quanto tempo para receber?",
                value="Entregas são instantâneas ou em até 24h após confirmação do pagamento.",
                inline=False
            )
            embed.add_field(
                name="🔄 Posso trocar ou devolver?",
                value="Sim, oferecemos garantia! Consulte nossa política de trocas.",
                inline=False
            )
            embed.add_field(
                name="🛡️ Como funciona a garantia?",
                value="Todas as compras têm garantia contra problemas técnicos.",
                inline=False
            )
            embed.add_field(
                name="📧 Como entro em contato?",
                value=f"Abra um ticket em <#{self.created_channels['ticket'].id}> para atendimento personalizado!",
                inline=False
            )
            
            await self.created_channels['faq'].send(embed=embed)
            results['created']['messages'] += 1
        
        # ==================== PAINEL: INFORMAÇÕES ====================
        if 'info' in self.created_channels:
            embed = discord.Embed(
                title="ℹ️ Informações da Loja",
                description="Tudo que você precisa saber sobre nossa loja!",
                color=0x9b59b6
            )
            embed.add_field(
                name="🏪 Sobre Nós",
                value="Somos a loja mais confiável de Roblox! Anos de experiência no mercado.",
                inline=False
            )
            embed.add_field(
                name="⭐ Diferenciais",
                value="• Preços competitivos\n• Entrega rápida\n• Suporte 24/7\n• Garantia em todos os produtos\n• Milhares de clientes satisfeitos",
                inline=False
            )
            embed.add_field(
                name="📊 Estatísticas",
                value="• +5000 vendas realizadas\n• 99% de satisfação\n• Avaliação 5⭐",
                inline=False
            )
            embed.add_field(
                name="🔗 Links Úteis",
                value=f"📜 [Regras](<#{self.created_channels['rules'].id}>)\n📧 [Suporte](<#{self.created_channels['ticket'].id}>)\n⭐ [Avaliações](<#{self.created_channels['proofs'].id}>)",
                inline=False
            )
            
            await self.created_channels['info'].send(embed=embed)
            results['created']['messages'] += 1
        
        # ==================== PAINEL: CONTAS ====================
        if 'accounts' in self.created_channels:
            embed = discord.Embed(
                title="🎮 Contas Roblox Disponíveis",
                description="""
                **Contas premium prontas para uso!**
                
                📌 Todas as contas incluem:
                ✅ Email e senha completos
                ✅ Sem restrições
                ✅ Garantia de 7 dias
                ✅ Entrega instantânea
                
                💡 **Novas contas são postadas aqui regularmente!**
                
                Para comprar, clique no botão "🛒 Comprar Conta" em qualquer anúncio abaixo.
                """,
                color=0x00ff00
            )
            embed.set_footer(text="Estoque atualizado diariamente")
            
            await self.created_channels['accounts'].send(embed=embed)
            results['created']['messages'] += 1
        
        logger.info(f"✅ Painéis configurados: {results['created']['messages']} mensagens enviadas")
