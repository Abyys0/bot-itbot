# 🏪 Comando: Nova Loja Profissional

## 🎯 Descrição

O comando `!nova_loja` cria uma estrutura completa e profissional de loja Roblox do zero, apagando todos os canais e categorias existentes (mantém os cargos) e criando uma nova organização otimizada para vendas e comunidade.

## ⚠️ AVISO IMPORTANTE

**ESTE COMANDO É DESTRUTIVO!**
- ❌ Apaga TODAS as categorias
- ❌ Apaga TODOS os canais (texto e voz)
- ✅ Mantém todos os cargos intactos
- ✅ Cria estrutura profissional automaticamente

## 📝 Como Usar

### 1. Faça um Backup Primeiro (OBRIGATÓRIO!)
```
!backup_loja
```

### 2. Execute o Comando
```
!nova_loja CONFIRMAR
```

### 3. Se Não Gostar, Restaure
```
!listar_backups
!restaurar_backup <arquivo> confirmar
```

## 🏗️ Estrutura Criada

### 📢 CATEGORIA: INFORMAÇÕES
Canal somente leitura para visitantes:
- **👋│boas-vindas** - Mensagem de boas-vindas profissional
- **📜│regras** - Regras formatadas e organizadas
- **📢│anúncios** - Para novidades e atualizações
- **ℹ️│informações** - Informações sobre a loja

### 🛒 CATEGORIA: LOJA
Canais de produtos (somente leitura):
- **🎮│contas-roblox** - Contas disponíveis com botão de compra
- **💎│robux** - Venda de Robux
- **🎫│passes-e-itens** - Game passes e itens
- **🔥│promoções** - Ofertas especiais

### 💰 CATEGORIA: ATENDIMENTO
Sistema de suporte:
- **📧│abrir-ticket** - Painel de tickets configurado automaticamente
- **⭐│avaliações** - Feedbacks de clientes
- **❓│dúvidas-frequentes** - FAQ completo

### 💬 CATEGORIA: COMUNIDADE
Interação com membros:
- **💭│chat-geral** - Chat livre
- **😂│memes** - Memes de Roblox
- **📸│mídia** - Screenshots e vídeos
- **🤝│parcerias** - Propostas de parceria
- **🎤│Conversa Geral** - Canal de voz
- **🎮│Jogando Roblox** - Canal de voz para jogar

### 🔧 CATEGORIA: STAFF (Privada)
Área administrativa:
- **📊│logs** - Logs do bot e servidor
- **🤖│comandos** - Comandos administrativos
- **⚙️│configuração** - Configurações

## 🎨 Painéis Automáticos

Os seguintes painéis são criados automaticamente:

### 1. Painel de Boas-Vindas
- Mensagem de boas-vindas elegante
- Links para canais importantes
- Informações sobre a loja

### 2. Painel de Regras
- 6 regras principais formatadas
- Explicação de punições
- Design profissional

### 3. Painel de Tickets
- Botão "Abrir Ticket" funcional
- Instruções claras
- Sistema já integrado

### 4. Painel de FAQ
- 6 perguntas frequentes
- Respostas completas
- Links úteis

### 5. Painel de Informações
- Sobre a loja
- Diferenciais
- Estatísticas
- Links importantes

### 6. Painel de Contas
- Instruções de compra
- Informações sobre garantia
- Descrição dos produtos

## 📊 Fluxo de Criação

```
Fase 1: Limpeza
├─ Deletar todos os canais de texto
├─ Deletar todos os canais de voz
└─ Deletar todas as categorias

Fase 2: Criação
├─ Criar 5 categorias
├─ Criar 17+ canais
└─ Configurar permissões

Fase 3: Painéis
├─ Enviar 6+ mensagens formatadas
├─ Configurar botões interativos
└─ Integrar sistema de tickets
```

## 💡 Exemplos de Uso

### Cenário 1: Primeira Configuração
```bash
# 1. Faça backup da estrutura atual
!backup_loja

# 2. Crie a nova loja
!nova_loja CONFIRMAR

# 3. Pronto! Agora configure os produtos
```

### Cenário 2: Não Gostei, Quero Voltar
```bash
# 1. Liste os backups
!listar_backups

# 2. Restaure o backup anterior
!restaurar_backup backup_MeuServidor_20250101_120000.json confirmar

# 3. Tudo voltou ao normal!
```

### Cenário 3: Atualizar a Loja
```bash
# 1. Backup da loja atual
!backup_loja

# 2. Criar nova versão
!nova_loja CONFIRMAR

# 3. Se preferir a antiga, restaure
!restaurar_backup <arquivo_anterior> confirmar
```

## ⚙️ Configurações Pós-Criação

### 1. Atualizar IDs no .env
```env
TICKET_CHANNEL_ID=<novo_id_do_canal_tickets>
LOG_CHANNEL_ID=<novo_id_do_canal_logs>
```

### 2. Configurar Cargos de Staff
- Dê permissões de acesso à categoria STAFF
- Configure cargos com cores diferentes
- Organize a hierarquia

### 3. Adicionar Produtos
- Acesse o painel web
- Vá na aba "Contas"
- Adicione suas contas Roblox

### 4. Personalizar Mensagens
- Edite os painéis conforme necessário
- Adicione informações específicas da sua loja
- Atualize estatísticas e links

## 🛡️ Segurança

### Permissões Necessárias
- ✅ Administrador (obrigatório)
- ✅ Bot precisa de permissões de:
  - Gerenciar canais
  - Gerenciar permissões
  - Enviar mensagens
  - Enviar embeds

### Proteções Implementadas
- ✅ Confirmação obrigatória antes de executar
- ✅ Aviso sobre backup recente
- ✅ Logs de todas as operações
- ✅ Validação de permissões

### Sistema de Rollback
Se algo der errado:
```bash
!restaurar_backup <arquivo> confirmar
```

## 🎯 Design Profissional

### Características:
- ✅ **Organização clara** - Categorias bem definidas
- ✅ **Emojis padronizados** - Visual atraente
- ✅ **Cores consistentes** - Embeds com cores apropriadas
- ✅ **Informações completas** - Todos os painéis bem explicados
- ✅ **Funcional** - Tickets e compras já funcionando
- ✅ **Escalável** - Fácil adicionar mais canais

### Otimizado para:
- 🎮 Vendas de contas Roblox
- 💎 Vendas de Robux
- 🎫 Vendas de passes e itens
- 💬 Comunidade ativa
- 📧 Suporte eficiente

## 📈 Resultados Esperados

Após criar a nova loja:
- ✅ Aparência mais profissional
- ✅ Melhor organização
- ✅ Facilidade de navegação
- ✅ Aumento de confiança dos clientes
- ✅ Sistema de tickets integrado
- ✅ Painéis informativos
- ✅ Área exclusiva para staff

## 🔧 Troubleshooting

### Problema: Bot sem permissões
**Solução:** Garanta que o bot tenha cargo com permissões administrativas

### Problema: Alguns canais não foram deletados
**Solução:** Verifique se há canais com permissões especiais bloqueando

### Problema: Painéis não aparecem
**Solução:** Verifique os logs do bot, pode haver erro de rate limit

### Problema: Quero voltar ao anterior
**Solução:** Use `!restaurar_backup <arquivo> confirmar`

## 📞 Suporte

Se tiver problemas:
1. Verifique os logs: canal `📊│logs`
2. Use `!ajuda_backup` para ver comandos
3. Restaure o backup se necessário
4. Verifique as permissões do bot

---

**🎉 Transforme seu Discord em uma Loja Profissional com um Comando!**
