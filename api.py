from flask import Flask, jsonify
from database import obter_conexao

app = Flask(__name__)

@app.route("/obras", methods=["GET"])
def listar_obras():
    conexao = obter_conexao()
    try:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT * FROM obras")
            resultados = cursor.fetchall()
            return jsonify(resultados)  
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar no banco: {str(e)}"}), 500
    finally:
        conexao.close()

if __name__ == "__main__":
    print("Iniciando API Flask em http://127.0.0.1:5000/obras")
    app.run(debug=True, port=5000)