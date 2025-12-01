# 🎫 iBot - Sistema Completo para Discord

Um bot de Discord completo para gerenciar tickets de suporte, vendas de contas, anúncios e backup do servidor.

## 📋 Funcionalidades

### 🎫 Sistema de Tickets
✅ Usuários podem criar tickets com um clique
✅ Privacidade total - Apenas criador e staff podem ver o ticket
✅ Permissões por cargo - Apenas staff pode fechar tickets
✅ Logging completo - Todos os eventos são registrados
✅ Botões interativos - Interface amigável
✅ Canais de voz para chamadas no ticket
✅ Sistema de adicionar membros aos tickets

### 🎮 Sistema de Vendas de Contas
✅ Adicionar contas através do painel web
✅ Anúncios automáticos no Discord com embeds bonitos
✅ Botão "Comprar Conta" que abre ticket automaticamente
✅ Gerenciamento de disponibilidade (marcar como vendido)
✅ Remoção de contas do sistema

### 📢 Sistema de Anúncios
✅ Enviar anúncios para canal específico via painel web
✅ Embeds profissionais e formatados
✅ Integração com o Discord em tempo real

### 💾 Sistema de Backup
✅ Backup completo do servidor (cargos, canais, categorias)
✅ Restauração com um comando
✅ Listagem de todos os backups disponíveis
✅ Sistema de segurança com confirmação
✅ Logs detalhados de todas as operações

### 🌐 Painel Web
✅ Interface web completa para gerenciar o bot
✅ Visualização de estatísticas em tempo real
✅ Criar e gerenciar tickets pelo navegador
✅ Adicionar contas para venda
✅ Enviar anúncios
✅ Design responsivo e moderno

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
TICKET_CATEGORY_ID=111222333
LOG_CHANNEL_ID=444555666
STAFF_ROLE_IDS=777888999,000111222
```

#### Como obter os IDs:

1. **GUILD_ID** (ID do Servidor):
   - Clique direito no nome do servidor → Copiar ID do Servidor

2. **TICKET_CHANNEL_ID** (Canal de Tickets):
   - Clique direito no canal → Copiar ID do Canal
   - Este é o canal onde os usuários verão o botão "Abrir Ticket"

3. **TICKET_CATEGORY_ID** (Categoria dos Tickets):
   - Clique direito na categoria → Copiar ID
   - Onde os canais de ticket serão criados

4. **LOG_CHANNEL_ID** (Canal de Logs):
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

O bot iniciará em duas portas:
- **Porta 8080**: Painel Web (http://localhost:8080)
- **Porta 5001**: API interna do bot

### Acessar o Painel Web

Abra seu navegador e acesse:
```
http://localhost:8080
```

### Fluxo de Usuário - Tickets

1. **Abrir Ticket**
   - Usuário clica no botão "🎫 Abrir Ticket" no canal de tickets
   - Um novo canal privado é criado (ex: `ticket-1`)
   - Só o criador e staff podem ver o canal

2. **Suporte**
   - Staff responde no canal do ticket
   - Conversas privadas e seguras
   - Botões para notificar equipe, adicionar membros, criar call

3. **Fechar Ticket**
   - Clique no botão "🔒 Fechar Ticket"
   - Digite o motivo do fechamento
   - Canal é deletado após 10 segundos

### Fluxo de Venda de Contas

1. **Adicionar Conta (Painel Web)**
   - Acesse a aba "🎮 Contas"
   - Preencha informações da conta
   - Clique em "Adicionar e Anunciar"

2. **Anúncio Automático**
   - Bot posta no canal de contas
   - Embed bonito com botão "Comprar Conta"

3. **Compra**
   - Usuário clica em "Comprar Conta"
   - Ticket é aberto automaticamente
   - Staff é notificado

### Sistema de Backup

1. **Criar Backup**
   ```
   !backup_loja
   ```

2. **Ver Backups**
   ```
   !listar_backups
   ```

3. **Restaurar**
   ```
   !restaurar_backup <arquivo> confirmar
   ```

4. **Ajuda**
   ```
   !ajuda_backup
   ```

📖 **Guia completo:** Veja [BACKUP_GUIDE.md](BACKUP_GUIDE.md)

## 📁 Estrutura de Arquivos

```
Bot-ibot/
├── bot.py                 # Bot principal
├── config.py             # Configurações
├── ticket_manager.py     # Gerenciador de tickets
├── backup_manager.py     # Sistema de backup
├── painel_api.py         # API do painel web
├── index.html            # Interface do painel
├── requirements.txt      # Dependências Python
├── .env                  # Variáveis de ambiente
├── README.md             # Este arquivo
├── BACKUP_GUIDE.md       # Guia de backups
├── tickets.json          # Dados dos tickets
├── accounts.json         # Contas para venda
└── backups/              # Backups do servidor
```

## 📊 Dados Armazenados

### tickets.json
```json
{
  "ticket_1": {
    "user_id": "123456789",
    "number": 1,
    "status": "open",
    "created_at": "2024-01-15T10:30:00",
    "channel_id": 987654321
  }
}
```

### accounts.json
```json
[
  {
    "id": "account_1",
    "title": "Conta Valorant Platina",
    "description": "Conta level 50 com skins raras",
    "price": "R$ 150,00",
    "image_url": "https://...",
    "available": true,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

## 🔧 Comandos

### Comandos de Ticket
- `!ticketinfo` - Informações do sistema de tickets

### Comandos de Backup (Apenas Administradores)
- `!backup_loja` - Cria backup completo do servidor
- `!listar_backups` - Lista todos os backups
- `!restaurar_backup <arquivo> confirmar` - Restaura um backup
- `!deletar_backup <arquivo>` - Remove um backup
- `!ajuda_backup` - Guia completo do sistema

### Comando de Loja (Apenas Administradores)
- `!nova_loja CONFIRMAR` - Cria loja profissional do zero (DESTRUTIVO!)
  - ⚠️ Apaga todos os canais e categorias
  - ✅ Mantém todos os cargos
  - ✅ Cria estrutura profissional automática
  - 📖 **Guia completo:** [NOVA_LOJA_GUIDE.md](NOVA_LOJA_GUIDE.md)

## 🌐 Painel Web - Funcionalidades

### Aba Overview
- Estatísticas em tempo real
- Total de tickets
- Tickets abertos/fechados

### Aba Tickets
- Visualizar todos os tickets
- Notificar equipe
- Adicionar membros
- Fechar tickets

### Aba Criar Ticket
- Criar tickets pelo painel
- Especificar usuário e motivo

### Aba Anúncios
- Enviar anúncios no Discord
- Mensagens formatadas

### Aba Contas
- Adicionar contas para venda
- Gerenciar disponibilidade
- Remover contas

### Aba Funções
- Resumo de todas as funcionalidades

## 🛡️ Recursos de Segurança

✅ **Permissões Restritas**
- Canal privado do ticket
- Apenas criador e staff têm acesso
- Seleção explícita de permissões por membro

✅ **Validações**
- Previne múltiplos tickets do mesmo usuário
- Verifica permissão antes de fechar
- Logging de todas as ações

✅ **Backups Seguros**
- Apenas administradores podem criar/restaurar
- Confirmação obrigatória para restauração
- Logs completos de operações

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
