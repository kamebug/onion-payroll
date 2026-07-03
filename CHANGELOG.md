# Changelog — Onion Payroll

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
