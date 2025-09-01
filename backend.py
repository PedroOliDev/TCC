from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import date, timedelta

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5500"}})
app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_secreta_segura')

#a senha esta a mostra pois é so um trabalho escolar, mas em um ambiente real deve ser protegida
def conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "food4you"),
        user=os.environ.get("DB_USER" , "render "),
        password=os.environ.get("DB_PASS", "21102110p"),
        dbname=os.environ.get("DB_NAME", "food4you"),
        cursor_factory=RealDictCursor
    )



@app.route('/perfil', methods=['GET'])
def perfil():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']

    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT nome, email, foto_url FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if usuario:
            return jsonify(usuario), 200
        else:
            return jsonify({'message': 'Usuário não encontrado'}), 404

    except Exception as e:
        return jsonify({'message': f'Erro ao buscar perfil: {str(e)}'}), 500
    finally:
        if conn:
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

    if not endereco or not dia or not metodo:
        return jsonify({'message': 'Campos obrigatórios faltando'}), 400

    if metodo == 'cartao':
        cc = data.get('cc') or {}
        if not cc.get('numero') or not cc.get('validade') or not cc.get('cvv'):
            return jsonify({'message': 'Dados do cartão incompletos'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor()

        
        if metodo == 'pix':
            pagamento_ok = True  
            detalhe_pag = 'Via PIX'
        else:
            pagamento_ok = True
            detalhe_pag = f"Cartão final {cc.get('numero')[-4:]}"

        if not pagamento_ok:
            return jsonify({'message': 'Pagamento recusado'}), 402

        data_inicio = date.today()
        proximo = data_inicio + timedelta(days=30)

        cursor.execute("""
            INSERT INTO assinaturas 
            (id_usuario, data_inicio, status, proximo_pagamento, dia, endereco, metodo_pagamento, detalhe_pagamento)
            VALUES (%s, %s, 'ativa', %s, %s, %s, %s, %s)
        """, (usuario_id, data_inicio, proximo, dia, endereco, metodo, detalhe_pag))

        conn.commit()

        return jsonify({
            'message': f'Assinatura criada com sucesso! {detalhe_pag}',
            'assinatura': {
                'data_inicio': str(data_inicio),
                'proximo_pagamento': str(proximo),
                'status': 'ativa',
                'dia': dia,
                'endereco': endereco,
                'metodo': metodo
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Erro ao criar assinatura: {str(e)}'}), 500
    finally:
        if conn:
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
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO usuarios (nome, email, senha, foto_url) VALUES (%s, %s, %s, NULL)', 
            (nome, email, senha)
        )
        conn.commit()

        cursor.execute('SELECT * FROM usuarios WHERE email = %s AND nome = %s', (email, nome))
        usuario = cursor.fetchone()

        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome']
        session['usuario_email'] = usuario['email']

        return jsonify({'message': 'Usuário cadastrado com sucesso!', 'usuario': usuario}), 201

    except Exception as e:
        return jsonify({'message': f'Erro no servidor: {str(e)}'}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('password')

    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
        usuario = cursor.fetchone()

        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            return jsonify({'message': 'Login bem-sucedido!', 'usuario': usuario}), 200
        else:
            return jsonify({'message': 'Email ou senha inválidos'}), 401

    except Exception as e:
        return jsonify({'message': f'Erro no servidor: {str(e)}'}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout realizado com sucesso'}), 200


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
            "SEU_CLIENT_ID_DO_GOOGLE"
        )

        email = idinfo.get('email')
        nome = idinfo.get('name')  

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        usuario = cursor.fetchone()

        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            return jsonify({'message': 'Login com Google bem-sucedido!', 'usuario': usuario}), 200
        else:
            cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, 'GOOGLE'))
            conn.commit()
            cursor.execute('SELECT * FROM usuarios WHERE email = %s AND nome = %s', (email, nome))
            usuario = cursor.fetchone()
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            return jsonify({'message': 'Usuário Google cadastrado e logado com sucesso!', 'usuario': usuario}), 201

    except Exception as e:
        return jsonify({'message': f'Erro no servidor: {str(e)}'}), 500
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
