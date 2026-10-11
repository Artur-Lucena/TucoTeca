"""Prova de arquivos/HTTP reais em casa descartável (sem rede externa)."""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import sys
import tempfile
from pathlib import Path


def provar(raiz):
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_"):
            os.environ.pop(chave)
    os.environ.update(BIBLIOTECA_HOME=str(raiz), BIBLIOTECA_REDE="0",
                      BIBLIOTECA_SCAN_ROOTS=str(raiz / "jogos"))
    for p in (Path(__file__).parent.parent, Path(__file__).parent.parent / "frontends", Path(__file__).parent):
        sys.path.insert(0, str(p))
    import bib_core as core
    from bib_nucleo import organizacao_local, pastas_vigiadas, saves, screenshots
    from bib_nucleo.api_local import ApiLocal
    from bib_nucleo.everything import buscar_executaveis
    from servicos_ui import ServicoBiblioteca
    core.garantir_dirs()
    con = core.get_db(core.DEFAULT_DB)
    jogo = core.criar_jogo(con, {"titulo": "Jogo sintético", "executable_path": str(raiz / "jogos/game.exe")})
    con.close()
    svc = ServicoBiblioteca(core.DEFAULT_DB)
    api = ApiLocal(svc)
    try:
        api.iniciar()
        def consultar(path, token=True, host="", origem="", method="GET"):
            h = {"Authorization": "Bearer " + api.token} if token else {}
            if host:
                h["Host"] = host
            if origem:
                h["Origin"] = origem
            c = http.client.HTTPConnection("127.0.0.1", api.porta, timeout=3)
            try:
                c.request(method, path, headers=h)
                r = c.getresponse()
                status, body, cabecalhos = r.status, r.read(), dict(r.getheaders())
                assert not any(k.lower() == "access-control-allow-origin" for k in cabecalhos)
                return status, body
            finally:
                c.close()
        assert consultar("/status", token=False)[0] == 401
        assert consultar("/jogos", host="rebinding.invalid")[0] == 401
        assert consultar("/jogos", origem="https://pagina.invalid")[0] == 401
        status, dados = consultar("/jogos")
        assert status == 200 and json.loads(dados)[0]["titulo"] == jogo["titulo"]
        assert consultar("/status")[0] == 200
        assert consultar("/jogar")[0] == 404
        assert consultar("/jogos", method="POST")[0] in (405, 501)
        porta = api.porta
    finally:
        api.fechar()
    with socket.socket() as s:
        s.settimeout(1)
        assert s.connect_ex(("127.0.0.1", porta)) != 0
    pasta = raiz / "saves"
    pasta.mkdir()
    slot = pasta / "slot.sav"
    slot.write_bytes(b"progresso original")
    saves.configurar_saves(jogo, [str(pasta)])
    snapshot = saves.snapshot_saves(jogo)
    slot.write_bytes(b"progresso atual")
    restaurado = saves.restaurar_snapshot(jogo, snapshot["destino"])
    assert slot.read_bytes() == b"progresso original" and Path(restaurado["backup_antes"]).is_file()
    destino = raiz / "copia"
    r = organizacao_local.copiar_ou_ligar(pasta, destino, hardlinks=True)
    assert (destino / "slot.sav").read_bytes() == slot.read_bytes()
    if r["hardlinks"]:
        assert os.path.samefile(slot, destino / "slot.sav")
    imagens = screenshots.pasta_screenshots(jogo)
    imagens.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new("RGB", (80, 60), "blue").save(imagens / "prova.png")
    assert screenshots.listar_screenshots(jogo)[0]["nome"] == "prova.png"
    watch = raiz / "watch"
    watch.mkdir()
    (watch / "arquivo.zip").write_bytes(b"pacote sintetico")
    v = pastas_vigiadas.VigiaPasta(watch, estabilidade_s=15)
    assert not v.consultar(agora=0)
    assert len(v.consultar(agora=16)) == 1 and not v.consultar(agora=20)
    scan = buscar_executaveis([raiz / "jogos"])
    return {"api_loopback": "rotas, token, Origin/Host, sem mutação e encerramento OK",
            "saves": "snapshot/restauração/backup prévio reais OK",
            "hardlinks": r["hardlinks"], "copias": r["copiados"],
            "screenshots": "arquivo real listado OK", "watch": "estabilidade e não repetição OK",
            "everything": "CLI executada" if scan is not None else "BYOB ausente/sem índice; fallback disponível"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", required=True)
    args = parser.parse_args()
    saida = Path(args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="integracoes-locais-", dir=saida) as tmp:
        r = provar(Path(tmp))
    (saida / "integracoes-locais.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
