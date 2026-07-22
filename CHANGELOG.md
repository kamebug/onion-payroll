# Changelog — Onion Payroll

> **Nota de versionamento (a partir de 2026-07-18, pós v2.55.0):** o
> projeto passou a seguir SemVer (MAJOR.MINOR.PATCH) rigorosamente:
> **PATCH** sobe quando a versão é só correção de bug, sem nada novo;
> **MINOR** sobe quando tem pelo menos uma funcionalidade nova (mesmo
> que também tenha bugfixes junto); **MAJOR** fica reservado pra uma
> mudança que quebre compatibilidade com dados/uso já existente (não
> aconteceu até agora). Versões anteriores a essa data bumpavam MINOR
> pra qualquer mudança, inclusive bugfix puro — não retroagidas, só
> documentado aqui pra explicar a diferença de critério.

## [2.58.1] — 2026-07-21 — TEXTOS DO 休日出勤 MAIS CLAROS PRO PÚBLICO PT-BR (PATCH)

### 🔧 Alterado

- Corrigido o botão de status "休日出勤" que estava com kanji cru como
  rótulo principal — quebrava o padrão de todos os outros status
  (rótulo PT principal + kanji secundário, ex: "Falta" / 欠勤). Agora
  é "Folga Trabalhada" / 休日出勤, igual ao resto
- Adicionado gloss/romaji em todo texto visível ao usuário onde
  休日出勤, 所定休日 ou 法定休日 apareciam sem tradução nem romaji:
  texto de ajuda em ⚙️ Config, cabeçalho da seção, aba Ajuda (regra,
  parágrafo de aviso, item de "Trabalho em Folga/Feriado"), e legenda
  de cores do calendário
- Nenhuma mudança de lógica — só texto. 135 testes automatizados
  continuam passando sem alteração

---

## [2.58.0] — 2026-07-21 — DOMINGO DE FOLGA TAMBÉM FICA VERMELHO

### 🟢 Adicionado

- **Domingo de folga (não trabalhado) agora fica com fundo vermelho**
  (`C_RED`, `#FF5252`) no calendário — antes só domingo TRABALHADO
  tinha destaque visual próprio (vermelho escuro); domingo de folga
  ficava com o mesmo azul de qualquer outra folga do ciclo, com a
  distinção escondida só na cor do número, fácil de passar despercebido
- Dois tons de vermelho agora distinguem os dois casos: `#FF5252`
  (vermelho vivo) para domingo de folga, `#C62828`/`CAL_SUNDAY_WORK`
  (vermelho escuro) para domingo trabalhado
- Legenda de cores (aba Ajuda) atualizada com a nova entrada

### 🐛 Corrigido

- Código morto removido no cálculo da cor do número: um `elif is_sunday:`
  no fim da cadeia tinha DUAS atribuições seguidas pra `num_color`
  (`= C_RED` imediatamente sobrescrita por `= C_BLUE`), então a
  primeira nunca tinha efeito — e na prática esse branch nem era mais
  alcançável (domingo só pode ter `cycle_st` "work" ou "off", ambos já
  tratados antes dele). Removido; o `else` final (`CAL_TEXT_WORK`) já
  cobre corretamente os casos restantes

---

## [2.57.0] — 2026-07-21 — COR PRÓPRIA PRO 休日出勤 NO CALENDÁRIO

### 🟢 Adicionado

- **休日出勤 (Kyūjitsu Shukkin) ganha cor própria no calendário** —
  azul claro (`#29B6F6`, `CAL_KYUJITSU`), com indicador "休" no canto.
  Antes caía no mesmo teal genérico de "horário customizado" (mesma
  cor de Saída Antecipada ou qualquer dia normal com horário editado
  manualmente), sem nenhuma distinção visual — só perceptível abrindo
  o dia no modal e olhando o status selecionado
- Branch de prioridade `status == "holiday"` adicionado ANTES do
  catch-all de `has_time` na decisão de cor da célula — necessário
  porque todo dia de 休日出勤 tem horário preenchido, então cairia
  sempre no catch-all genérico se não tivesse prioridade própria
- Legenda de cores (aba Ajuda) atualizada com a nova entrada

### 📝 Nota

- Status "Domingo 1,35x" (`legal`, explícito) ainda cai no mesmo teal
  genérico — não tem cor própria, mesma situação que 休日出勤 tinha
  antes desta versão. Não alterado aqui por não ter sido pedido; considerar
  se faz sentido dar uma cor própria também numa próxima sessão

---

## [2.56.0] — 2026-07-21 — TAXA CONFIGURÁVEL DE 休日出勤 (KYŪJITSU SHUKKIN)

### 🟢 Adicionado

- **Taxa configurável de 休日出勤** — nova opção em ⚙️ Config → "Taxa
  de 休日出勤 (Kyūjitsu Shukkin)", com 3 modos: **1,35x integral**
  (padrão, preserva o comportamento anterior a esta versão),
  **1,25x integral**, e **Dia normal** (sem taxa de feriado nenhuma —
  calcula como um dia comum de trabalho, 基本給 + 残業 só acima do
  limiar configurado)
- **Domingo (法定休日) continua SEMPRE 1,35x fixo** — folga legalmente
  obrigatória pela lei japonesa, não é escolha da empresa, nunca lê a
  nova configuração. Só 休日出勤 (所定休日 — folga que a empresa concede
  além do mínimo legal, ex: sábado de folga trabalhado, feriado
  corporativo marcado manualmente) usa a taxa configurável
- `calculate_shift_pay()` ganhou os parâmetros `holiday_kind`
  ("legal"|"kyujitsu") e `kyujitsu_rate_mode` ("1.35"|"1.25"|"normal");
  `compute_monthly_forecast()` ganhou `kyujitsu_rate_mode`, propagado
  a partir de ⚙️ Config
- Modo "Dia normal" é uma ramificação de cálculo própria (não só troca
  o multiplicador) — desvia pro mesmo caminho de um dia comum de
  trabalho, inclusive pro 延長 (que passa a somar em hora extra 1,25x
  em vez de dentro das horas de feriado)
- 12 novos testes automatizados cobrindo os 3 modos, isolamento entre
  domingo e 休日出勤, e um cenário de mês misto (domingo + 休日出勤 juntos)

### 🐛 Corrigido (preventivo — achado durante esta implementação)

- **Risco real de "decisão vs. agregação divergindo" pela 4ª vez**
  (mesmo padrão do item #31 do PROBLEMAS_RECORRENTES.md): a agregação
  mensal usava uma ÚNICA variável `_rate_holiday`, sobrescrita a cada
  dia iterado no loop, compartilhada entre domingo e 休日出勤. Isso
  nunca causou bug até agora porque as duas categorias sempre tiveram
  a mesma taxa (0,35 fixo). Com 休日出勤 podendo ter taxa DIFERENTE de
  domingo, um mês com os dois tipos coexistindo faria `total_holiday`
  ou `total_legal` usar a taxa do último dia iterado, não a taxa certa
  de cada categoria — corrigido separando em `_rate_legal` e
  `_rate_kyujitsu`, cada uma capturada só dentro do branch
  correspondente. Coberto pelo teste
  `test_mes_misto_domingo_e_kyujitsu_nao_diverge`

### 📝 Nota

- Status "Feriado 1,35x" → "休日出勤 Kyūjitsu Shukkin" (v2.55.1) estava
  registrado como concluído no handoff da sessão anterior, mas não
  estava presente no arquivo — aplicado nesta sessão como parte da
  v2.56.0 (ver entrada [2.55.1] abaixo para o que teria sido o
  changelog isolado dessa mudança)

---

## [2.55.1] — 2026-07-18 — RENOMEAÇÃO DE STATUS (PATCH)

### 🔧 Alterado

- Status "Feriado 1,35x" (chave `holiday`) renomeado para "休日出勤
  Kyūjitsu Shukkin" — nome mais preciso, já que a taxa deixou de ser
  fixa em 1,35x a partir da v2.56.0

---

## [2.55.0] — 2026-07-18 — BLOQUEIO POR PIN + FIX DE COR DA STATUS BAR

### 🟢 Adicionado — bloqueio por PIN de verdade

O switch "Ativar Bloqueio PIN / Biométrico" existia desde sempre em
⚙️ Config → Segurança, mas nunca teve nenhuma funcionalidade real por
trás — só salvava um valor, sem nenhuma tela de criar PIN, nenhuma
verificação, nenhum bloqueio de fato. Implementado do zero:

- **Criação do PIN** — 4 dígitos, digitado duas vezes pra confirmar
- **Método de recuperação escolhido na criação** — "Código de
  Recuperação" (8 dígitos, mostrado uma única vez, recupera sem
  perder dados) ou "Resetar Tudo se Esquecer" (mais simples, mas
  exige apagar tudo se esquecer)
- **Tela de bloqueio no boot** — pede o PIN antes de mostrar qualquer
  conteúdo do app, com limite de 5 tentativas (trava o campo depois,
  direciona pro link "Esqueci o PIN")
- **"Esqueci o PIN"** sempre acessível na tela de bloqueio — com
  código de recuperação, digita o código e entra sem perder dados;
  o botão "Resetar Tudo" fica visível de imediato mesmo nesse fluxo
  (não escondido atrás de uma tentativa falha), pra quem esqueceu o
  código também não precisar tentar e falhar antes de encontrar a
  saída
- **Desativar exige o PIN atual** — evita que qualquer pessoa com
  acesso ao app desligue a proteção sem saber o PIN
- **Armazenamento seguro** — PIN e código de recuperação nunca ficam
  em texto puro, só hash SHA-256 com salt aleatório por instalação
- Rótulo do switch corrigido para "Ativar Bloqueio por PIN" (sem
  mencionar biometria — investigado e não é viável pra esse app, que
  roda como web app via `flet build web`/Pyodide, não como app nativo
  compilado; pacotes de biometria do Flet como `flet_auth` só
  funcionam em builds nativos)
- Documentado na aba Ajuda, seção "🔒 Bloqueio por PIN" (não existia
  nenhuma menção a essa funcionalidade no manual antes)

### 🔴 Corrigido — cor da status bar/barra de endereço aparecia azul

O `assets/manifest.json` já tinha `theme_color: "#00C2A8"` configurado
corretamente, mas só valia quando o app estava instalado (modo
standalone) — numa aba normal do navegador, o Flet/Flutter usava sua
própria cor azul padrão, porque faltava a tag
`<meta name="theme-color">` no HTML. Adicionada a injeção dessa tag
no `deploy.ps1`, removendo antes qualquer tag equivalente que o Flet
já tenha gerado sozinho no build (evita duplicata/conflito). Testado
e confirmado correto no app instalado; numa aba de navegador comum,
alguns navegadores (principalmente iOS Safari) simplesmente não
suportam essa tag fora do modo instalado — limitação da plataforma,
não do app.

### 🟢 Corrigido — contagem de testes desatualizada no README

Mencionava 119 testes; o arquivo já tinha 123 desde a rodada anterior
(bug do feriado nacional), só não tinha sido atualizado no README
naquela hora.

---

## [2.54.0] — 2026-07-18 — CRÍTICO: FERIADO NACIONAL DESCONTAVA DIAS TRABALHADOS

### 🔴 Corrigido — CRÍTICO: feriado nacional tratado como "fábrica fechada"

Confirmado com holerite real de abril/2026: um dia normal de trabalho
escalado (sem nenhuma marcação manual) que também calhava de ser
feriado nacional (29/04 é 昭和の日) estava sendo descontado do total
de dias trabalhados do mês — 19 dias esperados, só 16 contados.

**Causa raiz:** o código tratava feriado NACIONAL e feriado
CORPORATIVO como a mesma coisa (`is_holiday`, uma variável só,
mesclando as duas listas). A regra "sem registro manual = não
trabalhou" foi pensada especificamente pro cenário de feriado
CORPORATIVO (decisão da empresa de fechar a fábrica) — mas feriado
nacional sozinho não implica isso. Muitas fábricas (a do usuário,
inclusive) funcionam normalmente em feriados nacionais, só fecham
quando o feriado corporativo é explicitamente marcado.

**Corrigido em duas partes, ao longo do dia:**
1. `compute_monthly_forecast` ganhou um parâmetro separado,
   `corp_holiday_days`, distinto do `holiday_days` mesclado — a
   decisão de `shift_type` passou a usar `is_corp_hol`
   especificamente. Feriado nacional sozinho virou puramente
   informativo (bandeira 🎌 + borda vermelha no calendário), sem
   nenhum efeito no cálculo.
2. **Reaberto e corrigido de novo horas depois:** um bloco de
   AGREGAÇÃO separado (que soma os totais do mês por categoria) ainda
   usava o `is_holiday` mesclado numa condição própria
   (`status == "holiday" or is_holiday`), fazendo o dia cair de volta
   na categoria "feriado trabalhado" mesmo com a decisão de
   `shift_type` já corrigida. **Terceira vez que esse padrão exato de
   bug aparece nessa mesma área** (decisão vs. agregação divergindo)
   — corrigido de vez usando `shift_type` diretamente na agregação,
   eliminando a duplicata de lógica que permitia essa divergência.

**Também corrigido:** status "Saída Antecipada" (early) sem os campos
de horário explicitamente preenchidos agora também conta como
"trabalhou apesar do feriado corporativo", igual `has_time` — e o
preview do modal de ponto foi alinhado com a mesma distinção
nacional/corporativo, pra não mostrar texto incoerente com o que a
aba Holerite realmente calcula.

### 🟢 Testes — 4 novos, 3 corrigidos, 123 no total

Testes antigos que usavam `holiday_days` sozinho pra representar
feriado corporativo foram corrigidos pra passar `corp_holiday_days`
explicitamente. Nova classe `TestFeriadoNacionalNaoAfetaCalculo` trava
especificamente que feriado nacional sozinho não muda nada no
cálculo, mesmo caindo num domingo — e um teste dedicado trava o bug
de agregação da segunda rodada, pra nunca mais divergir da decisão.

---

## [2.53.0] — 2026-07-17 — CRÍTICO: APP NÃO ABRIA (NameError) + BUSCA AUTOMÁTICA DE FERIADOS DA EMPRESA

### 🔴 Corrigido — CRÍTICO: app travava no boot com NameError

`fetch_updated_holidays()` parou de existir como função chamável — numa
edição anterior (ao adicionar `fetch_feriados_empresa`), a linha
`async def fetch_updated_holidays()...` foi perdida. O corpo da função
ficou com a mesma indentação da função anterior, sem nenhum erro de
sintaxe detectável (`py_compile` passava normalmente) — só virou
código morto, nunca executado, dentro da função vizinha. Resultado:
`NameError: name 'fetch_updated_holidays' is not defined` no boot,
app inteiro travando com tela de fundo, sem carregar nada. Corrigido,
restaurando a função como definição própria e independente.

### 🟢 Adicionado — busca automática de feriados corporativos

Novo botão **"🔄 Buscar Feriados da Empresa"** na aba 🏭 Feriados —
busca `feriados-empresa.csv` (publicado manualmente pelo mantenedor
na raiz do repositório) em tempo de execução via `pyfetch()`, mesmo
padrão dos feriados nacionais. Mensagem de status mostra quantos dias
novos foram importados, ou avisa se não conseguiu buscar (offline,
arquivo ainda não publicado). Dias vindos do CSV continuam editáveis
normalmente — tocar num dia desmarca, e uma busca futura não
sobrescreve edição manual já feita (só adiciona dias novos).

### 🔴 Corrigido — texto do feriado no modal quase invisível

Romaji e nome em português do feriado nacional usavam cores claras
(`TEXT_PRIMARY`/`TEXT_SECONDARY`, feitas pro tema escuro do resto do
app) sobre o fundo claro (rosa) da caixa de feriado — texto quase
ilegível. Trocado por tons escuros avermelhados, com contraste
correto contra esse fundo específico.

### 🔴 Corrigido — feriado nacional confundindo com outras cores

Feriado nacional sozinho estava preenchendo a célula inteira de
vermelho, confundindo com falta/folga/yukyu. Ajustado em duas rodadas
até o resultado final: fundo da célula sempre segue a categoria real
do dia (trabalho/folga/falta/yukyu/feriado corporativo), com borda
vermelha SEMPRE presente quando for feriado nacional (somando, nunca
substituindo). Bandeira 🎌 empilha embaixo de outro indicador (🏭,
欠, 有, ↓, ●) quando os dois aparecem no mesmo dia, em vez de ficar
apertada ao lado.

### 🟢 Corrigido — campo de Desconto Fixo ficava visível sem necessidade

Campo "Valor de Desconto Fixo" continuava aparecendo preenchido
mesmo com "Média Histórica" selecionado, dando a impressão errada de
estar em uso (o cálculo já ignorava certo, só a tela confundia).
Agora esconde/mostra conforme o modo ativo. Removido também um
`print` de depuração esquecido no código.

### 🟢 Padronizado — 時給 (Jikyuu) com kanji + romaji + português

Campos e textos relacionados a 時給 em ⚙️ Config, 📋 Histórico e
❓ Ajuda agora seguem "時給 Jikyuu — Valor por Hora" consistentemente.
Levantamento completo dos demais termos japoneses do app registrado
em `PROBLEMAS_RECORRENTES.md` — padrão definido pra aplicações
futuras é kanji + português (sem romaji), com exceção do 時給 que já
foi implementado com romaji e fica como está.

---

## [2.52.0] — 2026-07-16 — MUDANÇA DE 時給/DESCONTO REAL NO HISTÓRICO + FIX DE PRIORIDADE DOMINGO/FERIADO

### 🔴 Corrigido — CRÍTICO: prioridade domingo vs feriado corporativo estava invertida

A v2.51.0 corrigiu o bug de domingo+feriado corporativo dando prioridade
**absoluta** ao domingo — mas isso estava errado na direção oposta.
Confirmado com caso real: um domingo TAMBÉM marcado como feriado
corporativo (fábrica fechada) deve continuar **não contando** como
trabalhado, mesmo estando escalado — feriado sem horário registrado
sempre vence, mesmo em domingo. Só volta a contar como domingo
trabalhado se tiver horário registrado (trabalhou mesmo com a fábrica
fechada) ou se não houver feriado nenhum marcado nesse dia específico.
Teste automatizado correspondente reescrito para validar a direção
certa.

### 🟢 Adicionado — Mudança de 時給 (aumento de salário) sem afetar meses passados

Novo campo **"時給 a partir deste mês"** no registro de Histórico
(opcional). O 時給 configurado em ⚙️ Config valia sempre, inclusive
retroativamente para meses passados sem registro — um aumento de
salário mudava a previsão de meses ANTES do aumento também. Agora,
registrando o mês em que o aumento começou, a previsão de qualquer mês
sem registro passa a usar automaticamente o 時給 vigente na época (o
marco mais recente igual ou anterior ao mês sendo visto). Funciona com
múltiplos aumentos ao longo do tempo. Documentado na aba Ajuda e
direto abaixo do campo 時給 em Config.

### 🟢 Adicionado — Desconto real substitui a previsão em meses já registrados

Ao registrar um holerite real no Histórico, o mês correspondente na
aba Holerite deixa de usar a previsão de desconto (Média Histórica ou
Fixo) e passa a mostrar o valor REAL registrado — já é um dado
conhecido, não precisa mais estimar. A nota abaixo do valor muda para
"📋 Registro real". Meses sem registro continuam usando a previsão
normalmente.

### 🟢 Adicionado — preenchimento automático no campo de mês do Histórico

Campo "Mês 月 (AAAA-MM)" ganha o mesmo preenchimento automático
(`on_blur`) já usado nos campos de hora/data — aceita `202602`,
`2026/2`, `2026.02`, `2026-2`, todos convertidos para `2026-02`.

### 🛠️ Refatorado — funções de busca extraídas para o nível do módulo

`jikyuu_vigente_para_mes()` e `desconto_real_para_mes()` eram funções
locais dentro da tela do Holerite — extraídas para o nível do módulo,
tornando-as testáveis isoladamente sem precisar montar a UI inteira.

### 🟢 Testes — 17 novos, 119 no total

Cobrindo `jikyuu_vigente_para_mes` (7 testes: sem histórico, sem
marco, antes/no/entre/depois de marcos, marcos fora de ordem),
`desconto_real_para_mes` (4 testes) e `normalize_yyyymm` (6 testes).

---

## [2.51.0] — 2026-07-16 — CRÍTICO: DOMINGO+FERIADO CORPORATIVO, YUKYU TRAVANDO, 延長 EM DOMINGO + RECALIBRAÇÃO COMPLETA DOS TESTES

### 🔴 Corrigido — CRÍTICO: domingo marcado como feriado corporativo virava dia normal

Confirmado com holerite real de maio/2026 (dia 3, domingo E 憲法記念日
E feriado corporativo ao mesmo tempo): Salário Base e Hora Extra
saíam inflados, Domingo saía reduzido — o dia caía no cálculo de "dia
normal de trabalho" em vez de "domingo trabalhado".

**Causa raiz, em duas partes:**
1. A lógica de decisão de `shift_type` tratava domingo/feriado/escala
   como uma cadeia frágil de prioridades (`elif`), sem garantia de que
   um domingo TAMBÉM marcado como feriado seguisse pelo caminho certo.
2. Mesmo depois de corrigir a decisão de `shift_type` (separando
   escala/tipo de dia/status como sinais independentes), um bloco de
   **agregação separado** — que soma os minutos/valores de cada
   categoria pro total do mês — ainda usava a condição antiga
   (`is_sunday and not is_holiday`), fazendo o dia cair na categoria
   errada mesmo com `shift_type` já correto. Bug real pego só depois
   de escrever um teste automatizado específico pra esse cenário.

**Corrigido nos dois lugares.** Domingo agora tem prioridade
consistente sobre feriado corporativo/nacional tanto na decisão do
cálculo quanto na agregação mensal — feriado é só uma informação
adicional, nunca sobrepõe a escala nem o domingo.

### 🔴 Corrigido — CRÍTICO: mês com Yukyu travava o Holerite (KeyError)

Qualquer dia marcado como Yukyu fazia `compute_monthly_forecast`
travar com `KeyError: '_ot_rate_full'`. Causa: as taxas expostas no
resultado de `calculate_shift_pay` (usadas pelo cálculo mensal com
arredondamento único) só eram definidas depois de um `return`
antecipado no caminho do Yukyu — dias de Yukyu nunca chegavam lá.

**Corrigido:** as taxas agora são calculadas logo no início da função,
antes de qualquer `return` antecipado (Yukyu, Falta, `shift_type`
inválido, etc.) — garantindo que todo caminho de saída tenha essas
chaves preenchidas.

### 🔴 Corrigido — 延長 (minutos extras) em domingo/feriado não entrava no cálculo

Campo calculava o valor certo dentro de `calculate_shift_pay`, mas
jogava em `overtime_pay`/`overtime_minutes` (taxa de 1,25x) — que o
cálculo mensal **nunca lê** para dias de domingo/feriado (só
`holiday_pay`/`night_pay` são acumulados nesse caso). O minuto extra
era calculado e descartado em silêncio. Corrigido: 延長 em domingo
entra nas horas de domingo, à taxa de 1,35x.

### 🟢 Recalibrado — `test_main.py` completo para v2.50/v2.51

- Removida a classe inteira que testava a Taxa de Referência
  descontinuada (`TestAcrescimoTaxaPremium`), substituída por
  `TestAcrescimoLiderModoArredondamento`, testando o sistema novo
  (Adicional de Líder + Modo de Arredondamento)
- 3 testes de domingo/noturno atualizados — noturno não é mais zerado
  em domingo, é linha separada
- 4 testes novos travando os bugs críticos desta versão: 延長 em
  domingo, domingo+feriado corporativo (o bug de agregação acima), e
  Yukyu não travar mais com KeyError
- **101 testes, todos passando** (era 94 antes desta rodada)

---

## [2.50.0] — 2026-07-15 — FERIADOS AUTOMÁTICOS + FIXES CRÍTICOS DE NOTURNO/ARREDONDAMENTO/延長

### 🔴 Corrigido — CRÍTICO: 延長 (minutos extras) nunca entrava no Holerite

Campo salvava o valor e mostrava prévia bonita no modal, mas a prévia
usava uma fórmula duplicada e isolada — nunca chegava no motor de
cálculo mensal (`compute_monthly_forecast`). Agora `extra_minutes` é
parâmetro de verdade em `calculate_shift_pay`, somado à Hora Extra
respeitando Modo de Arredondamento e Adicional de Líder. Preview do
modal simplificado para chamar a função real, eliminando a duplicata.

### 🔴 Corrigido — CRÍTICO: adicional noturno de domingo/feriado zerado

`night_pay` era zerado sempre que o dia era domingo/feriado, partindo
da premissa de que o valor já estava embutido no 1,35x. Holerite real
mostrou o contrário: 深夜手当 é linha **separada e independente**,
somando as horas noturnas de **todos** os dias (incluindo domingo),
calculadas à taxa noturna normal — só a linha do domingo em si
(休日手当) não deve misturar noturno. Corrigido, com `total_legal`/
`total_holiday` ajustados para não duplicar o valor.

### 🔴 Corrigido — CRÍTICO: resíduo de arredondamento acumulado (mês inteiro)

Somar valores já arredondados de cada dia (ex: 20 dias de Hora Extra,
cada um arredondado "pra cima" individualmente) acumula alguns yens a
mais que arredondar o total do mês de uma vez — exatamente como o
holerite real calcula (33h × ¥2.011/h = ¥66.363 exato, não a soma de
vários dias). Motor de cálculo reestruturado: acumula só **minutos**
durante o loop mensal, aplica a taxa (constante o mês inteiro) e
arredonda **uma única vez** no final, para Base, Hora Extra, Noturno,
Domingo, Feriado e Yukyu.

### 🟢 Adicionado — feriados nacionais se atualizam sozinhos

Novo scraper (`scraper/scrape_holidays.py`) busca o CSV oficial do
Gabinete do Governo japonês uma vez por ano (GitHub Action, 10 de
janeiro), gera `holidays.json`. O app busca esse arquivo em tempo de
execução via `pyodide.http.pyfetch()` (não `httpx` — tem bug conhecido
dentro do Pyodide, issues #4926/#4840 do próprio Flet), com timeout de
5s e fallback automático pro `JP_HOLIDAYS_BUILTIN` fixo se falhar —
nunca trava o boot, nunca quebra o "100% offline".

### 🟢 Adicionado — moldura vermelha + nome do feriado nacional no modal

Feriados nacionais ganham borda vermelha de 2px na célula do
calendário (além do preenchimento), com prioridade até sobre o
destaque de "hoje". Modal de ponto mostra o nome completo em
japonês/romaji/português (`JP_HOLIDAY_NAMES_BUILTIN`, 39 feriados de
2025-2026, datas móveis calculadas e verificadas, não digitadas de
memória).

### 🔴 Corrigido — hol_text sempre mostrava "Feriado da Empresa"

Mesmo quando o dia era feriado **nacional**, o texto no modal mostrava
"🏭 Feriado da Empresa" — a distinção nacional/corporativo só era
calculada depois, para outra finalidade. Corrigido junto com a
funcionalidade acima.

### 🔴 Corrigido — dado incorreto: 22/09/2025 não é feriado

`JP_HOLIDAYS_BUILTIN` tinha 22/09/2025 marcado como feriado nacional.
Verificado com cálculo exato de dia da semana + fontes oficiais: o
feriado "sanduíche" (国民の休日) entre 敬老の日 e 秋分の日 só
acontece em 2026, não em 2025 (intervalo de 8 dias entre os dois
feriados naquele ano, não 1). Removido.

### 🟢 Adicionado — campo Abono Mensal, separado do Adicional de Líder

Novo campo "Abono Mensal — separado (¥)" em ⚙️ Config — soma
automaticamente no bruto todo mês, igual ao Adicional Fixo Mensal, mas
**nunca** entra no cálculo de arredondamento de Extra/Noturno/Domingo,
mesmo com essa regra ativada. Para qualquer abono fixo que não deva
afetar a taxa.

### 🟢 Simplificado — importação CSV de feriados

Removida a opção de tag `jp` (feriados nacionais) do campo de
importação — feriados nacionais agora se atualizam sozinhos, não
precisam mais de importação manual. Campo continua funcionando só para
feriados corporativos (textos e exemplos atualizados no modal e na
aba Ajuda).

### 🟢 Corrigido — textos desatualizados na aba Ajuda e no modal de ponto

- "Feriados nacionais de 2025-2026 já vêm embutidos" → texto sem menção
  a anos fixos, mencionando a atualização automática
- Seção antiga "Arredondamento da Taxa por Hora (sempre ativo)" —
  duplicada e desatualizada (dizia "não é configurável", já não é
  verdade) — removida, exemplo numérico atualizado migrado pra dentro
  da seção nova "Arredondamento de Salário"
- Switch "有休 em Feriado (+8h)" → "有休 em Feriado" (jornada usada é
  a configurada, não mais 8h fixo)
- Texto "Trabalho Normal" acima dos campos Entrada/Saída → dica sobre
  saída antecipada, mais útil

---

## [2.49.0] — 2026-07-15 — REFORMULAÇÃO DO ARREDONDAMENTO DE SALÁRIO

### 🔴 Alterado — CRÍTICO: Taxa de Referência descontinuada, substituída por sistema novo

**Motivo:** RH real confirmou que o cálculo de hora extra/noturno/domingo,
para empresas com adicional fixo mensal (ex: リーダー手当), usa arredondamento
**separado** por parcela — jikyuu e o acréscimo do adicional são
arredondados individualmente (o acréscimo sempre pra cima), depois
somados — não uma taxa única arredondada de uma vez só, como o app
fazia até aqui.

**Exemplo real (confirmado por RH):** jikyuu=¥1.590, adicional
líder=¥3.000/mês, 168h padrão, 33h de hora extra:
```
Taxa do jikyuu:     1.590 × 1,25            = ¥1.988 (arredondado)
Taxa do adicional:  (3.000 ÷ 168) × 1,25     = ¥23    (sempre pra cima)
Taxa final:         1.988 + 23               = ¥2.011
Total:               2.011 × 33h              = ¥66.363
```

**Dois controles novos em ⚙️ Config, substituindo a antiga "Taxa de
Referência" (nunca ficou visível — estava escondida atrás de um switch
desligado desde sempre):**

1. **Modo de Arredondamento** (geral) — "Sempre pra Cima" (novo padrão)
   ou "Regra do 0,5" (comportamento anterior). Afeta Salário Base,
   Hora Extra, Noturno, Feriado/Domingo e o campo 延長. **Não afeta** a
   Média Histórica de desconto, que continua sempre na Regra do 0,5.
2. **Usar Adicional de Líder no Arredondamento** — switch, desligado
   por padrão. Reaproveita o valor já configurado em "Adicional Fixo
   Mensal — Líder" (o mesmo que já soma no bruto) — não duplica campo.
   Revela "Horas Padrão para este Cálculo" (padrão 168h, configurável).

⚠️ **Mudança de padrão para todo mundo:** como "Sempre pra Cima" virou
o padrão geral (não só para quem ativar o adicional de líder), os
valores calculados mudam para **todos os usuários** a partir desta
versão, mesmo quem nunca mexer em nenhuma configuração nova. Decisão
consciente — ver `PROBLEMAS_RECORRENTES.md` para o raciocínio completo.

**Removido:** `premium_allowances_monthly`, `premium_standard_hours`,
`night_addon_extra` (settings), e toda a UI/lógica correspondente em
`calculate_shift_pay`/`compute_monthly_forecast`. `README.md` — seção
"Taxa de Referência" substituída por "Arredondamento com Adicional de
Líder".

**Pendente:** recalibrar `test_main.py` contra os 5 holerites reais
(esses continuam fixos na Regra do 0,5, já que foi o que gerou os
valores reais impressos) — a fazer depois da revisão visual do app.

### 🔴 Corrigido — hora extra do Alternado Semanal/Mensal ignorava o horário configurado

**Sintoma:** campo "残業 Início Hora Extra" não aparecia na tela de
configuração do turno Alternado (Semanal e Mensal), e mesmo que
aparecesse, não fazia efeito nenhum no cálculo.

**Causa raiz:** dentro do loop mensal, o horário de início da hora
extra para turnos alternados estava **hardcoded** (`"18:35"`/`"06:35"`),
ignorando completamente o parâmetro `cfg_ot` configurado pelo usuário
— diferente do 4x2/5x2, que já respeitavam esse campo corretamente.

**Corrigido:** campo adicionado à tela (`section_alt_container`) e o
cálculo agora usa `cfg_ot` quando preenchido, com fallback idêntico ao
valor hardcoded anterior para quem não configurar nada (nenhuma
mudança de comportamento pra quem já usa o padrão).

### 🟢 Corrigido — textos confusos no modal de ponto

- Switch "有休 em Feriado (+8h)" → "有休 em Feriado" (o "+8h" já não
  era mais verdade — a jornada usada é a configurada, não 8h fixo)
- Texto "Trabalho Normal", que aparecia acima dos campos Entrada/Saída
  sem agregar informação, trocado por uma dica útil: "Preencha
  Entrada/Saída para horário real (inclusive saída antecipada)"

---

## [2.48.0] — 2026-07-14 — MÉDIA HISTÓRICA EM IENES + TELA DE CARREGAMENTO + FIX SAFARI/FIREFOX

### 🔴 Corrigido — Média Histórica inflava o desconto (porcentagem vs. valor fixo)

**Causa raiz:** o desconto médio era calculado como porcentagem
(desconto ÷ bruto × 100) e depois reaplicado sobre o **bruto
previsto** do mês (`gross * history_avg_pct / 100`). Isso inflava o
valor em meses com bruto maior (hora extra, bônus), já que o desconto
real (INSS/imposto/etc.) tende a variar pouco em valor absoluto entre
holerites — não é proporcional ao bruto.

**Corrigido:** a Média Histórica agora é a **média simples dos valores
em ¥** já registrados (`entry["deductions"]`), aplicada diretamente,
sem multiplicar por nada. Parâmetro renomeado em todo o código:
`history_avg_pct` → `history_avg_deduction`.

**Textos atualizados:** "Média histórica: X%" → "Média histórica: ¥X"
(aba Holerite); "Taxa Média de Desconto" → "Desconto Médio" (aba
Histórico); badge de porcentagem removido dos cards do histórico (já
mostravam o valor em ¥ embaixo, ficava duplicado).

### 🟢 Alterado — só 1 campo obrigatório no registro de holerite

Como o cálculo agora depende só do valor de desconto, `総支給額 Total
Bruto` e `差引支給額 Salário Líquido` deixaram de ser obrigatórios —
viraram uma seção "💰 TOTAIS (opcional)". Só `控除合計 Total Desconto`
continua na caixa "⭐ OBRIGATÓRIO". Textos de aviso atualizados (3
campos → 1 campo) em `main.py` e em 2 pontos da aba Ajuda.
`README.md` — seção "Registro de Holerite Real" reescrita.

**Validado:** 94 testes automatizados passando (`test_main.py`,
corrigido para o novo nome do parâmetro).

### 🟢 Adicionado — tela de carregamento com logo animada

GIF gerado a partir da própria logo (efeito de respiração, ~65KB),
exibido instantaneamente via HTML/CSS puro logo após `<body>` —
aparece antes de qualquer script do Flutter/Pyodide rodar, e some
sozinho quando o evento `flutter-first-frame` dispara (com timeout de
segurança de 8s). Substitui a tela em branco que aparecia durante o
boot do Pyodide, especialmente notável na primeira visita (sem cache).

### 🔴 Corrigido — botões "Compartilhar" e "Relatar Problema" não abriam no Safari/Firefox

**Causa raiz:** bug conhecido e documentado do próprio Flet (issue
#1105) — Safari bloqueia `launch_url()` quando há qualquer atraso
assíncrono entre o clique e a abertura da aba. Nosso `page.run_task()`
introduzia exatamente esse atraso.

**Corrigido:** trocado `on_click` + `page.run_task` + `page.launch_url`
pelo parâmetro nativo `url=` + `url_target=ft.UrlTarget.BLANK` direto
no botão — vira um link nativo de verdade, confirmado pelo próprio
criador do Flet como 100% confiável no Safari. Bônus: mais simples e
mais compatível em geral, não só um caso especial.

### 🟢 Corrigido — espaçamento da tela de disclaimer

Reduzidos os espaçamentos verticais (padding da tela, espaço entre
logo/título/aviso/botões) para o botão "Recusar" caber na tela sem
precisar rolar, sem alterar fonte ou texto.

---

## [2.47.0] — 2026-07-14 — PÁGINA DE COMPARTILHAMENTO + ÍCONE QUEBRADO NO BANNER

### 🟢 Adicionado — botão "Compartilhar" com página dedicada

Substituídos os dois campos de texto selecionável (link do app + link
do vídeo, copiados com "toque e segure") por um único botão
"Compartilhar" em ❓ Ajuda, que abre `compartilhar.html` — mesmo padrão
já validado no botão de feedback (`page.launch_url` + `async def` +
`page.run_task`).

**Motivo da troca:** o balão de seleção de texto do Flutter Web
(usado pelos campos antigos) demorava muito pra aparecer, exigindo
várias tentativas pra conseguir copiar — limitação conhecida da
simulação de seleção de texto dentro do motor de renderização
Flutter/Skia, não é comportamento nativo do navegador.

Na página nova, o botão "Copiar Link" usa `navigator.clipboard.writeText()`
— API real do navegador, fora do Flutter/Pyodide, sem essa lentidão.
Inclui também:
- QR code do link do app (otimizado de 720KB → ~18KB, paleta reduzida)
- Botão "Abrir Vídeo" (abre direto, além de copiar o link)
- Link "← Voltar para o app" no topo

**Lição de arquitetura:** os textos dos links (`LINK_APP`/`LINK_VIDEO`)
existem como constante única no JavaScript, com o texto exibido na
tela preenchido a partir delas — evita repetir o mesmo padrão de bug
dos blocos de cor duplicados no `main.py` (fonte única, sem
duplicação silenciosa).

`deploy.ps1` — passo de cópia de arquivos extras generalizado (antes
só cobria `feedback.html`, agora é uma lista `$arquivosExtras` que
inclui `compartilhar.html` e `qr-app.png` também).

### 🔴 Corrigido — ícone genérico (quebrado) no banner de instalação

**Sintoma:** o banner customizado "Instalar Onion Payroll" (Android/
iOS) mostrava um ícone genérico de seta, não a logo do app.

**Causa raiz:** `deploy.ps1` referenciava `icons/apple-touch-icon-192.png`
— arquivo que **nunca existiu**. O Flet gera os ícones como
`Icon-192.png`/`Icon-512.png` (conforme `manifest.json`), não com esse
nome. 404 silencioso, navegador caía no ícone de fallback.

**Corrigido:** referência trocada pra `icons/Icon-192.png` — arquivo
que já existe, sem necessidade de gerar/enviar nenhuma imagem nova.

### 🟢 Corrigido — emoji genérico no título da tela de aviso

Título "🧅 Onion Payroll" na tela de disclaimer usava o emoji padrão
🧅 (amarelo), inconsistente com a logo roxa real já exibida 12px acima
no mesmo card. Trocado por uma versão pequena (26×26px) da própria
`logo_icon.png`, ao lado do texto — reaproveitando o arquivo existente,
sem asset novo.

---

## [2.46.0] — 2026-07-13 — AJUSTES NO SISTEMA DE FEEDBACK

### 🔴 Corrigido — envio falhava com erro 422 (Unprocessable Entity)

**Causa raiz:** o campo `email` do formulário mandava o texto
`"(não informado)"` quando ficava vazio. O Formspree valida
automaticamente qualquer campo chamado `email` como endereço real —
um texto qualquer nesse campo é rejeitado com 422, mesmo com o resto
do formulário correto.

**Corrigido:** o campo `email` só é incluído no envio se for
preenchido de verdade. Vazio = campo omitido, não mais um texto
placeholder inválido.

### 🟢 Adicionado — link para voltar ao app

A página `feedback.html` abre numa aba separada (via `page.launch_url`),
sem histórico de navegação natural pra voltar. Adicionado link "←
Voltar para o app" fixo no topo da página, e um botão destacado
"Voltar para o app" na mensagem de sucesso depois do envio.

### 🟢 Adicionado — bloqueio de links no texto do relato

Diferente do filtro de palavrão (que censura e permite confirmar o
envio mesmo assim), texto contendo link (`http://`, `https://`,
`www.`, ou domínio tipo `.com`/`.io`/`.com.br`) **bloqueia o envio
por completo** — precisa remover o link e reenviar, sem opção de
confirmar. Motivo: link no texto tende a ser sinal de spam/bot, não
de usuário legítimo relatando um problema. Como efeito colateral
esperado, e-mails digitados dentro do texto livre (não no campo
dedicado) também são bloqueados, já que batem no mesmo padrão de
domínio.

**Validado:** testado em produção com e sem e-mail preenchido, e com
link no texto — os três cenários funcionando como esperado.

---

## [2.45.0] — 2026-07-13 — SISTEMA DE FEEDBACK/RELATO DE BUG

### 🟢 Adicionado — botão "Relatar Problema" em ❓ Ajuda

Nova página `feedback.html` (fora do app Flet, HTML/JS puro), com dois
campos guiados ("O que você estava tentando fazer?" / "O que aconteceu
de errado?") + e-mail opcional. Envia via Formspree, sem servidor
próprio. Inclui:
- Filtro de baixo calão em JS: detecta, censura automaticamente
  (`p****`), mostra prévia censurada e exige confirmação antes de
  enviar (não bloqueia, não deixa passar batido)
- Honeypot anti-spam
- `BUILD_ID` capturado automaticamente via `?build=` na URL, viajando
  junto no envio — identifica a versão exata onde o bug apareceu, sem
  precisar perguntar pro usuário

### 🔴 Corrigido — botão não fazia nada ao tocar (TypeError silencioso)

**Sintoma:** botão "Relatar Problema" não abria nada — sem erro visível
na tela, só um clique morto.

**Causa raiz:** `page.run_task(page.launch_url, FEEDBACK_URL)` —
passar o método `page.launch_url` diretamente pro `run_task` não
funciona nessa versão do Flet. O decorator de depreciação que embrulha
esse método (`launch_url` está deprecado desde 0.80.0, removido na
0.90.0) faz o `inspect.iscoroutinefunction()` interno do `run_task` não
reconhecer o método como coroutine, lançando `TypeError: handler must
be a coroutine function`.

**Corrigido:** envolvido numa função `async def` própria
(`_abrir_feedback_task`), que por sua vez chama `await
page.launch_url(...)` — mesmo padrão já usado nos outros 3 lugares do
código que chamam `page.run_task()` (`_persist`, `_remove`,
`_do_diag`). **Nunca passar um método do Flet direto pro `run_task` —
sempre embrulhar numa função `async def` criada no próprio código.**

**Contexto:** esse é mais um episódio do padrão recorrente de "botão
não funciona" já visto antes (v2.10, v2.11, v2.18 — Dropdown resetando
seleção, botões de Copiar Link removidos por não funcionar de forma
confiável). Motivo raiz diferente dessa vez (API assíncrona do Flet,
não Dropdown), mas mesmo sintoma: interação que só quebra em runtime
real, nunca em `py_compile`.

---

## [2.44.0] — 2026-07-12 — NOME DO PWA INSTALADO E CORES DA SPLASH SCREEN

### 🟢 Corrigido — nome do app instalado aparecia como "onion_payroll"

**Sintoma:** ao instalar o PWA, o ícone ficava com o nome
`onion_payroll` (minúsculo, com underscore) em vez de "Onion Payroll",
mesmo com `[tool.flet] short_name = "OnionPayroll"` já declarado no
`pyproject.toml`.

**Causa raiz:** o campo `short_name` **não é reconhecido pelo `flet
build web`** dentro de `[tool.flet]` — só existe para o comando
`flet publish` (diferente do que o `deploy.ps1` usa). O campo `product`
funciona normalmente (`name` no `manifest.json` gerado saía certo,
"Onion Payroll"), mas não existe equivalente reconhecido para
`short_name` nesse fluxo de build — o valor "onion_payroll" era gerado
automaticamente a partir do nome do projeto, sem meio de sobrescrever
via `pyproject.toml`.

**Corrigido:** criado `assets/manifest.json` customizado — o Flet usa
esse arquivo (se presente) em vez de gerar um novo do zero, sobrepondo
qualquer valor derivado automaticamente. `short_name` agora fixado como
`"Onion Payroll"`, idêntico ao `name`.

### 🟢 Corrigido — splash screen branca, incoerente com o tema escuro

Aproveitando o `manifest.json` customizado: `background_color` (era
`#FFFFFF`, branco) e `theme_color` (era `#0175C2`, azul padrão do
Flutter) causavam um "flash" claro na tela de splash ao abrir o PWA
instalado, antes do app carregar — destoando do tema escuro Neo
Petronas do resto do app. Ajustados para `#2c2c2a` (`BG_DEEP`) e
`#00C2A8` (`ACCENT`), batendo com a paleta do app.

**Importante para desenvolvedores:** `docs/manifest.json` é gerado
automaticamente a cada deploy — nunca editar esse arquivo diretamente,
as mudanças se perdem no próximo build. A fonte de verdade agora é
`assets/manifest.json`.

**Validado:** JSON validado (`python -m json.tool`), deploy feito,
app desinstalado e reinstalado — nome e splash screen corretos.

---

## [2.43.0] — 2026-07-12 — CRÍTICO: APP NÃO ABRIA (DEPENDÊNCIA SEM VERSÃO TRAVADA) + AJUSTES DE LOGO

### 🔴 Corrigido — CRÍTICO: tela cinza sem erro nenhum, app não abria

**Causa raiz nº1:** `pyproject.toml` tinha `dependencies = ["flet"]` **sem
versão travada**. Cada deploy passava a baixar a versão mais recente do
Flet disponível no momento do build, em vez da versão testada
(0.85.3). Isso silenciosamente trocou o comportamento de
`page.shared_preferences` (API de storage, depreciada desde a 0.80.0),
travando o `await` de carregamento inicial (`boot_load_storage`) sem
lançar nenhuma exceção visível — o app ficava preso numa tela cinza,
sem nada no console.

**Corrigido:** `dependencies = ["flet==0.85.3"]` — versão travada,
confirmada contra o ambiente local (`pip show flet`).

**Causa raiz nº2** (introduzida ao corrigir a nº1, mesma sessão):
depois de travar a versão, um novo erro real apareceu no traceback:
`AttributeError: module 'flet.controls.alignment' has no attribute
'center'`. O atalho `ft.alignment.center` não existe no Flet 0.85.3 —
usado por engano em 4 `Container`s novos da logo (ver abaixo). Todo o
resto do código já usava corretamente `ft.Alignment(0, 0)`.
Padronizado em todas as ocorrências.

**Lição de processo:** depois desse episódio, qualquer mudança em
`pyproject.toml` que envolva a versão do Flet deve ser seguida de teste
real no navegador (Console aberto) antes de considerar o deploy
concluído — nem `py_compile` nem o stub de renderização local pegam
esse tipo de bug, porque a versão instalada localmente nunca muda
sozinha; só o build de produção (via micropip, no navegador) é afetado.

### 🟢 Adicionado — cores do calendário nos tons oficiais do Google Calendar

**Pedido antigo, finalmente aplicado:** os tons verde/azul do calendário
(dias de trabalho/folga) já tinham sido pedidos para usar a paleta
oficial do Google Calendar antes, mas a mudança nunca tinha "pegado" —
o valor certo estava sendo editado, só que numa variável que não era a
efetivamente aplicada no cálculo dos elementos de calendário.

```
WORK_COLOR       #1a3d2b → #0F9D58   (verde Google — Sage)
OFF_COLOR        #1e2e4a → #4285F4   (azul Google — Peacock)
CAL_TEXT_WORK    #86efac → #C8F7DC   (texto, ajustado p/ contraste)
CAL_TEXT_OFF     #93c5fd → #DBEAFE   (texto, ajustado p/ contraste)
CAL_BORDER_WORK  #22c55e → #7ade9f   (borda, ajustada p/ contraste)
CAL_BORDER_OFF   #60a5fa → #a0c3ed   (borda, ajustada p/ contraste)
C_BLUE           #40C4FF → #90CAF9   (letra de sábado, mais suave)
borda genérica   #D0D0D0 → #E5E7EB   (célula do calendário)
```

Os tons de texto/borda precisaram de ajuste fino depois da troca das
cores de fundo principais, para manter contraste legível — as cores
mais vibrantes do Google exigem texto/borda mais claros do que a
paleta dessaturada anterior.

### 🟢 Adicionado — logo com cantos arredondados e fundo suavizado

Logo do cabeçalho e das duas telas de disclaimer (aceite/recusa) agora
dentro de um `Container` com `border_radius` e `bgcolor=BG_CARD` —
suaviza o contraste da imagem de fundo transparente contra o fundo
escuro do header. Nova imagem 1024×1024 com fundo transparente
substituindo `assets/logo_icon.png`.

### 🟢 Adicionado — romaji nas menções ao 精皆勤手当 (Ajuda e Config)

Título e primeiro parágrafo da seção de assiduidade em ❓ Ajuda, e o
label do campo de limiar em ⚙️ Config, agora incluem "seikaikin teate"
ao lado do kanji — legível por quem não lê japonês.

**Validado:** `py_compile` limpo, deploy testado em aba anônima após a
correção, app abrindo normalmente.

---

## [2.30] — 2026-07-04 — LICENÇA MIT E INDICAÇÃO DE ACEITE

### 🟢 Adicionado — arquivo `LICENSE` (MIT)

**Pedido do usuário**, completando uma lacuna identificada na conversa
sobre robustez jurídica: o `LICENSE` MIT tinha sido sugerido antes, mas
nunca foi de fato criado nem referenciado na tela de aceite (v2.29).
Adicionado agora na raiz do projeto — texto padrão, sem modificações
(a Licença MIT é um modelo feito pra ser reutilizado literalmente,
diferente de conteúdo autoral).

### 🟢 Adicionado — indicação de quando o usuário aceitou os termos

**Confirmado o critério de aceite:** é exclusivamente o clique no botão
"Aceitar e Continuar" (`disclaimer_accepted=True`) — não há nenhuma
lógica que infira aceite a partir de dados já registrados ou qualquer
outro comportamento indireto. Verificado linha por linha no código.

**Novo:** o momento exato do clique agora é registrado
(`disclaimer_accepted_at`, timestamp ISO) e exibido em dois lugares:
- ⚙️ Config → nova seção "TERMOS E LICENÇA" ("✅ Termos aceitos em: ...")
- ❓ Ajuda → seção "⚠️ Aviso Legal", junto com a referência ao `LICENSE`

**Validado:** as 6 abas e o boot completo do `main()` testados de novo
via stub, sem erro.

---

## [2.29] — 2026-07-04 — TELA DE ACEITE NO PRIMEIRO USO (DISCLAIMER)

### 🟢 Adicionado — consentimento explícito ("clickwrap") no primeiro acesso

**Sugestão do usuário**, em resposta a uma discussão sobre robustez
jurídica do disclaimer: em vez de só um aviso passivo no README (que a
pessoa pode nunca ler), adicionar uma tela de aceite obrigatória antes
de abrir o app pela primeira vez — padrão usado por apps comerciais
para consentimento informado, mais defensável do que um aviso "browsewrap".

**Como funciona:**
- Antes de qualquer aba abrir, mostra logo + Aviso Legal completo +
  botões "Aceitar e Continuar" / "Recusar"
- **Aceitar** → grava a escolha (`disclaimer_accepted=True`), abre o
  app normalmente, nunca mais pergunta
- **Recusar** → tela fica só com a logo, sem nenhum botão ou conteúdo
  — recarregar a página dá uma nova chance (não é um bloqueio
  permanente e sem saída, o que criaria uma armadilha sem acesso ao
  "Apagar Dados" em Config)

**Reforço em mais 2 lugares**, com a mesma linguagem mais robusta
("como está", sem garantias, não é advogado/contador):
- Rodapé da aba Holerite (já existia desde v2.6, atualizado)
- Seção "⚠️ Aviso Legal" completa no manual (aba ❓ Ajuda)

### 🔴 Bug de teste corrigido durante o desenvolvimento (infraestrutura)

Ao construir o teste do fluxo de clique (Aceitar/Recusar) com o stub de
Flet falso, descoberto que o `__getattr__` de fallback do stub fazia
`hasattr()` sempre retornar `True` — isso impedia o loop que deveria
salvar os kwargs reais (como `on_click`) de rodar, fazendo os testes de
clique "passarem" chamando um Mock vazio em vez da função real. Só
percebido porque o valor esperado (`disclaimer_accepted=True` após o
clique) não mudava de fato — reforça a lição de sempre verificar o
*efeito* de um teste, não só a ausência de erro. Corrigido no stub
(não afeta o app em si).

**Validado:** `main()` completo testado via `asyncio.run()` com o stub,
nos cenários: disclaimer já aceito (vai direto pro app), disclaimer
novo (mostra a tela), clique em Aceitar (abre o app de verdade), clique
em Recusar (mostra só a logo) — todos sem erro.

---

## [2.26] — 2026-07-04 — VARREDURA COMPLETA: MESMO BUG EM OUTRO HELPER

### 🟡 Encontrado preventivamente — `_color_legend()` tinha a mesma vulnerabilidade do `_item()`

**Pedido do usuário:** depois de corrigir o `_item()` (v2.25), verificar
se o mesmo padrão de bug (campo sem largura definida roubando espaço do
vizinho `expand=True`) acontecia em outro lugar do manual.

**Encontrado:** `_color_legend()` (usado na seção "🎨 Cores do
Calendário") tinha a coluna de texto (label+desc) **sem `expand=True`**
— o mesmo problema estrutural do `_item()` antes da correção, só que
ainda sem ter gerado uma reclamação visível (o vizinho fixo, um quadrado
de cor 14×14px, é pequeno demais pra "roubar" espaço perceptível, mas o
risco estrutural era o mesmo).

**Correção:** `expand=True` adicionado à coluna. Conferidos também
`_rule()` (já tinha `expand` nos dois lados — seguro) e `_title()`/
`_sec()`/`_p()` (texto único, sem Row — sem risco).

### 🟡 Limpeza — 5 chamadas de `_item()` com conteúdo mais longo que os vizinhos

Mesmo já protegidas pela largura fixa da v2.25, essas 5 chamadas
ficariam "enroladas" em várias linhas sem necessidade. Encurtadas,
movendo a informação de cor da célula para a descrição (que tem espaço
de sobra) — mantém consistência visual com os itens vizinhos na mesma
seção.

---

## [2.25] — 2026-07-04 — CRÍTICO: TEXTO ESPREMIDO NUMA COLUNA ESTREITA NA AJUDA

### 🔴 Bug corrigido — descrição virava uma coluna de 1 palavra por linha

**Reportado pelo usuário** (com print): a descrição de um item específico
na seção de Yukyu aparecia espremida numa faixa vertical estreitíssima
no canto direito da tela, uma palavra por linha, com um vazio enorme à
esquerda — mesmo depois de dar zoom.

**Causa raiz:** `_item(icon, label, desc)` espera um ícone/rótulo CURTO
no primeiro parâmetro — mas a chamada da seção de Yukyu passou uma
frase inteira ali ("Se o dia marcado não tiver saldo disponível", 44
caracteres). Esse campo é um `ft.Text` simples, sem `expand` nem largura
definida — quando o conteúdo é longo, ele reivindica a maior parte da
largura da linha pra si mesmo, sobrando um fiapo de espaço pra coluna de
descrição (que aí sim tem `expand=True`, mas não tinha mais espaço
nenhum pra usar).

**Correção — duas camadas:**
1. Conteúdo da chamada específica corrigido (frase longa movida para o
   `desc`, ícone virou um rótulo curto, igual aos itens vizinhos)
2. `_item()` endurecido: o campo de ícone agora tem `width=100` fixo —
   mesmo que outro texto longo demais escape ali no futuro, fica
   confinado à própria coluna, sem roubar espaço da descrição

**Nota:** essa correção provavelmente também resolve o "espaço vazio ao
dar zoom" relatado junto — era o mesmo elemento vazando largura.

---

## [2.24] — 2026-07-04 — TEXTO DA AJUDA ESTOURAVA A LARGURA DA TELA

### 🔴 Bug corrigido — precisava de zoom de 50% pra ler o conteúdo

**Reportado pelo usuário:** a aba ❓ Ajuda não cabia na tela do celular
— precisava reduzir o zoom do navegador pra 50% pra conseguir ler,
mesmo em modo retrato normal.

**Causa raiz provável:** o helper `_example()` usa fonte monoespaçada
(`font_family="monospace"`) para blocos de cálculo — e uma das linhas
(tabela de progressão de Yukyu) tinha ~60 caracteres. Em fonte
monoespaçada (caracteres mais largos que fonte proporcional), isso é
largo o suficiente para estourar a largura útil de telas de celular
mais estreitas, sem quebra de linha automática garantida — o que pode
forçar a coluna inteira da página a ficar mais larga que a tela.

**Correção:** todas as linhas dos 4 blocos de exemplo (`_example()`)
encurtadas para no máximo ~28 caracteres, bem dentro da margem segura
para fonte monoespaçada em tela estreita. Preferido reduzir o conteúdo
diretamente em vez de depender de comportamento de quebra de linha do
Flet não verificado (mesma cautela já aplicada a `ft.Icons`/
`page.launch_url` nas versões anteriores).

**Nota sobre pinch-to-zoom:** o Flet/Flutter Web com renderizador
CanvasKit frequentemente intercepta gestos de toque antes de chegarem
no controle nativo de zoom do navegador — mesmo com `user-scalable=no`
removido do `index.html` (v2.11), pinch-to-zoom pode continuar limitado
por essa característica da plataforma, não por configuração do app.

---

## [2.23] — 2026-07-04 — RESUMO DE YUKYU MENOS POLUÍDO PRA QUEM TEM MUITOS ANOS DE EMPRESA

### 🟢 Melhorado — só concessões ativas, expiração como data

**Reportado pelo usuário** (com print de um cenário de 16 anos de
empresa): o resumo listava as 17 concessões históricas desde a
admissão, e mostrava totais acumulados ("Concedido até hoje: 301 |
Usado: 1 | Expirado: 261") sem contexto de tempo — números frios, sem
indicar quando algo vai vencer.

**Correção:**
- A lista detalhada agora mostra só concessões **ainda ativas** (não
  expiradas) — concessões já vencidas não têm mais utilidade prática
  pro saldo de hoje, e o histórico completo já fica implícito nos dias
  marcados no calendário
- A linha de totais "Concedido/Usado/Expirado" foi removida, substituída
  por **"Próxima expiração: DATA (X dias em risco)"** — informação
  concreta e útil (quando agir), não um acumulado histórico

**Validado:** cenário de 16 anos de empresa (admissão 2009) — lista cai
de 17 para 2 linhas de concessões ativas.

---

## [2.22] — 2026-07-04 — DATA SEM HÍFEN E DETALHAMENTO DO YUKYU

### 🟢 Adicionado — normalização de data (sem exigir hífen)

**Reportado pelo usuário:** os campos de data (Admissão, Início do
Ciclo, Referência do Alternado Mensal) exigiam digitar o hífen
manualmente (AAAA-MM-DD), sem tolerância a outros formatos.

**Correção:** nova função `normalize_date()` (mesmo padrão já usado em
`normalize_hhmm()` pros campos de horário) — aceita `20260703`,
`2026/07/03`, `2026.7.3` ou já com hífen, normalizando tudo pra
AAAA-MM-DD ao sair do campo. Entrada inválida (data que não existe, ou
formato não reconhecido) mantém o texto como veio, sem travar o campo.

### 🟢 Adicionado — datas reais no detalhamento do Yukyu

**Reportado pelo usuário:** o resumo de saldo mostrava só totais
("Concedido: 10, Expirado: 0"), sem indicar QUANDO cada concessão
aconteceu ou vai expirar.

**Correção:** cada concessão no resumo agora mostra a data exata:
`• 2026-05-01: +10d (usado 2, expira 2028-05-01)` — usando o detalhe
que `calcular_yukyu()` já calculava internamente (`detalhe_concessoes`)
mas não estava sendo exibido.

### 🔵 Refatorado — atualização direcionada, sem refresh_all()

Ao implementar a atualização em tempo real do resumo de Yukyu quando a
Data de Admissão muda, a primeira tentativa usou `refresh_all()` — o
que reintroduziria o bug de scroll voltando ao topo (já corrigido
várias vezes nesta aba). Corrigido antes de entregar: a lógica de
montar o texto do resumo foi extraída para uma função reutilizável
(`_montar_texto_yukyu()`), e a atualização usa um widget nomeado
(`yukyu_texto_widget`) com `.update()` direcionado, seguindo o mesmo
cuidado já documentado em `PROBLEMAS_RECORRENTES.md`.

---

## [2.21] — 2026-07-04 — BOTÃO "APAGAR TODOS OS DADOS" NÃO ATUALIZAVA A TELA

### 🔴 Bug corrigido — storage apagava de verdade, mas a UI mostrava dados antigos

**Contexto:** ao revisar o botão "Apagar Todos os Dados Locais" (nunca
testado a fundo nesta série de correções), confirmado que ele realmente
limpa as 5 chaves certas de `shared_preferences` — igual às 5 chaves
que `boot_load_storage()` carrega, sem sobrar nada. Porém, achado um bug
separado: a tela não refletia a limpeza imediatamente.

**Causa raiz:** `refresh_all()` só atualiza `state["settings"]` quando
`_mem_cache.get(KEY_SETTINGS)` retorna algo (`if _cached and
isinstance(...)`, pensado para preservar edições feitas por
`__setitem__` sem precisar recarregar do disco). Depois de
`remove_storage()`, o cache fica vazio (`None`) — a condição falha, e
`state["settings"]` continua com o objeto ANTIGO em memória. Resultado:
o storage já estava vazio de verdade, mas a tela de Config continuava
mostrando jikyuu, Data de Admissão, etc. antigos até um reload completo
do app.

**Correção:** `_confirm()` (dentro de `_clear_all`) agora reseta
`state["settings"/"history"/"overrides"/"holidays"/"holidays_corp"]`
explicitamente para os valores padrão, e sincroniza `_mem_cache`, antes
de chamar `refresh_all()` — sem depender do carregamento implícito que
falha quando o cache está vazio.

**Validado:** simulação completa do fluxo (settings customizados →
apagar → conferir reset) confirmando que `jikyuu` volta ao padrão e
`hire_date` some, sem precisar reabrir o app.

---

## [2.20] — 2026-07-03 — MANUAL: SEÇÃO DE YUKYU QUE FALTAVA

### 🔴 Bug corrigido — link "Ver ❓ Ajuda para detalhes" não levava a nada

**Reportado pelo usuário:** o resumo de saldo de Yukyu (v2.19) tem o
texto "Ver ❓ Ajuda para detalhes", mas a seção detalhada nunca foi
escrita — a única menção a Yukyu no manual era uma linha genérica sobre
a cor da célula no calendário.

**Correção:** nova seção "🌴 Direito a Yukyu (有給休暇)" na aba ❓ Ajuda,
logo após "📅 Registrando o Ponto" — com a tabela de progressão completa
(6m=10 até 6a6m+=20 dias), a regra de expiração de 2 anos, como o
desconto automático funciona, e as duas limitações já documentadas no
`README.md` (sem checagem de 80% de presença, sem proporcional de
part-time).

---

## [2.19] — 2026-07-03 — DIREITO A YUKYU (有給休暇) CALCULADO AUTOMATICAMENTE

### 🟢 Adicionado — cálculo de saldo de Yukyu conforme a Lei Trabalhista Japonesa

**Pedido do usuário:** ao marcar a Data de Admissão, o app agora calcula
automaticamente quantos dias de Yukyu (有給休暇) o usuário tem direito,
e desconta cada dia marcado como "yukyu" no calendário.

**Pesquisado diretamente na Lei Trabalhista Japonesa (Art. 39, 労働基準法)**
antes de implementar — não foi assumido de memória:
- Direito nasce aos 6 meses de vínculo (10 dias), com 80%+ de presença
  no período — a checagem de presença **não é verificada automaticamente**
  nesta versão (assume elegibilidade; ver limitação documentada)
- Progressão: 6m=10, 1a6m=11, 2a6m=12, 3a6m=14, 4a6m=16, 5a6m=18,
  6a6m+=20 dias (teto, mantido a cada 12 meses depois disso)
- Cada concessão expira 2 anos depois (Art. 115) — implementado com um
  "livro-razão" (ledger) que consome o saldo mais antigo primeiro (FIFO),
  a mesma lógica prática usada para não desperdiçar dias prestes a vencer
- Cobertura: só tabela cheia (5+ dias/semana) — 比例付与 (proporcional
  para part-time) fica para uma versão futura, se necessário

**Novo campo:** "Data de Admissão" (⚙️ Config, Etapa 4) — separado da
"Data de Início do Ciclo" (que é sobre o turno, não a admissão).

**Novo resumo automático:** mostra saldo disponível, total concedido,
usado, expirado, e a data/quantidade da próxima concessão — recalculado
toda vez que a aba Config é aberta, lendo os dias marcados como "yukyu"
em todo o histórico do calendário (não só o mês atual).

**Validado:** 8 novos testes (`TestYukyu`), incluindo progressão
completa até o teto de 20 dias, expiração de 2 anos, uso antes da
concessão (inválido) e uso além do saldo (inválido) — total agora 64
testes.

### 🔴 Bug de teste corrigido — mesma categoria de antes

Ao inserir a classe `TestYukyu`, o bloco `if __name__ == "__main__":`
foi apagado por engano (não só mal posicionado — removido). A suíte
rodava sem erro mas **sem executar nenhum teste** (saída vazia, código
de saída 0). Detectado só porque o processo de conferir a contagem de
testes (lição da v2.9) foi seguido antes de entregar.

---

## [2.18] — 2026-07-03 — LIMPEZA DA ABA AJUDA (PALETA, LINKS, EXEMPLOS)

### 🔴 Bug corrigido — fundo branco e texto ilegível na aba Ajuda

**Causa raiz:** `build_help_tab()` tinha uma paleta de cores clara
definida localmente (`BG_CARD = "#FFFFFF"`), desalinhada do tema escuro
usado no resto do app — e pior, com `TEXT_PRIMARY`/`YEN_GOLD` ainda nas
cores claras originais (quase brancas), pensadas para fundo ESCURO.
Resultado: título quase invisível (texto quase branco sobre fundo quase
branco).

**Correção:** paleta local removida por completo — a função agora herda
as constantes globais do tema escuro, iguais a todas as outras abas.

### 🟡 Botões "Copiar Link" removidos

`page.set_clipboard()` não estava funcionando de forma confiável nos
testes do usuário. Em vez de investigar mais uma API não documentada,
os botões foram removidos — os links continuam como texto selecionável
(toque e segure para copiar, padrão do navegador), sem depender de API
nenhuma.

### 🟡 Exemplos de funções desativadas removidos do manual

As seções "Arredondamento do Ponto" e "Taxa de Hora Extra/Noturno/
Domingo" no manual explicavam funcionalidades que foram escondidas da
aba Config na v2.14 (`hidden_advanced_container`). Manter os exemplos
no manual, com a função inacessível na tela, só gerava confusão.
Removidas; a seção "Arredondamento da Taxa por Hora" foi mantida (esse
mecanismo continua sempre ativo, não é uma função desativada).

### 🟡 Animação de opacidade morta removida

`content_area` tinha `animate_opacity` configurado mas a opacidade
nunca era de fato alterada em lugar nenhum do código — animação sem
efeito, removida por limpeza (investigando relato de "luz piscando"
na troca de abas, ainda não localizado com certeza).

### Metodologia — deploy falho não é sempre bug de código

Durante a investigação desta versão, descobriu-se que alguns "bugs"
reportados eram na verdade falhas do GitHub Actions (`Deployment
failed, try again later` / `Multiple artifacts named "github-pages"`)
causadas por múltiplos deploys em sequência rápida colidindo. **Lição:**
antes de assumir que é bug de código, conferir se o deploy mais recente
realmente terminou com sucesso (aba Actions do GitHub, ícone verde) —
usar o Build ID no cabeçalho do app para confirmar qual versão está
realmente no ar.

---

## [2.17] — 2026-07-03 — CRÍTICO: ABAS CONFIG E AJUDA NÃO ABRIAM

### 🔴 Bug crítico corrigido — Config quebrada desde a v2.14

**Reportado pelo usuário:** as abas ⚙️ Config e ❓ Ajuda pararam de abrir.

**Causa raiz (Config):** ao reorganizar a aba em wizard por etapas
(v2.14), o `hidden_advanced_container` (seção "Avançado" escondida) foi
criado referenciando `block_label`, `block_row`, `round_mode_label`,
`round_mode_row`, `premium_switch` e `premium_fields_col` — mas essas
variáveis só eram definidas MAIS TARDE na função. Isso não gera erro de
sintaxe (por isso passou despercebido em todas as verificações
anteriores), mas quebra em tempo de execução com `UnboundLocalError`
assim que a aba tenta renderizar.

**Correção:** `hidden_advanced_container` movido para depois de todas
as variáveis que ele usa já existirem.

### 🔴 Bug crítico corrigido — Ajuda quebrada desde a v2.16

**Causa raiz:** os botões "Copiar Link" e "Ver Vídeo" (v2.16) usavam
`ft.Icons.COPY` / `ft.Icons.PLAY_CIRCLE_OUTLINE` — um padrão de ícone
diferente do que o resto do app já usa comprovadamente (`icon="upload"`,
string minúscula simples).

**Correção:** trocado para `icon="copy"` / `icon="play_circle_outline"`,
igual ao padrão já validado em produção.

### Metodologia nova — teste de renderização sem o Flet instalado

Criado um módulo `flet` "falso" (aceita qualquer chamada/atributo sem
precisar da lib real) para testar se as funções `build_*_tab()` executam
sem erro, sem precisar abrir o app de verdade. Isso pega exatamente essa
classe de bug (`UnboundLocalError`, `NameError`, ordem de definição
errada) que passa despercebida em `py_compile` (só verifica sintaxe) e
em `unittest` (só testa o motor de cálculo, não a UI).

**Lição para o processo:** ao adicionar qualquer container/variável nova
dentro de `build_settings_tab()` ou outra função de UI grande, testar a
função inteira renderizando com o stub antes de considerar a mudança
pronta — não basta `python -m py_compile`.

---

## [2.16] — 2026-07-03 — VÍDEO DE APRESENTAÇÃO NO COMPARTILHAMENTO

### 🟢 Adicionado

Botão "Ver Vídeo de Apresentação (30s)" na seção "📤 Compartilhar o
Onion Payroll" (aba ❓ Ajuda), abrindo o vídeo curto do app no YouTube
(`page.launch_url`), junto do QR code e do link já existentes.

---

## [2.15] — 2026-07-03 — NOVO CICLO: ALTERNADO MENSAL

### 🟢 Adicionado — Alternado Mensal (1 mês diurno + 1 mês noturno)

**Pedido do usuário:** além do Alternado Semanal já existente, um novo
tipo de ciclo onde o turno (diurno/noturno) muda a cada MÊS inteiro em
vez de a cada semana — comum em fábricas com rotação mensal de turno.

**Padrão de folga configurável dentro do Alternado Mensal:**
- **5×2** (padrão): folga sábado/domingo, igual ao Alternado Semanal
- **4×2**: folga em blocos de 4 dias trabalho + 2 folga, respeitando
  Grupo A/B/C — reaproveita `generate_4x2_calendar()` (mesma lógica já
  validada do ciclo 4×2 puro, incluindo o mecanismo `anchor_group`)

**Duas datas de referência independentes** (só quando 4×2 é o padrão de
folga escolhido):
- Data do ciclo de folga (já existente, com Grupo A/B/C)
- Nova "Data de Referência — Mês Diurno": qualquer dia dentro do
  primeiro mês trabalhado de dia — define a alternância mensal

**Correção de nomenclatura:** o antigo botão "Alternado" foi renomeado
para "Alternado Semanal" para diferenciar do novo "Alternado Mensal".
Nenhuma mudança de comportamento para quem já usa o Alternado Semanal.

**Implementação:** nova função `generate_alternating_monthly_calendar()`,
que separa duas responsabilidades que antes estavam grudadas na função
semanal — o PADRÃO DE FOLGA (quais dias são trabalho/descanso) e a
ALTERNÂNCIA DE TURNO (quando troca diurno/noturno) — permitindo combinar
qualquer padrão de folga com qualquer período de alternância no futuro,
sem duplicar código.

**Validado:** 7 novos testes (`TestAlternadoMensal`), cobrindo os dois
padrões de folga, a alternância mês a mês, a integração com Grupo A/B/C,
e o forecast completo — total agora 56 testes.

---

## [2.14] — 2026-07-02 — ABA CONFIG REORGANIZADA EM WIZARD POR ETAPAS

### 🔵 Redesenho — preenchimento guiado por etapas

**Sugestão do usuário**, expandindo o padrão de switch/campo-escondido
já usado na Taxa de Referência (v2.10) e no Diagnóstico (v2.10): a aba
⚙️ Config foi reorganizada num fluxo de 4 etapas, cada uma só aparecendo
depois que a anterior faz sentido ser preenchida.

**Novo fluxo:**
1. **Tipo de Ciclo** (4×2 / 5×2 / Alternado) — sempre visível, primeiro
2. **Horário do Turno** — só aparece depois da etapa 1; conteúdo muda
   conforme o ciclo (Diurno/Noturno + horários para 4×2/5×2; par de
   horários dia+noite para Alternado, sem o seletor Diurno/Noturno)
3. **Grupo de Turno** (A/B/C + data) — só aparece se o ciclo for 4×2
4. **Configuração de Salário** (Valor Hora, bônus, adicional fixo) —
   aparece junto com a etapa 2, depois da etapa 1

**Escondidos por enquanto** (a pedido do usuário — mantidos no código,
só não aparecem na tela): Arredondamento do Ponto, Regra de
Arredondamento, e Taxa de Hora Extra/Noturno/Domingo. Reversível
trocando `hidden_advanced_container.visible = False` por `True`.

**Migração:** quem já usava o app antes desta versão não perde as
etapas — se `cycle_type` já estava salvo, o wizard é tratado como
"já confirmado" e tudo continua visível normalmente. Só usuários novos
(instalação limpa) veem o fluxo passo-a-passo.

---

## [2.13] — 2026-07-02 — GRUPO A/B/C: RASTREAMENTO AUTOMÁTICO (SEM SWITCH)

### 🔵 Redesenho — substituído o switch da v2.12 por rastreamento automático

**Sugestão do usuário**, refinando a correção da v2.12: em vez de um
switch manual "modo pessoal vs. compartilhado", o app agora **lembra
automaticamente qual grupo estava selecionado quando a data foi
definida** (`anchor_group`, gravado junto com `anchor_date` toda vez que
o campo de data perde o foco).

**Como funciona agora:**
- Selecionar Grupo B → digitar a data → aquele dia vira o dia 1 do
  **Grupo B** (sem deslocamento, `anchor_group == group`).
- Clicar em outro grupo DEPOIS, sem mexer na data, recalcula sozinho
  usando a relação de 2 dias entre turmas (`anchor_group != group`).

Isso cobre os dois casos de uso da v2.12 (pessoal e compartilhado) com
um único mecanismo, sem exigir que o usuário entenda ou lembre de
configurar um switch — o comportamento certo emerge naturalmente da
ordem em que as ações são feitas.

**UX adicional:**
- O campo de data só aparece depois que o usuário seleciona um grupo
  pela primeira vez (força a ordem correta) — mas só na primeira vez;
  quem já tem `anchor_group` salvo continua vendo o campo normalmente.
- Novo indicador "📅 Escala do Grupo X" no topo da aba Calendário,
  mostrando explicitamente de qual grupo é a escala visualizada (e, se
  a data foi definida por outro grupo, isso também aparece).

**Validado:** 9 testes em `TestGrupoABC`, incluindo o cenário completo
descrito pelo usuário (selecionar grupo → digitar data → trocar de
grupo sem mexer na data → conferir que nunca 2 grupos folgam juntos).

---

## [2.12] — 2026-07-02 — GRUPO PESSOAL VS. COMPARTILHADO, BOTÕES BILÍNGUES, COMPARTILHAR APP

### 🔴 Bug crítico corrigido — Grupo B/C deslocava a data digitada pelo usuário

**Reportado pelo usuário:** ao selecionar Grupo B ou C e digitar a própria
data de início de trabalho, o dia digitado aparecia como "folga" em vez
de "trabalho" — só funcionava certo se o Grupo A estivesse selecionado.

**Causa raiz:** a correção da v2.11 tratava `anchor_date` como se fosse
*sempre* a referência do Grupo A, deslocando B (+2 dias) e C (+4 dias)
em cima dela. Mas quando o próprio usuário digita a data, ele está
dizendo "esse é o MEU primeiro dia de trabalho" — não "esse é o primeiro
dia do Grupo A". O código deslocava uma data que já era pessoal,
deslocando duas vezes.

**Correção — dois modos, configuráveis:**
- **Modo pessoal (default)**: `anchor_date` é sempre o dia 1 do PRÓPRIO
  grupo selecionado, sem deslocamento algum. Grupo passa a servir só
  para o turno padrão (noturno/diurno).
- **Modo compartilhado (opcional, switch em ⚙️ Config)**: mantém o
  comportamento da v2.11 — `anchor_date` é a referência única do Grupo
  A, com B/C deslocados +2/+4 dias. Útil se a empresa fornece um único
  ponto de referência fixo para as 3 turmas.

**Validado:** 9 testes (`TestGrupoABC`), cobrindo os dois modos
separadamente, mais o cenário exato reportado pelo usuário (dia digitado
por Grupo B/C deve ser "work", não "off").

### 🟡 Botões do modal de ponto ficaram em japonês depois da conversão

Ao converter o Dropdown de Status para botões (v2.10), alguns labels
ficaram só em japonês (`有休`, `休出 (+35%)`, `法定休出 (+35%)`) — nada
óbvio para o público brasileiro do app, e o botão de Yukyu em particular
ficou "escondido" por não ser reconhecível.

**Correção:** botões agora mostram português como texto principal e
japonês como legenda secundária menor (ex: "Folga Remunerada" / `有休`),
preservando a referência japonesa para localizar a rubrica no holerite
real, sem esconder o significado atrás do idioma.

**Confirmado:** a lógica de cálculo do Yukyu já estava correta (8h fixas,
sem hora extra nem noturno) — o problema era só o rótulo do botão.

### 🟡 Texto cortado ao lado dos switches de esconder seção

`ft.Switch` com `label` embutido não quebra linha em telas estreitas —
mesma classe de problema já vista em Dropdowns, mas em Switch. Corrigido
substituindo o `label` embutido por um `ft.Text` separado dentro de uma
`Row`, que quebra linha normalmente.

### Adicionado
- Seção "📤 Compartilhar o Onion Payroll" na aba ❓ Ajuda — QR code (via
  api.qrserver.com) + link copiável com um toque
- 3 novos testes de Grupo A/B/C cobrindo o modo pessoal — total agora
  49 testes
- Simulação de holerite real documentada: sem calibrar a taxa de
  referência, extra/noturno/domingo mostram ~1,15%-1,24% de diferença
  (esperado); calibrado, ¥0 de diferença — confirmado contra os 3
  holerites de 2026

---

## [2.11] — 2026-07-02 — GRUPO A/B/C, ZOOM DO PWA E ÚLTIMOS DROPDOWNS

### 🔴 Bug crítico corrigido — Grupo A/B/C nunca afetava o calendário

**Reportado pelo usuário**, com evidência de planilha real de escala da
fábrica (3 turmas, cada uma com dias de trabalho/folga diferentes na
mesma semana, nunca duas turmas de folga no mesmo dia).

**Causa raiz:** `generate_4x2_calendar()` nunca recebia o parâmetro
`group` em nenhuma das duas chamadas (aba Calendário e
`compute_monthly_forecast`). O único efeito que `group` tinha no app
inteiro era servir de palpite (`"night" if group == "B" else "day"`)
para o turno padrão — nunca deslocava quais dias eram trabalho ou folga.
Ou seja: trocar de Grupo A/B/C **não tinha nenhum efeito real** no
calendário ou no cálculo de holerite.

**Evidência:** planilha da fábrica confirmou matematicamente um
deslocamento de 2 dias por turma dentro do ciclo de 6 dias (Grupo
A=+0, B=+2, C=+4), validado contra os 7 dias completos de cada grupo —
bate 100%, e garante que nunca duas turmas folgam no mesmo dia.

**Correção:** `generate_4x2_calendar()` ganhou o parâmetro `group`
(default `"A"`, compatível com código antigo), aplicando o deslocamento
`{"A": 0, "B": 2, "C": 4}` antes de calcular o dia do ciclo. As duas
chamadas (Calendário e forecast) agora passam `group` corretamente.

**Validado:** 21 casos de teste reproduzindo a planilha real completa
(7 dias × 3 grupos), mais checagem de que nunca 2 grupos folgam juntos.

### 🟡 Regressão de teste corrigida (efeito colateral da correção acima)

`test_domingo_sem_registro_nao_conta` presumia que o dia 14/jun/2026
era folga do Grupo B — só era, por acidente, porque o bug acima fazia
o grupo ser ignorado. Corrigido para usar o dia 4, confirmado como
folga real do Grupo B pela nova lógica.

### 🟡 Zoom do PWA bloqueado

`docs/index.html` tinha `maximum-scale=1.0, user-scalable=no` na tag
viewport, desativando pinch-to-zoom — herdado do template padrão que o
`flet build web` gera a cada deploy. Corrigir só o `docs/index.html`
manualmente resolveria até o próximo deploy sobrescrever de novo.

**Correção definitiva:** `deploy.ps1` agora remove `maximum-scale=1.0,
user-scalable=no` do `index.html` automaticamente, no mesmo passo que já
injeta Analytics e as meta tags anti-cache (passo 7) — não precisa mais
lembrar de corrigir isso manualmente depois de cada build.

### 🟡 Últimos 3 Dropdowns convertidos para botões

`group_dd`, `shift_type_dd` (⚙️ Config) e `status_dd` (modal de ponto)
ainda usavam `ft.Dropdown` com `refresh_all()` no `on_change` — mesmo
padrão de bug recorrente das versões anteriores. Convertidos para
botões. `status_dd` (6 opções) virou um grid 3×2 com um texto de
descrição do status selecionado logo abaixo. Não sobrou nenhum
`ft.Dropdown` no app.

### Adicionado
- `_ValueHolder`: classe auxiliar mínima (só atributo `.value`) para
  substituir Dropdowns por botões sem reescrever todos os pontos de
  leitura do valor selecionado
- Switch "Mostrar ferramentas de diagnóstico" — Diagnóstico de
  Armazenamento agora escondido por padrão, mesmo padrão usado na Taxa
  de Referência (v2.10)
- 6 novos testes automatizados (`TestGrupoABC`) validando o
  deslocamento de grupo contra a planilha real — total agora 46 testes

---

## [2.10] — 2026-07-01 — UX DA ABA CONFIG (RECORRÊNCIA DE BUGS DE UI)

### 🟡 Bug recorrente corrigido — Dropdown de arredondamento resetava a seleção

**Reportado pelo usuário em uso real no celular:** o Dropdown "Arredondamento
do Ponto" (adicionado na v2.9) tinha o mesmo bug que o seletor de Desconto
já teve antes de virar botão (v2.4/2.6): a seleção não fixava e a página
voltava ao topo ao escolher uma opção.

**Causa raiz:** `ft.Dropdown` nesta versão do Flet parece disparar
recomposição/scroll da página ao abrir o menu suspenso — o mesmo problema
que já tinha sido isolado e contornado no seletor de Desconto, mas não foi
replicado quando o Dropdown de arredondamento foi criado na v2.9.

**Correção:** `block_dd` e `round_mode_dd` (dropdowns) substituídos por
botões (`ft.FilledButton`), seguindo exatamente o padrão já usado no
seletor de Desconto — sem `refresh_all()`, atualizando só os próprios
botões via `.update()`.

**Lição para o processo:** ao introduzir um novo `ft.Dropdown` na aba
Config, replicar o padrão de botões desde o início, já que o Dropdown
tem histórico recorrente desse bug nesta base de código.

### 🟡 Bug corrigido — campo cortado em tela de celular

Os campos "Horas Padrão para o Cálculo" e "Ajuste Fino do Noturno"
(adicionados na v2.9) estavam lado a lado numa `ft.Row` sem `expand`,
cortando o segundo campo em telas estreitas de celular.

**Correção:** campos empilhados verticalmente (`ft.Column`) em vez de
lado a lado.

### 🟡 UX — aba Config estava poluída

Feedback do usuário: a seção "Taxa de Hora Extra/Noturno/Domingo"
(v2.9) tornou a aba Config confusa para quem não precisa dela — a
grande maioria dos usuários não tem esse tipo de adicional na empresa.

**Correção:** os 3 campos de calibração ficam escondidos atrás de um
`ft.Switch` ("Minha empresa usa taxa diferente...") desligado por
padrão. O texto de ajuda longo saiu da Config (que agora só tem uma
linha apontando para a aba Ajuda) — a explicação completa com fórmula
de calibração passo a passo ficou só na aba ❓ Ajuda.

### Adicionado
- Exemplos numéricos completos na aba ❓ Ajuda para os dois mecanismos de
  arredondamento (do ponto e da taxa por hora) e para o passo a passo de
  calibração da taxa de referência — usando os holerites reais já
  validados
- Mesma seção de exemplos replicada no `README.md`

---

## [2.9] — 2026-07-01 — TAXA DE REFERÊNCIA E ARREDONDAMENTO POR CATEGORIA

### 🟡 Precisão — resíduo de 1,2%-1,4% em extra/noturno/domingo corrigido

**Descoberto através de comparação com 5 holerites reais** (2021/11, 2022/03,
2026/02, 2026/03, 2026/04 — 2 valores de `jikyuu` diferentes, com e sem
adicional fixo de líder).

**Causa raiz nº1 — taxa de referência sem adicionais fixos:** o cálculo de
hora extra, noturno e domingo usava só o `jikyuu` puro. Quando a empresa
paga adicionais fixos mensais (ex: `リーダー手当`), a legislação exige que
esses adicionais entrem na "taxa de referência" usada nesses três cálculos
— só não entram no cálculo de horas normais. Sem isso, o app calculava
1,19%-1,38% a menos nessas três rubricas.

**Evidência matemática:** comparando os holerites de fev/mar/abr de 2026
(mesmo funcionário, `jikyuu`=¥1.590, com `リーダー手当`=¥3.000/mês) contra
os de 2021/2022 (mesmo funcionário, `jikyuu`=¥1.430, SEM `リーダー手当`),
o acréscimo desaparece exatamente quando o adicional de líder desaparece —
confirmando a causa.

**Causa raiz nº2 — ordem do arredondamento:** o valor final de cada
rubrica era arredondado no fim do cálculo (`shisha_gofuuu` aplicado ao
produto completo). O correto — confirmado com planilha de referência do
usuário e validado contra os 5 holerites — é arredondar a **taxa por
hora** para o yen mais próximo **antes** de multiplicar pelas horas
trabalhadas. Isso fechou os últimos centavos de diferença que sobravam
mesmo depois da correção nº1.

**Correção:** `calculate_shift_pay()` ganhou 3 parâmetros opcionais —
`fixed_allowances_monthly`, `standard_monthly_hours` (default 144) e
`night_addon_extra` — usados para elevar a taxa de extra/noturno/domingo
antes de arredondar por hora e multiplicar. Todos com default que preserva
o comportamento anterior (zero impacto em quem não configurar nada).

**Validado:** as 15 rubricas (extra/noturno/domingo × 5 holerites) batem
com diferença ¥0 contra os valores reais.

### 🟡 Bug de teste corrigido — 9 testes nunca executavam

`unittest.main()` estava posicionado no meio do `test_main.py`, antes de 3
classes de teste inteiras serem definidas (incluindo a que valida o fix de
domingo da v2.8). Como o Python executa o arquivo de cima pra baixo, essas
classes nunca chegavam a rodar. Corrigido movendo o bloco para o final
real do arquivo — de 26 para 35 testes efetivamente executados.

### 🟡 Arredondamento por categoria (hora extra/noturno)

`truncate_minutes()` ganhou um `round_mode` ("truncate", igual antes, ou
"nearest", arredonda pro múltiplo mais próximo). Hora extra e noturno
agora são arredondados separadamente, a partir do valor bruto — antes,
eram derivados do `net_min` já truncado, o que descartava a granularidade
correta por categoria (regra MHLW 昭63.3.14 基発150号: cada rubrica é
arredondada por dia, individualmente, antes de somar o mês).

### Adicionado
- Nova seção em ⚙️ Config: "Taxa de Hora Extra/Noturno/Domingo", com os 3
  campos novos e texto de ajuda explicando como calibrar contra um
  holerite real (o valor não é o mesmo que aparece impresso na rubrica de
  adicional — precisa ser calculado)
- Dropdown "Regra de Arredondamento" (truncar / mais próximo), visível
  quando o bloco de arredondamento é maior que 1 minuto
- Seção "📈 Taxa de Hora Extra/Noturno/Domingo" na aba de Ajuda
- 5 novos testes automatizados (`TestAcrescimoTaxaPremium`) validando a
  taxa elevada e o arredondamento por hora contra os 5 holerites reais —
  total agora 40 testes

### Metodologia de validação (referência futura, expandindo a da v2.8)
1. Quando o resíduo entre calculado e holerite real for pequeno e
   proporcional às horas (não aleatório), suspeitar de uma regra de
   arredondamento específica antes de assumir "ruído"
2. Testar a hipótese com pelo menos 2 pontos de dados com `jikyuu`
   diferentes — se o resíduo for uma % fixa do `jikyuu` OU um valor fixo
   em ¥/hora independente do `jikyuu`, nenhuma das duas simplificações
   costuma se sustentar sozinha; o valor real tende a vir de um adicional
   fixo mensal específico daquele período
3. Um holerite de um período SEM o adicional fixo (ex: antes de uma
   promoção) é o teste mais forte — se o resíduo cai a quase zero junto
   com o adicional, a causa está confirmada

---

## [2.8] — 2026-07-01 — VALIDAÇÃO E CORREÇÃO COM HOLERITES REAIS

### 🔴 Bug crítico corrigido — domingo/feriado pagava ~13% a mais

**Descoberto através de comparação direta com 2 holerites reais** (fevereiro e
março de 2026, mesmo funcionário, 2 e 4 domingos trabalhados respectivamente).

**Causa raiz:** o cálculo de domingo/feriado trabalhado somava três adicionais
de forma independente — `holiday_pay (+35%)` + `night_pay (+25%)` +
`overtime_pay (+25%)` — sobre o mesmo período de horas. O holerite real da
empresa aplica **apenas o adicional de +35%** sobre o total de horas
trabalhadas no domingo, sem empilhar noturno ou hora extra por cima.

**Evidência matemática:** o valor de `公出手当` (trabalho em domingo) dobrou
exatamente de ¥47.784 (2 domingos) para ¥95.568 (4 domingos) — confirmando
¥23.892 por domingo em ambos os holerites. Isolando a fórmula:
`11h × ¥1.590/h × 1,35 = ¥23.612` (precisão de 98,8% contra o valor real).
O app antes calculava ¥27.011 por domingo — 13% acima do correto.

**Correção:** quando `is_holiday=True`, `calculate_shift_pay()` agora zera
`overtime_pay` e `night_pay`, aplicando o adicional de 35% uma única vez
sobre `base_pay`. Validado com precisão de 98% contra dois holerites reais
de meses diferentes.

### 🔴 Bug crítico corrigido (relacionado) — turno errado em feriado noturno

Quando o status do dia era `"holiday"`, o sistema sempre assumia **turno
diurno** (08:35-20:35, OT após 18:35) para calcular os horários, mesmo
quando o funcionário trabalha no **turno noturno**. Isso causava cálculo
incorreto de minutos trabalhados em domingos no turno noturno.

**Correção:** novo parâmetro `base_shift` em `calculate_shift_pay()` informa
o turno real do funcionário (`night`/`day`), usado para determinar os
horários corretos independente do dia ser feriado ou não.

### Adicionado
- 9 novos testes automatizados (`TestBugTurnoNoturnoEmFeriado`) validando
  ambos os bugs e a precisão contra holerites reais — total agora 35 testes

### Metodologia de validação (referência futura)
1. Comparar dois holerites reais do mesmo funcionário em meses diferentes
2. Identificar categorias que variam (ex: domingos trabalhados) vs que
   permanecem idênticas (ex: horas normais, hora extra padrão)
3. Isolar o valor por unidade (ex: ¥/domingo) dividindo o total pela
   quantidade, e confirmar que bate entre os dois meses
4. Comparar a fórmula isolada com o que o motor de cálculo produz
5. Ajustar a fórmula no código, não os dados — manter o app genérico

---

## [2.7] — 2026-06-30 — CORREÇÃO CRÍTICA

### 🔴 Bug crítico corrigido — perda total de dados

**Causa raiz identificada:** `page.client_storage` e `page.eval_js`, usados desde o início do projeto para persistir dados (configurações, histórico, calendário, feriados), foram **descontinuados pelo Flet desde a versão 0.80** e não existem mais no Flet 0.85.3. Todas as tentativas de salvar/carregar falhavam silenciosamente (mascaradas por blocos try/except), fazendo o app funcionar **apenas em memória RAM** — qualquer fechamento do navegador apagava tudo: configurações, calendário marcado, histórico de holerites.

**Correção:** sistema de storage reescrito do zero usando `page.shared_preferences`, a API atual e correta do Flet para persistência em Web/PWA/Desktop:
- `main()` convertida para `async def` 
- `boot_load_storage()` agora é `async` e usa `await page.shared_preferences.get()`
- `save_json()` salva no cache em memória instantaneamente e dispara a gravação persistente em segundo plano via `page.run_task()`, sem travar a UI
- `remove_storage()` também usa `await page.shared_preferences.remove()`

**Validado:** testado fechando o Chrome completamente entre sessões no Android — configurações, histórico e dados do calendário agora persistem corretamente.

### Adicionado
- Seção de **🔍 Diagnóstico de Armazenamento** em ⚙️ Config — permite a qualquer usuário verificar se o storage do dispositivo está funcionando corretamente, útil para suporte futuro

---
## [2.6] — 2026-06-30

### Adicionado
- Campos obrigatórios destacados no modal de Histórico — Total Bruto, Total Desconto e Salário Líquido com borda turquesa e ⭐
- Nota explicativa esclarecendo que os demais ~25 campos do Histórico são opcionais
- **test_main.py** — suite de 28 testes automatizados

### Corrigido
- **Bug: histórico perdendo registros ao salvar múltiplos meses seguidos** — funções usavam variável local desatualizada em vez de `state["history"]`
- **Bug: feriado corporativo não afetava o cálculo** — só mudava a cor da célula, não era enviado ao motor de cálculo do holerite
- **Bug: botões 4×2/5×2/Alternado causavam scroll ao topo**
- Validação obrigatória do campo Mês no registro de histórico
- Modal de Histórico reorganizado — campos obrigatórios primeiro, mais espaço para teclado no celular

### Alterado
- Campo Abono renomeado para **"Abono / Vale / Bico extra"** — esclarecido que serve também para arubaito (バイト)

---

## [2.5] — 2026-06-30

### Adicionado
- **Tipo de Ciclo de Trabalho configurável** — 4×2, 5×2 e Alternado Semanal (dia/noite)
- Funções `generate_weekly_calendar()` e `generate_alternating_calendar()`

---

## [2.4] — 2026-06-30

### Adicionado
- Feriados japoneses 2025-2026 embutidos
- Abono / Vale do dia no modal de ponto
- Build ID no header
- Google Analytics
- Saída Antecipada como opção no dropdown
- Domingo Trabalhado com cor própria

### Corrigido
- Bug crítico de cálculo de hora extra na saída antecipada
- Bug de desconto fixo não persistindo na sessão
- `is_legal_holiday` não definido causando erro silencioso

---

## [2.3] — 2026-06-29

### Adicionado
- Minutos extras solicitados (延長)
- Turno configurável (entrada, saída, intervalo, início de hora extra)
- Domingo como 法定休日 com +35% automático
- Disclaimer legal
- Paleta visual Neo Petronas

---

## [2.2] — 2026-06-27

### Adicionado
- Aba de Ajuda com manual completo
- Aba de Feriados Corporativos
- Script de deploy automatizado

---

## [2.1] — 2026-06-26

### Adicionado
- Importação de feriados via CSV
- Calendário com semana iniciando no domingo

---

## [1.0] — 2026-06-24

### Lançamento inicial
- Calendário com ciclo 4×2 automático
- Cálculo de hora extra, adicional noturno e trabalho em feriado
