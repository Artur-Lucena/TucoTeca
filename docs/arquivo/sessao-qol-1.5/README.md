# TucoTeca — pasta dedicada do projeto Hub

Workspace do agente e da continuidade do Hub, separado da memória genérica.
Criada em 10/10/2026 (movido de `IA/Opencode Memory/`, deixada vazia).

- `continuidade/` — `TucoTeca.md` (memória de continuidade lida ao entrar
  no Linux; conservar a ordem de recência).
- `validacao/` — scripts de prova (`auditar_tucoteca.py`,
  `validar_tucoteca_qt.py`) e capturas. Saídas pesadas (cópias de banco)
  continuam em `%TEMP%\opencode`, fora da árvore compartilhada.
- `sessao/` — notas de sessão e resultados de auditoria.
- `projeto/` — ligação NTFS para o repositório canônico, incluindo `.git`.
  Abrir essa pasta no editor permite acompanhar o Git e editar os fontes reais.
- `Git-Projeto.bat` — painel ao vivo de branch, alterações e últimos commits
  (atualiza a cada 3 segundos; Ctrl+C encerra). `--uma-vez` imprime uma vez.

Código e coleção canônicos moram em `Jogos/biblioteca/` e não se movem:
`codigo/`, `dados/`, launchers e `.lnk` continuam válidos sem alteração.

No terminal desta raiz: `git -C projeto status --short --branch` e
`git -C projeto diff`. No Linux, usar diretamente o caminho canônico em
`Jogos/biblioteca/`; `projeto/` é uma junction criada no Windows.
