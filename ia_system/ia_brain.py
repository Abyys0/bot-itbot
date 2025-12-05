"""
Sistema de Inteligência Artificial do iBot
Cérebro principal com capacidade de conversação e busca na internet
"""
import os
import json
import logging
import aiohttp
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class IABrain:
    """Cérebro da IA - Sistema de conversação inteligente"""
    
    def __init__(self):
        self.memory_file = "ia_system/memory.json"
        self.personality_file = "ia_system/personality.json"
        self.memory = self._load_memory()
        self.personality = self._load_personality()
        self.conversation_context = {}
        self.current_mode = "default"  # Modo atual da personalidade
        self.mode_history = {}  # Histórico de modos por usuário
    def _load_memory(self) -> Dict:
        """Carrega memória de conversas anteriores"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_memory(self):
        """Salva memória das conversas"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)
    
    def _load_personality(self) -> Dict:
        """Carrega personalidade da IA"""
        if os.path.exists(self.personality_file):
            try:
                with open(self.personality_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Personalidade padrão
        default_personality = {
            "name": "iBot",
            "traits": [
                "amigável",
                "prestativo",
                "inteligente",
                "curioso",
                "respeitoso"
            ],
            "style": "casual e acessível",
            "knowledge_areas": [
                "tecnologia",
                "discord",
                "programação",
                "FiveM",
                "jogos",
                "internet"
            ]
        }
        
        os.makedirs(os.path.dirname(self.personality_file), exist_ok=True)
        with open(self.personality_file, 'w', encoding='utf-8') as f:
            json.dump(default_personality, f, ensure_ascii=False, indent=2)
        
        return default_personality
    
    def _detect_mode(self, message: str) -> str:
        """Detecta qual modo de personalidade usar baseado na mensagem"""
        message_lower = message.lower()
        
        # Se não tiver modos configurados, usa default
        if "modes" not in self.personality:
            return "default"
        
        modes = self.personality.get("modes", {})
        best_match = "default"
        max_matches = 0
        
        # Verifica cada modo e conta quantas keywords aparecem
        for mode_name, mode_data in modes.items():
            if mode_name == "default":
                continue
                
            keywords = mode_data.get("keywords", [])
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            
            if matches > max_matches:
                max_matches = matches
                best_match = mode_name
        
        return best_match
    
    def _get_current_mode_data(self) -> Dict:
        """Retorna os dados do modo atual"""
        if "modes" not in self.personality:
            return {
                "name": self.personality.get("name", "iBot"),
                "emoji": "🤖",
                "style": "casual",
                "tone": "amigável"
            }
        
        return self.personality["modes"].get(self.current_mode, self.personality["modes"]["default"])
    
    def _switch_mode(self, new_mode: str, user_id: str) -> Optional[str]:
        """Troca o modo de personalidade e retorna mensagem se houver mudança"""
        if new_mode == self.current_mode:
            return None
        
        # Verifica se deve mostrar mudança de modo
        show_change = self.personality.get("behavior", {}).get("show_mode_change", True)
        
        old_mode = self.current_mode
        self.current_mode = new_mode
        
        # Salva no histórico do usuário
        if user_id not in self.mode_history:
            self.mode_history[user_id] = []
        
        self.mode_history[user_id].append({
            "from": old_mode,
            "to": new_mode,
            "timestamp": datetime.now().isoformat()
        })
        
        if show_change:
            mode_data = self._get_current_mode_data()
            return f"{mode_data['emoji']} **Modo {mode_data['name']} ativado!**"
        
        return None
    
    def _analyze_intent(self, message: str) -> str:
        """Analisa a intenção da mensagem"""
        message_lower = message.lower()
        
        # Perguntas
        if any(word in message_lower for word in ['?', 'como', 'quando', 'onde', 'por que', 'porque', 'qual', 'quem', 'o que']):
            return "question"
        
        # Solicitação de busca
        if any(word in message_lower for word in ['pesquise', 'busque', 'procure', 'encontre', 'pesquisar', 'buscar']):
            return "search"
        
        # Saudação
        if any(word in message_lower for word in ['oi', 'olá', 'ola', 'hey', 'e ai', 'eai', 'bom dia', 'boa tarde', 'boa noite']):
            return "greeting"
        
        # Despedida
        if any(word in message_lower for word in ['tchau', 'até', 'falou', 'flw', 'bye', 'adeus']):
            return "goodbye"
        
        # Agradecimento
        if any(word in message_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks', 'vlw']):
            return "thanks"
        
        # Conversa casual
        return "casual"
    
    def _extract_search_query(self, message: str) -> Optional[str]:
        """Extrai o termo de busca da mensagem"""
        message_lower = message.lower()
        
        # Padrões comuns de busca
        patterns = [
            r'pesquise?\s+(?:sobre\s+)?(?:por\s+)?(.+)',
            r'busque?\s+(?:sobre\s+)?(?:por\s+)?(.+)',
            r'procure?\s+(?:sobre\s+)?(?:por\s+)?(.+)',
            r'encontre?\s+(?:sobre\s+)?(?:por\s+)?(.+)',
            r'o que (?:é|e)\s+(.+)',
            r'quem (?:é|e)\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def search_internet(self, query: str, deep_search: bool = True) -> Dict[str, any]:
        """Busca informações na internet - SEM LIMITAÇÕES"""
        try:
            # Usando DuckDuckGo Instant Answer API (gratuita e sem chave)
            async with aiohttp.ClientSession() as session:
                url = f"https://api.duckduckgo.com/?q={query}&format=json"
                
                # Adiciona parâmetros para busca mais profunda
                if deep_search:
                    url += "&no_redirect=1&no_html=1&skip_disambig=1"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = {
                            "success": True,
                            "query": query,
                            "abstract": data.get("Abstract", ""),
                            "abstract_text": data.get("AbstractText", ""),
                            "abstract_url": data.get("AbstractURL", ""),
                            "answer": data.get("Answer", ""),
                            "definition": data.get("Definition", ""),
                            "related_topics": []
                        }
                        
                        # Extrair TODOS os tópicos relacionados - SEM LIMITE
                        for topic in data.get("RelatedTopics", []):
                            if isinstance(topic, dict) and "Text" in topic:
                                result["related_topics"].append({
                                    "text": topic.get("Text", ""),
                                    "url": topic.get("FirstURL", "")
                                })
                            # Suporte para subtópicos
                            elif isinstance(topic, dict) and "Topics" in topic:
                                for subtopic in topic["Topics"]:
                                    if "Text" in subtopic:
                                        result["related_topics"].append({
                                            "text": subtopic.get("Text", ""),
                                            "url": subtopic.get("FirstURL", "")
                                        })
                        
                        return result
                    
        except Exception as e:
            logger.error(f"Erro ao buscar na internet: {e}")
        
        return {
            "success": False,
            "query": query,
            "error": "Não consegui buscar informações no momento."
        }
    
    def _generate_response(self, message: str, intent: str, user_id: str) -> str:
        """Gera resposta baseada na intenção e modo atual"""
        
        # Atualiza contexto do usuário
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = []
        
        self.conversation_context[user_id].append({
            "message": message,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "mode": self.current_mode
        })
        
        # SEM LIMITE de contexto - mantém toda a conversa
        
        # Pega dados do modo atual
        mode_data = self._get_current_mode_data()
        
        # Gera resposta baseada na intenção e personalidade
        if intent == "greeting":
            # Usa greeting do modo atual
            return mode_data.get("greeting_style", f"Olá! 👋 Sou o {self.personality['name']}, como posso ajudar?")
        
        elif intent == "goodbye":
            goodbyes = [
                f"Até logo! 👋 {mode_data['emoji']}",
                f"Tchau! Foi bom conversar com você! {mode_data['emoji']}",
                f"Falou! Volte sempre que precisar! {mode_data['emoji']}",
                f"Até a próxima! Estou sempre por aqui! {mode_data['emoji']}"
            ]
            import random
            return random.choice(goodbyes)
        
        elif intent == "thanks":
            thanks_responses = [
                f"Por nada! Estou aqui para isso! {mode_data['emoji']}",
                f"Fico feliz em ajudar! {mode_data['emoji']}",
                f"Sempre às ordens! 👍",
                f"De nada! Precisando, é só chamar! {mode_data['emoji']}"
            ]
            import random
            return random.choice(thanks_responses)
        
        elif intent == "question":
            return self._answer_question(message)
        
        elif intent == "casual":
            return self._casual_response(message)
        
        return "Entendi! Como posso ajudar você melhor com isso? 🤔"
    
    def _answer_question(self, question: str) -> str:
        """Responde perguntas"""
        question_lower = question.lower()
        
        # Perguntas sobre o bot
        if "quem é você" in question_lower or "quem e você" in question_lower:
            return f"Sou o {self.personality['name']}, uma inteligência artificial criada para ajudar neste servidor! Posso conversar, responder perguntas e até buscar informações na internet para você. 🤖"
        
        if "o que você faz" in question_lower or "o que voce faz" in question_lower:
            return "Eu posso:\n• Conversar naturalmente com você\n• Responder perguntas sobre diversos assuntos\n• Buscar informações na internet\n• Ajudar com comandos do servidor\n• E muito mais! Basta me perguntar!"
        
        if "como você funciona" in question_lower or "como voce funciona" in question_lower:
            return "Sou uma IA com sistema de processamento de linguagem natural! Analiso suas mensagens, entendo o contexto e gero respostas inteligentes. Também posso buscar informações em tempo real na internet! 🧠"
        
        # Resposta genérica para outras perguntas
        return "Hmm, essa é uma boa pergunta! 🤔 Para respostas mais precisas, você pode me pedir para buscar na internet. Exemplo: 'pesquise sobre [assunto]'"
    
    def _casual_response(self, message: str) -> str:
        """Resposta casual para conversas"""
        message_lower = message.lower()
        
        # Reações a palavras-chave
        if any(word in message_lower for word in ['legal', 'bacana', 'show', 'top', 'massa']):
            return "Que bom que você gostou! 😊 Estou aqui para ajudar sempre!"
        
        if any(word in message_lower for word in ['não', 'nao', 'errado', 'ruim']):
            return "Entendo... Vou melhorar! Como posso ajudar de forma diferente? 🤔"
        
        if any(word in message_lower for word in ['ajuda', 'help', 'socorro']):
            return "Claro! Estou aqui para ajudar! O que você precisa? Pode me fazer perguntas ou pedir para eu buscar algo na internet!"
        
        # Resposta padrão
        responses = [
            "Interessante! Conte-me mais sobre isso.",
            "Entendo. Como posso ajudar você com isso?",
            "Hmm, entendi. Quer que eu busque mais informações sobre isso?",
            "Legal! Tem algo específico que você gostaria de saber?"
        ]
        import random
        return random.choice(responses)
    
    async def process_message(self, message: str, user_id: str, username: str) -> Tuple[str, Optional[Dict], Optional[str]]:
        """
        Processa uma mensagem e retorna resposta
        Returns: (resposta_texto, dados_busca_opcional, mensagem_modo_opcional)
        """
        
        # Detecta e troca modo automaticamente se habilitado
        mode_change_msg = None
        if self.personality.get("behavior", {}).get("auto_switch", True):
            detected_mode = self._detect_mode(message)
            mode_change_msg = self._switch_mode(detected_mode, user_id)
        
        # Salva na memória
        if user_id not in self.memory:
            self.memory[user_id] = {
                "username": username,
                "first_interaction": datetime.now().isoformat(),
                "message_count": 0,
                "topics": [],
                "modes_used": []
            }
        
        self.memory[user_id]["message_count"] += 1
        self.memory[user_id]["last_interaction"] = datetime.now().isoformat()
        
        # Registra modo usado
        if self.current_mode not in self.memory[user_id].get("modes_used", []):
            if "modes_used" not in self.memory[user_id]:
                self.memory[user_id]["modes_used"] = []
            self.memory[user_id]["modes_used"].append(self.current_mode)
        
        # Analisa intenção
        intent = self._analyze_intent(message)
        
        # Se for busca, executa busca
        if intent == "search":
            search_query = self._extract_search_query(message)
            if search_query:
                search_results = await self.search_internet(search_query)
                
                if search_results.get("success"):
                    response = self._format_search_response(search_results)
                    self._save_memory()
                    return response, search_results, mode_change_msg
                else:
                    return "Desculpe, não consegui buscar essas informações no momento. Tente novamente mais tarde! 😅", None, mode_change_msg
        
        # Gera resposta normal
        response = self._generate_response(message, intent, user_id)
        self._save_memory()
        
        return response, None, mode_change_msg
    
    def _format_search_response(self, results: Dict) -> str:
        """Formata resultado da busca para resposta"""
        response = f"🔍 **Busquei sobre: {results['query']}**\n\n"
        
        # Resposta direta se houver
        if results.get("answer"):
            response += f"**Resposta:** {results['answer']}\n\n"
        
        # Abstract/Resumo - SEM LIMITE de caracteres
        if results.get("abstract_text"):
            abstract = results["abstract_text"]
            response += f"**Resumo:** {abstract}\n"
            
            if results.get("abstract_url"):
                response += f"🔗 [Saiba mais]({results['abstract_url']})\n"
        
        # Definição
        elif results.get("definition"):
            response += f"**Definição:** {results['definition']}\n"
        
        # Tópicos relacionados - TODOS, sem limitações
        if results.get("related_topics"):
            response += f"\n**📚 Tópicos Relacionados:**\n"
            for i, topic in enumerate(results["related_topics"], 1):
                response += f"{i}. {topic['text']}\n"
        
        if not results.get("answer") and not results.get("abstract_text") and not results.get("definition"):
            response += "Não encontrei informações detalhadas, mas você pode tentar pesquisar diretamente no Google ou DuckDuckGo! 😊"
        
        return response


# Instância global da IA
ia_brain = IABrain()
