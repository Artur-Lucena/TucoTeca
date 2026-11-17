<!-- Obrigado por contribuir! Preencha o que fizer sentido. -->
**O que este PR faz**

<!-- Ex.: corrige achar_exe descartando exe pequeno em subpasta -->

**Motivo / issue relacionada**

**Como testar**
```powershell
py -3.14 codigo/ferramentas/testes/executar.py
npm --prefix codigo/frontends/electron test
npm --prefix codigo/frontends/electron run typecheck
```

**Checklist**
- [ ] Suíte Python e vitest verdes
- [ ] `git diff --check` limpo (sem espaços no fim / conflitos)
- [ ] Docs atualizadas (`ARQUITETURA.md`, `DESKTOP_ELECTRON.md`, `docs/CHANGELOG.md`)
- [ ] Nenhum dado pessoal/coleção incluído no diff
- [ ] Sem segredos (tokens, credenciais)
