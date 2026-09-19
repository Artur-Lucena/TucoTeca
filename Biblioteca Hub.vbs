' Biblioteca Hub — duplo-clique para abrir, sem janela preta.
' Usa o Python do sistema; a casa e o banco ficam na pasta do projeto.
Option Explicit
Dim sh, fso, hub
Set sh = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
hub = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Environment("PROCESS")("BIBLIOTECA_HOME") = hub & "\"
sh.Run "python """ & hub & "\codigo\frontends\app_win.py""", 0, False
