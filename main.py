# api.py
from fastapi import FastAPI, HTTPException
from database import obter_conexao

app = FastAPI(title="API Obras Blumenau")

@app.get("/obras")
def listar_obras():
    conexao = obter_conexao()
    try:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT * FROM obras")
            resultados = cursor.fetchall()
            return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar no banco: {str(e)}")
    finally:
        conexao.close()