# Changelog — Onion Payroll

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
