# Bot iBot - Deploy no Render

## 🚀 Como fazer deploy no Render (sem dormir)

### Passo 1: Preparar o Repositório no GitHub

1. Crie um repositório no GitHub
2. **IMPORTANTE**: Crie um arquivo `.gitignore`:
   ```
   .env
   tickets.json
   __pycache__/
   *.pyc
   ```

3. Faça upload dos arquivos (exceto `.env`):
   ```bash
   git init
   git add .
   git commit -m "Bot iBot - Sistema de Tickets"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
   git push -u origin main
   ```

### Passo 2: Criar Conta no Render

1. Acesse [render.com](https://render.com)
2. Faça login com GitHub

### Passo 3: Criar o Web Service

1. Clique em **"New +"** → **"Web Service"**
2. Conecte seu repositório do GitHub
3. Configure:
   - **Name**: `ibot-discord`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`

### Passo 4: Adicionar Variáveis de Ambiente

Na seção **Environment Variables**, adicione:

```
BOT_TOKEN=seu_token_aqui
GUILD_ID=1443022206136225857
TICKET_CHANNEL_ID=1443028722113450014
TICKET_CATEGORY_ID=1443027159638609941
LOG_CHANNEL_ID=1443371301531160779
STAFF_ROLE_IDS=1443037136969535641,1443037137980231774
```

### Passo 5: Evitar que o Bot Durma (GRÁTIS) ⚡

O Render free hiberna após 15 minutos sem requisições. Para evitar:

#### Opção A: UptimeRobot (Recomendado)
1. Acesse [uptimerobot.com](https://uptimerobot.com)
2. Crie conta grátis
3. Adicione um **HTTP(s) Monitor**
4. URL: `https://seu-bot.onrender.com` (URL do Render)
5. Interval: **5 minutos**

Mas isso só funciona se o bot tiver endpoint HTTP. Vou adicionar isso ao código!

#### Opção B: Cron-Job.org
1. Acesse [cron-job.org](https://cron-job.org)
2. Crie conta grátis
3. Create Cronjob
4. URL: `https://seu-bot.onrender.com/health`
5. Interval: **5 minutos**

### Passo 6: Deploy

Clique em **"Create Web Service"** e aguarde o deploy!

---

## ⚠️ ATENÇÃO

Se você não quiser complicação e garantir que o bot NUNCA durma, considere:

1. **Railway** - Créditos mensais grátis
2. **Oracle Cloud Free Tier** - VPS grátis para sempre
3. **Render Paid** - $7/mês, mais confiável

---

## 📝 Precisa de Endpoint HTTP?

Para o UptimeRobot funcionar, o bot precisa de um endpoint HTTP. Quer que eu adicione isso ao código?
