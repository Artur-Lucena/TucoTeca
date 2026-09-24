# 🎮 TucoTeca

Sua biblioteca de jogos, sem depender do Hydra. Só Python 3.10+, sem instalar nada além disso — mesma coleção no Windows, no Linux e (em breve) no Mac.

## Abrir

- **Windows:** duplo-clique em **`TucoTeca.lnk`** (ou digite `tucoteca` no terminal).
- **Linux:** `./BibliotecaHub.sh` na raiz do projeto.
- **Mac:** duplo-clique em **`BibliotecaHubMac.command`** (suporte em construção — por enquanto, só ROMs 3DS/NDS).

## Instalar em outra máquina

Tudo 100% offline (Python + emuladores dentro, nada baixa nada):

- **Windows:** `TucoTeca-Setup.exe` — wizard clássico, sem admin, com desinstalador (a coleção em `dados\` é preservada).
- **Linux:** `tucoteca-setup.run` — `./tucoteca-setup.run`, pergunta a pasta, cria o ícone no menu e o `desinstalar.sh`.
- **Portátil:** o `.zip` de sempre continua existindo (extrair e abrir).

Os instaladores saem de `dist/` via `codigo/ferramentas/montar_portatil.py --setup` (Windows, precisa do Inno Setup 6) e `montar_linux.py` (Linux).

Tudo mora numa pasta só (banco, capas, backups): `D:\Tuco-Compartilhado\Jogos\biblioteca\` no Windows. Nunca abra em dois sistemas ao mesmo tempo — o app trava a segunda instância sozinho.

## O que ela faz

- 📚 **Catálogo** — cadastre jogos com capa, nota, status (backlog, jogando, zerado…), etiquetas e favorito. Busca e filtros por tudo isso.
- ▶️ **Play direto** — um clique abre o jogo no emulador ou exe certo, já com o caminho traduzido pro sistema atual.
- 🎮 **3DS e NDS** — scan de ROMs que lê título e capa de dentro do arquivo, atualiza o Azahar/DeSmuME sozinho e guarda saves com backup próprio.
- 🎨 **Mods 3DS por jogo** — importe um pack uma vez, ligue/desligue por jogo, e o Hub monta tudo sozinho na hora de jogar.
- ⏱️ **Horas automáticas** — o tempo jogado é somado sozinho.
- 📥 **Importar de tudo** — pasta, arquivo avulso, ou leitura do disco (Steam, GOG, Epic, Hydra…) sem duplicar o que já existe.
- 📦 **Pacote portátil** — um `.zip` com banco + capas + saves pra levar a coleção pra outra máquina.
- 💾 **Backup versionado** — um botão, guarda os últimos 10.

## Cuidando da coleção

1. **💾 Backup** dentro do app (vai pra pasta `backups/`), ou
2. **📦 Pacote portátil** pra levar pra outra máquina, ou
3. Copie `biblioteca.db` com tudo fechado.

O app avisa se o backup está velho (+7 dias) e faz um silencioso antes de cada importação.

## Pastas

- `codigo/` — o programa (núcleo, telas, ferramentas).
- `dados/` — o que é seu: banco, capas, backups, saves (nunca vai pro git).
- `dist/` — portáteis gerados.
