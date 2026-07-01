# Changelog — Onion Payroll

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
