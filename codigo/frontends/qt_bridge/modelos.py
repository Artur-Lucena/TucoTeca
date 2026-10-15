#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: modelos de lista, tarefas em thread e constantes de controle."""
from __future__ import annotations

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QRunnable,
    Qt,
    Signal,
)

SECOES_CONTROLE = ("inicio", "jogos", "musicas", "desejos", "downloads", "integracoes", "videos", "youtube")
TECLAS_CONTROLE = {"cima": Qt.Key.Key_Up, "baixo": Qt.Key.Key_Down, "esquerda": Qt.Key.Key_Left,
                   "direita": Qt.Key.Key_Right, "confirmar": Qt.Key.Key_Return, "voltar": Qt.Key.Key_Escape}


class ModeloItens(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.itens = []

    def roleNames(self):
        return {Qt.UserRole + 1: b"item"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.itens)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and 0 <= index.row() < len(self.itens):
            if role == Qt.UserRole + 1:
                return self.itens[index.row()]
        return None

    def substituir(self, itens):
        self.beginResetModel()
        self.itens = list(itens)
        self.endResetModel()


class SinaisTarefa(QObject):
    terminou = Signal(int, object, str)


class Tarefa(QRunnable):
    def __init__(self, numero, trabalho):
        super().__init__()
        self.numero, self.trabalho = numero, trabalho
        self.sinais = SinaisTarefa()

    def run(self):
        try:
            resultado, erro = self.trabalho(), ""
        except Exception as exc:
            resultado, erro = None, str(exc) or type(exc).__name__
        self.sinais.terminou.emit(self.numero, resultado, erro)


__all__ = ["SECOES_CONTROLE", "TECLAS_CONTROLE", "ModeloItens", "SinaisTarefa",
           "Tarefa"]
