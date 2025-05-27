from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
CORS(app)

# 🔧 Configuração de conexão com o MySQL
def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',     # <- Substitua pelo seu usuário
        password='Senai@118',   # <- Substitua pela sua senha
        database='food4you_db'
    )
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
        if e.errno == 1062:  # código de erro para "duplicate entry"
            return jsonify({'message': 'Usuário já existe.'}), 409
        print('Erro MySQL:', e)
        return jsonify({'message': 'Erro no servidor'}), 500
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
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
        usuario = cursor.fetchone()
        if usuario:
            return jsonify({'message': 'Login bem-sucedido!'}), 200
        else:
            return jsonify({'message': 'Email ou senha inválidos'}), 401
    except Error as e:
        print('Erro MySQL:', e)
        return jsonify({'message': 'Erro no servidor'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
