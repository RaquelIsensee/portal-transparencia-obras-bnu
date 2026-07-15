import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from database import obter_conexao

# --- FUNÇÕES AUXILIARES DE TRATAMENTO DE DADOS ---

def limpar_decimal(texto):
    if not texto or "Não" in texto or "-" in texto or texto.strip() == "":
        return None
    try:
        limpo = re.sub(r'[^\d,.-]', '', texto).replace('.', '').replace(',', '.')
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
        
        linhas = page.query_selector_all(".ui-datatable-data tr")
        
        if not linhas or len(linhas) == 0 or "Nenhum registro" in linhas[0].inner_text():
            print("Nenhuma obra listada ou a tabela está vazia.")
            browser.close()
            return

        total_linhas = len(linhas)
        print(f"Encontradas {total_linhas} obras na lista. Iniciando processamento...")
        
        for i in range(total_linhas):
            # Recarrega a linha para evitar Stale Elements
            linhas = page.query_selector_all(".ui-datatable-data tr")
            linha = linhas[i]
            colunas = linha.query_selector_all("td")
            
            if len(colunas) >= 6:
                codigo = colunas[0].inner_text().strip()
                if not codigo or codigo == "":
                    continue
                
                # Inicializa dicionário com valores padrão
                obra = {
                    "codigo": codigo,
                    "secretaria": colunas[1].inner_text().strip(),
                    "descricao": colunas[2].inner_text().strip(),
                    "logradouro": colunas[3].inner_text().strip(),
                    "intervencao": colunas[4].inner_text().strip(),
                    "situacao": colunas[5].inner_text().strip(),
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
                
                print(f"\nAcessando detalhes da Obra [{codigo}]...")
                
                try:
                    # Rola a tela até a linha que queremos clicar para garantir a ação do mouse
                    linha.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    
                    # Clica na linha correspondente da tabela principal para atualizar os painéis inferiores
                    linha.click()
                    time.sleep(3)  # Aguarda a requisição AJAX processar e renderizar os blocos inferiores

                    # 1. TRABALHANDO NO FORMULÁRIO DADOS DO CONTRATO
                    contrato_seletor = page.locator("#frmDadosContratoObra")
                    if contrato_seletor.count() > 0:
                        # Rola a tela até o container de Contratos
                        contrato_seletor.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        
                        def buscar_no_contrato(rotulo):
                            try:
                                # Procura o texto exato do rótulo dentro de #frmDadosContratoObra
                                elemento = contrato_seletor.locator(f"text='{rotulo}'")
                                if elemento.count() > 0:
                                    # Pega o irmão correspondente (normalmente a coluna ao lado na estrutura de grid do PrimeFaces)
                                    texto_completo = elemento.first.locator("xpath=../following-sibling::td[1] | ../following-sibling::div[1] | ..").first.inner_text()
                                    return texto_completo.replace(rotulo, "").strip()
                                return ""
                            except:
                                return ""

                        # Extração dos dados de Contrato
                        obra["num_licitacao"] = buscar_no_contrato("Número da licitação:") or "Não Cadastrado"
                        obra["num_contrato"] = buscar_no_contrato("Número do Contrato:")
                        obra["data_contrato"] = formatar_data(buscar_no_contrato("Data do Contrato:"))
                        obra["num_ordem_servico"] = buscar_no_contrato("Nº Ordem de Serviço:")
                        obra["tipo_recurso"] = buscar_no_contrato("Tipo de Recurso:")
                        
                        obra["inicio_obra"] = formatar_data(buscar_no_contrato("Início da obra:"))
                        obra["limite_execucao"] = formatar_data(buscar_no_contrato("Data Limite Execução:"))
                        obra["termino_contrato"] = formatar_data(buscar_no_contrato("Término Contrato:"))
                        obra["valor_contratado"] = limpar_decimal(buscar_no_contrato("Valor Total Contratado:"))

                    # 2. TRABALHANDO NO FORMULÁRIO DE ESTATÍSTICAS / ANDAMENTO
                    andamento_seletor = page.locator("#frmAndamentoObra")
                    if andamento_seletor.count() > 0:
                        # Rola a tela até o container de Estatísticas
                        andamento_seletor.scroll_into_view_if_needed()
                        time.sleep(0.5)

                        def buscar_no_andamento(rotulo):
                            try:
                                elemento = andamento_seletor.locator(f"text='{rotulo}'")
                                if elemento.count() > 0:
                                    texto_completo = elemento.first.locator("xpath=../following-sibling::td[1] | ../following-sibling::div[1] | ..").first.inner_text()
                                    return texto_completo.replace(rotulo, "").strip()
                                return ""
                            except:
                                return ""

                        # Extração dos dados de Andamento/Estatística
                        obra["valor_executado"] = limpar_decimal(buscar_no_andamento("Valor Executado (Medido):"))
                        obra["saldo_contrato"] = limpar_decimal(buscar_no_andamento("Saldo do Contrato:"))
                        obra["pct_executado"] = limpar_percentual(buscar_no_andamento("Percentual Executado:"))

                except Exception as ex_detalhes:
                    print(f"Erro ao extrair detalhes inferiores da obra [{codigo}]: {ex_detalhes}")

                # Gravação no banco de dados
                salvar_ou_atualizar_obra(obra)
                print(f"Obra [{codigo}] processada com sucesso no banco de dados.")

        browser.close()
        print("\nProcesso de scraping finalizado!")

if __name__ == "__main__":
    extrair_obras()