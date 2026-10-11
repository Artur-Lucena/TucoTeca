<!-- Obrigado por contribuir! Preencha o que fizer sentido. -->
**O que este PR faz**

<!-- Ex.: corrige achar_exe descartando exe pequeno em subpasta -->

**Motivo / issue relacionada**

**Como testar**
```powershell
py -3.14 codigo/ferramentas/testes/executar.py
py -3.14 codigo/ferramentas/testes/executar.py --modulo test_qt
py -3.14 codigo/frontends/desktop.py --selftest
```

**Checklist**
- [ ] Suíte verde (stdlib + Qt) e selftest
- [ ] `git diff --check` limpo (sem espaços no fim / conflitos)
- [ ] Docs atualizadas (`ARQUITETURA.md`, `DESKTOP_QT.md`, `CHANGELOG.md`)
- [ ] Nenhum dado pessoal/coleção incluído no diff
- [ ] Sem segredos (tokens, credenciais)
