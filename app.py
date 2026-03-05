from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# ===============================
# CACHE DE TABELAS (melhora performance no Render)
# ===============================

CACHE_TABELAS = {}

# ===============================
# LAYOUT DOS CAMPOS i-SIMP
# ===============================

layout = [
    {"nome": "CONTADOR SEQUENCIAL", "inicio": 0, "tamanho": 10},
    {"nome": "AGENTE REGULADO INFORMANTE", "inicio": 10, "tamanho": 10},
    {"nome": "MÊS DE REFERÊNCIA (MMAAAA)", "inicio": 20, "tamanho": 6},
    {"nome": "CÓDIGO DA OPERAÇÃO", "inicio": 26, "tamanho": 7},
    {"nome": "CÓDIGO DA INSTALAÇÃO 1", "inicio": 33, "tamanho": 7},
    {"nome": "CÓDIGO DA INSTALAÇÃO 2", "inicio": 40, "tamanho": 7},
    {"nome": "CÓDIGO DO PRODUTO OPERADO", "inicio": 47, "tamanho": 9},
    {"nome": "QUANTIDADE UNITÁRIA MEDIDA ANP", "inicio": 56, "tamanho": 15},
    {"nome": "QUANTIDADE DE PRODUTO EM KG", "inicio": 71, "tamanho": 15},
    {"nome": "CÓDIGO DO MODAL", "inicio": 86, "tamanho": 2},
    {"nome": "CÓDIGO DO VEÍCULO", "inicio": 88, "tamanho": 6},
    {"nome": "IDENTIFICAÇÃO DO TERCEIRO", "inicio": 94, "tamanho": 14},
    {"nome": "CÓDIGO DO MUNICÍPIO", "inicio": 108, "tamanho": 7},
    {"nome": "CÓDIGO DA ATIVIDADE ECONÔMICA", "inicio": 115, "tamanho": 5},
    {"nome": "CÓDIGO DO PAÍS", "inicio": 120, "tamanho": 6},
    {"nome": "LI - LICENÇA DE IMPORTAÇÃO", "inicio": 126, "tamanho": 6},
    {"nome": "DI - DECLARAÇÃO DE IMPORTAÇÃO", "inicio": 132, "tamanho": 9},
    {"nome": "NÚMERO DA NOTA FISCAL", "inicio": 141, "tamanho": 6},
    {"nome": "CÓDIGO DA SÉRIE DA NF", "inicio": 147, "tamanho": 6},
    {"nome": "DATA DA NOTA FISCAL", "inicio": 153, "tamanho": 8},
    {"nome": "CÓDIGO DO SERVIÇO ACORDADO", "inicio": 161, "tamanho": 2},
    {"nome": "CÓDIGO DA CARACTERÍSTICA FÍSICO-QUÍMICA", "inicio": 163, "tamanho": 2},
    {"nome": "CÓDIGO DO MÉTODO", "inicio": 165, "tamanho": 2},
    {"nome": "MODALIDADE DO FRETE", "inicio": 167, "tamanho": 3},
    {"nome": "CÓDIGO DO PRODUTO / OPER / RESULTANTE", "inicio": 170, "tamanho": 19},
    {"nome": "VALOR INTEIRO REAIS", "inicio": 189, "tamanho": 3},
    {"nome": "VALOR DECIMAIS CENTAVOS", "inicio": 192, "tamanho": 3},
    {"nome": "RECIPIENTE GLP", "inicio": 195, "tamanho": 3},
    {"nome": "CHAVE DE ACESSO NF-E", "inicio": 198, "tamanho": 44},
]

# ===============================
# FUNÇÃO PARA LER XLSX (ANP)
# ===============================

def carregar_codigos(arquivo, usecols=None):

    cache_key = f"{arquivo}_{usecols}"

    if cache_key in CACHE_TABELAS:
        return CACHE_TABELAS[cache_key]

    caminho = os.path.join("codigos", arquivo)

    if not os.path.exists(caminho):
        return []

    try:

        df = pd.read_excel(
            caminho,
            skiprows=1,
            usecols=usecols
        )

        df = df.iloc[:, 0:3].copy()
        df.columns = ["codigo", "cnpj", "razao"]

        df = df.fillna("")

        df["codigo"] = df["codigo"].astype(str).str.replace(".0", "", regex=False)
        df["cnpj"] = df["cnpj"].astype(str).str.replace(".0", "", regex=False)
        df["razao"] = df["razao"].astype(str)

        dados = df.to_dict(orient="records")

        CACHE_TABELAS[cache_key] = dados

        return dados

    except Exception as e:
        print("Erro ao ler planilha:", e)
        return []

# ===============================
# QUEBRAR LINHA EM CAMPOS
# ===============================

def destrinchar(linha):

    resultado = []

    for campo in layout:

        inicio = campo["inicio"]
        fim = inicio + campo["tamanho"]

        valor = linha[inicio:fim]

        resultado.append({
            "campo": campo["nome"],
            "inicio": inicio + 1,
            "fim": fim,
            "tamanho": campo["tamanho"],
            "valor": valor
        })

    return resultado

# ===============================
# GERAR NOVA LINHA
# ===============================

def gerar_linha(campos):

    linha = ""

    for i, campo in enumerate(layout):

        valor = campos.get(f"campo{i}", "")
        tamanho = campo["tamanho"]

        valor = str(valor).ljust(tamanho, "0")[:tamanho]

        linha += valor

    return linha

# ===============================
# PÁGINA PRINCIPAL
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():

    resultado = []
    linha = ""
    nova_linha = None

    if request.method == "POST":

        if "linha" in request.form:

            linha = request.form["linha"].strip()
            resultado = destrinchar(linha)

        else:

            nova_linha = gerar_linha(request.form)
            resultado = destrinchar(nova_linha)
            linha = nova_linha

    return render_template(
        "index.html",
        resultado=resultado,
        linha=linha,
        nova_linha=nova_linha,
        layout=layout
    )

# ===============================
# DETALHES DOS CÓDIGOS
# ===============================

@app.route("/detalhes/<campo>")
def detalhes(campo):

    mapa = {
        "AGENTE REGULADO INFORMANTE": {
            "arquivo": "T001-Codigos_agentes_regulados.xlsx",
            "usecols": "A:C"
        },
    }

    config = mapa.get(campo)

    if not config:
        return jsonify({
            "status": "dev",
            "dados": []
        })

    dados = carregar_codigos(
        config["arquivo"],
        config.get("usecols")
    )

    return jsonify({
        "status": "ok",
        "dados": dados
    })
@app.route("/buscar")
def buscar():

    campo = request.args.get("campo")
    termo = request.args.get("termo","").lower()

    if len(termo) < 2:
        return jsonify({"dados":[]})


    mapa = {
        "AGENTE REGULADO INFORMANTE": {
            "arquivo": "T001-Codigos_agentes_regulados.xlsx",
            "usecols": "A:C"
        }
    }

    config = mapa.get(campo)

    if not config:
        return jsonify({"dados":[]})

    dados = carregar_codigos(
        config["arquivo"],
        config.get("usecols")
    )

    resultados = []

    for item in dados:

        texto = f"{item.get('codigo','')} {item.get('razao','')} {item.get('cnpj','')}".lower().strip()

        if termo in texto:
            resultados.append(item)

        if len(resultados) >= 20:
            break

    return jsonify({"dados":resultados})
# ===============================
# LIMPAR CACHE (opcional)
# ===============================

@app.route("/limpar-cache")
def limpar_cache():

    CACHE_TABELAS.clear()

    return jsonify({
        "status": "cache limpo"
    })
def preload_cache():

    print("Pré carregando tabelas ANP...")

    arquivos = [
        "T001-Codigos_agentes_regulados.xlsx"
    ]

    for arq in arquivos:
        carregar_codigos(arq,"A:C")

    print("Cache carregado:", len(CACHE_TABELAS), "tabelas")
# ===============================
# START SERVER
# ===============================

if __name__ == "__main__":

    preload_cache()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )