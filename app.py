import streamlit as st
import mysql.connector
import pandas as pd

st.set_page_config(
    page_title="Gestão de Obras - Blumenau",
    page_icon="🚧",
    layout="wide"
)

def conectar_banco():
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",         
            password="admin",          
            database="obrasblumenau"
        )
        return conexao
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def buscar_dados():
    conn = conectar_banco()
    if conn:
        query = "SELECT * FROM obras"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

st.title("🚧 Portal de Acompanhamento de Obras Municipais")
st.markdown("Dados consolidados diretamente do sistema fiscalizador de Blumenau/SC.")

df_obras = buscar_dados()

if not df_obras.empty:
    df_obras['valor_contratado'] = df_obras['valor_contratado'].fillna(0).astype(float)
    df_obras['valor_executado'] = df_obras['valor_executado'].fillna(0).astype(float)
    df_obras['saldo_contrato'] = df_obras['saldo_contrato'].fillna(0).astype(float)
    df_obras['pct_executado'] = df_obras['pct_executado'].fillna(0).astype(float)
    
    st.sidebar.header("Filtros do Painel")
    
    secretarias = ["Todas"] + sorted(list(df_obras["secretaria"].dropna().unique()))
    sec_selecionada = st.sidebar.selectbox("Secretaria:", secretarias)
    
    situacoes = ["Todas"] + sorted(list(df_obras["situacao"].dropna().unique()))
    sit_selecionada = st.sidebar.selectbox("Situação da Obra:", situacoes)
    
    df_filtrado = df_obras.copy()
    if sec_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["secretaria"] == sec_selecionada]
    if sit_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["situacao"] == sit_selecionada]

    st.subheader("📊 Indicadores Gerais")
    col1, col2, col3, col4 = st.columns(4)
    
    total_obras = len(df_filtrado)
    total_contratado = df_filtrado["valor_contratado"].sum()
    total_executado = df_filtrado["valor_executado"].sum()
    media_progresso = df_filtrado["pct_executado"].mean() if total_obras > 0 else 0

    with col1:
        st.metric("Obras Filtradas", f"{total_obras}")
    with col2:
        st.metric("Total Contratado", f"R$ {total_contratado:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
    with col3:
        st.metric("Total Executado (Pago)", f"R$ {total_executado:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
    with col4:
        st.metric("Progresso Médio", f"{media_progresso:.1f}%")

    st.markdown("---")

    st.subheader("📋 Detalhamento das Obras Encontradas")
    
    df_visualizacao = df_filtrado.copy()
    
    st.dataframe(
        df_visualizacao,
        column_config={
            "codigo": "Código",
            "secretaria": "Secretaria",
            "descricao": "Descrição",
            "logradouro": "Logradouro",
            "intervencao": "Intervenção",
            "situacao": "Situação",
            "valor_contratado": st.column_config.NumberColumn("Valor Contratado", format="R$ %.2f"),
            "valor_executado": st.column_config.NumberColumn("Valor Executado", format="R$ %.2f"),
            "saldo_contrato": st.column_config.NumberColumn("Saldo Contrato", format="R$ %.2f"),
            "pct_executado": st.column_config.ProgressColumn("Progresso (%)", min_value=0, max_value=100, format="%.1f%%")
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("📉 Análise e Distribuição Financeira")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.write("**Investimento por Secretaria (R$)**")
        financeiro_sec = df_filtrado.groupby("secretaria")["valor_contratado"].sum().reset_index()
        st.bar_chart(data=financeiro_sec, x="secretaria", y="valor_contratado", color="#1F77B4")
        
    with col_chart2:
        st.write("**Quantidade de Obras por Situação**")
        contagem_situacao = df_filtrado.groupby("situacao")["codigo"].count().reset_index()
        contagem_situacao.columns = ["Situação", "Quantidade"]
        st.bar_chart(data=contagem_situacao, x="Situação", y="Quantidade", color="#FF7F0E")

else:
    st.info("Nenhum dado encontrado. Execute o script de Scraping primeiro para popular a tabela 'obras'.")
