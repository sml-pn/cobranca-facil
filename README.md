# 🚗 Cobrança Fácil

Sistema inteligente de cobrança e gestão de parcelas para lojistas e prestadores de serviços. Gerencia clientes, calcula parcelas automaticamente, exibe um dashboard financeiro e envia **lembretes automáticos em três estágios** via WhatsApp (5 dias antes, 1 dia antes e no dia do vencimento).

**💰 Monetização:** Ideal para venda como SaaS (assinatura mensal), white-label ou sistema exclusivo para um cliente.

---

## ✨ Funcionalidades

### 🧾 Gestão de Clientes
- Cadastro completo: nome, telefone, veículo, valor total, quantidade de parcelas e dia de vencimento.
- Cálculo automático das parcelas com base no dia fixo escolhido.
- Edição de dados do cliente.

### 📊 Dashboard Profissional
- Cards de resumo: **Vencidas**, **Vence Hoje**, **Esta Semana**, **Total a Receber**.
- Lista de **próximas parcelas** de cada cliente (apenas a parcela mais urgente).
- Filtros por status e ordenação por data, nome ou valor.
- Interface 100% responsiva (mobile e desktop).

### 💬 Lembretes Automáticos via WhatsApp
- Envio **automático** de mensagens para os clientes em **três momentos**:
  - **5 dias antes** do vencimento (lembrete amigável).
  - **1 dia antes** do vencimento (alerta de urgência).
  - **No dia do vencimento** (cobrança direta).
- Utiliza a API gratuita [CallMeBot](https://www.callmebot.com/).

### 🔐 Autenticação e Segurança
- Tela de login com proteção de rotas.
- Recuperação de senha via **link enviado por WhatsApp**.
- Senha armazenada com hash SHA-256.

### 📱 PWA (Progressive Web App)
- Instalável como aplicativo no celular e computador.
- Ícone personalizado e tela de splash.
- Service Worker para funcionamento offline básico e cache.

### ⚙️ Deploy e Monitoramento
- Hospedagem gratuita no **Render**.
- Banco de dados PostgreSQL gratuito no **Neon**.
- **cron-job.org** configurado para pingar o serviço e evitar hibernação.
- Retentativas automáticas de conexão com o banco de dados.

---

## 🛠️ Tecnologias Utilizadas (Todas Gratuitas)

| Camada | Ferramenta | Função |
|--------|------------|--------|
| Backend | Python 3 + Flask | Lógica do servidor e rotas |
| Banco de Dados | Neon (PostgreSQL) | Armazenamento na nuvem (5 GB grátis) |
| Hospedagem | Render | Servidor web gratuito |
| Mensagens | CallMeBot | API gratuita para WhatsApp |
| Monitoramento | cron-job.org | Pings para manter o Render ativo |
| Versionamento | Git + GitHub | Controle de versão e deploy automático |
| Frontend | HTML, CSS, Jinja2 | Interface responsiva |

---

## 📁 Estrutura do Projeto

```

cobranca-facil/
├── app.py                 # Código principal do Flask
├── requirements.txt       # Dependências Python
├── runtime.txt            # Versão do Python para o Render
├── Procfile               # Comando de inicialização
├── static/
│   ├── manifest.json      # Configuração do PWA
│   ├── sw.js              # Service Worker
│   └── icons/             # Ícones do app
└── templates/
├── base.html          # Layout padrão
├── index.html         # Dashboard
├── clientes.html      # Lista de clientes
├── novo_cliente.html  # Cadastro
├── editar_cliente.html
├── login.html
├── esqueci_senha.html
└── redefinir_senha.html

```

---

## 🔧 Guia de Instalação e Configuração

### 1. Pré-requisitos
Crie contas gratuitas nos seguintes serviços:

| Serviço | Link | Objetivo |
|---------|------|----------|
| GitHub | [github.com](https://github.com) | Armazenar o código |
| Neon | [neon.tech](https://neon.tech) | Banco de dados PostgreSQL |
| Render | [render.com](https://render.com) | Hospedagem |
| CallMeBot | [callmebot.com](https://www.callmebot.com/blog/free-api-whatsapp-messages/) | API do WhatsApp |
| cron-job.org | [cron-job.org](https://cron-job.org) | Ping para evitar hibernação |

### 2. Configuração do Banco de Dados (Neon)
1. Crie um projeto no Neon.
2. Copie a **Connection String** (formato `postgresql://...`).
3. Ela será usada como variável `DATABASE_URL` no Render.

### 3. Configuração do CallMeBot
1. Adicione o número `+34 644 71 81 99` aos seus contatos.
2. Envie a mensagem `I allow callmebot to send me messages` por WhatsApp.
3. Guarde a **API Key** recebida.

### 4. Deploy no Render
1. Faça um fork ou clone deste repositório no GitHub.
2. No Render, crie um novo **Web Service** conectado ao repositório.
3. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
4. Adicione as **variáveis de ambiente**:
   - `DATABASE_URL`: string de conexão do Neon.
   - `SECRET_KEY`: uma chave secreta (gere uma aleatória).
   - `CALLMEBOT_API_KEY`: sua API Key.
   - `CALLMEBOT_PHONE_NUMBER`: seu número com código do país (ex: `5511999999999`).
5. Clique em **Create Web Service**.

### 5. Manter o Render Ativo (cron-job.org)
1. Crie um cron job no cron-job.org.
2. URL: `https://seu-app.onrender.com/ping`
3. Intervalo: a cada **10 minutos**.

---

## 🧑‍🤝‍🧑 Guia para Configurar um Novo Cliente (SaaS)

Se você for vender o sistema para vários lojistas, repita os passos abaixo para cada cliente:

### 3.1. Criação de Contas para o Cliente
Cada cliente precisará de contas próprias (ou você gerencia para ele):
- **GitHub**: para clonar o repositório.
- **Neon**: para o banco de dados.
- **Render**: para a hospedagem.
- **CallMeBot**: para o envio de WhatsApp (usando o número do cliente).
- **cron-job.org**: para o ping.

### 3.2. Configuração do Ambiente
1. Clone o repositório para o cliente (ou use um fork).
2. Crie um novo Web Service no Render apontando para o repositório do cliente.
3. Adicione as variáveis de ambiente específicas do cliente.
4. Após o deploy, o cliente acessa `https://[nome-do-cliente].onrender.com`.

### 3.3. Personalização (Opcional)
- Substitua os ícones em `static/icons/`.
- Altere as cores no `base.html`.
- Modifique o título e o nome do sistema.

---

## 🧪 Testando o Sistema

1. Acesse a URL do Render e faça login com:
   - **Usuário:** `admin`
   - **Senha:** `admin123`
2. Cadastre um cliente com vencimento para **hoje + 5 dias**.
3. Aguarde o agendador diário (às 5h da manhã) ou force via rota `/forcar-lembretes` (se adicionada temporariamente).
4. Verifique se as mensagens de WhatsApp chegam nos momentos corretos.

---

## 💰 Modelos de Negócio

| Modelo | Descrição | Preço Sugerido |
|--------|-----------|----------------|
| **SaaS Mensal** | Hospedagem gerenciada por você, cada cliente paga mensalidade. | R$ 97/mês |
| **Venda Única** | Entrega do sistema configurado no servidor do cliente. | R$ 1.500 – R$ 3.000 |
| **White-Label** | Sistema personalizado com a marca do cliente. | Negociável |

---

## 📝 Personalizações Possíveis

- Texto das mensagens de WhatsApp (função `enviar_whatsapp_direto`).
- Prazos dos lembretes (parâmetros `days=5`, `days=1`, `days=0`).
- Cores e logo (CSS e ícones).
- Adicionar novos relatórios (PDF/Excel).

---

## 🧑‍💻 Autor

Desenvolvido por **Samuel Pena**  
📧 smlpnsz.pena@gmail.com  
🐙 GitHub: [sml-pn](https://github.com/sml-pn)

---

## 📄 Licença

Este projeto é open-source para fins educacionais. Para uso comercial, entre em contato.

---

**Feito com ❤️ usando apenas ferramentas gratuitas.**
```

---

