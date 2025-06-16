from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from flask import Flask, session
from datetime import date, timedelta

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5500"}})



app.secret_key = 'uma_chave_secreta_segura'

# 🔧 Configuração de conexão com o MySQL
def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Senai@118',
        database='food4you_db'
    )

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


# 📝 Rota para inscrição (formulário separado)
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

    # Simulação de validação de dados do cartão
    if metodo == 'cartao':
        cc = data.get('cc') or {}
        if not cc.get('numero') or not cc.get('validade') or not cc.get('cvv'):
            return jsonify({'message': 'Dados do cartão incompletos'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor()

        # Simulação do processo de pagamento
        if metodo == 'pix':
            pagamento_ok = True  # suponha aprovação imediata
            detalhe_pag = 'Via PIX'
        else:
            pagamento_ok = True  # suponha aprovação
            detalhe_pag = f"Cartão final {cc.get('numero')[-4:]}"

        if not pagamento_ok:
            return jsonify({'message': 'Pagamento recusado'}), 402

        data_inicio = date.today()
        proximo = data_inicio + timedelta(days=30)

        cursor.execute("""
            INSERT INTO assinaturas 
              (id_usuario, data_inicio, status, proximo_pagamento, dia, endereco)
            VALUES (%s, %s, 'ativa', %s, %s, %s)
        """, (usuario_id, data_inicio, proximo, dia, endereco))
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

        # Busca o usuário recém cadastrado
        cursor.execute('SELECT * FROM usuarios WHERE email = %s AND nome = %s', (email, nome))
        usuario = cursor.fetchone()

        # Armazena dados na sessão
        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome']
        session['usuario_email'] = usuario['email']

        return jsonify({'message': 'Usuário cadastrado com sucesso!', 'usuario': usuario}), 201

    except Error as e:
        if e.errno == 1062:
            return jsonify({'message': 'Usuário já existe, vá para página de entrada.'}), 409
        return jsonify({'message': f'Erro no servidor: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()




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

        # Salvar a foto (opcional)
        foto_url = None
        if foto:
            caminho_foto = f'static/fotos/{usuario_id}.jpg'
            foto.save(caminho_foto)
            foto_url = f'/static/fotos/{usuario_id}.jpg'

        # Atualiza os dados
        query = "UPDATE usuarios SET nome=%s, senha=%s"
        valores = [nome, senha]

        if foto_url:
            query += ", foto_url=%s"
            valores.append(foto_url)

        query += " WHERE id=%s"
        valores.append(usuario_id)

        cursor.execute(query, valores)
        conn.commit()

        return jsonify({'message': 'Perfil atualizado com sucesso'}), 200

    except Exception as e:
        return jsonify({'message': f'Erro ao atualizar perfil: {str(e)}'}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# 🟢 Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout realizado com sucesso'}), 200



# 🟢 Login tradicional
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
            return jsonify({'message': 'Login bem-sucedido!', 'usuario': usuario}), 200
        else:
            return jsonify({'message': 'Email ou senha inválidos'}), 401
    except Error as e:
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# 🟡 Cadastro/Login com Google
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
            # ✅ Login automático
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            return jsonify({'message': 'Login com Google bem-sucedido!', 'usuario': usuario}), 200
        else:
            # ✅ Cadastro
            cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, 'GOOGLE'))
            conn.commit()

            # ✅ Buscar novamente e logar
            cursor.execute('SELECT * FROM usuarios WHERE email, nome = %s,%s', (email,nome))
            usuario = cursor.fetchone()
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']

            return jsonify({'message': 'Usuário Google cadastrado e logado com sucesso!', 'usuario': usuario}), 201

    except ValueError:
        return jsonify({'message': 'Token inválido'}), 401
    except Error as e:
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

            

if __name__ == '__main__':
    app.run(debug=True)

