"""Watch folder por polling: só entrega arquivos estáveis; automação é opt-in."""
from __future__ import annotations

import time
from pathlib import Path

from bib_nucleo.rede.repacks import ARQUIVO_EXTS, eh_pacote_hub


class VigiaPasta:
    def __init__(self, pasta, estabilidade_s=15):
        self.pasta = Path(pasta)
        self.estabilidade_s = max(0, float(estabilidade_s))
        self._vistos, self._entregues = {}, set()

    def consultar(self, agora=None):
        if not self.pasta.is_dir():
            return []
        agora = time.monotonic() if agora is None else agora
        presentes, prontos = set(), []
        for arq in sorted(self.pasta.iterdir()):
            if arq.is_symlink() or not arq.is_file() or arq.suffix.lower() not in ARQUIVO_EXTS:
                continue
            if getattr(arq.lstat(), "st_file_attributes", 0) & 0x400:
                continue
            stat = arq.stat()
            if not stat.st_size:
                continue
            assinatura = (stat.st_size, stat.st_mtime_ns)
            chave = str(arq.resolve())
            presentes.add(chave)
            antes = self._vistos.get(chave)
            if antes is None or antes[0] != assinatura:
                self._vistos[chave] = (assinatura, agora)
                self._entregues.discard(chave)
            elif (chave not in self._entregues and agora - antes[1] >= self.estabilidade_s
                  and not any(arq.with_name(arq.name + ext).exists() for ext in (".part", ".crdownload"))):
                self._entregues.add(chave)
                if not eh_pacote_hub(arq):
                    prontos.append({"nome": arq.name, "path": chave, "bytes": stat.st_size})
        self._vistos = {k: v for k, v in self._vistos.items() if k in presentes}
        self._entregues.intersection_update(presentes)
        return prontos
