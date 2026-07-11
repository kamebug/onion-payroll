# Problemas Recorrentes — Histórico e Status

Documento de rastreamento dos bugs e problemas de UX já identificados
e corrigidos no Onion Payroll, organizados por categoria.

---

## ✅ Cobertos por testes automatizados (`test_main.py`)

Esses problemas têm teste permanente — rodam toda vez que `test_main.py`
é executado, prevenindo regressão futura.

| Problema | Teste | Versão corrigida |
|---|---|---|
| OT calculado errado na saída antecipada | `TestCalculoHoraExtra.test_saida_antes_do_limite_nao_gera_hora_extra` | 2.4 |
| Desconto fixo não persistia | `TestDesconto.test_desconto_fixo_usa_valor_exato` | 2.4 |
| `is_legal_holiday` undefined (erro silencioso) | `TestFeriadoEDomingo.*` | 2.4 |
| Falta/Yukyu não descontavam | `TestFaltaEYukyu.*` | 2.4 |
| Feriado corporativo não afetava cálculo | `TestFeriadoCorporativo.*` | 2.7 |
| Adicional fixo mensal (líder) | `TestAdicionalFixoMensal.*` | 2.8 |
| Normalização de horário (HH:MM) | `TestNormalizacaoHorario.*` | 2.4 |
| Ciclos 4x2/5x2/Alternado | `TestCiclos.*`, `TestCiclosNoForecast.*` | 2.5 |
| Abono por dia | `TestAbono.*` | 2.4 |
| Domingo/feriado empilhava noturno+extra por cima do +35% | `TestBugTurnoNoturnoEmFeriado.*` | 2.8 |
| Taxa de extra/noturno/domingo sem adicionais fixos mensais (リーダー手当 etc.) | `TestAcrescimoTaxaPremium.test_com_acrescimo_bate_com_holerites_2026` | 2.9 |
| Arredondamento aplicado ao total final em vez da taxa por hora | `TestAcrescimoTaxaPremium.test_sem_acrescimo_bate_com_holerites_2021_2022` | 2.9 |
| **Grupo A/B/C não afetava o calendário** (deslocamento de turma nunca aplicado) | `TestGrupoABC.*` (validado contra planilha real de escala) | **2.11 (crítico)** |
| **Grupo B/C deslocava a data pessoal digitada pelo usuário** (dia 1 aparecia como folga) | `TestGrupoABC.*` — resolvido definitivamente com `anchor_group` (rastreamento automático, sem switch) | **2.12→2.13 (crítico)** |
| Alternado Mensal não existia (só semanal) | `TestAlternadoMensal.*` — nova função `generate_alternating_monthly_calendar()`, reaproveitando `generate_4x2_calendar()` para o padrão de folga 4×2 | 2.15 |
| Direito a Yukyu não era calculado (usuário controlava manualmente) | `TestYukyu.*` — nova função `calcular_yukyu()`, pesquisada na Lei Trabalhista Japonesa Art. 39/115 antes de implementar | 2.19 |

**Total: 64 testes, cobrindo o motor de cálculo inteiro.**

---

## ⚠️ NÃO cobertos por testes automatizados (requerem teste manual)

Esses são problemas de **interface/UX** que só existem quando o Flet
renderiza de verdade num navegador — `unittest` não consegue simular
isso, pois testa só funções Python puras, sem o Flutter/DOM por trás.

| Problema | Causa raiz | Versão corrigida | Como testar manualmente |
|---|---|---|---|
| Scroll voltava ao topo ao editar campo | `refresh_all()` chamado sem necessidade, reconstruindo a página inteira | 2.4 / 2.6 | Editar campo em Config, observar se a página rola para o topo |
| Histórico perdia registros ao salvar 3+ vezes | Variável local desatualizada (closure) em vez de `state["history"]` | 2.6 | Registrar 3-4 meses seguidos, conferir se todos aparecem |
| **Dados perdidos ao fechar o navegador** | `page.client_storage`/`page.eval_js` descontinuados no Flet 0.85, todo storage falhava silenciosamente | **2.7 (crítico)** | Inserir dado, fechar o navegador completamente, reabrir |
| Botões 4×2/5×2/Alternado causavam scroll ao topo | Mesma causa do item 1, isolada nesses botões específicos | 2.6 | Trocar tipo de ciclo em Config, observar scroll |
| **Dropdown de arredondamento do ponto resetava seleção e voltava ao topo** | `ft.Dropdown` — mesmo padrão de bug já visto no seletor de Desconto (item acima), mas reintroduzido ao criar um Dropdown novo na v2.9 sem replicar o fix de botões | 2.10 | Mudar "Arredondamento do Ponto" em Config, observar se a seleção fixa e se a página rola |
| Dropdown de Grupo de Turno e Turno (Config) tinham o mesmo problema | Mesmo padrão — `refresh_all()` chamado desnecessariamente no `on_change` | 2.11 | Mudar "Grupo de Turno" ou "Turno" em Config |
| Dropdown de Status no modal de ponto (6 opções) | Mesmo padrão — último `ft.Dropdown` restante no app | 2.11 | Abrir um dia no Calendário, trocar o Status |
| Texto cortado ao lado dos switches que escondem seção (Diagnóstico, Taxa de Referência) | `ft.Switch` com `label` embutido não quebra linha em tela estreita | 2.12 | Abrir ⚙️ Config no celular estreito, ver se o texto ao lado do switch aparece completo |
| Botões de Status do modal ficaram só em japonês após virar botão (v2.10) | Conversão de Dropdown→botão manteve os labels originais (japonês), sem repensar pro público brasileiro | 2.12 | Abrir modal de ponto, conferir se os botões têm texto em português como principal |
| Pinch-to-zoom bloqueado no PWA | `maximum-scale=1.0, user-scalable=no` na tag viewport do `index.html` | 2.11 | Abrir o app no celular, tentar dar zoom com dois dedos |
| **Aba Ajuda com fundo branco e texto ilegível** | Paleta de cores clara definida localmente em `build_help_tab()`, com `TEXT_PRIMARY`/`YEN_GOLD` ainda nas cores de tema escuro (quase branco sobre quase branco) | **2.17→2.18 (crítico)** | Abrir aba ❓ Ajuda, checar se o fundo é escuro (igual ao resto do app) e o título é legível |
| Botões "Copiar Link" não funcionavam | `page.set_clipboard()` não confiável nos testes reais — removidos, mantido só texto selecionável | 2.18 | Abrir ❓ Ajuda → Compartilhar, conferir que não há mais botão de copiar, só os links em texto |
| Deploy falhando não é sempre bug de código | GitHub Actions "Deployment failed" / "Multiple artifacts" por deploys simultâneos colidindo — não relacionado ao `main.py` | processo | Antes de investigar código, conferir aba Actions do GitHub (ícone verde ✓) e o Build ID no cabeçalho do app |
| "Apagar Todos os Dados" limpava o storage mas a tela continuava com dados antigos | `refresh_all()` só recarrega `state["settings"]` se o cache não estiver vazio — depois de `remove_storage()` o cache fica `None`, então a condição falhava | 2.21 | Preencher configurações, apagar tudo, conferir se os campos voltam ao padrão SEM precisar fechar e reabrir o app |
| Migração do wizard por etapas (v2.14) precisa ser testada manualmente | Não dá pra testar via `unittest` porque depende de `settings` salvos previamente + renderização real da UI | 2.14 | Simular um `settings` salvo de versão anterior (com `cycle_type` mas sem `cycle_type_confirmed`) e confirmar que as etapas 2/3/4 aparecem direto, sem precisar reclicar no tipo de ciclo |
| Texto da aba Ajuda estourava a largura, precisava de zoom 50% pra ler | Linha monoespaçada de ~60 caracteres no bloco `_example()` de progressão do Yukyu | 2.24 | Abrir ❓ Ajuda no celular sem nenhum zoom manual, conferir se todo o texto cabe na largura da tela |
| Campo "Ajuste Fino do Noturno" cortado em tela de celular | `ft.Row` com 2 campos lado a lado, sem `expand`, na v2.9 | 2.10 | Abrir ⚙️ Config no celular, ligar o switch de taxa de referência, ver se os 2 campos aparecem inteiros |
| Teclado do celular cobria campos no modal | Modal centralizado verticalmente, sem espaço reservado | 2.6 | Abrir modal de Histórico no celular, tocar em campo perto do fim |

---

## 🛠️ Problemas de infraestrutura de teste (categoria nova)

Diferente das duas categorias acima, este é um problema **no próprio
`test_main.py`** — não no `main.py` — que mascarou a cobertura real do
projeto por pelo menos uma versão inteira.

| Problema | Causa raiz | Versão corrigida | Como foi descoberto |
|---|---|---|---|
| 9 testes nunca executavam (`TestFeriadoCorporativo`, `TestAdicionalFixoMensal`, `TestBugTurnoNoturnoEmFeriado`) | `unittest.main()` posicionado no meio do arquivo, antes dessas 3 classes serem definidas — Python executa de cima pra baixo, então elas nunca chegavam a existir quando os testes rodavam | 2.9 | Rodando `python test_main.py` manualmente e comparando a contagem de testes executados (26) com a contagem de classes definidas no arquivo (12) |
| **Suíte inteira parou de rodar (saída vazia, "sucesso" falso)** | Bloco `if __name__ == "__main__":` apagado por engano ao inserir uma classe de teste nova no final do arquivo — dessa vez não mal posicionado, removido de vez | **2.19** | Saída completamente vazia com código de saída 0 — só percebido porque virou hábito conferir a contagem de testes (lição da linha acima) |

**Lição para o processo:** ao adicionar uma nova classe de teste, sempre
confirmar que `unittest.main()` está no **final real do arquivo** — não
basta ver "OK" na saída, é preciso conferir se o número de testes rodados
bate com o esperado.

---

## 🔴 Bugs que passam no `py_compile` mas quebram em runtime (categoria nova)

Diferente de erro de sintaxe (`py_compile` pega) ou erro de cálculo
(`unittest` pega), esses bugs só aparecem quando a função de UI é
**executada de verdade** — algo que nem `py_compile` nem `unittest`
fazem, já que `unittest` só testa o motor de cálculo, não as funções
`build_*_tab()`.

| Problema | Causa raiz | Versão corrigida | Como foi descoberto |
|---|---|---|---|
| **Aba Config não abria** (crash total) | `hidden_advanced_container` (v2.14) referenciava `block_label`/`premium_switch`/etc. antes delas serem definidas na função — `UnboundLocalError` | **2.17 (crítico)** | Stub de teste (ver abaixo) rodando `build_settings_tab()` de verdade |
| **Aba Ajuda não abria** (crash total) | Botões novos (v2.16) usavam `ft.Icons.COPY`/`ft.Icons.PLAY_CIRCLE_OUTLINE`, divergindo do padrão já validado no resto do app (`icon="upload"`, string minúscula) | **2.17 (crítico)** | Mesmo stub, rodando `build_help_tab()` |
| **App inteiro não abria** (`AttributeError: module 'flet.controls.alignment' has no attribute 'center'`) | `ft.alignment.center` usado em `Container`s novos da logo — esse atalho não existe no Flet 0.85.3, só `ft.Alignment(0, 0)` (padrão já usado no resto do código) | **2.43 (crítico)** | Traceback completo no Console do navegador (`main.dart.mjs` [stderr]) após deploy em produção — não pego pelo stub local porque o stub de Flet falso não valida atributos reais do módulo |

**Metodologia criada para pegar isso no futuro:** um módulo `flet` "falso"
(`unittest.mock.MagicMock` respondendo a qualquer atributo/chamada),
permitindo importar `main.py` e chamar `build_*_tab(page, state,
refresh_all)` de verdade — sem precisar do Flet instalado — e capturar
qualquer `NameError`/`UnboundLocalError`/`AttributeError` real que só
aparece em tempo de execução.

**Processo recomendado a partir de agora:** depois de qualquer mudança
em `build_settings_tab()`, `build_help_tab()`, ou qualquer outra função
`build_*_tab()`, rodar esse teste de renderização (não só
`py_compile`) antes de considerar a mudança pronta para entregar.

---

## 📦 Bugs de versionamento de dependência (só aparecem no build de produção, não localmente)

Categoria distinta das anteriores: esses bugs **não existem no ambiente
de desenvolvimento local** (onde o Flet já está instalado numa versão
fixa) — só se manifestam no build de produção do GitHub Pages, porque
o navegador baixa os pacotes Python via `micropip` no momento do
carregamento, seguindo exatamente o que está declarado em
`pyproject.toml`/`requirements.txt`.

| Problema | Causa raiz | Versão corrigida | Como foi descoberto |
|---|---|---|---|
| **App travava numa tela cinza, sem NENHUM erro no console** | `pyproject.toml` tinha `dependencies = ["flet"]` sem versão travada — o build de produção baixava a versão mais recente do Flet disponível no momento, que silenciosamente mudou o comportamento de `page.shared_preferences` (API de storage), travando o `await` de carregamento inicial sem lançar exceção visível | **2.43 (crítico)** | Processo de eliminação: sem erro no Console, sem erro no Network, funcionava igual em aba anônima (não era cache) — só ficou claro ao ler o log linha por linha e notar que parava logo após o aviso de depreciação do `shared_preferences`, sem nenhuma linha depois |
| **Nome do PWA instalado saía "onion_payroll"** em vez de "Onion Payroll" | `[tool.flet] short_name = "..."` no `pyproject.toml` **não é um campo reconhecido** pelo `flet build web` (só existe para o comando `flet publish`, diferente) — `product` funciona normalmente, mas não há equivalente para `short_name` nesse fluxo; o valor errado era gerado automaticamente a partir do nome do projeto | **2.44** | Comparação manual do `manifest.json` gerado em `docs/` com o que estava declarado no `pyproject.toml` — os valores não batiam, apesar de `product` funcionar corretamente |

**Processo recomendado a partir de agora:**
- **Nunca deixar `dependencies` sem versão travada** no `pyproject.toml`
  — sempre `"flet==X.Y.Z"`, confirmando a versão com `pip show flet` no
  ambiente local antes de travar
- Depois de qualquer mudança em `pyproject.toml` (mesmo que pareça não
  afetar o Flet diretamente, como a correção do bug "build_src"),
  **testar o deploy de produção com o Console do navegador aberto**,
  não só rodar `deploy.ps1` e assumir que terminou "limpo" — terminar
  sem erro no terminal PowerShell não garante que o app abre no
  navegador
- Se a tela ficar travada sem erro nenhum no Console: não é
  necessariamente cache. Testar em aba anônima primeiro; se persistir
  mesmo assim, suspeitar de dependência sem versão travada antes de
  suspeitar do próprio código

---

## 📋 Processo recomendado para novos problemas

1. **Se for de cálculo** (números errados, lógica de negócio) →
   adicionar teste em `test_main.py` na classe apropriada
2. **Se for de UX/interface** (scroll, persistência, layout) →
   documentar aqui em "NÃO cobertos", já que não há teste automatizado
   confiável possível sem infraestrutura de browser automation
   (Selenium/Playwright, fora do escopo atual do projeto)
3. **Se for de precisão numérica sutil** (resíduo pequeno e proporcional,
   não aleatório) → suspeitar de regra de arredondamento ou taxa de
   referência antes de assumir "ruído"; validar com pelo menos 2
   holerites reais de contextos diferentes (ex: `jikyuu` diferente, com
   e sem adicional fixo) antes de codificar a correção
4. **Sempre** registrar a correção no `CHANGELOG.md` com a versão
5. **Depois de adicionar testes**, rodar `python test_main.py` e conferir
   se a contagem total de testes bate com o esperado — não confiar só no
   "OK" final (ver categoria "infraestrutura de teste" acima)
6. **Nunca usar `ft.Dropdown` na aba Config** — tem histórico recorrente
   de resetar a seleção e voltar o scroll ao topo (v2.4, v2.6, v2.10).
   Usar sempre o padrão de botões (`ft.FilledButton` com `.update()`
   individual, sem `refresh_all()`), como no seletor de Desconto
7. **Campos lado a lado em `ft.Row`** só se houver certeza de que cabem
   em tela de celular estreita — na dúvida, empilhar em `ft.Column`
8. **Depois de mexer em qualquer `build_*_tab()`**, rodar o teste de
   renderização com o stub de Flet falso (ver categoria "Bugs que passam
   no py_compile mas quebram em runtime" acima) — `py_compile` não pega
   `UnboundLocalError`/ordem de variável errada, só erro de sintaxe
9. **Se um campo precisa atualizar outro widget na mesma tela** (ex:
   Data de Admissão atualizando o resumo de Yukyu), nunca usar
   `refresh_all()` dentro de ⚙️ Config — extrair a lógica de montagem
   do texto/widget pra uma função reutilizável, guardar o widget numa
   variável nomeada, e chamar `.update()` só nele
10. **Resumos que crescem com o tempo de uso do app** (ex: histórico de
    concessões desde a admissão) — mostrar só o que ainda é relevante
    HOJE (ex: concessões ativas), não o histórico completo desde o
    início. Testar sempre com um cenário de "muitos anos de uso" antes
    de considerar pronto — problema só aparece com dados antigos o
    suficiente, não com uma conta nova de teste
11. **Texto com `font_family="monospace"`** (blocos de exemplo/fórmula)
    — manter cada linha em ~28 caracteres ou menos. Fonte monoespaçada
    é mais larga que proporcional por caractere, e não há garantia de
    quebra automática — mais seguro encurtar o conteúdo do que confiar
    no comportamento de wrap do Flet sem poder testar ao vivo
12. **`main.py` tem dois blocos de definição de cor (TOKENS)** — as
    mesmas variáveis (`WORK_COLOR`, `OFF_COLOR`, `HEADER_BG`, etc.) são
    declaradas duas vezes no arquivo; a segunda declaração sempre
    vence, silenciosamente, sem erro. Ao alterar qualquer cor do tema,
    conferir com `grep -n "NOME_DA_VARIAVEL ="` se ela aparece mais de
    uma vez, e editar **todas** as ocorrências — não só a primeira que
    aparecer ao rolar o arquivo
13. **Nem todo campo do `pyproject.toml` é garantidamente lido pelo
    `flet build web`** — alguns existem só para `flet publish` (comando
    diferente). Depois de configurar algo em `[tool.flet]` que afeta o
    PWA (nome, cores, ícones), **conferir o arquivo gerado de verdade**
    (`docs/manifest.json`) em vez de assumir que o campo "pegou" só
    porque o deploy terminou sem erro. Se um campo não for respeitado,
    a solução é colocar um `manifest.json` próprio em `assets/` — o
    Flet usa esse arquivo no lugar de gerar um novo, sobrepondo
    qualquer valor automático

---

## 🔮 Possível melhoria futura (não implementada)

Para cobrir os problemas de UX automaticamente, seria necessário
configurar testes end-to-end com **Playwright** ou **Selenium**
controlando um navegador real apontando para o app rodando localmente.
Isso é significativamente mais complexo de manter que `unittest` puro
e não foi implementado por ora — os testes manuais documentados acima
são o processo atual.
