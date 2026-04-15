import os
from flask import Flask, render_template, request, redirect, url_for, flash
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

# --- 🆕 FUNÇÃO DE ENVIO DE WHATSAPP VIA CALLMEBOT (MENSAGEM REFORMULADA) ---
def enviar_whatsapp_callmebot(numero_destino, nome_cliente, parcela_num, parcela_total, carro, data_venc, valor):
    api_key = os.environ.get('CALLMEBOT_API_KEY')
    seu_numero = os.environ.get('CALLMEBOT_PHONE_NUMBER')
    
    if not api_key or not seu_numero:
        print("❌ Erro: Chave API ou número de telefone do CallMeBot não configurados.")
        return False

    data_formatada = data_venc.strftime('%d/%m/%Y') if hasattr(data_venc, 'strftime') else data_venc
    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Mensagem profissional com pedido de comprovante
    mensagem = (
        f"Olá {nome_cliente}, tudo bem?\n\n"
        f"Passando para lembrar que a parcela {parcela_num}/{parcela_total} do seu contrato ({carro}) "
        f"vence em {data_formatada}.\n"
        f"💵 Valor: R$ {valor_formatado}\n\n"
        f"Após efetuar o pagamento, por favor, envie o comprovante por aqui mesmo. "
        f"Assim já dou baixa no sistema e evito novos lembretes.\n\n"
        f"Fico à disposição para qualquer dúvida. Tenha um ótimo dia!"
    )
    
    mensagem_codificada = quote(mensagem)
    url = f"https://api.callmebot.com/whatsapp.php?phone={seu_numero}&text={mensagem_codificada}&apikey={api_key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"✅ WhatsApp enviado para {nome_cliente} ({numero_destino})")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp para {nome_cliente}: {e}")
        return False

# --- ROTAS ---
@app.route('/')
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

@app.route('/api/todas-parcelas')
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

# --- VERIFICAÇÃO DIÁRIA COM ENVIO AUTOMÁTICO DE WHATSAPP ---
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
            for p in parcelas:
                cliente = p.cliente
                telefone_limpo = cliente.telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                
                enviar_whatsapp_callmebot(
                    numero_destino=telefone_limpo,
                    nome_cliente=cliente.nome,
                    parcela_num=p.numero,
                    parcela_total=cliente.quantidade_parcelas,
                    carro=cliente.carro,
                    data_venc=p.data_vencimento,
                    valor=p.valor
                )
        else:
            print("Nenhum lembrete para hoje.")

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(func=verificar_lembretes, trigger=CronTrigger(hour=8, minute=0))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# --- CRIAÇÃO DAS TABELAS ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
