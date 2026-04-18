import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func
import atexit
import calendar
import pytz
import hashlib
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from urllib.parse import quote
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

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

# --- FILTRO PARA FORMATAR MOEDA (R$ 1.000,00) ---
@app.template_filter('real')
def format_real(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- MODELOS ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

# --- DECORATOR DE AUTENTICAÇÃO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar o sistema.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- GERAÇÃO DE TOKEN CSRF SIMPLES ---
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

def validate_csrf_token(token):
    return token == session.get('_csrf_token')

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        senha = request.form['senha']
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(senha):
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
        flash(f'Link de recuperação gerado. Acesse: {reset_url}', 'info')
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
        user = Usuario.query.filter_by(username=username).first()
        if user:
            user.set_password(nova_senha)
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

# --- 🆕 NOVA ROTA: LISTAR PARCELAS DE UM CLIENTE ESPECÍFICO ---
@app.route('/cliente/<int:id>/parcelas')
@login_required
def parcelas_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    parcelas = Parcela.query.filter_by(cliente_id=id).order_by(Parcela.numero).all()
    return render_template('parcelas_cliente.html', cliente=cliente, parcelas=parcelas)

# --- ROTA PARA MARCAR PARCELA COMO PAGA (PROTEGIDA COM POST E CSRF) ---
@app.route('/parcela/pagar/<int:id>', methods=['POST'])
@login_required
def pagar_parcela(id):
    token = request.form.get('_csrf_token')
    if not validate_csrf_token(token):
        abort(403, 'Token CSRF inválido')
    parcela = Parcela.query.get_or_404(id)
    parcela.pago = True
    parcela.data_pagamento = agora_sp()
    db.session.commit()
    flash(f'Parcela {parcela.numero}/{parcela.cliente.quantidade_parcelas} de {parcela.cliente.nome} paga!', 'success')
    return redirect(url_for('index'))

# --- API PARA NOTIFICAÇÕES (CONSULTADA PELO SERVICE WORKER) ---
@app.route('/api/notificacoes')
def api_notificacoes():
    hoje = hoje_sp()
    alvo_5 = hoje + timedelta(days=5)
    alvo_1 = hoje + timedelta(days=1)
    alvo_0 = hoje
    alvo_atraso = hoje - timedelta(days=1)

    parcelas_5 = Parcela.query.filter(Parcela.data_vencimento == alvo_5, Parcela.pago == False).all()
    parcelas_1 = Parcela.query.filter(Parcela.data_vencimento == alvo_1, Parcela.pago == False).all()
    parcelas_0 = Parcela.query.filter(Parcela.data_vencimento == alvo_0, Parcela.pago == False).all()
    parcelas_atraso = Parcela.query.filter(Parcela.data_vencimento <= alvo_atraso, Parcela.pago == False).all()

    notificacoes = []

    def formatar(p, dias_texto):
        cliente = p.cliente
        tel_limpo = ''.join(filter(str.isdigit, cliente.telefone))
        if not tel_limpo.startswith('55'):
            tel_limpo = '55' + tel_limpo
        msg_whats = (
            f"Olá {cliente.nome}, a parcela {p.numero}/{cliente.quantidade_parcelas} "
            f"do contrato {cliente.carro} vence {dias_texto}. Valor: R$ {p.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        return {
            'id': p.id,
            'titulo': f'🔔 {cliente.nome} - {dias_texto}',
            'mensagem': msg_whats,
            'url': f'https://wa.me/{tel_limpo}?text={quote(msg_whats)}',
            'acao_pagar': f'/parcela/pagar/{p.id}'
        }

    for p in parcelas_5:
        notificacoes.append(formatar(p, 'em 5 dias'))
    for p in parcelas_1:
        notificacoes.append(formatar(p, 'amanhã'))
    for p in parcelas_0:
        notificacoes.append(formatar(p, 'hoje'))
    for p in parcelas_atraso:
        dias_atraso = (hoje - p.data_vencimento).days
        notificacoes.append(formatar(p, f'vencida há {dias_atraso} dias'))

    return {'notificacoes': notificacoes}

# --- VERIFICAÇÃO DIÁRIA (APENAS LOG) ---
def verificar_lembretes():
    with app.app_context():
        hoje = hoje_sp()
        alvo_5 = hoje + timedelta(days=5)
        alvo_1 = hoje + timedelta(days=1)
        total = 0
        total += Parcela.query.filter(Parcela.data_vencimento == alvo_5, Parcela.pago == False).count()
        total += Parcela.query.filter(Parcela.data_vencimento == alvo_1, Parcela.pago == False).count()
        total += Parcela.query.filter(Parcela.data_vencimento == hoje, Parcela.pago == False).count()
        print(f"===== {total} LEMBRETES IDENTIFICADOS =====")

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(func=verificar_lembretes, trigger=CronTrigger(hour=8, minute=0))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# --- CRIAÇÃO DAS TABELAS E USUÁRIO PADRÃO ---
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuário 'admin' criado com senha 'admin123'")
    if not Configuracao.query.first():
        config = Configuracao(tipo_chave='telefone', chave_pix='', nome_titular='', banco='')
        db.session.add(config)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
