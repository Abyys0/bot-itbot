# Sistema de IA do iBot

## 📁 Estrutura

```
ia_system/
├── ia_brain.py       # Cérebro principal da IA
├── personality.json  # Personalidade configurável
├── memory.json       # Memória de conversas
└── README.md         # Este arquivo
```

## 🤖 Funcionalidades

### 1. **Conversação Natural**
- Entende contexto das conversas
- Mantém histórico de interações
- Personalidade configurável

### 2. **Análise de Intenção**
Detecta automaticamente:
- ✅ Perguntas
- ✅ Saudações
- ✅ Despedidas
- ✅ Agradecimentos
- ✅ Solicitações de busca
- ✅ Conversa casual

### 3. **Busca na Internet**
- Pesquisa em tempo real usando DuckDuckGo API
- Retorna resumos, definições e links
- Tópicos relacionados

### 4. **Memória**
- Salva histórico de conversas
- Lembra de usuários anteriores
- Mantém contexto das últimas 10 mensagens

## 🎯 Como Usar

### No Discord:
Basta mencionar o bot ou conversar no canal configurado!

**Exemplos:**
```
iBot, quem é você?
iBot, pesquise sobre FiveM
O que é Discord?
Busque informações sobre Python
```

### Personalização:

Edite `personality.json` para mudar:
- Nome da IA
- Características
- Áreas de conhecimento
- Tom de conversa

## 🔧 Configuração

No arquivo `bot.py`, a IA é ativada automaticamente quando o bot detecta mensagens que não são comandos.

## 📊 Dados Salvos

- **memory.json**: Histórico de interações com usuários
- **personality.json**: Configuração da personalidade

## 🌐 API Usada

- **DuckDuckGo Instant Answer API** (gratuita, sem necessidade de chave)

## 🚀 Próximas Melhorias

- [ ] Integração com mais APIs de busca
- [ ] Aprendizado com base em feedbacks
- [ ] Comandos personalizados por usuário
- [ ] Análise de sentimentos
- [ ] Respostas com imagens/GIFs
