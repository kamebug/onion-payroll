# Changelog — Onion Payroll

## [2.2] — 2026-06-27
### Alterado
- Novo tema visual: fundo claro, header e nav escuros
- Turquesa como cor de destaque principal
- Calendário com cores claras e de alta legibilidade

### Corrigido
- Aba Holerite não abria quando campo de desconto estava vazio
- Desconto em ¥0 agora exibe corretamente sem valor padrão de 25%
- Nota de desconto mais clara: indica modo ativo e origem do valor
- Aba Feriados não voltava mais ao topo a cada clique

---

## [2.1] — 2026-06-26
### Adicionado
- Aba ❓ Ajuda com manual completo de uso em português
- Aba 🏭 Feriados Corporativos — calendário anual editável diretamente no app
- Página de manutenção (`manutencao.html`) para uso durante atualizações
- Script de deploy automático (`deploy.ps1`)
- Suporte a feriados nacionais (jp) e corporativos (corp) no CSV
- Preview ao vivo do cálculo no modal de ponto diário

### Alterado
- Subtítulo alterado para "DESCASQUE SEU SALÁRIO"
- Importação de CSV substituída por textarea (compatível com PWA)
- Scroll do modal de holerite com padding para não cobrir campos
- Janela configurada como redimensionável

### Corrigido
- Yukyu parcial: com horário preenchido calcula horas reais (sem OT/noturno)
- Saída antecipada: hora extra só se ultrapassar o limiar
- Todos os modais migrados para `page.overlay` (compatível com Flet 0.85)
- `ft.IconButton` substituído por `ft.TextButton` com símbolos unicode
- Ícones da nav convertidos para emojis (compatível com Flet 0.85)

---

## [2.0] — 2026-06-25
### Adicionado
- Tema Neo Corporate (paleta escura inicial)
- Semana começa no domingo
- Dom=vermelho, Sáb=azul no cabeçalho do calendário
- Suporte a `page.overlay` para modais
- Storage universal: desktop + servidor web + PWA/WASM

### Alterado
- Repositório recriado do zero (limpeza de histórico com arquivos grandes)
- README traduzido para português brasileiro completo

---

## [1.0] — 2026-06-24
### Inicial
- Calendário 4×2 automático
- Cálculo de hora extra, adicional noturno e trabalho em feriado
- Arredondamento 四捨五入 (Shisha Gofuuu)
- 4 abas: Calendário, Holerite, Histórico, Configurações
- Storage via localStorage (PWA)
- Logo Onion Payroll
