"""Saves, perfis, pacotes, rede desligada e integridade — sem rede ou dados reais."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from executar import afirmar


def _base():
    import bib_core as core
    from servicos_ui import ServicoBiblioteca
    raiz = Path(tempfile.mkdtemp())
    con = core.get_db(raiz / "b.db")
    jogo = core.criar_jogo(con, {"titulo": "Aventura", "favorito": True})
    con.close()
    return raiz, jogo, ServicoBiblioteca(raiz / "b.db")


def teste_snapshot_saves_manifesto_hash_retencao_e_original_intacto():
    import zipfile

    from bib_nucleo import saves
    raiz, jogo, svc = _base()
    pasta = raiz / "meu-save"
    pasta.mkdir()
    (pasta / "slot.sav").write_bytes(b"progresso")
    saves.configurar_saves(jogo, [str(pasta)])
    primeiro = saves.snapshot_saves(jogo, manter=1)
    segundo = saves.snapshot_saves(jogo, manter=1)
    afirmar(not Path(primeiro["destino"]).exists() and Path(segundo["destino"]).is_file())
    with zipfile.ZipFile(segundo["destino"]) as z:
        meta = json.loads(z.read("snapshot.json"))
        arquivo = meta["arquivos"][0]
        afirmar(z.read(arquivo["nome"]) == b"progresso")
        afirmar(arquivo["sha256"] == hashlib.sha256(b"progresso").hexdigest())
    afirmar((pasta / "slot.sav").read_bytes() == b"progresso")
    try:
        saves.snapshot_saves(jogo, limite_bytes=1)
    except ValueError:
        pass
    else:
        raise AssertionError("snapshot acima do limite")
    afirmar(Path(segundo["destino"]).is_file(), "falha removeu backup anterior")


def teste_perfis_independentes_e_atalhos_sem_conflito():
    from bib_nucleo import preferencias_pessoais as P
    raiz, jogo, svc = _base()
    afirmar(svc.snapshot()["jogos"][0]["favorito"])
    P.trocar_perfil("Isa")
    afirmar(not svc.snapshot()["jogos"][0]["favorito"])
    svc.favorito(jogo["id"])
    afirmar(svc.snapshot()["jogos"][0]["favorito"])
    P.trocar_perfil("Tuco")
    svc.favorito(jogo["id"])
    afirmar(not svc.snapshot()["jogos"][0]["favorito"])
    P.trocar_perfil("Isa")
    afirmar(svc.snapshot()["jogos"][0]["favorito"], "Tuco alterou favorito da Isa")
    P.salvar_filtro("favoritos", "horas")
    afirmar(P.ler_preferencias()["perfis"]["Isa"]["filtro"] == "favoritos")
    try:
        P.salvar_atalhos({"paleta": "Ctrl+F"})
    except ValueError:
        pass
    else:
        raise AssertionError("atalhos conflitantes")
    afirmar(P.salvar_atalhos({"paleta": "Alt+K"})["atalhos"]["paleta"] == "Alt+K")


def teste_ferramenta_sha_divergente_preserva_instalacao():
    from bib_nucleo import baixar as B
    pasta = Path(tempfile.mkdtemp())
    antigo = pasta / "yt-dlp.exe"
    antigo.write_bytes(b"anterior")
    with patch.object(B, "_baixar_bin", return_value=b"MZarquivo adulterado"):
        r = B.instalar_ytdlp(pasta)
    afirmar(not r["ok"] and "SHA-256" in r["erro"] and antigo.read_bytes() == b"anterior")


def teste_rede_desligada_bloqueia_http_e_processos_remotos():
    from bib_nucleo import baixar, scans
    from bib_nucleo.rede import fontes, online
    from bib_nucleo.rede.videos_youtube import info_video_youtube
    with patch.dict(os.environ, BIBLIOTECA_REDE="0"), \
         patch("urllib.request.urlopen", side_effect=AssertionError("HTTP inesperado")), \
         patch("subprocess.run", side_effect=AssertionError("processo inesperado")):
        afirmar(scans.canonizar_steam("Aventura") == ("", ""))
        afirmar(fontes.buscar_steamrip("Aventura")["erros"])
        for f in (lambda: online.requisitar_json("https://example.org"),
                  lambda: info_video_youtube("abcdefghijk"),
                  lambda: baixar.casar_video("ytdlp", "a", "b")):
            try:
                f()
            except ValueError as e:
                afirmar("BIBLIOTECA_REDE" in str(e))
            else:
                raise AssertionError("rede não bloqueada")


def teste_estatisticas_registro_na_colecao_certa():
    raiz, jogo, svc = _base()
    svc.registrar_sessao(jogo["id"], 1.5)
    resumo = svc.estatisticas()
    afirmar(resumo["total_horas"] == 1.5 and sum(resumo["meses"]) == 1.5, resumo)
    afirmar(svc.jogo(jogo["id"])["horas"] == 1.5)


def teste_sponsorblock_filtra_tempos_invalidos_e_cache():
    from bib_nucleo.rede import sponsorblock as S
    dados = [{"category": "sponsor", "segment": [5, 10]},
             {"category": "sponsor", "segment": [-1, 2]},
             {"category": "sponsor", "segment": [1, float("nan")]},
             {"category": "intro", "segment": [0, 5]}]
    with patch.object(S.online, "requisitar_json", return_value=dados) as pedir:
        afirmar(S.buscar_segmentos("abcdefghijk") == [[5.0, 10.0]])
        afirmar(S.buscar_segmentos("abcdefghijk") == [[5.0, 10.0]] and pedir.call_count == 1)


def teste_snapshot_restauracao_hash_e_backup_antes():
    from bib_nucleo import saves
    raiz, jogo, svc = _base()
    pasta = raiz / "saves"
    pasta.mkdir()
    slot = pasta / "slot.sav"
    slot.write_bytes(b"antes")
    saves.configurar_saves(jogo, [str(pasta)])
    original = saves.snapshot_saves(jogo)
    slot.write_bytes(b"depois")
    r = saves.restaurar_snapshot(jogo, original["destino"])
    afirmar(slot.read_bytes() == b"antes" and Path(r["backup_antes"]).is_file(), r)
    import zipfile
    with zipfile.ZipFile(r["backup_antes"]) as z:
        afirmar(z.read("saves/0/slot.sav") == b"depois")
    ruim = Path(original["destino"]).with_name("saves-adulterado.zip")
    with zipfile.ZipFile(original["destino"]) as src, zipfile.ZipFile(ruim, "w") as dst:
        for nm in src.namelist():
            dst.writestr(nm, b"wrong" if nm.endswith(".sav") else src.read(nm))
    try:
        saves.restaurar_snapshot(jogo, ruim)
    except ValueError as e:
        afirmar("SHA-256" in str(e))
    else:
        raise AssertionError("snapshot adulterado aceito")
    afirmar(slot.read_bytes() == b"antes")


def teste_pacote_rejeita_links_reservados_duplicatas_e_backup_presets():
    import zipfile

    from bib_nucleo import pacotes as P
    raiz, jogo, svc = _base()
    for nome in ("presets/NUL.ini", "presets/perfil.ini ", "presets/../fora.ini"):
        afirmar(P._membro_pacote_ok(nome) is None, nome)
    alvo = P.presets_dir() / "perfil.ini"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(b"perfil atual")
    pacote = raiz / "p.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("biblioteca.json", json.dumps({"jogos": []}))
        z.writestr("presets/perfil.ini", b"perfil importado")
    r = P.importar_pacote(pacote, svc.db_path)
    afirmar(r["ok"] and alvo.read_bytes() == b"perfil importado", r)
    with zipfile.ZipFile(r["backup_arquivos"]) as z:
        afirmar(z.read("presets/perfil.ini") == b"perfil atual")
    hostil = raiz / "link.zip"
    zi = zipfile.ZipInfo("presets/link.ini")
    zi.create_system = 3
    zi.external_attr = 0o120777 << 16
    with zipfile.ZipFile(hostil, "w") as z:
        z.writestr("biblioteca.json", "[]")
        z.writestr(zi, "../../alvo")
    afirmar(not P.importar_pacote(hostil, svc.db_path)["ok"])


def teste_snapshot_nao_redireciona_origens_e_restauracao_de_save_apagado():
    from bib_nucleo import saves
    raiz, jogo, svc = _base()
    slot = raiz / "slot.sav"
    slot.write_bytes(b"progresso")
    saves.configurar_saves(jogo, [str(slot)])
    original = saves.snapshot_saves(jogo)
    outro = raiz / "outro.sav"
    outro.write_bytes(b"outro jogo")
    saves.configurar_saves(jogo, [str(outro)])
    try:
        saves.restaurar_snapshot(jogo, original["destino"])
    except ValueError as e:
        afirmar("caminhos" in str(e), e)
    else:
        raise AssertionError("snapshot foi redirecionado a outro save")
    afirmar(outro.read_bytes() == b"outro jogo")
    saves.configurar_saves(jogo, [str(slot)])
    slot.unlink()
    r = saves.restaurar_snapshot(jogo, original["destino"])
    afirmar(r["arquivos"] == 1 and slot.read_bytes() == b"progresso", r)


def teste_modo_aviao_bloqueia_entradas_remotas_sem_chamar_transporte():
    from bib_nucleo import emuladores, musicas, scans
    from bib_nucleo.rede import (
        binarios,
        capas_libretro,
        fontes,
        letras,
        online,
        sponsorblock,
        spotify,
    )
    with patch.dict(os.environ, BIBLIOTECA_REDE="0"), patch("urllib.request.urlopen") as abrir:
        for trabalho in (
            lambda: online.requisitar_json("https://example.org/a"),
            lambda: online.baixar_texto("https://example.org/a"),
            lambda: online.baixar_imagem("https://example.org/a.png"),
            lambda: letras.buscar_letras("A", "B"),
            lambda: sponsorblock.buscar_segmentos("abcdefghijk"),
            lambda: binarios._baixar_bin("https://example.org/tool.exe", 1),
            lambda: capas_libretro.buscar_capa_libretro("NDS", "Teste"),
            lambda: spotify.ClienteSpotify().iniciar_login(),
        ):
            try:
                trabalho()
            except ValueError as e:
                afirmar("BIBLIOTECA_REDE" in str(e), e)
            else:
                raise AssertionError("ação remota não recusou modo avião")
        afirmar(not fontes.abrir_url("https://steamrip.com/")["ok"])
        afirmar(scans.canonizar_steam("Teste") == ("", ""))
        afirmar(musicas.capa_album_url("A", "B", "C") == "")
        for consultar in (emuladores.azahar_release_info, emuladores.desmume_release_info):
            afirmar(not consultar().get("ok"))
        afirmar(not abrir.called, "transporte remoto foi chamado em modo avião")


def teste_sessao_manual_idempotente_se_apagar_marcador_falhar():
    from bib_nucleo import estatisticas
    from bib_nucleo import sessoes_manuais as S
    raiz, jogo, svc = _base()
    marcador = Path(S.iniciar_sessao_manual(jogo["id"], jogo["titulo"])["arquivo"])
    with patch.object(Path, "unlink", side_effect=OSError("ocupado")):
        r = S.encerrar_sessao_manual(str(marcador), 2.5, db_path=svc.db_path)
    afirmar(r["ok"] and r["somado"] == 2.5 and marcador.is_file(), r)
    repetido = S.encerrar_sessao_manual(str(marcador), 2.5, db_path=svc.db_path)
    afirmar(repetido["ok"] and repetido["somado"] == 0 and not marcador.exists(), repetido)
    import bib_core as core
    con = core.get_db(svc.db_path)
    try:
        afirmar(core.listar_jogos(con)[0]["horas"] == 2.5)
        afirmar(estatisticas.resumo_ano(con)["total_horas"] == 2.5)
    finally:
        con.close()
