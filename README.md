
# 📊 Cobrança Fácil

Sistema inteligente de cobrança e gestão de parcelas para lojistas. Gerencia clientes, calcula parcelas automaticamente, exibe um dashboard financeiro e envia lembretes de cobrança via WhatsApp de forma totalmente automatizada.

**💰 Ideal para:** Venda como SaaS (assinatura mensal), white-label para lojas de veículos ou sistemas de gestão de cobrança em geral.

---

## 🚀 Funcionalidades

- ✅ **Cadastro Completo de Clientes**: Nome, telefone, veículo, valor total, número de parcelas e dia de vencimento.
- ✅ **Cálculo Automático**: Geração automática de todas as parcelas com base no valor total e dia de vencimento escolhido.
- ✅ **Dashboard Profissional**: Visão geral com cards de resumo (Vencidas, Vence Hoje, Esta Semana, Total a Receber) e lista de próximas parcelas por cliente.
- ✅ **Gestão de Pagamentos**: Marcação de parcelas como pagas com registro da data do pagamento.
- ✅ **Notificações Automáticas**: Envio de lembretes de cobrança via WhatsApp **5 dias antes** do vencimento de cada parcela.
- ✅ **Recuperação de Senha**: Sistema de "Esqueci a senha" que envia um link de recuperação via WhatsApp.
- ✅ **PWA (Progressive Web App)**: Instalável como aplicativo no celular e computador, com ícone e funcionamento offline básico.
- ✅ **Deploy Contínuo**: Atualizações automáticas no servidor a cada `git push`.

---

## 🛠️ Tecnologias e Ferramentas (Todas Gratuitas)

| Categoria | Ferramenta | Função no Projeto |
|-----------|------------|-------------------|
| **Backend** | Python 3 + Flask | Lógica do servidor e rotas da aplicação. |
| **Banco de Dados** | Neon (PostgreSQL) | Armazenamento de clientes, parcelas e usuários na nuvem (5 GB gratuitos). |
| **Hospedagem** | Render | Servidor web gratuito que executa o código Flask 24/7. |
| **Mensagens** | CallMeBot | API gratuita para envio de mensagens de WhatsApp. |
| **Monitoramento** | cron-job.org | Pinga o servidor a cada 10 minutos para evitar que o Render hiberne. |
| **Versionamento** | Git + GitHub | Controle de versão do código e deploy automático. |
| **Frontend** | HTML, CSS, Jinja2 | Interface responsiva (funciona no celular e no PC). |

---

## 📁 Estrutura do Projeto

```

cobranca-auto/
├── app.py                 # Código principal do Flask (rotas, modelos, agendador)
├── requirements.txt       # Dependências Python do projeto
├── runtime.txt            # Versão do Python para o Render
├── Procfile               # Comando de inicialização no Render
├── .gitignore             # Arquivos ignorados pelo Git
├── static/                # Arquivos estáticos (CSS, JS, ícones, PWA)
│   ├── manifest.json      # Configuração do PWA
│   ├── sw.js              # Service Worker (cache e notificações)
│   └── icons/             # Ícones do app em vários tamanhos
└── templates/             # Templates HTML (frontend)
├── base.html          # Layout padrão (compartilhado)
├── index.html         # Dashboard principal
├── clientes.html      # Lista de clientes
├── novo_cliente.html  # Formulário de cadastro
├── editar_cliente.html# Formulário de edição
├── login.html         # Tela de login
├── esqueci_senha.html # Tela de recuperação de senha
└── redefinir_senha.html# Tela para criar nova senha

```

---

## 🔧 1. Pré-requisitos (Contas e Configurações)

Antes de rodar o projeto, você precisa criar contas gratuitas nas seguintes plataformas:

| Ferramenta | Link para Cadastro | O que você vai obter |
|------------|-------------------|----------------------|
| **GitHub** | [github.com/join](https://github.com/join) | Conta para armazenar o código e fazer deploy automático. [reference:0] |
| **Neon** | [neon.tech](https://neon.tech) | Banco de dados PostgreSQL gratuito (5 GB). Você receberá uma **Connection String**. [reference:1] |
| **Render** | [render.com](https://render.com) | Hospedagem gratuita para a aplicação. Conecte com sua conta do GitHub. [reference:2] |
| **CallMeBot** | [callmebot.com](https://www.callmebot.com/blog/free-api-whatsapp-messages/) | API gratuita para enviar mensagens de WhatsApp. Você receberá uma **API Key**. [reference:3] |
| **cron-job.org** | [cron-job.org](https://cron-job.org) | Serviço de ping para manter o Render sempre acordado. [reference:4] |

---

## ⚙️ 2. Configuração do Projeto (Passo a Passo)

### 📥 2.1. Clonar o Repositório

```bash
git clone https://github.com/sml-pn/cobranca-auto.git
cd cobranca-auto
```

📦 2.2. Instalar Dependências

```bash
python -m venv venv
source venv/bin/activate   # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

🗄️ 2.3. Configurar o Banco de Dados (Neon)

1. Crie uma conta no Neon. 
2. Crie um novo projeto e copie a Connection String (formato postgresql://...). 
3. Guarde essa string para usar como DATABASE_URL.

☁️ 2.4. Deploy no Render

1. Crie uma conta no Render. 
2. Clique em New + → Web Service e conecte seu GitHub.
3. Selecione o repositório cobranca-auto.
4. Configure:
   · Name: cobranca-facil (ou o nome que preferir)
   · Runtime: Python 3
   · Build Command: pip install -r requirements.txt
   · Start Command: gunicorn app:app
   · Instance Type: Free
5. Em Environment Variables, adicione:
   · DATABASE_URL: a string de conexão do Neon.
   · SECRET_KEY: uma chave secreta aleatória (use o botão "Generate").
   · CALLMEBOT_API_KEY: sua chave da API do CallMeBot.
   · CALLMEBOT_PHONE_NUMBER: seu número de telefone com código do país (ex: 5511999999999).
6. Clique em Create Web Service. 

💬 2.5. Configurar CallMeBot (WhatsApp)

1. Adicione o número +34 644 71 81 99 aos seus contatos. 
2. Envie a mensagem I allow callmebot to send me messages para esse contato via WhatsApp. 
3. Você receberá uma resposta com sua API Key. 
4. Adicione essa chave como CALLMEBOT_API_KEY no Render.

🔄 2.6. Manter o Render Sempre Ativo (cron-job.org)

1. Crie uma conta no cron-job.org. 
2. Clique em Create Cronjob.
3. Preencha:
   · URL: https://cobranca-facil.onrender.com/ping (ou o nome do seu serviço)
   · Intervalo: a cada 10 minutos.
4. Salve. Isso evita que o Render hiberne por inatividade. 

---

🧑‍🤝‍🧑 3. Guia de Onboarding: Como Configurar um Novo Cliente

Para oferecer o sistema como SaaS (um deploy por cliente), você precisará repetir as etapas acima para cada novo lojista. Siga este roteiro:

3.1. Criação de Contas para o Cliente

Você (ou o cliente) precisará criar contas gratuitas nos seguintes serviços. É importante usar um e-mail diferente para cada cliente ou gerenciar você mesmo as credenciais.

Serviço Ação para o Novo Cliente
GitHub Criar uma conta gratuita. Será usada para clonar o repositório e fazer o deploy inicial. 
Neon Criar uma conta gratuita e um novo projeto PostgreSQL. Copiar a DATABASE_URL. 
Render Criar uma conta gratuita (pode usar login do GitHub). Conectar o repositório e criar um novo Web Service. 
CallMeBot Ativar a API para o número de WhatsApp do cliente. O cliente receberá uma API Key própria. 
cron-job.org Criar uma conta gratuita e configurar um cron job para pingar a URL do Render do cliente. 

3.2. Configuração do Ambiente do Cliente

1. Clone o repositório para um novo diretório local ou faça um fork no GitHub para o cliente.
2. Crie um novo Web Service no Render apontando para o repositório do cliente.
3. Adicione as variáveis de ambiente específicas do cliente no Render:
   · DATABASE_URL: a string do Neon do cliente.
   · CALLMEBOT_API_KEY: a chave da API do CallMeBot do cliente.
   · CALLMEBOT_PHONE_NUMBER: o número de WhatsApp do cliente.
   · SECRET_KEY: uma nova chave secreta gerada para ele.
4. Após o deploy, o cliente poderá acessar o sistema em https://[nome-do-cliente].onrender.com.
5. Configure o cron-job.org para pingar a URL do cliente a cada 10 minutos.

3.3. Personalização (Opcional)

· Logo e Cores: Substitua os arquivos em static/icons/ e ajuste as cores no CSS do base.html.
· Nome do Sistema: Altere o título no base.html para o nome da loja do cliente.

3.4. Entrega ao Cliente

Forneça ao cliente:

· URL de acesso: https://[nome-do-cliente].onrender.com
· Credenciais iniciais: admin / admin123 (ele poderá alterar depois ou recuperar via WhatsApp).
· Instruções de uso: Como cadastrar clientes, marcar parcelas como pagas e receber os lembretes automáticos.

---

🧪 Testando o Sistema

1. Acesse http://localhost:5000 (local) ou a URL do Render.
2. Faça login com admin / admin123.
3. Cadastre um novo cliente com vencimento para daqui a 5 dias.
4. Aguarde o envio automático da mensagem de WhatsApp (ou force via rota /forcar-lembretes).
5. Marque a parcela como paga e verifique se ela sai da lista de pendentes.

---

💰 Como Vender Este Sistema

Modelo 1: SaaS (Assinatura Mensal)

· Cobre um valor mensal por loja (ex: R$ 97/mês).
· Para cada novo cliente, repita o processo de onboarding descrito acima.
· Gerencie as contas e ofereça suporte.

Modelo 2: Venda do Projeto (Pagamento Único)

· Cobre um valor único (ex: R$ 1.500 – R$ 3.000) para entregar o sistema configurado no servidor do cliente.
· Inclua personalização visual e treinamento.

Modelo 3: White-Label

· Ofereça o sistema com a marca do cliente (logo, cores).
· Ideal para lojas de veículos que desejam uma solução própria.

---

📝 Personalizações Possíveis

· Cores e Logo: Altere o CSS no base.html e os ícones em static/icons/.
· Mensagens de WhatsApp: Ajuste o texto na função enviar_whatsapp_callmebot no app.py.
· Prazos de Cobrança: Modifique o parâmetro days=5 na função verificar_lembretes para alterar a antecedência do lembrete.

---

🧑‍💻 Autor

Desenvolvido por Samuel Pena
📧 smlpnsz.pena@gmail.com
🐙 GitHub: sml-pn

---

📄 Licença

Este projeto é open-source para fins educacionais. Para uso comercial, entre em contato.

---

Feito com ❤️ usando apenas ferramentas gratuitas.

```