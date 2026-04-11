import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-aqui-mude-para-algo-seguro'

# --- CONFIGURAÇÃO INTELIGENTE DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cobranca.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)

# --- MODELOS ---
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    carro = db.Column(db.String(100))
    parcelas = db.relationship('Parcela', backref='cliente', lazy=True)

class Parcela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    pago = db.Column(db.Boolean, default=False)

# --- CONTEXTO GLOBAL ---
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# --- ROTAS ---
@app.route('/')
def index():
    hoje = datetime.now().date()
    limite = hoje + timedelta(days=5)
    parcelas_proximas = Parcela.query.filter(
        Parcela.data_vencimento.between(hoje, limite),
        Parcela.pago == False
    ).order_by(Parcela.data_vencimento).all()
    return render_template('index.html', parcelas=parcelas_proximas)

@app.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/novo', methods=['GET', 'POST'])
def novo_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        carro = request.form['carro']
        cliente = Cliente(nome=nome, telefone=telefone, carro=carro)
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('novo_cliente.html')

@app.route('/parcela/nova', methods=['GET', 'POST'])
def nova_parcela():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        numero = int(request.form['numero'])
        valor = float(request.form['valor'])
        data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date()
        parcela = Parcela(
            cliente_id=cliente_id,
            numero=numero,
            valor=valor,
            data_vencimento=data_vencimento
        )
        db.session.add(parcela)
        db.session.commit()
        flash('Parcela cadastrada!', 'success')
        return redirect(url_for('index'))
    clientes = Cliente.query.all()
    return render_template('nova_parcela.html', clientes=clientes)

@app.route('/parcela/pagar/<int:id>')
def pagar_parcela(id):
    parcela = Parcela.query.get_or_404(id)
    parcela.pago = True
    db.session.commit()
    flash(f'Parcela {parcela.numero} de {parcela.cliente.nome} marcada como paga.', 'success')
    return redirect(url_for('index'))

@app.route('/api/lembretes')
def api_lembretes():
    hoje = datetime.now().date()
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
            'parcela': p.numero,
            'valor': f"R$ {p.valor:.2f}",
            'dias': (p.data_vencimento - hoje).days,
            'telefone': p.cliente.telefone
        })
    return {'lembretes': resultado}

def verificar_lembretes():
    with app.app_context():
        hoje = datetime.now().date()
        alvo = hoje + timedelta(days=5)
        parcelas = Parcela.query.filter(
            Parcela.data_vencimento == alvo,
            Parcela.pago == False
        ).all()
        if parcelas:
            print("\n===== LEMBRETE DE COBRANÇA =====")
            for p in parcelas:
                print(f"Cliente: {p.cliente.nome} | Telefone: {p.cliente.telefone}")
                print(f"Carro: {p.cliente.carro} | Parcela {p.numero} - R$ {p.valor:.2f}")
                print(f"Vence em 5 dias ({p.data_vencimento.strftime('%d/%m/%Y')})")
                print("---------------------------------")
            print(f"Total de {len(parcelas)} lembretes gerados.")
        else:
            print("Nenhum lembrete para hoje.")

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(func=verificar_lembretes, trigger=CronTrigger(hour=8, minute=0, timezone='UTC'))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
