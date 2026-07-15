import sys
import time
import re
import unicodedata
from datetime import datetime
from playwright.sync_api import sync_playwright
from database import obter_conexao

# Garante exibição perfeita de caracteres especiais no terminal do Windows
sys.stdout.reconfigure(encoding='utf-8')

# --- FUNÇÕES AUXILIARES DE TRATAMENTO DE DADOS ---

def limpar_texto_utf(texto):
    """
    Remove caracteres de controle, normaliza quebras de linha, espaços duplicados
    e limpa sujeiras de codificação mantendo acentos e pontuações do Português.
    """
    if not texto:
        return ""
    
    # Decodifica possíveis sequências UTF-8 quebradas e remove espaços extras nas pontas
    texto = texto.strip()
    
    # Substitui quebras de linha, tabulações e múltiplos espaços por um único espaço
    texto = re.sub(r'\s+', ' ', texto)
    
    # Normaliza unicode (corrige problemas com caracteres combinados, ex: "a" + "˜" -> "ã")
    texto = unicodedata.normalize('NFC', texto)
    
    # Remove caracteres invisíveis/controle (ASCII de 0 a 31 e de 127 a 159)
    texto = "".join(ch for ch in texto if unicodedata.category(ch)[0] != "C")
    
    return texto

def limpar_decimal(texto):
    if not texto or "Não" in texto or "-" in texto or texto.strip() == "":
        return None
    try:
        limpo = re.sub(r'[^\d,.-]', '', texto).strip()
        limpo = limpo.replace('.', '').replace(',', '.')
        return float(limpo) if limpo else None
    except Exception:
        return None

def limpar_percentual(texto):
    if not texto or texto.strip() == "":
        return None
    try:
        limpo = texto.replace('%', '').replace(',', '.').strip()
        return float(limpo)
    except Exception:
        return None

def formatar_data(texto):
    if not texto or "/" not in texto:
        return None
    try:
        texto_limpo = texto.strip()
        return datetime.strptime(texto_limpo, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return None

# --- BANCO DE DADOS ---

def salvar_ou_atualizar_obra(obra):
    conexao = obter_conexao()
    try:
        with conexao.cursor() as cursor:
            sql = """
                INSERT INTO obras (
                    codigo, secretaria, descricao, logradouro, intervencao, situacao,
                    num_licitacao, num_contrato, data_contrato, num_ordem_servico,
                    tipo_recurso, inicio_obra, limite_execucao, termino_contrato,
                    valor_contratado, valor_executado, saldo_contrato, pct_executado
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    secretaria = VALUES(secretaria),
                    descricao = VALUES(descricao),
                    logradouro = VALUES(logradouro),
                    intervencao = VALUES(intervencao),
                    situacao = VALUES(situacao),
                    num_licitacao = VALUES(num_licitacao),
                    num_contrato = VALUES(num_contrato),
                    data_contrato = VALUES(data_contrato),
                    num_ordem_servico = VALUES(num_ordem_servico),
                    tipo_recurso = VALUES(tipo_recurso),
                    inicio_obra = VALUES(inicio_obra),
                    limite_execucao = VALUES(limite_execucao),
                    termino_contrato = VALUES(termino_contrato),
                    valor_contratado = VALUES(valor_contratado),
                    valor_executado = VALUES(valor_executado),
                    saldo_contrato = VALUES(saldo_contrato),
                    pct_executado = VALUES(pct_executado);
            """
            cursor.execute(sql, (
                obra.get('codigo'), 
                obra.get('secretaria'), 
                obra.get('descricao'), 
                obra.get('logradouro'), 
                obra.get('intervencao'), 
                obra.get('situacao'),
                obra.get('num_licitacao'),
                obra.get('num_contrato'),
                obra.get('data_contrato'),
                obra.get('num_ordem_servico'),
                obra.get('tipo_recurso'),
                obra.get('inicio_obra'),
                obra.get('limite_execucao'),
                obra.get('termino_contrato'),
                obra.get('valor_contratado'),
                obra.get('valor_executado'),
                obra.get('saldo_contrato'),
                obra.get('pct_executado')
            ))
            conexao.commit()
    except Exception as e:
        print(f"Erro ao salvar a obra {obra.get('codigo')}: {e}")
    finally:
        conexao.close()

# --- SCRAPER PRINCIPAL ---

def extrair_obras():
    url = "https://engegov.blumenau.sc.gov.br/portal-engegov/dashboard.xhtml?cidade=4898"
    
    print("Iniciando o navegador...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        page.goto(url)
        
        print("Aguardando a tabela principal carregar...")
        page.wait_for_selector(".ui-datatable-data", timeout=15000)
        time.sleep(3) 

        pagina_atual = 1
        
        while True:
            print(f"\n--- PROCESSANDO A PÁGINA {pagina_atual} ---")
            
            linhas = page.query_selector_all(".ui-datatable-data tr")
            total_linhas = len(linhas)
            
            if total_linhas == 0 or "Nenhum registro" in linhas[0].inner_text():
                print("Nenhuma obra encontrada nesta página.")
                break

            print(f"Encontradas {total_linhas} obras na página {pagina_atual}.")
            
            for i in range(total_linhas):
                # Recarrega a lista de linhas para evitar Stale Elements
                linhas = page.query_selector_all(".ui-datatable-data tr")
                linha = linhas[i]
                line_cols = linha.query_selector_all("td")
                
                if len(line_cols) >= 6:
                    codigo = limpar_texto_utf(line_cols[0].inner_text())
                    if not codigo:
                        continue
                    
                    obra = {
                        "codigo": codigo,
                        "secretaria": limpar_texto_utf(line_cols[1].inner_text()),
                        "descricao": limpar_texto_utf(line_cols[2].inner_text()),
                        "logradouro": limpar_texto_utf(line_cols[3].inner_text()),
                        "intervencao": limpar_texto_utf(line_cols[4].inner_text()),
                        "situacao": limpar_texto_utf(line_cols[5].inner_text()),
                        "num_licitacao": "Não Cadastrado",
                        "num_contrato": None,
                        "data_contrato": None,
                        "num_ordem_servico": None,
                        "tipo_recurso": None,
                        "inicio_obra": None,
                        "limite_execucao": None,
                        "termino_contrato": None,
                        "valor_contratado": None,
                        "valor_executado": None,
                        "saldo_contrato": None,
                        "pct_executado": None
                    }
                    
                    print(f"Acessando detalhes da Obra [{codigo}]...")
                    
                    try:
                        linha.scroll_into_view_if_needed()
                        time.sleep(0.3)
                        linha.click()
                        time.sleep(4)  # Tempo robusto para requisições AJAX do PrimeFaces

                        # 1. FORMULÁRIO DADOS DO CONTRATO
                        contrato_seletor = page.locator("#frmDadosContratoObra")
                        if contrato_seletor.count() > 0:
                            contrato_seletor.scroll_into_view_if_needed()
                            
                            def buscar_no_contrato(rotulo):
                                try:
                                    locator_label = contrato_seletor.locator(f"xpath=.//td[contains(., '{rotulo}')]/following-sibling::td[1]//label")
                                    if locator_label.count() > 0:
                                        return limpar_texto_utf(locator_label.first.inner_text())
                                    
                                    locator_td = contrato_seletor.locator(f"xpath=.//td[contains(., '{rotulo}')]/following-sibling::td[1]")
                                    return limpar_texto_utf(locator_td.first.inner_text())
                                except Exception:
                                    return ""

                            obra["num_licitacao"] = buscar_no_contrato("Número da licitação:") or "Não Cadastrado"
                            obra["num_contrato"] = buscar_no_contrato("Número do Contrato:")
                            obra["data_contrato"] = formatar_data(buscar_no_contrato("Data do Contrato:"))
                            obra["num_ordem_servico"] = buscar_no_contrato("Nº Ordem de Serviço:")
                            obra["tipo_recurso"] = buscar_no_contrato("Tipo de Recurso:")
                            obra["inicio_obra"] = formatar_data(buscar_no_contrato("Início da obra:"))
                            obra["limite_execucao"] = formatar_data(buscar_no_contrato("Data Limite Execução:"))
                            obra["termino_contrato"] = formatar_data(buscar_no_contrato("Término Contrato:"))
                            obra["valor_contratado"] = limpar_decimal(buscar_no_contrato("Valor Total Contratado:"))

                        # 2. FORMULÁRIO DE ESTATÍSTICAS E ANDAMENTO
                        andamento_seletor = page.locator("#frmAndamentoObra")
                        if andamento_seletor.count() > 0:
                            andamento_seletor.scroll_into_view_if_needed()

                            # Captura de Saldo do Contrato e Valor Executado (estruturas de span sequenciais)
                            def buscar_valor_span(rotulo):
                                try:
                                    elemento = andamento_seletor.locator(f"xpath=.//span[contains(normalize-space(), '{rotulo}')]/following-sibling::span[1]")
                                    if elemento.count() > 0:
                                        return limpar_texto_utf(elemento.first.inner_text())
                                    return ""
                                except Exception:
                                    return ""

                            obra["saldo_contrato"] = limpar_decimal(buscar_valor_span("Saldo do Contrato"))
                            obra["valor_executado"] = limpar_decimal(buscar_valor_span("Valor Executado"))

                            # Captura do Percentual Executado (Knob input)
                            try:
                                knob_input = andamento_seletor.locator("input.knob")
                                if knob_input.count() > 0:
                                    obra["pct_executado"] = limpar_percentual(knob_input.first.get_attribute("value"))
                            except Exception as ex_knob:
                                print(f"Não foi possível obter o percentual executado para a obra [{codigo}]: {ex_knob}")

                    except Exception as ex_detalhes:
                        print(f"Erro ao extrair detalhes inferiores da obra [{codigo}]: {ex_detalhes}")

                    # Salva ou atualiza a obra no banco de dados
                    salvar_ou_atualizar_obra(obra)
                    print(f"Obra [{codigo}] processada com sucesso.")

            # --- PAGINAÇÃO ---
            paginador_proximo = page.locator("#frmListaObras\\:tblListaObras_paginator_bottom .ui-paginator-next")
            
            if paginador_proximo.count() == 0:
                print("Paginador de páginas não encontrado. Finalizando script.")
                break
            
            classes = paginador_proximo.get_attribute("class") or ""
            if "ui-state-disabled" in classes:
                print("\nTodas as páginas foram processadas com êxito!")
                break
                
            print("\nAvançando para a próxima página...")
            paginador_proximo.click()
            time.sleep(4)  # Aguarda renderização completa da nova página
            pagina_atual += 1

        browser.close()
        print("\nProcesso de scraping finalizado com sucesso!")

if __name__ == "__main__":
    extrair_obras()
