"""O app em si: notificações que ficam, verificar/baixar atualização e downloads na lista de trabalhos.

GitHub e download simulados: nenhuma rede é usada.
"""
import hashlib
import tempfile
import threading
import time
from pathlib import Path

from bib_nucleo import notificacoes as N
from bib_nucleo.rede import versao_nova as V
from executar import afirmar


def teste_notificacoes_gravam_deduplicam_e_somem():
    afirmar(N.listar() == [])
    N.registrar([{"id": "a", "texto": "Backup feito.", "tom": "info"}, {"texto": "  Falhou   o download ", "tom": "atencao"}])
    itens = N.registrar([{"id": "a", "texto": "Backup feito de novo.", "tom": "estranho"}])
    afirmar([i["id"] for i in itens] == ["a", "Falhou o download"], itens)
    afirmar(itens[0]["tom"] == "info" and itens[0]["texto"] == "Backup feito de novo." and itens[0]["em"], itens[0])
    afirmar(N.listar() == itens)  # relido do disco
    afirmar([i["id"] for i in N.dispensar("a")] == ["Falhou o download"])
    N.registrar([{"id": str(i), "texto": f"aviso {i}"} for i in range(N.LIMITE + 5)])
    afirmar(len(N.listar()) == N.LIMITE)
    afirmar(N.limpar() == [] and N.listar() == [])
    try:
        N.registrar([{"texto": "  "}])
        raise AssertionError("aceitou aviso vazio")
    except ValueError:
        pass


def _release(tag="v2.3.0", digest="sha256:" + "0" * 64):
    nomes = ["TucoTeca-Setup-2.3.0-x64.exe", "TucoTeca-2.3.0-mac-arm64.dmg", "TucoTeca-2.3.0-mac-x64.dmg",
             "TucoTeca-2.3.0-linux-x64.AppImage", "NOTAS-2.3.0.md"]
    return {"tag_name": tag, "body": "## Novidades", "html_url": "https://github.com/Artur-Lucena/TucoTeca/releases/tag/v2.3.0",
            "published_at": "2026-11-20T12:00:00Z",
            "assets": [{"name": n, "size": 10, "digest": digest,
                        "browser_download_url": f"https://github.com/Artur-Lucena/TucoTeca/releases/download/{tag}/{n}"}
                       for n in nomes]}


def teste_verificar_atualizacao_por_plataforma():
    afirmar(V.mais_nova("2.10.0", "2.9.9") and not V.mais_nova("v2.2.0", "2.2.0") and not V.mais_nova("x", "1.0.0"))
    for plataforma, nome in (("windows-x64", "TucoTeca-Setup-2.3.0-x64.exe"), ("macos-arm64", "TucoTeca-2.3.0-mac-arm64.dmg"),
                             ("macos-x64", "TucoTeca-2.3.0-mac-x64.dmg"), ("linux-x64", "TucoTeca-2.3.0-linux-x64.AppImage")):
        r = V.verificar(obter=_release, atual="2.2.0", plataforma=plataforma)
        afirmar(r["nova"] and r["ultima"] == "2.3.0" and r["instalador"]["nome"] == nome, r)
        afirmar(r["instalador"]["sha256"] == "0" * 64 and r["publicada_em"] == "2026-11-20")
    igual = V.verificar(obter=_release, atual="2.3.0", plataforma="windows-x64")
    afirmar(not igual["nova"] and igual["instalador"] is None, igual)
    fora = _release()
    fora["assets"][0]["browser_download_url"] = "https://exemplo.test/TucoTeca-Setup-2.3.0-x64.exe"
    afirmar(V.verificar(obter=lambda: fora, atual="2.2.0", plataforma="windows-x64")["instalador"] is None)
    try:
        V.verificar(obter=lambda: {"tag_name": "nightly"}, atual="2.2.0")
        raise AssertionError("aceitou tag sem versão")
    except ValueError:
        pass
    afirmar(V.plataforma_atual() in V.PADROES)


def teste_baixar_instalador_confere_sha256():
    conteudo = b"instalador de teste"
    certo = hashlib.sha256(conteudo).hexdigest()
    pasta = V.pasta_atualizacoes()
    pasta.mkdir(parents=True)
    (pasta / "TucoTeca-Setup-2.2.0-x64.exe").write_bytes(b"velho")

    def baixar(url, titulo, destino, progresso, cancelado):
        alvo = Path(destino) / titulo
        alvo.write_bytes(conteudo)
        return {"ok": True, "path": str(alvo)}

    inst = {"nome": "TucoTeca-Setup-2.3.0-x64.exe", "url": "https://github.com/x/TucoTeca-Setup-2.3.0-x64.exe", "sha256": certo}
    r = V.baixar_instalador(inst, baixar=baixar)
    afirmar(r["ok"] and r["conferido"] and [p.name for p in pasta.iterdir()] == ["TucoTeca-Setup-2.3.0-x64.exe"], r)
    try:
        V.baixar_instalador({**inst, "sha256": "f" * 64}, baixar=baixar)
        raise AssertionError("aceitou SHA-256 diferente")
    except ValueError as e:
        afirmar("SHA-256" in str(e))
    afirmar(not (pasta / "TucoTeca-Setup-2.3.0-x64.exe").exists())  # o que não confere é apagado
    for ruim in ({**inst, "nome": "virus.exe"}, {**inst, "url": "https://exemplo.test/a.exe"}):
        try:
            V.baixar_instalador(ruim, baixar=baixar)
            raise AssertionError("aceitou instalador estranho")
        except ValueError:
            pass


def _esperar(ponte, ident):
    limite = time.monotonic() + 30
    while time.monotonic() < limite:
        item = next(t for t in ponte.trabalhos.listar() if t["id"] == ident)
        if item["estado"] not in ("rodando", "cancelando"):
            return item
        time.sleep(0.02)
    raise AssertionError("trabalho não terminou")


class _Servico:
    def __init__(self):
        from servicos_ui.mix_app import MixApp
        self.app = MixApp()

    def __getattr__(self, nome):
        return getattr(self.app, nome)

    def baixar_atualizacao(self, instalador, progresso=None, cancelado=None):
        progresso(50)
        return {"ok": True, "arquivo": "x"}


def teste_ponte_avisos_e_downloads_no_grupo():
    from ponte import Ponte, Trabalhos
    eventos = []
    ponte = Ponte(_Servico(), trabalhos=Trabalhos(eventos.append))
    d = ponte.despachar
    afirmar(d("avisos.registrar", {"avisos": [{"id": "x", "texto": "Oi"}]})["resultado"][0]["id"] == "x")
    afirmar(d("avisos.listar")["resultado"][0]["texto"] == "Oi")
    afirmar(d("avisos.dispensar", {"id": "x"})["resultado"] == [])
    afirmar(not d("avisos.registrar", {"avisos": "x"})["ok"])
    afirmar(d("avisos.limpar")["resultado"] == [])
    r = d("app.baixar_atualizacao", {"instalador": {"nome": "a"}, "versao": "2.3.0"})
    fim = _esperar(ponte, r["resultado"]["trabalho"]["id"])
    afirmar(fim["estado"] == "ok" and fim["grupo"] == "download" and "2.3.0 baixado" in fim["detalhe"]["aviso"], fim)
    trava = threading.Event()
    rodando = ponte.trabalhos.iniciar("Outro", lambda p, c: trava.wait(5), grupo="download")
    afirmar(d("trabalhos.limpar", {"grupo": "download"})["resultado"] == {"removidos": 1})
    afirmar([t["id"] for t in ponte.trabalhos.listar()] == [rodando["id"]])  # o que roda fica
    trava.set()
    _esperar(ponte, rodando["id"])
    afirmar(d("trabalhos.limpar")["resultado"] == {"removidos": 1} and ponte.trabalhos.listar() == [])
    afirmar(tempfile.gettempdir())  # sandbox ativo
