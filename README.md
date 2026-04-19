# 🚗 Cobrança Fácil

Sistema inteligente de cobrança e gestão de parcelas para lojistas e prestadores de serviços. Gerencia clientes, calcula parcelas automaticamente, exibe um dashboard financeiro e oferece **notificações PWA nativas** e **links diretos para WhatsApp** com mensagens prontas.

**💰 Monetização:** Ideal para venda como SaaS (assinatura mensal), white-label ou sistema exclusivo para um cliente.

---

## ✨ Funcionalidades

### 🧾 Gestão de Clientes
- Cadastro completo: nome, telefone, veículo, valor total, quantidade de parcelas e dia de vencimento.
- Cálculo automático das parcelas com base no dia fixo escolhido.
- Edição e exclusão segura de clientes.
- Visualização detalhada do histórico de parcelas de cada cliente.

### 📊 Dashboard Profissional
- Cards de resumo: **Vencidas**, **Vence Hoje**, **Esta Semana**, **Total a Receber**.
- Lista da **próxima parcela pendente** de cada cliente.
- Filtros por status e ordenação por data, nome ou valor.
- Interface 100% responsiva com **menu hambúrguer animado** para dispositivos móveis.

### 💬 Integração com WhatsApp
- Botão em cada parcela que abre o WhatsApp com uma **mensagem personalizada pronta** (sem necessidade de salvar contato).
- Texto adaptável: "hoje", "amanhã", "em X dias" ou "vencida há Y dias".

### 🔔 Notificações PWA (Progressive Web App)
- Notificações nativas no dispositivo para parcelas:
  - 5 dias antes do vencimento
  - 1 dia antes do vencimento
  - No dia do vencimento
  - Após o vencimento
- Ações na notificação: **"Já Paguei"** (marca como paga) e **"WhatsApp"** (abre conversa pronta).

### 🔐 Autenticação e Segurança
- Tela de login com proteção de rotas.
- Recuperação de senha via **código OTP de 6 dígitos enviado por WhatsApp**.
- Senhas armazenadas com **hash seguro (werkzeug)**.
- Proteção contra **CSRF** em todos os formulários sensíveis.

### 📱 PWA (Progressive Web App)
- Instalável como aplicativo no celular e computador (Android, iOS, Windows, macOS).
- Ícone personalizado e tela de splash.
- Service Worker para cache e funcionamento offline básico.
- Botão inteligente de instalação com guia visual para iOS.

### ⚙️ Deploy e Monitoramento
- Hospedagem gratuita no **Render**.
- Banco de dados PostgreSQL gratuito no **Neon** (5 GB).
- **cron-job.org** configurado para pingar o serviço a cada 10 minutos e evitar hibernação.
- Retentativas automáticas de conexão com o banco de dados.

---

## 🛠️ Ferramentas Utilizadas (100% Gratuitas)

| Ferramenta | Função no Projeto |
|------------|-------------------|
| **Python 3** | Linguagem de programação principal |
| **Flask** | Framework web para backend |
| **Flask-SQLAlchemy** | ORM para comunicação com banco de dados |
| **Jinja2** | Template engine (renderização HTML) |
| **Werkzeug** | Hashing seguro de senhas |
| **itsdangerous** | Geração de tokens seguros (recuperação de senha) |
| **APScheduler** | Agendador de tarefas (verificação diária de parcelas) |
| **pytz** | Manipulação de fuso horário (America/Sao_Paulo) |
| **requests** | Chamadas HTTP (integração com CallMeBot) |
| **secrets** | Geração de tokens CSRF aleatórios |
| **Neon** | Banco de dados PostgreSQL serverless (5 GB gratuitos) |
| **Render** | Hospedagem da aplicação Flask (Web Service gratuito) |
| **cron-job.org** | Serviço de ping automático para evitar hibernação do Render |
| **CallMeBot** | API gratuita para envio de mensagens WhatsApp (recuperação de senha OTP) |
| **Service Worker** | Cache, notificações PWA e instalação offline |
| **Manifest (manifest.json)** | Configuração do PWA (ícones, nome, standalone) |
| **Font Awesome** | Biblioteca de ícones (gratuita) |
| **Git** | Controle de versão |
| **GitHub** | Repositório remoto e deploy automático via Render |
| **Termux** | Ambiente de desenvolvimento no celular Android |
| **nano** | Editor de texto no terminal |

---

## 📁 Estrutura do Projeto

```

cobranca-facil/
├── app.py                     # Código principal do Flask
├── requirements.txt           # Dependências Python
├── runtime.txt                # Versão do Python para o Render
├── Procfile                   # Comando de inicialização
├── static/
│   ├── manifest.json          # Configuração do PWA
│   ├── sw.js                  # Service Worker (cache + notificações)
│   ├── android-icon-.png     # Ícones do app (vários tamanhos)
│   ├── apple-icon-.png       # Ícones para iOS
│   ├── favicon-*.png/ico      # Favicons
│   └── browserconfig.xml
└── templates/
├── base.html              # Layout padrão (com menu hambúrguer)
├── index.html             # Dashboard com cards
├── clientes.html          # Lista de clientes (com excluir)
├── novo_cliente.html      # Cadastro
├── editar_cliente.html    # Edição
├── parcelas_cliente.html  # Histórico de parcelas
├── login.html             # Tela de login
├── esqueci_senha.html     # Solicitar código OTP
├── validar_codigo.html    # Validar código OTP
├── redefinir_senha_otp.html # Nova senha após validação
└── configuracoes.html     # Configurações de Pix (com máscaras)

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
| cron-job.org | [cron-job.org](https://cron-job.org) | Ping para evitar hibernação |
| CallMeBot | [callmebot.com](https://www.callmebot.com/blog/free-api-whatsapp-messages/) | (Opcional) Recuperação de senha OTP |

### 2. Configuração do Banco de Dados (Neon)
1. Crie um projeto no Neon.
2. Copie a **Connection String** (formato `postgresql://...`).
3. Ela será usada como variável `DATABASE_URL` no Render.

### 3. Configuração do CallMeBot (Opcional – apenas para recuperação de senha)
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
   - `CALLMEBOT_API_KEY`: (opcional) sua API Key do CallMeBot.
   - `CALLMEBOT_PHONE_NUMBER`: (opcional) seu número com código do país (ex: `5511999999999`).
5. Clique em **Create Web Service**.

### 5. Manter o Render Ativo (cron-job.org)
1. Crie um cron job no cron-job.org.
2. URL: `https://seu-app.onrender.com/ping`
3. Intervalo: a cada **10 minutos**.

---

## 🧑‍🤝‍🧑 Guia para Configurar um Novo Cliente (SaaS)

### Criação de Contas para o Cliente
Cada cliente precisará de contas próprias (ou você gerencia para ele):
- **GitHub**: para clonar o repositório.
- **Neon**: para o banco de dados.
- **Render**: para a hospedagem.
- **cron-job.org**: para o ping.
- **CallMeBot**: (opcional) para recuperação de senha.

### Configuração do Ambiente
1. Clone o repositório para o cliente (ou use um fork).
2. Crie um novo Web Service no Render apontando para o repositório do cliente.
3. Adicione as variáveis de ambiente específicas do cliente.
4. Após o deploy, o cliente acessa `https://[nome-do-cliente].onrender.com`.

### Personalização (Opcional)
- Substitua os ícones em `static/`.
- Altere as cores no `base.html`.
- Modifique o título e o nome do sistema.

---

## 🧪 Testando o Sistema

1. Acesse a URL do Render e faça login com:
   - **Usuário:** `admin`
   - **Senha:** `admin123`
2. Cadastre um cliente com vencimento para **hoje + 5 dias**.
3. Permita notificações no navegador.
4. Aguarde as notificações automáticas ou clique no botão **WhatsApp** para abrir uma conversa pronta.
5. Marque parcelas como pagas e veja o dashboard atualizar.

---

## 💰 Modelos de Negócio

| Modelo | Descrição | Preço Sugerido |
|--------|-----------|----------------|
| **SaaS Mensal** | Hospedagem gerenciada por você, cada cliente paga mensalidade. | R$ 97/mês |
| **Venda Única** | Entrega do sistema configurado no servidor do cliente. | R$ 1.500 – R$ 3.000 |
| **White-Label** | Sistema personalizado com a marca do cliente. | Negociável |

---

## 📝 Personalizações Possíveis

- Texto das mensagens de WhatsApp.
- Prazos das notificações (parâmetros em `verificar_lembretes`).
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
