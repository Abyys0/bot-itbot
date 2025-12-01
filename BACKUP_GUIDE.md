# 💾 Sistema de Backup do Discord

Sistema completo para fazer backup e restaurar toda a estrutura do seu servidor Discord.

## 🎯 Funcionalidades

O sistema faz backup completo de:
- ✅ **Cargos** (nomes, cores, permissões, posições)
- ✅ **Categorias** (nomes, posições, permissões)
- ✅ **Canais de Texto** (nomes, tópicos, slowmode, NSFW, permissões)
- ✅ **Canais de Voz** (nomes, bitrate, limite de usuários, permissões)
- ✅ **Emojis** (nomes, IDs, URLs)
- ✅ **Configurações do Servidor** (nome, ícone, banner, descrição, etc)

## 📝 Comandos Disponíveis

### 1. Criar Backup
```
!backup_loja
```
Cria um backup completo do servidor. O arquivo será salvo em `backups/` com timestamp.

**Exemplo de saída:**
- Arquivo: `backup_MeuServidor_20250101_120000.json`
- Estatísticas completas do que foi salvo

### 2. Listar Backups
```
!listar_backups
```
Mostra todos os backups disponíveis com informações detalhadas.

### 3. Restaurar Backup
```
!restaurar_backup <nome_arquivo> confirmar
```
Restaura um backup específico. **Requer confirmação!**

**Exemplo:**
```
!restaurar_backup backup_MeuServidor_20250101_120000.json confirmar
```

⚠️ **ATENÇÃO:** A restauração criará novos canais e cargos baseados no backup.

### 4. Deletar Backup
```
!deletar_backup <nome_arquivo>
```
Remove um backup do sistema.

### 5. Ajuda
```
!ajuda_backup
```
Mostra o guia completo do sistema de backup.

## 🔐 Permissões

- Todos os comandos requerem permissão de **Administrador**
- Apenas membros com essa permissão podem criar, restaurar ou deletar backups

## 💡 Casos de Uso

### Cenário 1: Antes de Reorganizar o Servidor
```bash
# 1. Criar backup
!backup_loja

# 2. Fazer as mudanças no servidor
# ... reorganizar canais, categorias, etc ...

# 3. Se não gostar, restaurar
!listar_backups
!restaurar_backup backup_MeuServidor_20250101_120000.json confirmar
```

### Cenário 2: Backup Regular
```bash
# Criar backup diário/semanal
!backup_loja

# Manter apenas os 5 backups mais recentes
!listar_backups
!deletar_backup <backup_antigo>
```

### Cenário 3: Recuperação de Desastre
```bash
# Se algo der errado, restaure rapidamente
!listar_backups
!restaurar_backup <backup_mais_recente> confirmar
```

## 📊 Estrutura do Backup

Os backups são salvos em formato JSON com a seguinte estrutura:

```json
{
  "backup_info": {
    "guild_name": "Nome do Servidor",
    "guild_id": 123456789,
    "created_at": "2025-01-01T12:00:00",
    "member_count": 100
  },
  "roles": [...],
  "categories": [...],
  "channels": [...],
  "emojis": [...],
  "guild_settings": {...}
}
```

## ⚠️ Limitações

- **Não faz backup de:** Mensagens, histórico de chat, membros do servidor
- **Não restaura:** Integrações, webhooks, bots adicionados
- **Permissões:** Permissões são restauradas apenas para cargos, não para usuários individuais
- **Emojis:** Os emojis são catalogados mas precisariam ser re-upload manualmente

## 🛡️ Segurança

- Backups são salvos **localmente** no servidor onde o bot está rodando
- Não são enviados para serviços externos
- Apenas administradores têm acesso aos comandos
- Logs completos de todas as operações

## 📁 Localização dos Backups

Os backups são salvos em:
```
Bot-ibot/backups/
```

Cada backup tem um nome único com timestamp:
```
backup_NomeDoServidor_YYYYMMDD_HHMMSS.json
```

## 🔄 Processo de Restauração

O processo de restauração segue esta ordem:
1. ✅ Restaura cargos (mantém hierarquia)
2. ✅ Restaura categorias
3. ✅ Restaura canais (associa às categorias corretas)
4. ✅ Aplica permissões

**Importante:** A restauração NÃO deleta itens existentes por padrão, apenas adiciona os que estão no backup.

## 📞 Suporte

Se tiver problemas:
1. Verifique os logs do bot
2. Use `!ajuda_backup` para ver o guia
3. Certifique-se de ter permissão de Administrador
4. Verifique se o bot tem permissões suficientes no servidor

## 🎯 Boas Práticas

1. **Faça backup antes de mudanças grandes**
2. **Mantenha vários backups** (antes e depois de mudanças)
3. **Teste a restauração** em um servidor de teste primeiro
4. **Delete backups antigos** regularmente para economizar espaço
5. **Documente as mudanças** que você faz após cada backup

---

**Desenvolvido para iBot** - Sistema de Backup Automático v1.0
