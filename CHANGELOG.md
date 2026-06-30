# Changelog — Onion Payroll

## [2.6] — 2026-06-30

### Adicionado
- **Campos obrigatórios destacados** no modal de Histórico — Total Bruto, Total Desconto e Salário Líquido agora têm borda turquesa e ícone ⭐, deixando claro que só esses 3 campos são essenciais para o cálculo da Média Histórica de desconto
- Nota explicativa no topo do modal de Histórico esclarecendo que os demais ~25 campos são opcionais (apenas registro pessoal)
- **test_main.py** — suite de 26 testes automatizados cobrindo cálculo de hora extra, ciclos, descontos, feriados, domingo, falta, yukyu, abono e formatação de horário

### Corrigido
- **Bug: botões 4×2/5×2/Alternado causavam scroll ao topo** — agora alternam a visibilidade das seções diretamente em vez de reconstruir a aba inteira com `refresh_all()`
- Ordem de criação dos campos de turno corrigida (estavam sendo referenciados antes de existir)

### Alterado
- Campo **Abono** no modal de ponto renomeado para **"Abono / Vale / Bico extra"** — esclarecido que serve também para registrar ganhos de arubaito (バイト), gorjetas ou qualquer valor extra do dia

---

## [2.5] — 2026-06-30

### Adicionado
- **Tipo de Ciclo de Trabalho configurável** — botões em ⚙️ Config:
  - **4×2** (padrão) — 4 dias trabalho + 2 folga
  - **5×2** — segunda a sexta, fim de semana livre (turno comercial)
  - **Alternado Semanal** — 1 semana inteira diurno + 1 semana inteira noturno, alternando automaticamente
- Funções `generate_weekly_calendar()` e `generate_alternating_calendar()`
- Campos de horário separados para turno Dia/Noite no modo Alternado

### Corrigido
- Validação cruzada confirmou que não há regressão nos fluxos: preenchimento de campos, scroll, formatação automática de horário e cálculo

---

## [2.4] — 2026-06-30

### Adicionado
- **Feriados japoneses 2025-2026 embutidos** — aparecem automaticamente sem importar CSV
- **Abono / Vale do dia** — campo no modal de ponto, acumulado no holerite
- **Build ID** no header — número único a cada deploy (gerado pelo `deploy.ps1`)
- **Google Analytics G-2Z4173R5NS** — acompanhamento de acessos
- **Saída Antecipada** como opção no dropdown do modal de ponto
- **Domingo Trabalhado** — célula vermelha escura automática quando ciclo=work
- Campos de horas no histórico aceitam decimal (ex: 155.5)

### Corrigido
- **Bug crítico: OT na saída antecipada** — `minutes_between` retornava positivo incorreto causando hora extra falsa quando o funcionário saía antes do horário normal
- **Bug crítico: desconto fixo não persistia** — `refresh_all` recriava settings perdendo mudanças do usuário
- **Bug crítico: `is_legal_holiday` não definido** — causava erro silencioso zerando todo o cálculo do holerite
- `day_abono` não definido no loop do forecast
- Dropdown de desconto substituído por botões (Flet 0.85 não dispara `on_change` em Dropdown de forma confiável)
- Settings agora fazem merge com DEFAULT_SETTINGS no boot
- Contraste do número do domingo trabalhado — branco sobre vermelho escuro

### Alterado
- Desconto configurável via botões **Média Histórica / Desconto Fixo**
- Campos de bônus centralizados em ⚙️ Config (removidos da aba Holerite)
- Holerite discrimina **Feriado** e **Domingo** separadamente, com contagem de dias
- `refresh_all` usa cache em memória em vez de recarregar do storage a cada chamada

---

## [2.3] — 2026-06-29

### Adicionado
- Campo **延長 Minutos extras solicitados** no modal de ponto
- **Turno configurável** — entrada, saída, intervalo e início de hora extra
- Campo **Turno** (🌙 Noturno / ☀️ Diurno) separado do Grupo
- **Domingo como 法定休日** — adicional de +35% automático
- **Disclaimer legal** no Holerite e na aba Ajuda
- Efeitos visuais: sombra nos cards, gradiente no header, fade na troca de abas, blur nos modais

### Alterado
- Paleta **Neo Petronas** — fundo `#121212`, cards `#1E1E1E`, destaque turquesa `#00D2C6`
- Calendário com paleta inspirada no Google Calendar
- Subtítulo do app: **"PEEL YOUR PAYCHECK"**
- Células do calendário mudam de cor conforme o status do dia

### Corrigido
- Scroll do modal de histórico cobria os campos
- Variável de borda do calendário não definida, causando erro ao abrir o app

---

## [2.2] — 2026-06-27

### Adicionado
- Aba ❓ Ajuda com manual completo de uso
- Aba 🏭 Feriados Corporativos com calendário anual editável
- Script `deploy.ps1` para automatizar build e publicação
- Preview ao vivo dos valores no modal de ponto
- Sistema de storage universal funcionando em desktop, web e PWA

### Corrigido
- Modais migrados para `page.overlay`, resolvendo problemas de sobreposição
- Cálculo de yukyu parcial com horário registrado

---

## [2.1] — 2026-06-26

### Adicionado
- Importação de feriados via CSV colado em campo de texto
- Suporte a feriados nacionais e corporativos
- Calendário com semana iniciando no domingo

---

## [1.0] — 2026-06-24

### Lançamento inicial
- Calendário com ciclo 4×2 automático
- Cálculo de hora extra, adicional noturno e trabalho em feriado
- Quatro abas: Calendário, Holerite, Histórico e Configurações
