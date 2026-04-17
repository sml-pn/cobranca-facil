import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func
import atexit
import calendar
import pytz
import requests
from urllib.parse import quote
import hashlib
from functools import wraps
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui-mude-para-algo-seguro')

# --- BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cobranca.db'

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5
    }
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

serializer = URLSafeTimedSerializer(app.secret_key)

# --- FILTRO PARA FORMATAR MOEDA ---
@app.template_filter('real')
def format_real(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- MODELOS ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(64), nullable=False)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_chave = db.Column(db.String(20), default='telefone')
    chave_pix = db.Column(db.String(100), nullable=False, default='')
    nome_titular = db.Column(db.String(100), nullable=False, default='')
    banco = db.Column(db.String(50), nullable=False, default='')

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    carro = db.Column(db.String(100), nullable=False)
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    quantidade_parcelas = db.Column(db.Integer, nullable=False, default=1)
    valor_parcela = db.Column(db.Float, nullable=False, default=0.0)
    dia_vencimento = db.Column(db.Integer, nullable=False, default=10)
    data_cadastro = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
    parcelas = db.relationship('Parcela', backref='cliente', lazy=True, cascade='all, delete-orphan')

class Parcela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.DateTime, nullable=True)
    pago = db.Column(db.Boolean, default=False)
    observacao = db.Column(db.String(200), nullable=True)

# --- FUNÇÃO PARA DIA FIXO ---
def calcular_proximo_vencimento(data_base, dia_fixo):
    ano = data_base.year
    mes = data_base.month
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(dia_fixo, ultimo_dia)
    vencimento = date(ano, mes, dia)
    if vencimento < data_base:
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(dia_fixo, ultimo_dia)
        vencimento = date(ano, mes, dia)
    return vencimento

# --- OBTÉM DATA/HORA NO FUSO SP ---
def agora_sp():
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

def hoje_sp():
    return agora_sp().date()

# --- CONTEXTO GLOBAL ---
@app.context_processor
def inject_now():
    return {'now': agora_sp()}

# --- FUNÇÃO AUXILIAR: PRÓXIMA PARCELA PENDENTE DE CADA CLIENTE ---
def get_proximas_parcelas(filtro_data=None):
    hoje = hoje_sp()
    subquery = db.session.query(
        Parcela.cliente_id,
        func.min(Parcela.data_vencimento).label('proxima_data')
    ).filter(Parcela.pago == False).group_by(Parcela.cliente_id).subquery()

    query = Parcela.query.join(
        subquery,
        (Parcela.cliente_id == subquery.c.cliente_id) &
        (Parcela.data_vencimento == subquery.c.proxima_data) &
        (Parcela.pago == False)
    )

    if filtro_data == 'vencidas':
        query = query.filter(Parcela.data_vencimento < hoje)
    elif filtro_data == 'hoje':
        query = query.filter(Parcela.data_vencimento == hoje)
    elif filtro_data == 'semana':
        limite = hoje + timedelta(days=7)
        query = query.filter(Parcela.data_vencimento.between(hoje, limite))

    return query.order_by(Parcela.data_vencimento).all()

# --- FUNÇÃO PARA OBTER DADOS PIX (formatação) ---
def get_dados_pix():
    config = Configuracao.query.first()
    if not config or not config.chave_pix:
        return ""
    return (
        f"\n\n📌 Dados para pagamento (PIX):\n"
        f"Chave: {config.chave_pix}\n"
        f"Titular: {config.nome_titular}\n"
        f"Banco: {config.banco}"
    )

# --- 🆕 FUNÇÃO DE ENVIO DE WHATSAPP (CORRIGIDA) ---
def enviar_whatsapp_direto(numero_destino, mensagem):
    """Envia uma mensagem de WhatsApp via CallMeBot."""
    api_key = os.environ.get('CALLMEBOT_API_KEY')
    if not api_key:
        print("❌ Erro: Chave API do CallMeBot não configurada.")
        return False
    mensagem_codificada = quote(mensagem)
    url = f"https://api.callmebot.com/whatsapp.php?phone={numero_destino}&text={mensagem_codificada}&apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")
        return False

# --- DECORATOR DE AUTENTICAÇÃO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar o sistema.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        user = Usuario.query.filter_by(username=username, password_hash=senha_hash).first()
        if user:
            session['usuario'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        telefone = request.form['telefone'].replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        username = 'admin'
        token = serializer.dumps(username, salt='password-reset')
        reset_url = url_for('redefinir_senha', token=token, _external=True)
        mensagem = (
            f"🔐 Recuperação de Senha - Cobrança Fácil\n\n"
            f"Clique no link abaixo para redefinir sua senha (válido por 1 hora):\n"
            f"{reset_url}\n\n"
            f"Se você não solicitou, ignore esta mensagem."
        )
        mensagem_codificada = quote(mensagem)
        api_key = os.environ.get('CALLMEBOT_API_KEY')
        seu_numero = os.environ.get('CALLMEBOT_PHONE_NUMBER')
        if api_key and seu_numero:
            url = f"https://api.callmebot.com/whatsapp.php?phone={seu_numero}&text={mensagem_codificada}&apikey={api_key}"
            try:
                requests.get(url, timeout=10)
                flash('Um link de recuperação foi enviado para o WhatsApp cadastrado.', 'success')
            except:
                flash('Erro ao enviar mensagem. Tente novamente.', 'danger')
        else:
            flash(f'Link de recuperação: {reset_url}', 'warning')
        return redirect(url_for('login'))
    return render_template('esqueci_senha.html')

@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        username = serializer.loads(token, salt='password-reset', max_age=3600)
    except:
        flash('O link de recuperação é inválido ou expirou.', 'danger')
        return redirect(url_for('esqueci_senha'))
    if request.method == 'POST':
        nova_senha = request.form['senha']
        senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
        user = Usuario.query.filter_by(username=username).first()
        if user:
            user.password_hash = senha_hash
            db.session.commit()
            flash('Senha redefinida com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Usuário não encontrado.', 'danger')
    return render_template('redefinir_senha.html', token=token)

# --- ROTA DE CONFIGURAÇÕES (PIX) ---
@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(tipo_chave='telefone', chave_pix='', nome_titular='', banco='')
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        config.tipo_chave = request.form.get('tipo_chave', 'telefone')
        config.chave_pix = request.form.get('chave_pix', '')
        config.nome_titular = request.form.get('nome_titular', '')
        config.banco = request.form.get('banco', '')
        db.session.commit()
        flash('Configurações do Pix atualizadas com sucesso!', 'success')
        return redirect(url_for('configuracoes'))

    return render_template('configuracoes.html', config=config)

# --- ROTAS PROTEGIDAS ---
@app.route('/')
@login_required
def index():
    hoje = hoje_sp()
    vence_hoje_todas = Parcela.query.filter(Parcela.data_vencimento == hoje, Parcela.pago == False).all()
    limite = hoje + timedelta(days=7)
    esta_semana_todas = Parcela.query.filter(Parcela.data_vencimento.between(hoje, limite), Parcela.pago == False).all()
    vencidas_todas = Parcela.query.filter(Parcela.data_vencimento < hoje, Parcela.pago == False).all()
    pendentes_todas = Parcela.query.filter_by(pago=False).all()
    total_receber = sum(p.valor for p in pendentes_todas)
    proximas_vencidas = get_proximas_parcelas('vencidas')
    proximas_hoje = get_proximas_parcelas('hoje')
    proximas_semana = get_proximas_parcelas('semana')

    def parcela_to_dict(p):
        return {
            'id': p.id,
            'numero': p.numero,
            'valor': p.valor,
            'data_vencimento': p.data_vencimento.isoformat(),
            'cliente': {
                'id': p.cliente.id,
                'nome': p.cliente.nome,
                'telefone': p.cliente.telefone,
                'carro': p.cliente.carro,
                'quantidade_parcelas': p.cliente.quantidade_parcelas
            }
        }

    return render_template('index.html',
                         vence_hoje=[parcela_to_dict(p) for p in proximas_hoje],
                         esta_semana=[parcela_to_dict(p) for p in proximas_semana],
                         vencidas=[parcela_to_dict(p) for p in proximas_vencidas],
                         total_receber=total_receber,
                         total_pendentes=len(pendentes_todas),
                         count_vencidas=len(vencidas_todas),
                         count_hoje=len(vence_hoje_todas),
                         count_semana=len(esta_semana_todas))

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.data_cadastro.desc()).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/novo', methods=['GET', 'POST'])
@login_required
def novo_cliente():
    if request.method == 'POST':
        ultimo = Cliente.query.order_by(Cliente.id.desc()).first()
        novo_id = (ultimo.id + 1) if ultimo else 1
        codigo = f"CLI-{novo_id:03d}"
        valor_total = float(request.form['valor_total'])
        quantidade = int(request.form['quantidade_parcelas'])
        valor_parcela = valor_total / quantidade
        dia_vencimento = int(request.form.get('dia_vencimento', 10))
        cliente = Cliente(
            codigo=codigo,
            nome=request.form['nome'],
            telefone=request.form['telefone'],
            carro=request.form['carro'],
            valor_total=valor_total,
            quantidade_parcelas=quantidade,
            valor_parcela=valor_parcela,
            dia_vencimento=dia_vencimento
        )
        db.session.add(cliente)
        db.session.flush()
        data_primeira = datetime.strptime(request.form['data_primeiro_vencimento'], '%Y-%m-%d').date()
        for i in range(1, quantidade + 1):
            if i == 1:
                data_vencimento = data_primeira
            else:
                data_vencimento = calcular_proximo_vencimento(
                    data_primeira + timedelta(days=30*(i-1)),
                    dia_vencimento
                )
            parcela = Parcela(
                cliente_id=cliente.id,
                numero=i,
                valor=valor_parcela,
                data_vencimento=data_vencimento,
                pago=False
            )
            db.session.add(parcela)
        db.session.commit()
        flash(f'Cliente {codigo} cadastrado com {quantidade} parcelas!', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('novo_cliente.html')

@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.telefone = request.form['telefone']
        cliente.carro = request.form['carro']
        cliente.dia_vencimento = int(request.form.get('dia_vencimento', 10))
        db.session.commit()
        flash(f'Cliente {cliente.codigo} atualizado!', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/parcela/pagar/<int:id>')
@login_required
def pagar_parcela(id):
    parcela = Parcela.query.get_or_404(id)
    parcela.pago = True
    parcela.data_pagamento = agora_sp()
    db.session.commit()
    flash(f'Parcela {parcela.numero}/{parcela.cliente.quantidade_parcelas} de {parcela.cliente.nome} paga!', 'success')
    return redirect(url_for('index'))

@app.route('/api/lembretes')
@login_required
def api_lembretes():
    hoje = hoje_sp()
    limite = hoje + timedelta(days=5)
    parcelas = Parcela.query.filter(
        Parcela.data_vencimento.between(hoje, limite),
        Parcela.pago == False
    ).all()
    resultado = []
    for p in parcelas:
        resultado.append({
            'cliente': p.cliente.nome,
            'carro': p.cliente.carro,
            'parcela': f"{p.numero}/{p.cliente.quantidade_parcelas}",
            'valor': f"R$ {p.valor:.2f}",
            'dias': (p.data_vencimento - hoje).days,
            'telefone': p.cliente.telefone
        })
    return {'lembretes': resultado}

@app.route('/api/todas-parcelas')
@login_required
def api_todas_parcelas():
    parcelas = get_proximas_parcelas()
    resultado = []
    for p in parcelas:
        resultado.append({
            'id': p.id,
            'numero': p.numero,
            'valor': p.valor,
            'data_vencimento': p.data_vencimento.isoformat(),
            'cliente': {
                'id': p.cliente.id,
                'nome': p.cliente.nome,
                'telefone': p.cliente.telefone,
                'carro': p.cliente.carro,
                'quantidade_parcelas': p.cliente.quantidade_parcelas
            }
        })
    return {'parcelas': resultado}

# --- VERIFICAÇÃO DIÁRIA COM MÚLTIPLOS LEMBRETES E DADOS PIX (CORRIGIDA) ---
def verificar_lembretes():
    with app.app_context():
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                hoje = hoje_sp()
                dados_pix = get_dados_pix()
                
                # 5 dias
                alvo_5dias = hoje + timedelta(days=5)
                parcelas_5dias = Parcela.query.filter(
                    Parcela.data_vencimento == alvo_5dias,
                    Parcela.pago == False
                ).all()
                
                # amanhã
                alvo_amanha = hoje + timedelta(days=1)
                parcelas_amanha = Parcela.query.filter(
                    Parcela.data_vencimento == alvo_amanha,
                    Parcela.pago == False
                ).all()
                
                # hoje
                parcelas_hoje = Parcela.query.filter(
                    Parcela.data_vencimento == hoje,
                    Parcela.pago == False
                ).all()
                
                total_envios = 0
                
                for p in parcelas_5dias:
                    cliente = p.cliente
                    tel = cliente.telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                    msg = (f"Olá {cliente.nome}, tudo bem?\n\n"
                           f"Passando para lembrar que a parcela {p.numero}/{cliente.quantidade_parcelas} do seu contrato ({cliente.carro}) "
                           f"vence em 5 dias, no dia {p.data_vencimento.strftime('%d/%m/%Y')}.\n"
                           f"💵 Valor: R$ {p.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") +
                           f"{dados_pix}\n\n"
                           f"Se já tiver efetuado o pagamento, desconsidere esta mensagem.")
                    enviar_whatsapp_direto(tel, msg)
                    total_envios += 1
                
                for p in parcelas_amanha:
                    cliente = p.cliente
                    tel = cliente.telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                    msg = (f"Olá {cliente.nome}, tudo bem?\n\n"
                           f"⚠️ Lembrete importante: a parcela {p.numero}/{cliente.quantidade_parcelas} do seu contrato ({cliente.carro}) "
                           f"vence AMANHÃ, dia {p.data_vencimento.strftime('%d/%m/%Y')}.\n"
                           f"💵 Valor: R$ {p.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") +
                           f"{dados_pix}\n\n"
                           f"Não deixe para a última hora!")
                    enviar_whatsapp_direto(tel, msg)
                    total_envios += 1
                
                for p in parcelas_hoje:
                    cliente = p.cliente
                    tel = cliente.telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                    msg = (f"Olá {cliente.nome}, tudo bem?\n\n"
                           f"🔴 A parcela {p.numero}/{cliente.quantidade_parcelas} do seu contrato ({cliente.carro}) "
                           f"vence HOJE, dia {p.data_vencimento.strftime('%d/%m/%Y')}.\n"
                           f"💵 Valor: R$ {p.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") +
                           f"{dados_pix}\n\n"
                           f"Por favor, efetue o pagamento. Após, envie o comprovante.")
                    enviar_whatsapp_direto(tel, msg)
                    total_envios += 1
                
                print(f"\n===== {total_envios} LEMBRETES GERADOS =====")
                break
            except Exception as e:
                print(f"Tentativa {tentativa + 1} falhou: {e}")
                if tentativa == max_tentativas - 1:
                    print("❌ Todas as tentativas de conexão com o banco falharam.")
                else:
                    time.sleep(5)

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(func=verificar_lembretes, trigger=CronTrigger(hour=11, minute=20))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# --- CRIAÇÃO DAS TABELAS E DADOS INICIAIS ---
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='admin').first():
        senha_padrao = hashlib.sha256('admin123'.encode()).hexdigest()
        admin = Usuario(username='admin', password_hash=senha_padrao)
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuário 'admin' criado com senha 'admin123'")
    if not Configuracao.query.first():
        config = Configuracao(tipo_chave='telefone', chave_pix='', nome_titular='', banco='')
        db.session.add(config)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
