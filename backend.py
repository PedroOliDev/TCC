from flask import Flask, request, jsonify, session , render_template, redirect, url_for
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import date, timedelta
import os
import json

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5500"}})
app.secret_key = 'uma_chave_secreta_segura'


def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='21102110p',
        database='food4you_db'
    )

# ====================== ROTAS ======================

@app.route('/perfil', methods=['GET'])
def perfil():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']

    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome, email, foto_url FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if usuario:
            return jsonify(usuario), 200
        else:
            return jsonify({'message': 'Usuário não encontrado'}), 404

    except Exception as e:
        return jsonify({'message': f'Erro ao buscar perfil: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/assinatura', methods=['POST'])
def criar_assinatura():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    data = request.get_json()
    endereco = data.get('endereco')
    dia = data.get('dia')
    metodo = data.get('metodo')
    usuario_id = session['usuario_id']  
    categoria = data.get('categoria')  
    plano_id = data.get('plano')  

    if not endereco or not dia or not metodo:
        return jsonify({'message': 'Campos obrigatórios faltando'}), 400

    
    plano = 'Plano básico'  
    if categoria and categoria in PLANOS_POR_CATEGORIA:
        planos = PLANOS_POR_CATEGORIA[categoria]
        for p in planos:
            if p['id'] == plano_id:
                plano = p['title']
                break

    if metodo == 'cartao':
        cc = data.get('cc') or {}
        if not cc.get('numero') or not cc.get('validade') or not cc.get('cvv'):
            return jsonify({'message': 'Dados do cartão incompletos'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor()

        if metodo == 'pix':
            detalhe_pag = 'Via PIX'
        else:
            detalhe_pag = f"Cartão final {cc.get('numero')[-4:]}"

        data_inicio = date.today()
        proximo = data_inicio + timedelta(days=30)

        cursor.execute("""
            INSERT INTO assinaturas 
            (id_usuario, data_inicio, status, proximo_pagamento, dia, endereco, metodo_pagamento, detalhe_pagamento, plano)
            VALUES (%s, %s, 'ativa', %s, %s, %s, %s, %s, %s)
        """, (usuario_id, data_inicio, proximo, dia, endereco, metodo, detalhe_pag, plano))

        conn.commit()

        return jsonify({
            'message': f'Assinatura criada com sucesso! {detalhe_pag}',
            'assinatura': {
                'data_inicio': str(data_inicio),
                'proximo_pagamento': str(proximo),
                'status': 'ativa',
                'dia': dia,
                'endereco': endereco,
                'metodo': metodo,
                'plano': plano
            }
        }), 200

    except Error as e:
        return jsonify({'message': f'Erro ao criar assinatura: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/register', methods=['POST'])
def register():
    dados = request.get_json()
    nome = dados.get('name')
    email = dados.get('email')
    senha = dados.get('password')

    if not email or not senha or not nome:
        return jsonify({'message': 'Preencha todas as tabelas'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            'INSERT INTO usuarios (nome, email, senha, foto_url) VALUES (%s, %s, %s, NULL)', 
            (nome, email, senha)
        )
        conn.commit()
        usuario_id = cursor.lastrowid  

        
        session['usuario_id'] = usuario_id
        session['usuario_nome'] = nome
        session['usuario_email'] = email

        usuario = {
            'id': usuario_id,
            'nome': nome,
            'email': email,
            'foto_url': None
        }

        return jsonify({'message': 'Usuário cadastrado com sucesso!', 'usuario': usuario}), 201

    except Error as e:
        if e.errno == 1062:
            return jsonify({'message': 'Usuário já existe, vá para página de entrada.'}), 409
        return jsonify({'message': f'Erro no servidor: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('password')
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
        usuario = cursor.fetchone()
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            session['is_admin'] = usuario['is_admin'] == 1  
            return jsonify({'message': 'Login bem-sucedido!', 'usuario': usuario}), 200
        else:
            return jsonify({'message': 'Email ou senha inválidos'}), 401
    except Error as e:
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



@app.route('/register-google', methods=['POST'])
def register_google():
    dados = request.get_json()
    token = dados.get('token')

    if not token:
        return jsonify({'message': 'Token não fornecido'}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            grequests.Request(),
            "844429812632-gi775pp6vfiqo2kbj5h0h9bam1u90pon.apps.googleusercontent.com"
        )

        email = idinfo.get('email')
        nome = idinfo.get('name')

        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        usuario = cursor.fetchone()

        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            session['is_admin'] = usuario['is_admin'] == 1  
            return jsonify({'message': 'Login com Google feito com sucesso!', 'usuario': usuario}), 200
        else:
            cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, 'GOOGLE'))
            conn.commit()
            usuario_id = cursor.lastrowid
            usuario = {
                'id': usuario_id,
                'nome': nome,
                'email': email,
                'foto_url': None,
                'is_admin': 0  
            }
            session['usuario_id'] = usuario_id
            session['usuario_nome'] = nome
            session['usuario_email'] = email
            session['is_admin'] = False  
            return jsonify({'message': 'Usuário Google cadastrado e logado com sucesso!', 'usuario': usuario}), 201

    except ValueError:
        return jsonify({'message': 'Token inválido'}), 401
    except Error as e:
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/check_admin', methods=['GET'])
def check_admin():
    if 'usuario_id' not in session:
        return jsonify({'is_admin': False}), 200
    is_admin = session.get('is_admin', False)
    return jsonify({'is_admin': is_admin}), 200

@app.route('/atualizar-perfil', methods=['POST'])
def atualizar_perfil():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    foto = request.files.get('foto')

    try:
        conn = conectar()
        cursor = conn.cursor()

        foto_url = None
        if foto:
            
            pasta_fotos = os.path.join(app.root_path, 'static', 'fotos')
            if not os.path.exists(pasta_fotos):
                os.makedirs(pasta_fotos)

        
            extensao = os.path.splitext(foto.filename)[1]
            caminho_foto = os.path.join(pasta_fotos, f'{usuario_id}{extensao}')
            foto.save(caminho_foto)

            
            foto_url = f'/static/fotos/{usuario_id}{extensao}'

        
        query = "UPDATE usuarios SET nome=%s, senha=%s"
        valores = [nome, senha]
        if foto_url:
            query += ", foto_url=%s"
            valores.append(foto_url)
        query += " WHERE id=%s"
        valores.append(usuario_id)

        cursor.execute(query, valores)
        conn.commit()

        
        session['usuario_nome'] = nome
        if foto_url:
            session['usuario_foto'] = foto_url

        return jsonify({'message': 'Perfil atualizado com sucesso', 'foto_url': foto_url}), 200

    except Exception as e:
        return jsonify({'message': f'Erro ao atualizar perfil: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout realizado com sucesso'}), 200


@app.route('/historico-assinaturas', methods=['GET'])
def historico_assinaturas():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']

    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT plano, status, data_inicio AS data
            FROM assinaturas
            WHERE id_usuario = %s
            ORDER BY data_inicio DESC
        """, (usuario_id,))
        historico = cursor.fetchall()

        
        resultado = []
        for item in historico:
            resultado.append({
                'plano': item['plano'] or 'Plano básico',
                'status': item['status'].capitalize(),
                'data': str(item['data'])
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'message': f'Erro ao carregar histórico: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/assinaturas-mais-consumidas', methods=['GET'])
def assinaturas_mais_consumidas():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']

    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT plano, COUNT(*) AS total
            FROM assinaturas
            WHERE id_usuario = %s
            GROUP BY plano
            ORDER BY total DESC
            LIMIT 5
        """, (usuario_id,))
        resultados = cursor.fetchall()

        
        lista = []
        for item in resultados:
            plano = item['plano'] or 'Plano básico'
            dias = item['total'] * 30  
            lista.append({
                'plano': plano,
                'dias': dias
            })

        return jsonify(lista), 200

    except Exception as e:
        return jsonify({'message': f'Erro ao carregar assinaturas mais consumidas: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



@app.route('/admin')
def admin_page():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return redirect(url_for('login_page'))  
    return render_template('admin.html')  


@app.route('/api/restaurantes/<int:id>', methods=['GET'])
def get_restaurante(id):
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM restaurantes WHERE id = %s", (id,))
        restaurante = cursor.fetchone()
        
        if not restaurante:
            return jsonify({'message': 'Restaurante não encontrado'}), 404
        
        return jsonify(restaurante), 200
    
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



@app.route('/api/restaurantes', methods=['GET'])
def get_restaurantes():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM restaurantes")
        restaurantes = cursor.fetchall()
        return jsonify(restaurantes), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



@app.route('/api/restaurantes', methods=['POST'])
def create_restaurante():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    nome = request.form.get('nome')
    endereco = request.form.get('endereco', '')
    telefone = request.form.get('telefone', '')
    descricao = request.form.get('descricao', '')
    categoria = request.form.get('categoria', 'lanches')
    rating = request.form.get('rating', '4.0')
    delivery_time = request.form.get('delivery_time', '20-30 min')
    delivery_fee = request.form.get('delivery_fee', 'Grátis')
    tags = request.form.get('tags', '[]')
    badge = request.form.get('badge')

    foto_url = None
    foto = request.files.get('foto') 
    if foto:
        pasta_fotos = os.path.join(app.root_path, 'static', 'imagens')
        if not os.path.exists(pasta_fotos):
            os.makedirs(pasta_fotos)
        
        extensao = os.path.splitext(foto.filename)[1]
        nome_arquivo = f'restaurante_{nome.replace(" ", "_")}{extensao}'
        caminho_foto = os.path.join(pasta_fotos, nome_arquivo)
        try:
            foto.save(caminho_foto)
            foto_url = f'/static/imagens/{nome_arquivo}'  
            print(f"Imagem salva com sucesso: {foto_url}")  
        except Exception as e:
            print(f"Erro ao salvar imagem: {str(e)}")  
            foto_url = None  
        
       
        
    if not nome:
        return jsonify({'message': 'Nome é obrigatório'}), 400
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO restaurantes (nome, endereco, telefone, descricao, categoria, rating, delivery_time, delivery_fee, tags, badge, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (nome, endereco, telefone, descricao, categoria, rating, delivery_time, delivery_fee, tags, badge, foto_url or '../static/imagens/default_restaurante.png'))
        conn.commit()
        return jsonify({'message': 'Restaurante criado com sucesso'}), 201
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/restaurantes/<int:id>', methods=['PUT'])
def update_restaurante(id):
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403

    nome = request.form.get('nome')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    descricao = request.form.get('descricao')
    categoria = request.form.get('categoria')
    rating = request.form.get('rating')
    delivery_time = request.form.get('delivery_time')
    delivery_fee = request.form.get('delivery_fee')
    tags = request.form.get('tags')
    badge = request.form.get('badge')
    foto = request.files.get('foto')

    foto_url = None
    if foto:
        pasta_fotos = os.path.join(app.root_path, 'static', 'imagens')
        if not os.path.exists(pasta_fotos):
            os.makedirs(pasta_fotos)

        extensao = os.path.splitext(foto.filename)[1]
        nome_arquivo = f'restaurante_{nome.replace(" ", "_")}{extensao}'
        caminho_foto = os.path.join(pasta_fotos, nome_arquivo)
        foto.save(caminho_foto)
        foto_url = f'/static/imagens/{nome_arquivo}'

    try:
        conn = conectar()
        cursor = conn.cursor()

        sql = """
            UPDATE restaurantes
            SET nome=%s, endereco=%s, telefone=%s, descricao=%s, categoria=%s,
                rating=%s, delivery_time=%s, delivery_fee=%s, tags=%s, badge=%s
        """
        valores = [nome, endereco, telefone, descricao, categoria, rating, delivery_time, delivery_fee, tags, badge]

        if foto_url:
            sql += ", image=%s"
            valores.append(foto_url)

        sql += " WHERE id=%s"
        valores.append(id)

        cursor.execute(sql, valores)
        conn.commit()

        return jsonify({'message': 'Restaurante atualizado com sucesso'}), 200

    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/restaurantes/<int:id>', methods=['DELETE'])
def delete_restaurante(id):
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM restaurantes WHERE id=%s", (id,))
        conn.commit()
        return jsonify({'message': 'Restaurante deletado com sucesso'}), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome, email, foto_url, is_admin FROM usuarios")
        clientes = cursor.fetchall()
        return jsonify(clientes), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/clientes/<int:id>', methods=['PUT'])
def update_cliente(id):
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    data = request.get_json()
    nome = data.get('nome')
    is_admin = data.get('is_admin', 0)
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nome=%s, is_admin=%s WHERE id=%s", (nome, is_admin, id))
        conn.commit()
        return jsonify({'message': 'Cliente atualizado com sucesso'}), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/clientes/<int:id>', methods=['DELETE'])
def delete_cliente(id):
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id=%s", (id,))
        conn.commit()
        return jsonify({'message': 'Cliente deletado com sucesso'}), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/restaurantes/categoria/<categoria>', methods=['GET'])
def get_restaurantes_por_categoria(categoria):
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome AS name, endereco AS cuisine, rating, delivery_time, delivery_fee, tags, badge, image
            FROM restaurantes
            WHERE categoria = %s
        """, (categoria,))
        restaurantes = cursor.fetchall()
        
        for r in restaurantes:
            try:
                r['tags'] = json.loads(r['tags']) if r['tags'] else []
            except json.JSONDecodeError:
                r['tags'] = []
        return jsonify(restaurantes), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


PLANOS_POR_CATEGORIA = {
    "Lanches": [
        {
            "id": "basic",
            "title": "Plano Básico",
            "description": "Ideal para quem quer experimentar nossos sabores",
            "price": "R$ 19,90",
            "period": "/mês",
            "features": ["Lanches até R$ 20,00", "Entrega grátis", "Lanches Novos todo Mes", "Suporte prioritário"],
            "popular": False
        },
        {
            "id": "premium",
            "title": "Plano Premium",
            "description": "Para os verdadeiros amantes de hambúrguer",
            "price": "R$ 39,90",
            "period": "/mês",
            "popular": True,
            "features": ["Lanches acima de R$ 30,00", "Entrega grátis", "Acesso antecipado a novos produtos", "Brinde mensal exclusivo", "Suporte VIP 24/7"]
        },
        {
            "id": "family",
            "title": "Plano Família",
            "description": "Perfeito para compartilhar com toda a família",
            "price": "R$ 59,90",
            "period": "/mês",
            "features": ["Lanches acima de R$ 40,00 para até 4 pessoas", "Entrega grátis", "Válido para até 4 pessoas", "Combos familiares exclusivos", "Festa de aniversário grátis"]
        }
    ],
    "pizzas": [
        {
            "id": "basic",
            "title": "Pizza Lover",
            "description": "Para os amantes de pizza",
            "price": "R$ 29,90",
            "period": "/mês",
            "features": ["20% de desconto em pizzas", "Entrega grátis em pedidos acima de R$ 40", "Pizza grátis no seu aniversário", "Acesso a sabores exclusivos"],
            "popular": False
        },
        {
            "id": "premium",
            "title": "Pizza Master",
            "description": "A experiência definitiva em pizzas",
            "price": "R$ 49,90",
            "period": "/mês",
            "popular": True,
            "features": ["30% de desconto em todas as pizzas", "Entrega grátis ilimitada", "2 pizzas grátis por mês", "Acesso antecipado a novos sabores", "Personalização exclusiva de pizzas"]
        }
    ],
    
    
    "Italiana": [
        { 
            "id": "basic",
            "title": "Plano Italiano",
            "description": "Para os amantes da culinária italiana",
            "price": "R$ 34,90",
            "period": "/mês",
            "features": ["20% de desconto em pratos italianos", "Entrega grátis em pedidos acima de R$ 50", "Acesso a pratos exclusivos"],
            "popular": False
        },
        {
            "id": "premium",
            "title": "Plano Gourmet Italiano",
            "description": "Experiência completa da culinária italiana",
            "price": "R$ 59,90",
            "period": "/mês",
            "popular": True,
            "features": ["30% de desconto em todos os pratos italianos", "Entrega grátis ilimitada", "2 pratos gourmet grátis por mês", "Acesso antecipado a novos pratos"]
        }
    ],
    "Japonesa": [
        {
            "id": "basic",
            "title": "Plano Japonês",
            "description": "Para os amantes da culinária japonesa",
            "price": "R$ 39,90",
            "period": "/mês",
            "features": ["20% de desconto em pratos japoneses", "Entrega grátis em pedidos acima de R$ 60", "Acesso a pratos exclusivos"],
            "popular": False
        },
        {
            "id": "premium",
            "title": "Plano Gourmet Japonês",
            "description": "Experiência completa da culinária japonesa",
            "price": "R$ 69,90",
            "period": "/mês",
            "popular": True,
            "features": ["30% de desconto em todos os pratos japoneses", "Entrega grátis ilimitada", "2 pratos gourmet grátis por mês", "Acesso antecipado a novos pratos"]
        }   
    ],
    
    "default": [ 
        {
            "id": "basic",
            "title": "Plano Básico",
            "description": "Plano padrão",
            "price": "R$ 19,90",
            "period": "/mês",
            "features": ["Descontos básicos", "Entrega grátis"],
            "popular": False
        }
    ]

}


@app.route('/restaurante/<int:id>', methods=['GET'])
def get_restaurante_com_planos(id):
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT nome AS name, categoria AS cuisine, image, rating, delivery_time AS deliveryTime, delivery_fee AS deliveryFee
            FROM restaurantes
            WHERE id = %s
        """, (id,))
        restaurante = cursor.fetchone()
        
        if not restaurante:
            return jsonify({'message': 'Restaurante não encontrado'}), 404
        
        
        categoria = restaurante.get('cuisine', 'default')
        plans = PLANOS_POR_CATEGORIA.get(categoria, PLANOS_POR_CATEGORIA['default'])
        
        
        restaurante['plans'] = plans
        
        return jsonify(restaurante), 200
    
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/graficos/categorias-restaurantes', methods=['GET'])
def graficos_categorias_restaurantes():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT categoria, COUNT(*) AS total
            FROM restaurantes
            GROUP BY categoria
            ORDER BY total DESC
        """)
        dados = cursor.fetchall()
        return jsonify(dados), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/graficos/planos-assinaturas', methods=['GET'])
def graficos_planos_assinaturas():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT plano, COUNT(*) AS total
            FROM assinaturas
            GROUP BY plano
            ORDER BY total DESC
        """)
        dados = cursor.fetchall()
        return jsonify(dados), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/graficos/categorias-assinaturas', methods=['GET'])
def graficos_categorias_assinaturas():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.categoria, COUNT(a.id) AS total_assinaturas
            FROM assinaturas a
            JOIN restaurantes r ON a.plano LIKE CONCAT('%', r.categoria, '%')
            GROUP BY r.categoria
            ORDER BY total_assinaturas DESC
        """)
        dados = cursor.fetchall()
        return jsonify(dados), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/graficos/usuarios-tipo', methods=['GET'])
def graficos_usuarios_tipo():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT CASE WHEN is_admin = 1 THEN 'Admin' ELSE 'Usuário Comum' END AS tipo,
                COUNT(*) AS total
            FROM usuarios
            GROUP BY is_admin
        """)
        dados = cursor.fetchall()
        return jsonify(dados), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
@app.route('/api/graficos/assinaturas-mensal', methods=['GET'])
def graficos_assinaturas_mensal():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return jsonify({'message': 'Acesso negado'}), 403
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DATE_FORMAT(data_inicio, '%Y-%m') AS mes, COUNT(*) AS total
            FROM assinaturas
            GROUP BY mes
            ORDER BY mes
        """)
        dados = cursor.fetchall()
        return jsonify(dados), 200
    except Error as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
@app.route('/graficos')
def graficos_page():
    if 'usuario_id' not in session or not session.get('is_admin', False):
        return redirect(url_for('login_page'))  
    return render_template('graficos.html') 


@app.route('/avaliar', methods=['POST'])
def avaliar_restaurante():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    data = request.get_json()
    restaurante_id = data.get('restaurante_id')
    estrelas = data.get('estrelas')
    comentario = data.get('comentario', '')

    if not restaurante_id or not estrelas or estrelas < 1 or estrelas > 5:
        return jsonify({'message': 'Dados inválidos. Estrelas devem ser de 1 a 5.'}), 400

    usuario_id = session['usuario_id']

    try:
        conn = conectar()
        cursor = conn.cursor()

        
        cursor.execute("""
            SELECT id FROM avaliacoes WHERE usuario_id = %s AND restaurante_id = %s
        """, (usuario_id, restaurante_id))
        if cursor.fetchone():
            return jsonify({'message': 'Você já avaliou este restaurante.'}), 409

        
        cursor.execute("""
            INSERT INTO avaliacoes (usuario_id, restaurante_id, estrelas, comentario)
            VALUES (%s, %s, %s, %s)
        """, (usuario_id, restaurante_id, estrelas, comentario))
        conn.commit()

        
        cursor.execute("""
            SELECT AVG(estrelas) AS media FROM avaliacoes WHERE restaurante_id = %s
        """, (restaurante_id,))
        media = cursor.fetchone()[0]
        if media:
            cursor.execute("""
                UPDATE restaurantes SET rating = %s WHERE id = %s
            """, (round(media, 1), restaurante_id))
            conn.commit()

        return jsonify({'message': 'Avaliação enviada com sucesso!'}), 201

    except Error as e:
        return jsonify({'message': f'Erro ao avaliar: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/avaliacoes/<int:restaurante_id>', methods=['GET'])
def get_avaliacoes(restaurante_id):
    try:
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.estrelas, a.comentario, a.data, u.nome AS usuario_nome
            FROM avaliacoes a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.restaurante_id = %s
            ORDER BY a.data DESC
        """, (restaurante_id,))
        avaliacoes = cursor.fetchall()
        return jsonify(avaliacoes), 200
    except Error as e:
        return jsonify({'message': f'Erro ao carregar avaliações: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



if __name__ == '__main__':
    app.run(debug=True)
