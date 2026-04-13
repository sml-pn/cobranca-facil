import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import calendar
import pytz

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-aqui-mude-para-algo-seguro'

# --- BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cobranca.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- FILTRO PARA FORMATAR MOEDA (R$ 1.000,00) ---
@app.template_filter('real')
def format_real(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- MODELOS ---
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

# --- ROTAS ---
@app.route('/')
def index():
    hoje = hoje_sp()

    vence_hoje = Parcela.query.filter(
        Parcela.data_vencimento == hoje,
        Parcela.pago == False
    ).order_by(Parcela.data_vencimento).all()

    limite = hoje + timedelta(days=7)
    esta_semana = Parcela.query.filter(
        Parcela.data_vencimento.between(hoje, limite),
        Parcela.pago == False
    ).order_by(Parcela.data_vencimento).all()

    vencidas = Parcela.query.filter(
        Parcela.data_vencimento < hoje,
        Parcela.pago == False
    ).order_by(Parcela.data_vencimento).all()

    pendentes = Parcela.query.filter_by(pago=False).all()
    total_receber = sum(p.valor for p in pendentes)

    # Função auxiliar para converter objeto Parcela em dict serializável
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
                         vence_hoje=[parcela_to_dict(p) for p in vence_hoje],
                         esta_semana=[parcela_to_dict(p) for p in esta_semana],
                         vencidas=[parcela_to_dict(p) for p in vencidas],
                         total_receber=total_receber,
                         total_pendentes=len(pendentes))

@app.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.data_cadastro.desc()).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/novo', methods=['GET', 'POST'])
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
def pagar_parcela(id):
    parcela = Parcela.query.get_or_404(id)
    parcela.pago = True
    parcela.data_pagamento = agora_sp()
    db.session.commit()
    flash(f'Parcela {parcela.numero}/{parcela.cliente.quantidade_parcelas} de {parcela.cliente.nome} paga!', 'success')
    return redirect(url_for('index'))

@app.route('/api/lembretes')
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

# --- NOVA API: TODAS AS PARCELAS PENDENTES (SEM LIMITE DE DATA) ---
@app.route('/api/todas-parcelas')
def api_todas_parcelas():
    parcelas = Parcela.query.filter_by(pago=False).order_by(Parcela.data_vencimento).all()
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

# --- VERIFICAÇÃO DIÁRIA (LOG) ---
def verificar_lembretes():
    with app.app_context():
        hoje = hoje_sp()
        alvo = hoje + timedelta(days=5)
        parcelas = Parcela.query.filter(
            Parcela.data_vencimento == alvo,
            Parcela.pago == False
        ).all()
        if parcelas:
            print(f"\n===== {len(parcelas)} LEMBRETES GERADOS =====")

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(func=verificar_lembretes, trigger=CronTrigger(hour=8, minute=0))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# --- CRIAÇÃO DAS TABELAS ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
