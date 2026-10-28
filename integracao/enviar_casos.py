"""Integração circuito -> nuvem: envia à API os 5 casos testados no Logisim.

Os valores são exatamente os dos arquivos estacao/estacao_caso_*.circ (em hexadecimal
no circuito). Para cada caso, o script mostra o LED que acendeu no circuito e o estado
que a API devolveu. Se todos baterem, o circuito e a nuvem concordam.

Uso (PowerShell, dentro da pasta integracao):
    $env:API_KEY = "a-mesma-chave-da-api"
    python enviar_casos.py                                   # API local (http://localhost:8000)
    python enviar_casos.py --url https://SEU-APP.azurewebsites.net   # API publicada na Azure

Só usa a biblioteca padrão do Python (não precisa instalar nada).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# (nome do caso, TEMP, UMID, LUZ, EN, LED aceso no circuito, estado esperado na API)
CASOS = [
    ("1 normal",              0x17, 0x20, 0x20, 1, "NORMAL (verde)",    "normal"),
    ("2 atencao temperatura", 0x23, 0x20, 0x20, 1, "ATENCAO (amarelo)", "atencao"),
    ("3 atencao umidade",     0x17, 0x0E, 0x20, 1, "ATENCAO (amarelo)", "atencao"),
    ("4 alarme",              0x23, 0x0E, 0x20, 1, "ALARME (vermelho)", "alarme"),
    ("5 desligado",           0x23, 0x0E, 0x20, 0, "nenhum",            "desligado"),
]


def enviar(url_base: str, chave: str, temp: int, umid: int, luz: int, en: int) -> dict:
    corpo = json.dumps({
        "temperatura": temp,
        "umidade": umid,
        "luminosidade": luz,
        "ligada": bool(en),
    }).encode()
    pedido = urllib.request.Request(
        url_base.rstrip("/") + "/readings",
        data=corpo,
        headers={"Content-Type": "application/json", "X-API-Key": chave},
        method="POST",
    )
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return json.loads(resposta.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Envia os 5 casos do circuito para a API.")
    parser.add_argument("--url", default="http://localhost:8000", help="endereço da API")
    args = parser.parse_args()

    chave = os.getenv("API_KEY", "")
    if not chave:
        print("Defina a variável API_KEY com a mesma chave configurada na API.")
        return 2

    print(f"API: {args.url}\n")
    print(f"{'Caso':<24}{'TEMP':>6}{'UMID':>6}{'LUZ':>5}{'EN':>4}   {'LED no circuito':<19}{'Estado na API':<15}OK?")
    acertos = 0
    for nome, temp, umid, luz, en, led, esperado in CASOS:
        try:
            resposta = enviar(args.url, chave, temp, umid, luz, en)
        except urllib.error.HTTPError as erro:
            print(f"{nome:<24} erro HTTP {erro.code}: {erro.read().decode(errors='replace')}")
            return 1
        except OSError as erro:  # inclui URLError, conexão recusada e conexão derrubada
            print(f"Não consegui falar com a API ({getattr(erro, 'reason', erro)}). Ela está rodando nesse endereço?")
            return 1
        estado = resposta["estado"]
        ok = estado == esperado
        acertos += ok
        print(f"{nome:<24}{temp:>6}{umid:>6}{luz:>5}{en:>4}   {led:<19}{estado:<15}{'sim' if ok else 'NÃO'}")

    print(f"\n{acertos} de {len(CASOS)} casos: circuito e API {'concordam' if acertos == len(CASOS) else 'DIVERGEM'}.")
    return 0 if acertos == len(CASOS) else 1


if __name__ == "__main__":
    sys.exit(main())
