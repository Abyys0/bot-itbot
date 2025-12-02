# 💳 Sistema de Pagamento PIX - Guia Completo

Sistema automático de pagamento via PIX integrado ao bot iBot.

## 🚀 Como Funciona

### Para Clientes
1. Cliente clica em **"🛒 Comprar Conta"** no anúncio
2. Ticket é criado automaticamente
3. Sistema gera **código PIX copia e cola**
4. Cliente copia a chave PIX
5. Realiza o pagamento no app bancário
6. Clica em **"✅ Já Paguei"**
7. Staff recebe notificação
8. Staff confirma pagamento
9. Cliente recebe a conta

### Para Staff
1. Recebe notificação quando cliente paga
2. Verifica o pagamento no banco
3. Usa comando `!confirmar_pix <ID>` para confirmar
4. Entrega a conta ao cliente

---

## ⚙️ Configuração Inicial

### 1. Configurar Chave PIX

```bash
!config_pix <sua_chave_pix> <seu_nome>
```

**Exemplos:**
```bash
# Com CPF
!config_pix 12345678900 João Silva

# Com E-mail
!config_pix contato@minhaloja.com Loja Roblox

# Com Telefone
!config_pix +5511999999999 Maria Santos

# Com Chave Aleatória
!config_pix abc123def456 Vendedor Pro
```

### 2. Verificar Configuração

```bash
!config_pix
```

Mostra a configuração atual (chave mascarada por segurança).

---

## 📋 Comandos Disponíveis

### Para Administradores

#### Configurar PIX
```bash
!config_pix <chave_pix> <nome_beneficiario>
```
Configura ou atualiza a chave PIX para pagamentos.

#### Confirmar Pagamento
```bash
!confirmar_pix <payment_id>
```
Confirma que o pagamento foi recebido.

**Exemplo:**
```bash
!confirmar_pix a1b2c3d4
```

#### Listar Pagamentos
```bash
!listar_pagamentos [status]
```

**Opções de status:**
- `pending` - Pagamentos pendentes (padrão)
- `confirmed` - Pagamentos confirmados
- `all` - Todos os pagamentos

**Exemplos:**
```bash
!listar_pagamentos              # Lista pendentes
!listar_pagamentos pending      # Lista pendentes
!listar_pagamentos confirmed    # Lista confirmados
!listar_pagamentos all          # Lista todos
```

---

## 🔄 Fluxo Completo de Venda

### 1️⃣ Cliente Demonstra Interesse
- Vê anúncio de conta no Discord
- Clica no botão **"🛒 Comprar Conta"**

### 2️⃣ Sistema Cria Ticket
- Ticket privado é aberto automaticamente
- Cliente e staff têm acesso

### 3️⃣ Sistema Gera Pagamento PIX
```
💳 Pagamento via PIX

💰 Valor: R$ 50,00
🆔 ID do Pagamento: a1b2c3d4

📱 Chave PIX (Copia e Cola)
12345678900

📋 Como pagar:
1️⃣ Copie a chave PIX acima
2️⃣ Abra seu app bancário
3️⃣ Vá em PIX → Pagar
4️⃣ Cole a chave
5️⃣ Confira o valor e pague
6️⃣ Clique em '✅ Já Paguei' abaixo
```

### 4️⃣ Cliente Realiza Pagamento
- Copia a chave PIX
- Paga no app bancário
- Clica em **"✅ Já Paguei"**

### 5️⃣ Staff Recebe Notificação
```
💰 Pagamento Realizado - Aguardando Confirmação

@Staff
João Silva informou que realizou o pagamento!

💳 ID do Pagamento: a1b2c3d4
💰 Valor: R$ 50,00
⏰ Status: ⏳ Aguardando confirmação da equipe
```

### 6️⃣ Staff Verifica e Confirma
```bash
!confirmar_pix a1b2c3d4
```

### 7️⃣ Cliente Recebe Confirmação
- Mensagem no ticket
- DM automática (se possível)
- Staff entrega a conta

---

## 📊 Painel Web - API Endpoints

### GET `/api/pix/config`
Retorna configuração atual do PIX.

**Resposta:**
```json
{
  "success": true,
  "config": {
    "pix_key": "1234****8900",
    "pix_name": "João Silva",
    "pix_city": "SAO PAULO",
    "enabled": true
  }
}
```

### POST `/api/pix/config`
Atualiza configuração do PIX.

**Body:**
```json
{
  "pix_key": "12345678900",
  "pix_name": "João Silva",
  "pix_city": "SAO PAULO"
}
```

### GET `/api/pix/payments`
Lista todos os pagamentos.

### GET `/api/pix/payments/pending`
Lista apenas pagamentos pendentes.

### POST `/api/pix/payment/<payment_id>/confirm`
Confirma um pagamento.

**Body:**
```json
{
  "staff_id": "123456789"
}
```

### POST `/api/pix/payment/<payment_id>/cancel`
Cancela um pagamento.

---

## 💾 Arquivos de Dados

### `pix_config.json`
Armazena configuração do PIX.

```json
{
  "pix_key": "12345678900",
  "pix_name": "João Silva",
  "pix_city": "SAO PAULO",
  "enabled": true
}
```

### `payments.json`
Armazena todos os pagamentos.

```json
{
  "a1b2c3d4": {
    "payment_id": "a1b2c3d4",
    "user_id": "123456789",
    "account_id": "5",
    "account_title": "Conta Roblox Level 150",
    "amount": 50.00,
    "pix_key": "12345678900",
    "status": "pending",
    "created_at": "2025-12-02T10:30:00",
    "confirmed_at": null,
    "confirmed_by": null
  }
}
```

**Status possíveis:**
- `pending` - Aguardando pagamento
- `confirmed` - Pagamento confirmado
- `cancelled` - Pagamento cancelado

---

## 🔒 Segurança

### ✅ Boas Práticas

1. **Nunca compartilhe** o arquivo `pix_config.json`
2. **Adicione ao .gitignore:**
   ```
   pix_config.json
   payments.json
   ```
3. **Verifique pagamentos** no app bancário antes de confirmar
4. **Mantenha logs** de todas as transações
5. **Use comandos apenas** em canais privados de staff

### ⚠️ Avisos Importantes

- Este sistema é **semi-automático** - requer confirmação manual do staff
- **Não integra** diretamente com APIs bancárias
- Staff deve **verificar** cada pagamento antes de confirmar
- **Não há estorno automático** - gerencie cancelamentos manualmente

---

## 🐛 Solução de Problemas

### PIX não está gerando
✅ **Solução:** Configure o PIX com `!config_pix`

### Cliente não vê chave PIX
✅ **Solução:** Verifique se o PIX está configurado corretamente

### Pagamento não confirma
✅ **Solução:** Use o comando `!confirmar_pix <ID>` manualmente

### Lista de pagamentos vazia
✅ **Solução:** Nenhum pagamento foi criado ainda. Teste criando uma compra.

---

## 📈 Próximas Melhorias (Futuro)

- ⏳ Integração com APIs de pagamento (Mercado Pago, PagSeguro)
- ⏳ QR Code PIX automático
- ⏳ Webhook de confirmação automática
- ⏳ Relatórios financeiros detalhados
- ⏳ Sistema de reembolso
- ⏳ Múltiplas chaves PIX

---

## 📞 Suporte

Para dúvidas sobre o sistema PIX:
1. Verifique se configurou corretamente com `!config_pix`
2. Teste o fluxo completo com uma conta
3. Consulte os logs do bot para erros

---

## 📄 Licença

Este sistema faz parte do bot iBot e é fornecido como está para uso pessoal e educacional.
