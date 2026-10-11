"""Saves, perfis, patches, pastas, API e integridade — sem rede ou dados reais."""
import hashlib
import json
import os
import struct
import tempfile
import zlib
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


def _numero_bps(n):
    dados = bytearray()
    while True:
        b = n & 127
        n >>= 7
        if n == 0:
            dados.append(b | 128)
            return bytes(dados)
        dados.append(b)
        n -= 1


def _bps(src, dst, acoes):
    raw = b"BPS1" + _numero_bps(len(src)) + _numero_bps(len(dst)) + _numero_bps(0) + acoes
    raw += struct.pack("<II", zlib.crc32(src), zlib.crc32(dst))
    return raw + struct.pack("<I", zlib.crc32(raw))


def teste_ips_normal_rle_e_truncamento():
    from bib_nucleo.patches_rom import aplicar_ips
    raw = b"PATCH" + b"\0\0\1\0\2XY" + b"\0\0\4\0\0\0\3Z" + b"EOF"
    afirmar(aplicar_ips(b"abcdef", raw) == b"aXYdZZZ")
    afirmar(aplicar_ips(b"abcdef", b"PATCHEOF\0\0\3") == b"abc")
    for ruim in (b"PATCH", b"PATCH\0\0\1\0\3X", b"PATCHEOFx"):
        try:
            aplicar_ips(b"abc", ruim)
        except ValueError:
            pass
        else:
            raise AssertionError("aceitou IPS truncado")


def teste_bps_quatro_acoes_crc_e_limites():
    from bib_nucleo.patches_rom import aplicar_bps
    src, dst = b"abcdef", b"abXcdcdcd"
    acoes = (_numero_bps((2 - 1) << 2) + _numero_bps(1) + b"X"
             + _numero_bps(((2 - 1) << 2) | 2) + _numero_bps(2 << 1)
             + _numero_bps(((4 - 1) << 2) | 3) + _numero_bps(3 << 1))
    raw = _bps(src, dst, acoes)
    afirmar(aplicar_bps(src, raw) == dst)
    for fonte, patch_bps, limite in ((b"wrong", raw, 100), (src, raw[:-1] + b"!", 100), (src, raw, 2)):
        try:
            aplicar_bps(fonte, patch_bps, limite)
        except ValueError:
            pass
        else:
            raise AssertionError("CRC/tamanho inválido aceito")


def teste_patch_preserva_rom_e_rejeita_destino_existente():
    from bib_nucleo.patches_rom import aplicar_patch
    raiz = Path(tempfile.mkdtemp())
    rom, ips, dest = raiz / "original.nds", raiz / "patch.ips", raiz / "nova.nds"
    rom.write_bytes(b"abc")
    ips.write_bytes(b"PATCH\0\0\1\0\1XEOF")
    afirmar(aplicar_patch(rom, ips, dest)["ok"] and dest.read_bytes() == b"aXc")
    afirmar(rom.read_bytes() == b"abc")
    try:
        aplicar_patch(rom, ips, rom)
    except ValueError:
        pass
    else:
        raise AssertionError("sobrescreveu original")


def teste_snapshot_saves_manifesto_hash_retencao_e_original_intacto():
    from bib_nucleo import saves
    import zipfile
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


def teste_watch_estabilidade_modificacao_e_nao_repete():
    from bib_nucleo.pastas_vigiadas import VigiaPasta
    pasta = Path(tempfile.mkdtemp())
    arq = pasta / "aventura.rar"
    arq.write_bytes(b"Rar!\x1a\x07\0" + b"x" * 100)
    vigia = VigiaPasta(pasta, estabilidade_s=10)
    afirmar(vigia.consultar(0) == [] and vigia.consultar(9) == [])
    afirmar(vigia.consultar(10)[0]["path"] == str(arq.resolve()))
    afirmar(vigia.consultar(20) == [])
    arq.write_bytes(arq.read_bytes() + b"novo")
    afirmar(vigia.consultar(21) == [])
    afirmar(len(vigia.consultar(31)) == 1)


def teste_hardlinks_fallback_copia_e_destino_protegido():
    from bib_nucleo.organizacao_local import copiar_ou_ligar
    raiz = Path(tempfile.mkdtemp())
    src = raiz / "origem"
    src.mkdir()
    (src / "game.exe").write_bytes(b"MZ123")
    with patch("os.link", side_effect=OSError("outro volume")):
        r = copiar_ou_ligar(src, raiz / "copia", hardlinks=True)
    afirmar(r["copiados"] == 1 and r["hardlinks"] == 0 and (src / "game.exe").is_file())
    try:
        copiar_ou_ligar(src, raiz / "copia")
    except ValueError:
        pass
    else:
        raise AssertionError("destino existente sobrescrito")


def teste_api_token_host_origin_e_rotas_de_leitura():
    from bib_nucleo.api_local import autorizado, consultar
    raiz, jogo, svc = _base()
    token = "a" * 43
    headers = {"Host": "127.0.0.1:8000", "Authorization": "Bearer " + token}
    afirmar(autorizado(headers, token, 8000))
    for mudanca in ({"Host": "evil.example:8000"}, {"Origin": "https://evil.example"},
                    {"Authorization": "Bearer errado"}):
        afirmar(not autorizado({**headers, **mudanca}, token, 8000))
    afirmar(consultar(svc, "/jogos")[1][0]["titulo"] == "Aventura")
    afirmar(consultar(svc, "/executar")[0] == 404)


def teste_ferramenta_sha_divergente_preserva_instalacao():
    from bib_nucleo import baixar as B
    pasta = Path(tempfile.mkdtemp())
    antigo = pasta / "yt-dlp.exe"
    antigo.write_bytes(b"anterior")
    with patch.object(B, "_baixar_bin", return_value=b"MZarquivo adulterado"):
        r = B.instalar_ytdlp(pasta)
    afirmar(not r["ok"] and "SHA-256" in r["erro"] and antigo.read_bytes() == b"anterior")


def teste_rede_desligada_bloqueia_http_e_processos_remotos():
    from bib_nucleo.rede import fontes, online
    from bib_nucleo import baixar, scans
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
    from bib_nucleo import estatisticas
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
    from bib_nucleo.rede import online, letras, fontes, sponsorblock, binarios, capas_libretro, spotify
    from bib_nucleo import emuladores, scans, musicas
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
    from bib_nucleo import sessoes_manuais as S, estatisticas
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
