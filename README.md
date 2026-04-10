O arquivo README.md ainda não foi criado. Vamos criá-lo agora com o conteúdo completo que você pediu e depois enviá-lo ao GitHub.

1️⃣ Criar o arquivo README.md

No Termux, dentro da pasta ~/sistema-cobranca, execute:

```bash
nano README.md
```

Agora copie o bloco completo que está abaixo (desde # 🚗 Cobrança Auto Fácil até o final **Feito com ❤️ usando apenas um celular Android e Termux.**) e cole no nano.

Para colar no Termux, pressione e segure a tela e selecione Paste ou use o botão de colar do teclado virtual.

```markdown
# 🚗 Cobrança Auto Fácil

Sistema inteligente de cobrança para lojas de veículos. Lembre-se de parcelas que vencem em **5 dias**, notificações no celular/computador, botão direto para WhatsApp do cliente e funciona como um aplicativo instalável.

**💰 Monetização:** Venda como SaaS (assinatura mensal) ou como sistema exclusivo para um cliente.

---

## ✨ Funcionalidades

- ✅ Cadastro de clientes (nome, telefone, veículo)
- ✅ Cadastro de parcelas (número, valor, data de vencimento)
- ✅ Dashboard com parcelas que vencem nos próximos **5 dias**
- ✅ Marcar parcela como paga
- ✅ **Notificações push do navegador** (Android, iOS, Desktop)
- ✅ **PWA** – Instalável como aplicativo nativo (ícone na tela inicial, abre em tela cheia)
- ✅ **Botão "Notificar cliente"** – Abre WhatsApp com mensagem pronta
- ✅ Agendador automático diário (verifica vencimentos às 5h da manhã)
- ✅ Banco de dados PostgreSQL gratuito (Neon ou Aiven)
- ✅ Deploy gratuito no Render

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3 + Flask |
| Banco de Dados | PostgreSQL (produção) / SQLite (desenvolvimento local) |
| Agendador | APScheduler |
| Frontend | HTML5, CSS3, Jinja2 |
| Notificações | Service Worker + Web Push API |
| Hospedagem | Render (gratuito) |
| Banco Cloud | Neon (PostgreSQL serverless gratuito) |
| Desenvolvimento Mobile | Termux (Android) |

---

## 📁 Estrutura do Projeto

```

sistema-cobranca/
├── app.py                 # Código principal do Flask
├── requirements.txt       # Dependências Python (desenvolvimento)
├── requirements-prod.txt  # Dependências para produção (psycopg2)
├── runtime.txt            # Versão do Python para o Render
├── Procfile               # Comando de inicialização no Render
├── .gitignore             # Arquivos ignorados pelo Git
├── static/                # Arquivos estáticos (ícones, service worker)
│   ├── manifest.json      # Configuração do PWA
│   ├── sw.js              # Service Worker para notificações
│   ├── icon-192.png       # Ícone 192x192
│   └── icon-512.png       # Ícone 512x512
└── templates/             # Templates HTML
├── base.html          # Layout padrão (compartilhado)
├── index.html         # Dashboard inicial
├── clientes.html      # Lista de clientes
├── novo_cliente.html  # Formulário de cadastro
└── nova_parcela.html  # Formulário de parcela

```

---

## 🚀 Como Executar Localmente (Termux / Android)

### 1. Instalar Termux e dependências

```bash
pkg update && pkg upgrade -y
pkg install python git nano -y
```

2. Clonar o repositório e preparar ambiente

```bash
git clone https://github.com/sml-pn/cobranca-auto.git
cd cobranca-auto
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Executar o servidor

```bash
python app.py
```

Acesse no navegador: http://localhost:5000

Modo produção (mais rápido):

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

---

☁️ Deploy no Render (Gratuito)

1. Banco de Dados no Neon

· Crie uma conta gratuita em neon.tech
· Crie um projeto e copie a string de conexão com -pooler (exemplo: postgresql://...pooler...)
· No Render, adicione a variável de ambiente DATABASE_URL com essa string.

2. Configuração no Render

· Crie um Web Service conectado ao repositório GitHub.
· Build Command:
  ```
  pip install -r requirements.txt && pip install -r requirements-prod.txt
  ```
· Start Command:
  ```
  gunicorn app:app
  ```
· Adicione a variável DATABASE_URL.

Após o deploy, acesse https://cobranca-auto.onrender.com.

---

📲 Instalando como Aplicativo (PWA)

Android

1. Acesse o site pelo Chrome.
2. Toque no menu (três pontinhos) e selecione "Instalar aplicativo" ou "Adicionar à tela inicial".

iOS (iPhone/iPad)

1. Acesse o site pelo Safari.
2. Toque no ícone de Compartilhar (quadrado com seta).
3. Role e selecione "Adicionar à Tela de Início".
4. Dê um nome e toque em Adicionar.
5. Abra o ícone criado – o sistema abrirá em tela cheia.

Após instalado, o navegador solicitará permissão para enviar notificações. Aceite.

---

🔔 Como Funcionam as Notificações

· Android / Windows / Mac: Notificações nativas via Service Worker (push).
· iOS: Funciona apenas se o site for instalado como PWA (Safari) e o dispositivo estiver com iOS 16.4+.
· O sistema verifica a cada 30 minutos se há parcelas vencendo nos próximos 5 dias.
· Se houver, exibe uma notificação com os detalhes do cliente.

---

💬 Botão "Notificar Cliente" (WhatsApp)

Em cada parcela pendente, há um botão verde com ícone do WhatsApp. Ao clicar, abre uma conversa com o número do cliente (cadastrado) e uma mensagem pronta:

"Olá [Nome], tudo bem? Lembrando que a parcela [X] do seu [Carro] vence em [N] dias ([Data]). Valor: R$ [Valor]. Posso enviar o boleto/PIX? Obrigado!"

---

🧪 Testando o Sistema

1. Cadastre um cliente.
2. Cadastre uma parcela com vencimento para hoje + 5 dias.
3. Aguarde o agendador rodar (ou reinicie o servidor) e veja a notificação no navegador.
4. Clique no botão do WhatsApp para simular o envio da mensagem.

---

💰 Como Vender Este Sistema

Modelo 1: SaaS (Assinatura Mensal)

· Cobre R$ 97/mês por loja.
· Crie um deploy separado para cada cliente (white-label).
· Ofereça suporte e atualizações.

Modelo 2: Venda do Projeto (Pagamento Único)

· Cobre R$ 1.500 – R$ 3.000 para entregar o sistema completo configurado no servidor do cliente.
· Inclua personalização de cores, logo e nome da loja.

Argumento de Venda

"Quantas parcelas você já deixou de cobrar por esquecimento? Esse sistema te avisa 5 dias antes, te ajuda a ligar pro cliente no momento certo e evita calote. Em uma única cobrança recuperada, ele já se paga."

---

📝 Personalizações Possíveis

· Alterar cores no base.html (variáveis CSS no <style>)
· Alterar logo/ícone substituindo os arquivos em static/
· Alterar texto da mensagem do WhatsApp no template index.html
· Ajustar o prazo de antecedência (5 dias) em app.py (variável timedelta(days=5))

---

🧑‍💻 Autor

Desenvolvido por sml-pn
📧 smlpnsz.pena@gmail.com
🐙 GitHub: sml-pn

---

📄 Licença

Este projeto é open-source para fins educacionais. Para uso comercial, entre em contato.

---

Feito com ❤️ usando apenas um celular Android e Termux.

```

Depois de colar, salve o arquivo:
- Pressione `Ctrl+O` (Volume Down + O no teclado virtual do Termux)
- Depois `Enter` para confirmar
- Pressione `Ctrl+X` para sair

### 2️⃣ Agora adicione, faça commit e envie

```bash
git add README.md
git commit -m "Adiciona README completo com instruções do sistema"
git push
```

Pronto! Agora o README.md estará no seu repositório cobranca-auto no GitHub.
