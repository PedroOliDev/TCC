from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from flask import Flask, session

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5500"}})



app.secret_key = 'uma_chave_secreta_segura'

# 🔧 Configuração de conexão com o MySQL
def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='21102110p',
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
        cursor.execute("SELECT nome, email, endereco, dia, foto_url FROM usuarios WHERE id = %s", (usuario_id,))
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
@app.route("/inscricao", methods=["POST"])
def inscricao():
    data = request.get_json()

    endereco = data.get("endereco")
    email = data.get("email")
    dia = data.get("dia")

    try:
        db = conectar()
        cursor = db.cursor()
        cursor.execute("INSERT INTO inscricoes (endereco, email, dia) VALUES ( %s, %s, %s)",
                       ( endereco, email, dia))
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
    nome = dados.get('name')
    email = dados.get('email')
    senha = dados.get('password')

    if not email or not senha or not nome:
        return jsonify({'message': 'preencha todas as tabelas'}), 400

    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (nome, email, senha, endereco, dia, foto_url) VALUES (%s, %s, %s, NULL, NULL, NULL)', 
               (nome, email, senha))
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



@app.route('/atualizar-perfil', methods=['POST'])
def atualizar_perfil():
    if 'usuario_id' not in session:
        return jsonify({'message': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    endereco = request.form.get('endereco')
    dia = request.form.get('dia')
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
        query = "UPDATE usuarios SET nome=%s, senha=%s, endereco=%s, dia=%s"
        valores = [nome, senha, endereco, dia]

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

