# Releases da TucoTeca

Uma release é uma entrega congelada: instaladores, fontes e tag são da
**mesma versão e revisão**. Nenhuma etapa toca a coleção pessoal (as provas
usam coleções sintéticas).

| Sistema | Entrega | Como instala |
|---|---|---|
| Windows 10/11 | `TucoTeca-Setup-<versão>-x64.exe` (NSIS, sem assinatura) | um clique: instala para o usuário, sem admin, e abre o app |
| macOS 13+ | `TucoTeca-<versão>-mac-<arm64\|x64>.dmg` (ad-hoc, sem notarização) | arrastar para *Aplicativos*; 1ª vez: botão direito → *Abrir* (macOS 15+: *Abrir Mesmo Assim* em Privacidade e Segurança) |

Os dois levam, em `resources/tucoteca/`, o núcleo (`bib_nucleo`), a ponte
(`ponte*.py`, `servicos_ui`), `abrir_hub.py`, `VERSION`, `LICENSE`, os docs do
menu Ajuda e o Python 3.14 da plataforma. Linux roda pelos fontes.

## 1. Congelar

Versão em `codigo/VERSION`, `pyproject.toml` e `package.json` (+ lock) e a
seção do `docs/CHANGELOG.md` — o preparador recusa divergência. Gates verdes
(`validar.py`), commit, push da branch e CI verde na revisão (`$sha`).

## 2. Instaladores

- **macOS:** saem do CI (jobs `app-mac` e `app-mac-intel`): runtime de cada
  arquitetura, `npm run dist:mac`, `preparar_release.py --conferir-mac`
  (confere cada `.app` e grava `conferencia-mac.json` com os SHA-256) e
  selftest — o da Intel instalado a partir da `.dmg` num Mac Intel.
  `gh run download <run> --name mac-dmgs --dir dist/mac-v<versão>`.
- **Windows:** no próprio checkout, com a árvore limpa na revisão da release (o
  repositório fica num caminho curto, como `C:\Projetos\TucoTeca`: o NSIS falha
  com caminho longo):

```powershell
py -3.14 -B codigo/ferramentas/preparar_runtime_python.py   # python.org, SHA-256 fixado
npm --prefix codigo/frontends/electron run dist
$env:BIBLIOTECA_HOME = "<coleção sintética de semear_prova_electron.py>"
codigo\frontends\electron\dist\win-unpacked\TucoTeca.exe --selftest
```

Sem Python embutido o `dist` falha; `TUCOTECA_SEM_RUNTIME=1` aceita e as
notas avisam. Ícones: `gerar_icone.py` (o teste confere os pixels).

## 3. Anexos

```powershell
py -3.14 -B codigo/ferramentas/preparar_release.py --revisao $sha `
    --saida dist/release/v<versão> --dist <dist do Windows> --mac dist/mac-v<versão>
```

Exige HEAD limpo no `$sha`, confere versões, o app empacotado (núcleo,
runtime, nada pessoal) e só aceita `.dmg` conferidas no Mac na mesma revisão
com o mesmo SHA-256. Gera, sem sobrescrever entrega antiga:

- anexos: os instaladores, `tucoteca-<versão>-fontes.zip`, `release.json`
  (revisão, instaladores, runtime) e `SHA256SUMS.txt`;
- `NOTAS-RELEASE.md`: o texto da página da release (instalação curta por
  sistema + changelog) — não vai como anexo.

## 4. Publicar

1. Merge `--no-ff` na `main`, tag anotada no `$sha`, push normal.
2. `gh release create v<versão> --draft --verify-tag --notes-file NOTAS-RELEASE.md <anexos>`.
3. Confira nomes, tamanhos e digests SHA-256 da API contra os arquivos.
4. `gh release edit v<versão> --draft=false --latest`.

Nunca `--clobber`, mover tag publicada ou reescrever histórico para corrigir
uma entrega: corrige-se com uma versão nova.
