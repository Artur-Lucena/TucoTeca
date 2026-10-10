#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Volume geral do PC via Windows Core Audio (stdlib, sem player externo).

Consulta a saída padrão a cada operação: fones/HDMI trocados e ajustes
feitos pelas teclas de volume continuam sincronizados com o Hub.
COM e interfaces são abertos/usados/liberados na mesma thread.
"""
from __future__ import annotations

import math
import os
import sys
import uuid


def volume_pc_disponivel() -> bool:
    return sys.platform != "darwin" and os.name == "nt"


class _EndpointWindows:
    """IAudioEndpointVolume da saída padrão, com vida limitada a uma operação."""

    def __init__(self):
        import ctypes

        self.ct = ctypes
        self._desinicializar = False
        self._enum = ctypes.c_void_p()
        self._device = ctypes.c_void_p()
        self._volume = ctypes.c_void_p()

        class GUID(ctypes.Structure):
            _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                        ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]

        self.GUID = GUID
        self.ole = ctypes.WinDLL("ole32", use_last_error=True)
        self.ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.ole.CoInitializeEx.restype = ctypes.c_int32
        self.ole.CoUninitialize.argtypes = []
        self.ole.CoUninitialize.restype = None
        self.ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p,
                                            ctypes.c_uint32, ctypes.POINTER(GUID),
                                            ctypes.POINTER(ctypes.c_void_p)]
        self.ole.CoCreateInstance.restype = ctypes.c_int32

    def _guid(self, texto):
        return self.GUID.from_buffer_copy(uuid.UUID(texto).bytes_le)

    @staticmethod
    def _checar(rc, contexto):
        if rc < 0:
            raise OSError(f"{contexto} (0x{rc & 0xFFFFFFFF:08X})")

    def _chamar(self, obj, indice, tipos, *args, retorno=None):
        ct = self.ct
        vtable = ct.cast(obj, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
        func = ct.WINFUNCTYPE(retorno or ct.c_int32, ct.c_void_p, *tipos)(vtable[indice])
        return func(obj, *args)

    def __enter__(self):
        ct = self.ct
        rc = self.ole.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
        # Outra biblioteca já pode ter inicializado esta thread como MTA.
        if (rc & 0xFFFFFFFF) != 0x80010106:  # RPC_E_CHANGED_MODE
            self._checar(rc, "Inicialização do áudio")
            self._desinicializar = True
        try:
            clsid = self._guid("BCDE0395-E52F-467C-8E3D-C4579291692E")
            iid_enum = self._guid("A95664D2-9614-4F35-A746-DE8DB63617E6")
            self._checar(self.ole.CoCreateInstance(ct.byref(clsid), None, 23,
                                                  ct.byref(iid_enum), ct.byref(self._enum)),
                         "Enumerador de áudio")
            self._checar(self._chamar(self._enum, 4,
                                      (ct.c_int32, ct.c_int32, ct.POINTER(ct.c_void_p)),
                                      0, 1, ct.byref(self._device)),  # eRender, eMultimedia
                         "Saída de áudio padrão")
            iid_volume = self._guid("5CDF2C82-841E-4546-9722-0CF74078229A")
            self._checar(self._chamar(self._device, 3,
                                      (ct.POINTER(self.GUID), ct.c_uint32,
                                       ct.c_void_p, ct.POINTER(ct.c_void_p)),
                                      ct.byref(iid_volume), 23, None, ct.byref(self._volume)),
                         "Controle de volume")
        except Exception:
            self._fechar()
            raise
        return self

    def __exit__(self, *_exc):
        self._fechar()

    def _fechar(self):
        try:
            for obj in (self._volume, self._device, self._enum):
                if obj:
                    self._chamar(obj, 2, (), retorno=self.ct.c_uint32)  # IUnknown.Release
                    obj.value = None
        finally:
            if self._desinicializar:
                self.ole.CoUninitialize()
                self._desinicializar = False

    def ler(self) -> dict:
        ct = self.ct
        scalar, mudo = ct.c_float(), ct.c_int32()
        self._checar(self._chamar(self._volume, 9, (ct.POINTER(ct.c_float),),
                                  ct.byref(scalar)), "Leitura do volume")
        self._checar(self._chamar(self._volume, 15, (ct.POINTER(ct.c_int32),),
                                  ct.byref(mudo)), "Leitura do silenciamento")
        return {"nivel": min(100.0, max(0.0, scalar.value * 100.0)),
                "mudo": bool(mudo.value)}

    def definir(self, nivel: float):
        ct = self.ct
        self._checar(self._chamar(self._volume, 7,
                                  (ct.c_float, ct.POINTER(self.GUID)), nivel / 100.0, None),
                     "Ajuste do volume")

    def silenciar(self, mudo: bool):
        ct = self.ct
        self._checar(self._chamar(self._volume, 14,
                                  (ct.c_int32, ct.POINTER(self.GUID)), int(mudo), None),
                     "Silenciamento do áudio")


def _nivel(valor) -> float:
    nivel = float(valor)
    if not math.isfinite(nivel):
        raise ValueError("volume deve ser um número entre 0 e 100")
    return min(100.0, max(0.0, nivel))


def _operar(acao) -> dict:
    if not volume_pc_disponivel():
        return {"ok": False, "erro": "Controle do volume do PC disponível no Windows."}
    try:
        with _EndpointWindows() as endpoint:
            estado = acao(endpoint)
        return {"ok": True, **estado}
    except (OSError, ValueError, AttributeError) as e:
        return {"ok": False, "erro": f"Volume do PC indisponível: {e}"}


def ler_volume_pc() -> dict:
    """{'ok', 'nivel' (0–100), 'mudo'} da saída padrão; não altera o volume."""
    return _operar(lambda ep: ep.ler())


def definir_volume_pc(nivel, mudo: bool | None = None) -> dict:
    """Ajusta o volume geral. `mudo=None` preserva o silenciamento atual."""
    try:
        limpo = _nivel(nivel)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "erro": "Volume deve ser um número entre 0 e 100."}

    def acao(ep):
        ep.definir(limpo)
        if mudo is not None:
            ep.silenciar(bool(mudo))
        return ep.ler()

    return _operar(acao)


def ajustar_volume_pc(delta=5) -> dict:
    """Sobe/desce pontos percentuais; restaura o som se o nível ficar >0."""
    try:
        passo = float(delta)
        if not math.isfinite(passo):
            raise ValueError("passo inválido")
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "erro": "Passo de volume inválido."}

    def acao(ep):
        novo = _nivel(ep.ler()["nivel"] + passo)
        ep.definir(novo)
        if novo > 0:
            ep.silenciar(False)
        return ep.ler()

    return _operar(acao)


def alternar_mudo_pc() -> dict:
    def acao(ep):
        ep.silenciar(not ep.ler()["mudo"])
        return ep.ler()

    return _operar(acao)


__all__ = ['volume_pc_disponivel', 'ler_volume_pc', 'definir_volume_pc',
           'ajustar_volume_pc', 'alternar_mudo_pc']
