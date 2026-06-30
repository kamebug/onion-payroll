# Changelog — Onion Payroll

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
