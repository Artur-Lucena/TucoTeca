# 🎮 TucoTeca

Biblioteca pessoal de jogos **zero dependências** (só Python 3.10+ da stdlib,
sem navegador e sem rede), com a mesma coleção no Windows e no Linux
(Mac em construção). Catálogo, play direto, emuladores 3DS/NDS, mods,
cheats, texturas HD, controles, músicas e repacks — tudo com backup
versionado e suíte de testes verde.

## Abrir

- **Windows:** duplo-clique em **`BibliotecaHub.bat`** (ou
  `python codigo/frontends/app_win.py`, comando `tucoteca`).
- **Linux:** `./BibliotecaHub.sh` na raiz do projeto.
- **Mac:** duplo-clique em **`BibliotecaHubMac.command`** (experimental).

Tudo mora na pasta do projeto (`dados/`: banco, capas, backups, saves —
nunca vai pro git). Nunca abra em dois sistemas ao mesmo tempo — o app
trava a segunda instância sozinho (`.biblioteca.lock`).

## O que ela faz

- 📚 **Catálogo** — título, capa 600×800, nota, status (backlog, jogando,
  zerado…), etiquetas, favorito, busca e filtros (inclusive por plataforma).
- ▶️ **Play direto** — um clique (ou `app_win.py --jogar "Nome"`, ideal para
  atalhos do Desktop) abre o jogo no emulador/exe certo, minimiza o Hub e
  volta ao fechar, somando as horas sozinho.
- 📥 **Repacks automáticos** — arraste `.rar/.zip/.7z/.iso`: extrai para
  `Piratas/`, organiza pastas, limpa sobras, acha o exe, importa sem
  duplicar e busca a capa Steam sozinho.
- 🎮 **3DS e NDS** — scan de ROMs que lê título e capa de dentro do arquivo,
  atualiza Azahar/DeSmuME sozinho, presets por jogo e saves centralizados
  com backup próprio.
- 🎨 **Mods 3DS por jogo** — importe o pack uma vez, ligue/desligue por jogo.
- 🖼️ **Texturas HD por jogo** — packs em `user/load/textures/<title-id>`,
  liga/desliga sem privilégio nem cópia.
- 💥 **Cheats Gateway por jogo** — `user/cheats/<title-id>.txt`, liga/desliga
  (valem após reiniciar o jogo).
- 🎮 **Controles** — detecta Xbox/PlayStation/Switch Pro, fotografa e aplica
  perfis do Azahar, testa apertos ao vivo.
- 🎵 **Músicas** — importa do Harmoni (`music/`) para `dados/musicas/`,
  toca no player do sistema, viaja no pacote portátil.
- 📦 **Pacote portátil** — `.zip` com banco + capas + saves (+ músicas
  opcional) para levar a coleção a outra máquina.
- 💾 **Backup versionado** — um botão, guarda os últimos 10 (e avisa se o
  último tem +7 dias, além de backup silencioso antes de cada importação).

## Instalar em outra máquina

Tudo 100% offline (Python + emuladores dentro, nada baixa nada):

- **Windows:** `TucoTeca-Setup.exe` — wizard clássico, sem admin, com
  desinstalador (a coleção em `dados\` é preservada).
- **Linux:** `tucoteca-setup.run` — pergunta a pasta, cria o ícone no menu
  e o `desinstalar.sh`.
- **Portátil:** o `.zip` de sempre continua existindo (extrair e abrir).

Os instaladores saem de `dist/` via `codigo/ferramentas/montar_portatil.py`
(Windows, precisa do Inno Setup 6) e `montar_linux.py` (Linux), ou todos de
uma vez via `montar_universal.py` (+ `INSTALAR.html` que detecta o SO).

## Pastas

- `codigo/bib_nucleo/` — o núcleo (`base`, `banco`, `scans`, `emuladores`,
  `pacotes`, `atualizacao`, `repacks`, `texturas`, `cheats`, `controles`,
  `musicas`); `codigo/bib_core.py` é só compat de import.
- `codigo/frontends/` — `app_win.py` (tkinter) e `app_tui.py` (curses).
- `codigo/ferramentas/` — testes, montadores e `instalador.iss`.
- `codigo/historico/` — arquivo local, fora do git.
- `dados/` — o que é seu (nunca vai pro git). `dist/` — gerados.
- `midia/fontes-capas/` — artes-fonte das capas.

## Testes

```bash
python codigo/ferramentas/testes/executar.py   # suíte em sandbox por teste
python codigo/frontends/app_win.py --selftest  # monta a UI oculta e sai
```

Cada `teste_*` roda isolado em subprocesso + diretório temporário próprios
(sem rede, sem escrita fora do sandbox). Padrão do projeto: backup antes de
qualquer escrita em disco, verificação executando após qualquer mudança.

## Licença

MIT — ver `LICENSE`.
