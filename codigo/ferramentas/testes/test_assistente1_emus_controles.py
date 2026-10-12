"""A1-05: atualização de emuladores e controles avançados no Qt.

Sucesso = status local sem rede; consulta mostra remoto; atualizar usa a info
consultada; presets fotografam/aplicam; mapa gera; estado lê o resumo.
Cancelamento = atualizar sem consultar avisa e não instala; nome vazio falha.
Falha = release com erro, instalar com erro e tipo inválido falham explícito.
Nenhum download/instalação real, nenhuma rede, nenhum hardware: release_info,
instalar, XInput e SDL são simulados por patch. Prova física e rede viva ficam
para validação coordenada.
Parte Qt usa _qt() e pula sem PySide6.
"""
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from servicos_ui import ServicoBiblioteca


def _servico_tmp():
    tmp = Path(tempfile.mkdtemp(prefix="a1-emu-"))
    db = tmp / "colecao.db"
    svc = ServicoBiblioteca(str(db))
    with closing(core.get_db(str(db))):
        pass
    return svc, tmp, db


def _prov_falso(chamadas, tag_remota="v2", instalar_ok=True):
    def release_info():
        chamadas.append("release_info")
        return {"tag": tag_remota, "size": 40 * 1048576, "url": "https://exemplo.invalid/emu.zip"}
    def versao_local():
        return "v1"
    def instalar(info, progresso=None):
        chamadas.append(("instalar", dict(info)))
        if instalar_ok:
            return {"ok": True, "tag": tag_remota}
        return {"ok": False, "erro": "rede caiu no meio"}
    return {"chave": "azahar", "nome": "Azahar Falso", "origens": (),
            "sistemas": (), "rom_exts": (),
            "release_info": release_info, "versao_local": versao_local,
            "instalar": instalar}


def teste_status_local_sem_rede():
    svc, _tmp, _db = _servico_tmp()
    chamadas: list = []
    falsos = {"azahar": _prov_falso(chamadas), "desmume": _prov_falso(chamadas)}
    with patch.object(core, "provedores", lambda: falsos):
        r = svc.emus_status()
    afirmar(len(r["itens"]) == 2, r)
    afirmar(all(i["tag"] == "" and i["atualizado"] is None for i in r["itens"]), r)
    afirmar("release_info" not in chamadas, chamadas)


def teste_consultar_mostra_remoto_e_atualizado():
    svc, _tmp, _db = _servico_tmp()
    chamadas: list = []
    falsos = {"azahar": _prov_falso(chamadas, "v2"), "desmume": _prov_falso(chamadas, "v2")}
    with patch.object(core, "provedores", lambda: falsos):
        c = svc.emu_consultar("azahar")
    afirmar(c["local"] == "v1" and c["tag"] == "v2", c)
    afirmar(c["atualizado"] is False and c["tamanho_mb"] == 40, c)
    afirmar(isinstance(c["info"], dict) and c["info"]["tag"] == "v2", c)
    falsos2 = {"azahar": _prov_falso([], "v1"), "desmume": _prov_falso([], "v1")}
    with patch.object(core, "provedores", lambda: falsos2):
        c2 = svc.emu_consultar("azahar")
    afirmar(c2["atualizado"] is True, c2)


def teste_consultar_com_erro_falha_explicita():
    svc, _tmp, _db = _servico_tmp()
    prov = _prov_falso([])
    prov["release_info"] = lambda: {"erro": "sem rede agora"}
    with patch.object(core, "provedores", lambda: {"azahar": prov, "desmume": _prov_falso([])}):
        try:
            svc.emu_consultar("azahar")
        except ValueError as e:
            afirmar("sem rede" in str(e), str(e))
        else:
            raise AssertionError("aceitou release com erro")
        try:
            svc.emu_consultar("inexistente")
        except ValueError as e:
            afirmar("desconhecido" in str(e).lower(), str(e))
        else:
            raise AssertionError("aceitou chave desconhecida")


def teste_atualizar_so_com_info_consultada():
    svc, _tmp, _db = _servico_tmp()
    chamadas: list = []
    falsos = {"azahar": _prov_falso(chamadas), "desmume": _prov_falso(chamadas)}
    with patch.object(core, "provedores", lambda: falsos):
        try:
            svc.emu_atualizar("azahar", {})
        except ValueError as e:
            afirmar("consulte" in str(e).lower(), str(e))
        else:
            raise AssertionError("instalou sem consultar")
        r = svc.emu_atualizar("azahar", {"tag": "v2", "size": 1})
    afirmar(r.get("ok") is True, r)
    afirmar(chamadas == [("instalar", {"tag": "v2", "size": 1})], chamadas)
    falsos_ruins = {"azahar": _prov_falso([], instalar_ok=False), "desmume": _prov_falso([])}
    with patch.object(core, "provedores", lambda: falsos_ruins):
        try:
            svc.emu_atualizar("azahar", {"tag": "v2"})
        except ValueError as e:
            afirmar("rede caiu" in str(e), str(e))
        else:
            raise AssertionError("anunciou sucesso na falha")


def teste_controles_fotografar_aplicar_gerar():
    svc, _tmp, _db = _servico_tmp()
    fotos: list = []
    with patch.object(core, "fotografar_perfil", lambda n: fotos.append(n) or {"ok": True, "preset": n}), \
            patch.object(core, "aplicar_preset_controle", lambda n: {"ok": True, "chaves": 12}), \
            patch.object(core, "detectar_sdl", lambda: []), \
            patch.object(core, "nomes_sdl", lambda: {}), \
            patch.object(core, "salvar_mapa_gerado",
                         lambda t, guid="", port=0, nome="", rotulos=None: {"ok": True, "preset": nome}):
        r = svc.controle_fotografar("Meu Pad")
        afirmar(r.get("preset") == "Meu Pad", r)
        afirmar(fotos == ["Meu Pad"], fotos)
        a = svc.controle_aplicar("Meu Pad")
        afirmar(a.get("chaves") == 12, a)
        g = svc.controle_gerar("xbox360")
        afirmar(g.get("preset") == "xbox360-hub", g)
        for fn, arg in ((svc.controle_fotografar, "  "), (svc.controle_aplicar, "")):
            try:
                fn(arg)
            except ValueError:
                pass
            else:
                raise AssertionError(f"aceitou nome vazio em {fn.__name__}")
        try:
            svc.controle_gerar("patinete")
        except ValueError as e:
            afirmar("tipo" in str(e).lower(), str(e))
        else:
            raise AssertionError("aceitou tipo inválido")


def teste_controle_estado_resumo():
    svc, _tmp, _db = _servico_tmp()
    with patch.object(core, "ler_estado_xinput", lambda slot: {"slot": slot}), \
            patch.object(core, "resumir_estado", lambda est: f"A=1 slot={est['slot']}"):
        r = svc.controle_estado()
    afirmar(r.get("resumo") == "A=1 slot=0", r)


def _sincrono(bridge):
    def executar(rotulo, trabalho, pronto=None, falha=None):
        try:
            r = trabalho()
        except Exception as exc:
            if falha:
                falha(str(exc))
            else:
                bridge.aviso.emit(str(exc), True)
            return
        if pronto:
            pronto(r)
    return patch.object(bridge, "executar", side_effect=executar)


def teste_qt_consulta_e_atualizacao_com_confirmacao():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    consulta = {"chave": "azahar", "nome": "Azahar", "local": "v1", "tag": "v2",
                "tamanho_mb": 40, "atualizado": False, "info": {"tag": "v2"}}
    instalacoes: list = []
    avisos: list = []
    bridge.aviso.connect(lambda texto, erro: avisos.append((texto, erro)))
    try:
        with _sincrono(bridge), \
                patch.object(bridge.servico, "emu_consultar", lambda c: dict(consulta)), \
                patch.object(bridge.servico, "emu_atualizar",
                             lambda c, i: instalacoes.append((c, dict(i))) or {"ok": True, "tag": "v2"}):
            bridge.atualizarEmu("azahar")
            afirmar(any("consulte" in t.lower() for t, _ in avisos), avisos)
            afirmar(instalacoes == [], instalacoes)
            bridge.consultarEmu("azahar")
            afirmar(bridge.emus["consulta"].get("tag") == "v2", bridge.emus)
            bridge.atualizarEmu("azahar")
            afirmar(instalacoes == [("azahar", {"tag": "v2"})], instalacoes)
    finally:
        bridge.fechar()


def teste_qt_pads_fotografar_aplicar_gerar_estado():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    aplicadas: list = []
    try:
        with _sincrono(bridge), \
                patch.object(bridge.servico, "controles_pads",
                             lambda: {"pads": [{"nome": "Pad Falso"}]}), \
                patch.object(bridge.servico, "controles_presets",
                             lambda: {"presets": ["Base"]}), \
                patch.object(bridge.servico, "controles_tipos",
                             lambda: {"tipos": [{"tipo": "xbox360", "nome": "xbox360"}]}), \
                patch.object(bridge.servico, "controle_fotografar",
                             lambda n: {"ok": True, "preset": n}), \
                patch.object(bridge.servico, "controle_aplicar",
                             lambda n: aplicadas.append(n) or {"ok": True, "chaves": 3}), \
                patch.object(bridge.servico, "controle_gerar",
                             lambda t: {"ok": True, "preset": f"{t}-hub"}), \
                patch.object(bridge.servico, "controle_estado",
                             lambda: {"resumo": "A=1"}):
            bridge.consultarPads()
            afirmar(bridge.pads["presets"] == ["Base"], bridge.pads)
            afirmar(bridge.pads["tipos"] == [{"tipo": "xbox360", "nome": "xbox360"}], bridge.pads)
            bridge.fotografarControle("Novo")
            bridge.aplicarControle("Base")
            afirmar(aplicadas == ["Base"], aplicadas)
            bridge.gerarControle("xbox360")
            bridge.lerEstadoControle()
            afirmar(bridge.pads["estado"] == "A=1", bridge.pads)
    finally:
        bridge.fechar()
