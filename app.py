from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

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
# - linha 1: cabeçalho geral
# - linha 2: nomes das colunas
# - linha 3+: dados
# ===============================

def carregar_codigos(arquivo: str, usecols: str | None = None):

    caminho = os.path.join("codigos", arquivo)

    if not os.path.exists(caminho):
        return []

    df = pd.read_excel(
        caminho,
        skiprows=1,          # pula SOMENTE a primeira linha
        usecols=usecols      # ex.: "A:C" (opcional)
    )

    # Para T001, queremos só as 3 primeiras colunas (A,B,C) já vêm via usecols,
    # mas isso garante caso alguém passe None e o arquivo tenha mais colunas:
    df = df.iloc[:, 0:3].copy()

    # Normaliza nomes para o front-end (evita undefined)
    df.columns = ["codigo", "cnpj", "razao"]

    # Remove NaN
    df = df.fillna("")

    # Garante string (evita virar float/exponencial)
    df["codigo"] = df["codigo"].astype(str).str.replace(".0", "", regex=False)
    df["cnpj"] = df["cnpj"].astype(str).str.replace(".0", "", regex=False)
    df["razao"] = df["razao"].astype(str)

    return df.to_dict(orient="records")

# ===============================
# QUEBRAR LINHA EM CAMPOS
# ===============================

def destrinchar(linha: str):

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

        # Mantém o tamanho correto
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

    # Mapeia campos -> arquivos
    mapa = {
        "AGENTE REGULADO INFORMANTE": {
            "arquivo": "T001-Codigos_agentes_regulados.xlsx",
            "usecols": "A:C"
        },
        # você pode ir adicionando outros aqui depois
    }

    config = mapa.get(campo)

    if not config:
        return jsonify({"dados": []})

    dados = carregar_codigos(
        config["arquivo"],
        config.get("usecols")
    )

    return jsonify({"dados": dados})

# ===============================
# START SERVER
# ===============================

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)