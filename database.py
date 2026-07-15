# database.py
import pymysql
import os

def obter_conexao():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "admin"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_DATABASE", "obrasblumenau"),
        cursorclass=pymysql.cursors.DictCursor 
    )