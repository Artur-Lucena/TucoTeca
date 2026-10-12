"""Mods, texturas, cheats e presets do Azahar no detalhe de um jogo 3DS (Qt)."""
from __future__ import annotations

from bib_nucleo import cheats as CHEATS
from bib_nucleo import controles as CONTROLES
from bib_nucleo import emuladores as EMU
from bib_nucleo import texturas as TEXTURAS
from bib_nucleo.base import traduzir_para_atual
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot


def _vazio(erro=""):
    return {"gid": 0, "titulo": "", "tid": "", "erro": erro, "mods": [], "mods_off": False,
            "cheats": [], "textura": {"instalado": False, "ativo": False, "arquivos": 0},
            "presets": [], "presets_controle": [], "controles": []}


def _tid(jogo):
    launch = (jogo.get("launch_options") or "").strip()
    return EMU.title_id_da_rom(traduzir_para_atual(launch)) if launch else ""


class FerramentasEmulador(QObject):
    mudou = Signal()

    def __init__(self, hub):
        super().__init__(hub)
        self._hub = hub
        self._geracao = 0
        self._dados = _vazio()

    @Property("QVariantMap", notify=mudou)
    def dados(self):
        return self._dados

    @Slot(int)
    def carregar(self, gid):
        self._geracao += 1
        geracao, gid = self._geracao, int(gid or 0)

        def mostrar(dados):
            if geracao == self._geracao:
                self._dados = dados
                self.mudou.emit()
        self._hub.executar("Lendo mods, texturas e cheats…", lambda: self._ler(gid), mostrar)

    @Slot()
    def limpar(self):
        self._geracao += 1
        self._dados = _vazio()
        self.mudou.emit()

    def _ler(self, gid):
        if not gid:
            return _vazio()
        jogo = self._hub.servico.jogo(gid)
        base = _vazio()
        base.update(gid=gid, titulo=jogo.get("titulo") or "")
        tid = _tid(jogo)
        if not tid:
            base["erro"] = "Escolha um jogo 3DS com ROM válida para gerenciar mods, texturas, cheats e presets."
            return base
        ativos = set(EMU.mods_ativos(jogo))
        base.update(
            tid=tid,
            mods=[{"nome": n, "ativo": n in ativos} for n in EMU.listar_mods(tid)],
            mods_off=bool(jogo.get("azahar_mods_off")),
            cheats=CHEATS.listar_cheats(tid),
            textura=TEXTURAS.estado_textura(tid),
            presets=EMU.listar_presets("azahar"),
            presets_controle=CONTROLES.listar_presets_controle(),
            controles=CONTROLES.listar_controles(),
        )
        return base

    def _depois(self, rotulo, trabalho):
        if self._hub.ocupado:
            self._hub.aviso.emit("Aguarde a operação atual terminar.", False)
            return

        def pronto(r):
            if isinstance(r, dict) and r.get("ok") is False:
                raise ValueError(r.get("erro", "A operação não foi concluída."))
            if isinstance(r, dict):
                for aviso in r.get("avisos") or []:
                    self._hub.aviso.emit(aviso, False)
            self.carregar(self._dados["gid"])
        self._hub.executar(rotulo, trabalho, pronto)

    def _tid_atual(self):
        tid = self._dados.get("tid") or ""
        if not tid:
            raise ValueError("Escolha um jogo 3DS com ROM válida.")
        return tid

    def _jogo_atual(self):
        return self._hub.servico.jogo(self._dados["gid"])

    def _salvar_mods(self, ativos, off):
        return self._hub.servico.salvar_mods_jogo(self._dados["gid"], ativos, off)

    def _alternar_mod(self, nome):
        if nome not in EMU.listar_mods(self._tid_atual()):
            raise ValueError("Mod não encontrado na biblioteca.")
        jogo = self._jogo_atual()
        atuais = list(EMU.mods_ativos(jogo))
        ativos = [m for m in atuais if m != nome] if nome in atuais else atuais + [nome]
        return self._salvar_mods(ativos, bool(jogo.get("azahar_mods_off")))

    def _alternar_mods_off(self):
        self._tid_atual()
        jogo = self._jogo_atual()
        return self._salvar_mods(list(EMU.mods_ativos(jogo)), not jogo.get("azahar_mods_off"))

    def _remover_mod(self, nome):
        r = EMU.remover_mod(self._tid_atual(), nome)
        if not r.get("ok"):
            return r
        jogo = self._jogo_atual()
        return self._salvar_mods([m for m in EMU.mods_ativos(jogo) if m != nome],
                                 bool(jogo.get("azahar_mods_off")))

    @Slot(str)
    def alternarMod(self, nome):
        self._depois("Atualizando mods…", lambda: self._alternar_mod(nome))

    @Slot()
    def alternarModsOff(self):
        self._depois("Atualizando mods…", self._alternar_mods_off)

    @Slot(str)
    def removerMod(self, nome):
        self._depois("Removendo mod…", lambda: self._remover_mod(nome))

    @Slot(QUrl)
    def importarMod(self, url):
        self._depois("Importando mod…", lambda: EMU.importar_mod(url.toLocalFile(), self._tid_atual()))

    @Slot()
    def alternarTextura(self):
        self._depois("Atualizando texturas…", lambda: TEXTURAS.alternar_textura(self._tid_atual()))

    @Slot(QUrl)
    def instalarTextura(self, url):
        self._depois("Instalando texturas…",
                     lambda: TEXTURAS.instalar_textura(self._tid_atual(), url.toLocalFile()))

    @Slot(str)
    def alternarCheat(self, nome):
        self._depois("Atualizando cheat…", lambda: CHEATS.alternar_cheat(self._tid_atual(), nome))

    @Slot(str, str)
    def adicionarCheat(self, nome, codigo):
        self._depois("Salvando cheat…", lambda: CHEATS.adicionar_cheat(self._tid_atual(), nome, codigo))

    @Slot(str)
    def removerCheat(self, nome):
        self._depois("Removendo cheat…", lambda: CHEATS.remover_cheat(self._tid_atual(), nome))

    @Slot(str)
    def aplicarPreset(self, nome):
        self._depois("Aplicando preset…", lambda: EMU.aplicar_preset(nome, "azahar"))

    @Slot(str)
    def salvarPreset(self, nome):
        self._depois("Salvando preset…", lambda: EMU.salvar_preset_de_atual(nome, "azahar"))

    @Slot(str)
    def aplicarPresetControle(self, nome):
        self._depois("Aplicando controles…", lambda: CONTROLES.aplicar_preset_controle(nome))

    @Slot(str)
    def salvarPresetControle(self, nome):
        self._depois("Salvando controles…", lambda: CONTROLES.fotografar_perfil(nome))
