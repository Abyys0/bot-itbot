# Guia Rápido de Configuração - iBot

## 1️⃣ Obter Token do Bot

1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em "New Application"
3. Dê um nome (ex: "iBot")
4. Vá até "Bot" → "Add Bot"
5. Copie o token em "TOKEN"
6. Cole no arquivo `.env` como `BOT_TOKEN=seu_token_aqui`

## 2️⃣ Obter IDs do Servidor

### GUILD_ID (ID do Servidor)
1. Clique direito no nome do servidor
2. Selecione "Copiar ID do Servidor"
3. Cole no `.env`

### TICKET_CHANNEL_ID (Canal de Tickets)
1. Crie um novo canal chamado `#tickets` (ou outro nome)
2. Clique direito nele → "Copiar ID do Canal"
3. Cole no `.env`

### LOG_CHANNEL_ID (Canal de Logs)
1. Crie um novo canal chamado `#logs-tickets`
2. Clique direito nele → "Copiar ID do Canal"
3. Cole no `.env`

### STAFF_ROLE_ID (Cargo de Staff)
1. Crie um novo cargo chamado `Staff` (ou outro nome)
2. Clique direito nele → "Copiar ID do Cargo"
3. Cole no `.env`

## 3️⃣ Configurar Permissões do Bot

1. Vá para [Developer Portal](https://discord.com/developers/applications)
2. Selecione sua aplicação "iBot"
3. Vá em "Bot" → "Scopes": selecione `bot`
4. Em "Permissions", selecione:
   - ✅ Send Messages
   - ✅ Manage Channels
   - ✅ Read Messages/View Channels
   - ✅ Manage Roles
   - ✅ Manage Messages

5. Copie a URL gerada em "Scopes"
6. Abra em seu navegador para convidar o bot ao servidor

## 4️⃣ Instalar Dependências

```bash
pip install -r requirements.txt
```

## 5️⃣ Executar o Bot

```bash
python bot.py
```

Você verá:
```
🚀 Iniciando bot iBot...
Bot conectado como iBot#1234
Comandos sincronizados!
Mensagem de ticket enviada com sucesso
```

## ✅ Tudo Pronto!

O bot está rodando! Agora:
- Vá para o canal `#tickets`
- Clique no botão "🎫 Abrir Ticket"
- Um novo canal privado será criado
- Teste o sistema!

## 📌 Notas Importantes

- O arquivo `.env` contém informações sensíveis (seu token), **NUNCA** o compartilhe
- Adicione `.env` ao `.gitignore` se usar Git
- O arquivo `tickets.json` armazena informações dos tickets automaticamente
- Reinicie o bot se fizer mudanças no código
