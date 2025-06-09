from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

app = Flask(__name__)
CORS(app)

# 🔧 Configuração de conexão com o MySQL
def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Senai@118',
        database='food4you_db'
    )

# 📝 Rota para inscrição (formulário separado)
@app.route("/inscricao", methods=["POST"])
def inscricao():
    data = request.get_json()
    nome = data.get("nome")
    endereco = data.get("endereco")
    email = data.get("email")
    dia = data.get("dia")

    try:
        db = conectar()
        cursor = db.cursor()
        cursor.execute("INSERT INTO inscricoes (nome, endereco, email, dia) VALUES (%s, %s, %s, %s)",
                       (nome, endereco, email, dia))
        db.commit()
        return jsonify({"message": "Inscrição salva com sucesso."}), 200
    except Exception as e:
        return jsonify({"message": f"Erro ao salvar: {str(e)}"}), 500
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()

# 🟢 Cadastro tradicional (email e senha)
@app.route('/register', methods=['POST'])
def register():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('password')

    if not email or not senha:
        return jsonify({'message': 'Email e senha são obrigatórios'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (email, senha) VALUES (%s, %s)', (email, senha))
        conn.commit()
        return jsonify({'message': 'Usuário cadastrado com sucesso!'}), 201
    except Error as e:
        if e.errno == 1062:
            return jsonify({'message': 'Usuário já existe, vá para página de entrada.'}), 409
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 🟢 Login tradicional
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
            return jsonify({'message': 'Login bem-sucedido!'}), 200
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
        # 🧠 Verificar o token JWT com o Google
        idinfo = id_token.verify_oauth2_token(
            token,
            grequests.Request(),
            "844429812632-gi775pp6vfiqo2kbj5h0h9bam1u90pon.apps.googleusercontent.com"
        )

        email = idinfo.get('email')

        if not email:
            return jsonify({'message': 'Não foi possível obter o email da conta Google'}), 400

        # 👤 Verifica se o usuário já está no banco
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        usuario = cursor.fetchone()

        if usuario:
            return jsonify({'message': 'Login com Google bem-sucedido!'}), 200
        else:
            # Cadastra o usuário no banco com senha nula
            cursor.execute('INSERT INTO usuarios (email, senha) VALUES (%s, %s)', (email, 'GOOGLE'))
            conn.commit()
            return jsonify({'message': 'Usuário Google cadastrado com sucesso!'}), 201
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
