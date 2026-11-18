"""Entrega de fontes e diagnóstico não transportam/migram a coleção pessoal."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from bib_nucleo import banco
from executar import afirmar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnosticar as DIAG
import empacotar_fontes as FONTES


def teste_pacote_fontes_exclui_dados_e_inclui_arvore_atual():
    tmp = Path(tempfile.mkdtemp(prefix="suite-fontes-"))
    repo = tmp / "repo"
    for nome in ("codigo/bib_nucleo/__init__.py", "codigo/bib_nucleo/volume.py", "codigo/frontends/desktop.py",
                 "docs/ARQUITETURA.md", "dados/biblioteca.db", "dist/antigo.zip",
                 "codigo/historico/antigo.py", "codigo/ferramentas/.cache/segredo.py",
                 "codigo/__pycache__/x.pyc"):
        path = repo / nome
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# conteúdo")
    (repo / "README.md").write_text("Projeto")
    (repo / "LICENSE").write_text("MIT")
    saida = tmp / "entrega.zip"
    r = FONTES.empacotar_fontes(saida, repo=repo)
    afirmar(r["ok"])
    with zipfile.ZipFile(saida) as z:
        nomes = z.namelist()
        afirmar("codigo/bib_nucleo/volume.py" in nomes and "docs/ARQUITETURA.md" in nomes, nomes)
        afirmar(not any(n.startswith(("dados/", "dist/")) or "historico" in n
                        or ".cache" in n or "__pycache__" in n for n in nomes), nomes)
        manifesto = json.loads(z.read("MANIFESTO-FONTES.json"))
        for nome, info in manifesto["arquivos"].items():
            afirmar(hashlib.sha256(z.read(nome)).hexdigest() == info["sha256"])


def teste_diagnostico_banco_so_leitura():
    tmp = Path(tempfile.mkdtemp(prefix="suite-diag-"))
    ausente = tmp / "ausente.db"
    afirmar(DIAG.diagnosticar_banco(ausente)["estado"] == "ausente")
    afirmar(not ausente.exists(), "diagnóstico criou coleção vazia")
    db = tmp / "b.db"
    con = banco.get_db(db)
    banco.criar_jogo(con, {"titulo": "Teste"})
    con.close()
    antes = db.read_bytes()
    resultado = DIAG.diagnosticar_banco(db)
    afirmar(resultado["estado"] == "ok" and resultado["contagens"]["jogos"] == 1, resultado)
    afirmar(db.read_bytes() == antes, "diagnóstico alterou o banco")


def teste_resumo_pastas_detecta_erro_de_sintaxe():
    tmp = Path(tempfile.mkdtemp(prefix="suite-diag-"))
    codigo = tmp / "codigo"
    codigo.mkdir()
    (codigo / "bom.py").write_text("def teste_exemplo():\n    return True\n")
    (codigo / "ruim.py").write_text("def sem_corpo(\n")
    r = DIAG.resumo_fontes(tmp)
    afirmar(r["python"] == 2 and r["testes_descobertos"] == 1, r)
    afirmar(len(r["erros_sintaxe"]) == 1, r)
