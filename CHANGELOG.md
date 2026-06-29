# Changelog — Onion Payroll

## [2.3] — 2026-06-29
### Adicionado
- Campo **延長 Minutos extras solicitados** no modal de ponto
- **Turno configurável** — entrada, saída, intervalo e início de OT personalizáveis
- Campo **Turno** (🌙 Noturno / ☀️ Diurno) separado do Grupo de equipe
- **Domingo como 法定休日** — +35% automático independente do ciclo 4×2
- **Disclaimer legal** — aviso em Holerite e aba Ajuda
- **有休 Yukyu** na lista do dropdown de ponto com descrição clara
- Efeitos visuais: `BoxShadow` nos cards, `gradient` no header, `animate_opacity` nas abas, `blur` nos overlays, `animate_scale` nos modais

### Alterado
- **Paleta Neo Petronas** — `#121212` / `#1E1E1E` / `#00D2C6` turquesa
- **Calendário** — cores Google Calendar: verde `#0F9D58`, azul `#4285F4`, vermelho `#DB4437`
- **Yukyu** — célula laranja `#FF6D00`, 8h fixo sem OT/noturno
- **Falta** — célula roxa `#7B1FA2`
- **Células do calendário** — cor muda conforme status (não só o número)
- Legenda em 2 colunas, sem fundo escuro
- Subtítulo alterado para **"PEEL YOUR PAYCHECK"**
- Header com gradient escuro → turquesa
- Texto "ONION" branco + "PAYROLL" turquesa

### Corrigido
- Bug: scroll do modal de histórico cobria os campos — resolvido com `_padded_row()`
- Bug: `CAL_BORDER_MODIF` não definido causava erro ao abrir app
- Bug: célula do calendário não mudava de cor ao marcar status

---

## [2.2] — 2026-06-27
### Adicionado
- Aba ❓ Ajuda com manual completo
- Aba 🏭 Feriados Corporativos — calendário anual editável
- Script `deploy.ps1` automático
- Página `manutencao.html`
- Preview ao vivo no modal de ponto
- Storage universal: desktop + web + PWA

### Corrigido
- Todos os modais migrados para `page.overlay`
- Yukyu parcial com horário calcula horas reais
- Desconto 0 não usava mais 25% como padrão

---

## [2.1] — 2026-06-26
### Adicionado
- Campo turno noturno/diurno
- Importação de CSV via textarea (compatível com PWA)
- Feriados nacionais e corporativos

### Alterado
- Semana começa no domingo
- Dom=vermelho, Sáb=azul no cabeçalho

---

## [1.0] — 2026-06-24
### Inicial
- Calendário 4×2 automático
- Cálculo 残業, 深夜, 休出
- 4 abas: Calendário, Holerite, Histórico, Config.
- Storage via localStorage
