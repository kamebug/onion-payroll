# Changelog — Onion Payroll

## [2.4] — 2026-06-30

### Adicionado
- **Feriados japoneses 2025-2026 embutidos** — aparecem automaticamente sem importar CSV
- **Abono / Vale do dia** — campo no modal de ponto, acumulado no holerite
- **Build ID** no header — número único a cada deploy para confirmar versão
- **Google Analytics G-2Z4173R5NS** — acompanhamento de acessos
- **Saída Antecipada** como opção no dropdown do modal de ponto
- **Domingo Trabalhado** — célula vermelha escura automática quando ciclo=work
- Feriados nacionais e corporativos unificados em tipo único no calendário
- Campos de horas no histórico aceitam decimal (ex: 155.5)

### Corrigido
- **Bug crítico: OT na saída antecipada** — `minutes_between` retornava positivo incorreto causando OT falso
- **Bug crítico: desconto fixo não persistia** — `refresh_all` recriava settings perdendo mudanças
- **Bug crítico: `is_legal_holiday` não definido** — causava NameError silencioso zerando o cálculo
- **`day_abono` não definido** no loop do forecast
- Dropdown de desconto substituído por botões (Flet 0.85 não dispara `on_change` em Dropdown)
- Settings merge com DEFAULT_SETTINGS no boot — campos novos aparecem sem reset
- Contraste número do domingo trabalhado — branco sobre vermelho escuro

### Alterado
- Desconto configurável via botões **Média Histórica / Desconto Fixo** em vez de dropdown
- Campos de bônus centralizados em ⚙️ Config (removidos do holerite)
- Holerite discrimina **Feriado** e **Domingo** separadamente com contagem de dias
- `refresh_all` usa `_mem_cache` em vez de recarregar do storage

---

## [2.3] — 2026-06-29

### Adicionado
- Campo **延長 Minutos extras solicitados** no modal de ponto
- **Turno configurável** — entrada, saída, intervalo e início de OT
- Campo **Turno** (🌙/☀️) separado do Grupo
- **Domingo como 法定休日** — +35% automático
- **Disclaimer legal** no Holerite e aba Ajuda
- Efeitos visuais: BoxShadow, gradient header, animate_opacity, blur, animate_scale

### Alterado
- Paleta **Neo Petronas** — `#121212` / `#1E1E1E` / `#00D2C6`
- Calendário com paleta Google Calendar
- Subtítulo **"PEEL YOUR PAYCHECK"**
- Células mudam de cor conforme status

### Corrigido
- Scroll modal histórico cobria campos
- `CAL_BORDER_MODIF` não definido

---

## [2.2] — 2026-06-27

### Adicionado
- Aba ❓ Ajuda com manual completo
- Aba 🏭 Feriados Corporativos
- Script `deploy.ps1` automático
- Preview ao vivo no modal de ponto
- Storage universal: desktop + web + PWA

### Corrigido
- Modais migrados para `page.overlay`
- Yukyu parcial com horário calcula horas reais

---

## [2.1] — 2026-06-26

### Adicionado
- Importação CSV via textarea
- Feriados nacionais e corporativos
- Semana começa no domingo

---

## [1.0] — 2026-06-24

### Inicial
- Calendário 4×2 automático
- Cálculo 残業, 深夜, 休出
- 4 abas: Calendário, Holerite, Histórico, Config.
