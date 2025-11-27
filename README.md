# 🎫 iBot - Sistema de Tickets para Discord

Um bot de Discord completo para gerenciar tickets de suporte com privacidade, permissões de cargo e logging.

## 📋 Funcionalidades

✅ **Sistema de Tickets** - Usuários podem criar tickets com um clique
✅ **Privacidade Total** - Apenas criador e staff podem ver o ticket
✅ **Permissões por Cargo** - Apenas staff com cargo específico pode fechar tickets
✅ **Logging Completo** - Todos os eventos são registrados em um canal dedicado
✅ **Botões Interativos** - Interface amigável com discord.ui buttons
✅ **Prevenção de Spam** - Usuários não podem ter múltiplos tickets abertos

## 🚀 Instalação

### 1. Pré-requisitos
- Python 3.8+
- Conta de Developer no Discord
- Bot criado no [Discord Developer Portal](https://discord.com/developers/applications)

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```env
BOT_TOKEN=seu_token_do_discord_aqui
GUILD_ID=123456789
TICKET_CHANNEL_ID=987654321
LOG_CHANNEL_ID=111222333
STAFF_ROLE_ID=444555666
```

#### Como obter os IDs:

1. **GUILD_ID** (ID do Servidor):
   - Clique direito no nome do servidor → Copiar ID do Servidor

2. **TICKET_CHANNEL_ID** (Canal de Tickets):
   - Clique direito no canal → Copiar ID do Canal
   - Este é o canal onde os usuários verão o botão "Abrir Ticket"

3. **LOG_CHANNEL_ID** (Canal de Logs):
   - Clique direito no canal → Copiar ID do Canal
   - Este é o canal onde os logs serão enviados

4. **STAFF_ROLE_ID** (Cargo de Staff):
   - Clique direito no cargo → Copiar ID do Cargo
   - Pessoas com este cargo poderão fechar tickets

### 4. Permissões do Bot

Certifique-se de que o bot tem as seguintes permissões:
- ✅ Gerenciar Canais
- ✅ Enviar Mensagens
- ✅ Gerenciar Mensagens
- ✅ Ler Histórico de Mensagens
- ✅ Gerenciar Funções
- ✅ Gerenciar Permissões do Canal

## 🎯 Como Usar

### Iniciar o Bot

```bash
python bot.py
```

### Fluxo de Usuário

1. **Abrir Ticket**
   - Usuário clica no botão "🎫 Abrir Ticket" no canal de tickets
   - Um novo canal privado é criado (ex: `ticket-1`)
   - Só o criador e staff podem ver o canal

2. **Suporte**
   - Staff responde no canal do ticket
   - Conversas privadas e seguras

3. **Fechar Ticket**
   - Clique no botão "🔒 Fechar Ticket"
   - Pode ser fechado pelo criador OU staff

## 📁 Estrutura de Arquivos

```
Bot-ibot/
├── bot.py                 # Bot principal
├── config.py             # Configurações
├── ticket_manager.py     # Gerenciador de tickets
├── requirements.txt      # Dependências Python
├── .env                  # Variáveis de ambiente
├── .env.example          # Exemplo de .env
├── README.md             # Este arquivo
└── tickets.json          # Arquivo de dados dos tickets (gerado automaticamente)
```

## 📊 Dados Armazenados

O bot salva automaticamente as informações dos tickets em `tickets.json`:

```json
{
  "ticket_1": {
    "user_id": 123456789,
    "ticket_number": 1,
    "status": "open",
    "created_at": "2024-01-15T10:30:00",
    "channel_id": 987654321
  }
}
```

## 🔧 Comandos

### `!ticketinfo`
Mostra informações sobre o sistema de tickets:
- Quantidade de tickets abertos
- Total de tickets
- Canais configurados

## 🛡️ Recursos de Segurança

✅ **Permissões Restritas**
- Canal privado do ticket
- Apenas criador e staff têm acesso
- Seleção explícita de permissões por membro

✅ **Validações**
- Previne múltiplos tickets do mesmo usuário
- Verifica permissão antes de fechar
- Logging de todas as ações

✅ **Auditoria**
- Todos os eventos registrados em log
- Data/hora de cada ação
- Identificação de quem realizou cada ação

## 🐛 Troubleshooting

### Bot não conecta
- Verifique se o `BOT_TOKEN` está correto
- Certifique-se de que o bot está convidado para o servidor

### Erro ao criar tickets
- Verifique as permissões do bot (Gerenciar Canais)
- Confirme que os IDs no `.env` estão corretos

### Botões não funcionam
- Reinicie o bot
- Verifique se as intents estão habilitadas no Developer Portal

## 📝 Logs

O bot registra todas as ações:
- ✅ Tickets criados
- 🔒 Tickets fechados
- ❌ Erros e exceções

## 🤝 Suporte

Para configuração adicional ou dúvidas, consulte a documentação do [discord.py](https://discordpy.readthedocs.io/).

## 📄 Licença

Este projeto é fornecido como está para uso educacional e pessoal.
