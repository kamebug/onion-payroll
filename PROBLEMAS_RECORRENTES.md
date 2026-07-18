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
| **Botão "Relatar Problema" não fazia nada ao tocar** (clique morto, sem erro visível na tela) | `page.run_task(page.launch_url, url)` — passar um método do Flet direto pro `run_task` não funciona; o decorator de depreciação que embrulha `launch_url` faz o `inspect.iscoroutinefunction()` interno não reconhecer como coroutine, gerando `TypeError: handler must be a coroutine function` | **2.45** | Traceback completo no Console do navegador — mesma metodologia do item acima (produção, não local) |

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
14. **`page.run_task()` nunca aceita um método do Flet direto**
    (ex: `page.run_task(page.launch_url, url)` quebra com `TypeError:
    handler must be a coroutine function`). Sempre criar uma função
    `async def` própria que faz o `await` internamente, e passar essa
    função pro `run_task` — é o padrão já usado em `_persist`,
    `_remove` e `_do_diag`. Vale pra qualquer método do Flet marcado
    como `@deprecated` (comum a partir da 0.80.0) — o decorator quebra
    a detecção de coroutine que o `run_task` depende
15. **Formspree valida automaticamente qualquer campo chamado
    `email`** como endereço real, mesmo em formulários AJAX/JSON — um
    texto qualquer (ex: placeholder tipo "não informado") é rejeitado
    com 422. Se o campo for opcional, **omitir a chave inteira** do
    JSON quando vazio, nunca mandar um valor placeholder nesse nome
    específico de campo
16. **Referências de arquivo dentro do HTML injetado pelo `deploy.ps1`**
    (banner de instalação, tags `<img>`, etc.) **não são conferidas em
    lugar nenhum automaticamente** — um nome de arquivo digitado errado
    (ex: `apple-touch-icon-192.png`, que nunca existiu; o Flet gera
    `Icon-192.png`) só aparece como ícone genérico quebrado, sem
    nenhum erro, warning, ou aviso no deploy. Depois de qualquer
    mudança em referência de ícone/imagem no `deploy.ps1`, **conferir
    visualmente em produção** (não só que o deploy "terminou sem
    erro") — mesma lição do item #13, mas pra HTML customizado em vez
    de `pyproject.toml`
17. **Testes automatizados validam consistência interna, não
    correção de negócio.** O bug da Média Histórica (porcentagem
    aplicada sobre o bruto previsto, inflando o desconto) passou pelo
    `py_compile` e por todos os 94 testes automatizados sem disparar
    nenhum alerta — os testes só conferiam que a fórmula fazia o que
    ela dizia fazer, não que o resultado batia com a realidade de um
    holerite de verdade. Reforça a regra do item #3: qualquer fórmula
    nova envolvendo dinheiro precisa ser validada contra pelo menos 1
    holerite real antes de confiar nela, mesmo com testes verdes
18. **Valores hardcoded "temporários" sobrevivem mais tempo do que se
    imagina.** O horário de início de hora extra do Alternado
    Semanal/Mensal estava fixo em `"18:35"`/`"06:35"` direto no meio do
    loop de cálculo, sem nenhum campo de configuração correspondente
    na tela — nem gerava erro, nem ficava óbvio, só calculava com um
    valor que ninguém tinha como mudar. Ao adicionar um campo de
    configuração novo, **sempre grep pela variável correspondente no
    motor de cálculo** pra confirmar que o valor configurado
    realmente chega até onde é usado — um campo na tela não garante
    que ele tem efeito nenhum
19. **Mudar um padrão geral do app (não just um recurso opt-in) é uma
    decisão consciente, não um efeito colateral.** A v2.49 tornou
    "Sempre pra Cima" o modo de arredondamento padrão pra TODOS os
    usuários (não só quem ativa o adicional de líder) — decisão
    tomada cientes de que isso muda os valores calculados até pra
    quem nunca mexer em nenhuma configuração nova, e invalida a
    calibração anterior contra holerites reais (que precisou ser
    recalibrada em `test_main.py`). Esse tipo de mudança de padrão
    geral deve sempre ser perguntado explicitamente ("isso muda o
    comportamento de quem não mexer em nada — confirma?"), nunca
    assumido implicitamente só porque parece a opção "mais correta"
20. **Somar valores já arredondados de cada dia ≠ arredondar o total
    do mês uma vez.** Motor de cálculo somava `shisha_gofuuu()` de
    cada dia individual — com "sempre pra cima", isso acumula alguns
    yens a mais que arredondar o total do mês de uma vez só (holerite
    real de fevereiro fechou 33h×¥2.011=¥66.363 exato, mas a soma dia
    a dia dava ¥66.364). Corrigido: acumular só MINUTOS durante o
    loop mensal, aplicar a taxa (constante o mês inteiro) e arredondar
    uma única vez no final. Vale pra qualquer cálculo que soma
    valores monetários já arredondados de itens individuais — sempre
    preferir somar as quantidades brutas e arredondar o total
21. **Premissa de negócio "óbvia" nem sempre é a certa — sempre
    validar contra holerite real, mesmo quando já parece "resolvida".**
    O código zerava `night_pay` em domingo/feriado, com justificativa
    registrada (bug antigo corrigido, validado contra holerite real
    de que não deveria empilhar). Só que a validação antiga conferiu
    a linha de domingo (休日手当) sozinha — não conferiu que 深夜手当
    é uma linha SEPARADA que também deveria somar as horas noturnas
    de domingo. As duas conclusões pareciam contraditórias até os
    números reais (¥45.338 = todos os 18 dias, não só 16) resolverem
    a ambiguidade. Nunca assumir que uma decisão documentada e
    "validada" está necessariamente completa — pode estar certa sobre
    UMA linha e incompleta sobre outra
22. **UI mostrando informação errada porque a lógica de classificação
    roda tarde demais.** `hol_text` no modal de ponto sempre exibia
    "🏭 Feriado da Empresa", mesmo em feriado NACIONAL — o código que
    distinguia nacional/corporativo existia, mas só era calculado
    DEPOIS de `hol_text` já estar montado (pra outra finalidade). Ao
    adicionar lógica de classificação nova, sempre conferir se algo
    ANTERIOR no mesmo bloco já deveria ter usado essa classificação e
    não usou
23. **Dados "óbvios"/hardcoded de calendário merecem verificação
    ativa, não só confiança.** `JP_HOLIDAYS_BUILTIN` tinha 22/09/2025
    marcado como feriado — nunca foi verdade (o feriado "sanduíche"
    naquele padrão só ocorre em 2026). Ao trabalhar com datas de
    calendário/feriados, usar `datetime` pra calcular o dia da semana
    de verdade em vez de assumir de memória, e cruzar com pelo menos
    uma fonte oficial antes de confiar num dado que já estava no
    código
24. **Corrigir a lógica de decisão não garante que a agregação use a
    mesma lógica.** O bug de domingo+feriado corporativo foi corrigido
    na decisão de `shift_type` — mas um bloco de agregação SEPARADO
    (que soma os totais do mês) tinha sua própria condição antiga
    duplicando a mesma regra de prioridade, e não foi atualizado
    junto. Sempre que uma regra de prioridade/decisão existir em mais
    de um lugar do código (decisão + agregação, cálculo + exibição,
    etc.), uma correção precisa varrer TODOS os lugares — `grep` pela
    mesma condição/padrão antes de considerar uma correção completa
25. **`return` antecipado dentro de uma função pode pular
    inicialização que outro código depende.** `calculate_shift_pay`
    tinha 2 `return`s antecipados (Yukyu, shift_type inválido) que
    pulavam o bloco onde `_ot_rate_full`/`_night_rate_increment`/etc.
    eram definidos no resultado — `compute_monthly_forecast` lia essas
    chaves incondicionalmente todo dia do loop, travando com
    `KeyError` em qualquer mês com Yukyu. Ao adicionar chaves num
    dicionário de retorno consumidas por quem chama a função,
    definir ANTES de qualquer `return` antecipado, não só no caminho
    "feliz" principal
26. **Escrever teste automatizado pra um bug já "corrigido" pode
    revelar que a correção estava incompleta.** O teste novo escrito
    especificamente pro cenário domingo+feriado corporativo (item 24)
    falhou na primeira tentativa — o que levou direto à descoberta do
    segundo bug (agregação) que a correção original não tinha coberto.
    Reforça: sempre escrever um teste específico pro cenário exato do
    bug relatado pelo usuário, não confiar só na correção "parecer"
    certa lendo o código
27. **Ao recalibrar testes depois de descontinuar uma feature, cuidado
    com classes duplicadas.** Uma substituição de classe de teste
    (`str_replace`) inseriu a classe nova mas deixou a classe antiga
    (com o mesmo nome) intacta mais abaixo no arquivo — em Python, a
    segunda declaração de uma classe com o mesmo nome sobrescreve a
    primeira silenciosamente, então os testes "novos" nunca rodavam de
    verdade, só os antigos (quebrados). Depois de qualquer substituição
    de classe/função, `grep -c` pelo nome pra confirmar que não sobrou
    duplicata
28. **Corrigir a prioridade errada de um jeito absoluto pode acertar
    um caso e quebrar outro.** A primeira correção do bug domingo+
    feriado corporativo deu prioridade ABSOLUTA ao domingo sobre
    qualquer feriado — resolvia o caso relatado originalmente, mas
    quebrava o caso oposto (feriado corporativo real, fábrica fechada,
    caindo num domingo escalado) só descoberto quando o usuário testou
    esse cenário específico depois do deploy. A prioridade certa
    dependia de UMA CONDIÇÃO A MAIS (tem horário registrado ou não),
    não só de qual sinal "vence". Ao corrigir uma prioridade entre
    dois sinais que podem coexistir no mesmo dia, sempre considerar
    os DOIS casos práticos (com e sem ação manual do usuário) antes de
    declarar a correção completa — não só o caso que gerou o relatório
    original
29. **`str_replace` pode engolir uma função inteira sem gerar erro de
    sintaxe.** Ao inserir `fetch_feriados_empresa` logo antes de
    `fetch_updated_holidays`, a linha `async def fetch_updated_
    holidays()...` foi perdida — o corpo dela ficou com a mesma
    indentação da função anterior, viraram código morto dentro dela,
    sem nenhum erro detectável no `py_compile` (sintaticamente 100%
    válido, só semanticamente quebrado). Só apareceu como `NameError`
    no boot do app de verdade. **Lição prática:** depois de qualquer
    edição perto de uma definição de função (`async def`/`def`),
    sempre `grep -n "^def nome_da_funcao\|^async def nome_da_funcao"`
    pra confirmar que a linha de definição ainda existe como tal —
    `py_compile` sozinho não garante que uma função continua sendo
    uma função
30. **Cor de texto "global" do app pode ficar ilegível em um fundo
    "local" diferente.** O nome do feriado no modal usava `TEXT_
    PRIMARY`/`TEXT_SECONDARY` (cores claras, calibradas pro tema
    escuro predominante do app) dentro de uma caixa com fundo CLARO
    (rosa) — texto quase invisível por baixo contraste, mas sem
    nenhum erro técnico, só um problema visual que só aparece
    olhando a tela de verdade. Sempre que um elemento tiver um fundo
    diferente do padrão do app (claro em vez de escuro, ou vice-
    versa), definir cores de texto ESPECÍFICAS pra esse fundo, nunca
    reaproveitar as constantes globais sem verificar o contraste
31. **O mesmo bug de "decisão vs. agregação divergindo" apareceu TRÊS
    vezes seguidas na mesma área de código.** Primeiro no bug original
    de domingo+feriado corporativo (decisão certa, agregação errada).
    Depois na inversão de prioridade (feriado sem registro deveria
    vencer, não domingo). Agora de novo, separando feriado nacional
    de corporativo (decisão corrigida pra usar `is_corp_hol`, mas a
    agregação continuou usando `is_holiday` mesclado numa condição
    PRÓPRIA, sem eu ter atualizado junto). Padrão claro: sempre que
    uma variável de classificação (`is_holiday`, `shift_type`, etc.)
    tiver mais de um lugar no código decidindo algo com base nela,
    ESSES LUGARES VÃO DIVERGIR eventualmente — a correção definitiva
    não é "lembrar de atualizar os dois toda vez", é ELIMINAR A
    DUPLICATA: fazer a agregação ler o `shift_type` já decidido
    (fonte única), em vez de recalcular uma condição parecida-mas-
    diferente a partir das variáveis brutas (`is_holiday`, `status`,
    etc.). Antes de considerar uma correção de prioridade/decisão
    completa, `grep` por QUALQUER outro lugar que leia as MESMAS
    variáveis brutas (não só a variável derivada tipo `shift_type`) e
    avaliar se deveria estar lendo o resultado já decidido em vez de
    recalcular
32. **Switch que salva uma configuração mas nenhum código lê de
    volta é um "switch fantasma".** "Ativar Bloqueio PIN / Biométrico"
    existia desde sempre em Config, com `on_change` salvando
    `pin_enabled` no settings — só que nenhum outro lugar do app
    JAMAIS verificava esse valor. O switch "funcionava" visualmente
    (ligava/desligava, persistia entre sessões), mas não tinha
    nenhuma funcionalidade real por trás — só foi descoberto quando o
    usuário tentou usar e notou que "não fez nada". Lição: ao herdar
    ou revisar um campo de configuração já existente, sempre `grep`
    pelo NOME da chave (`pin_enabled`, nesse caso) em todo o arquivo —
    se o único resultado for "onde é salvo" e nunca "onde é lido pra
    decidir alguma coisa", é sinal de uma feature pela metade
33. **Pesquisar compatibilidade de plataforma ANTES de prometer uma
    funcionalidade, não depois de começar a implementar.** Ao ser
    perguntado sobre biometria, pesquisei antes de responder e achei
    que o pacote de biometria do Flet (`flet_auth`) é pra apps NATIVOS
    compilados (`flet build apk`/`ipa`) — inútil pro Onion Payroll,
    que é 100% web (`flet build web`, roda via Pyodide no navegador).
    Web apps só têm acesso a biometria através da API WebAuthn do
    próprio navegador, que exigiria JavaScript customizado fora do
    Flet, com risco real de não funcionar de forma confiável. Evitar
    prometer/começar a implementar algo assim sem antes confirmar que
    a arquitetura de deploy do projeto (web vs. nativo) realmente
    suporta a tecnologia envolvida

---

## 🔮 Possível melhoria futura (não implementada)

Para cobrir os problemas de UX automaticamente, seria necessário
configurar testes end-to-end com **Playwright** ou **Selenium**
controlando um navegador real apontando para o app rodando localmente.
Isso é significativamente mais complexo de manter que `unittest` puro
e não foi implementado por ora — os testes manuais documentados acima
são o processo atual.
