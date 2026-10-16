# Roadmap — TucoTeca

Estado: **1.0.2 publicada** (14/10/2026, tag `v1.0.2`). Desenvolvimento da
**1.1.0** em curso; este documento substitui o roadmap da antiga estrutura de
assistentes, encerrada em 16/10/2026.

## 1.1.0 — frente atual

- **Poda do modo clássico (tkinter)**: remoção completa; o desktop passa a ser
  exclusivamente Qt Quick (PySide6) e a TUI curses continua atendendo
  Linux/macOS.
- **Upgrade visual do Qt Quick**: tema/tokens, cartões, hero e navegação no
  estilo de um launcher moderno.
- **Integrações modulares**: contrato com capacidades declaradas, template de
  provedor e guia para adicionar integrações em três passos
  (`docs/INTEGRACOES.md`).

## Pendências de produto (1.1.0)

- Prova macOS nativa (sem bundle validado; `.command` abre Qt e segue
  experimental).
- Prova física do controle (Xbox 360 reconhecido em XInput/SDL; falta a
  captura física dos botões).
- Credenciais vivas (Spotify, Steam, SteamGridDB): atualização pelo usuário no
  Hub; wishlist viva não comprovada (importação JSON é o fallback).
- Everything portátil: serviço ativo na máquina; preservar o uso de `-search*`
  (o parser do ES remove aspas com `-search`).

## Tarefas locais do coordenador (máquina do usuário)

- Testar `links_ntfs.py`; gerar/verificar ZIP de dados e metadados, com a
  origem inalterada.
- Preservar o Git divergente da instalação pessoal, históricos, backups e
  provas.
- Consolidar instalação/worktrees/atalhos/caches, somente nos alvos
  inventariados; a instalação pessoal continua pendente.
- Validar runtime, instalação/saves/rollback e preparar a release privada
  1.1.0 (sem assinatura, por decisão do usuário).

## Histórico

O caminho completo (rodadas de desenvolvimento, branches antigos e a release
1.0.2) está no `CHANGELOG.md` e em `docs/RECONCILIACAO_GITHUB.md`. O registro
local da estrutura de assistentes ficou arquivado em
`.provas/backups/poda-assistentes-2026-10-16/`.
