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

**Total: 40 testes, cobrindo o motor de cálculo inteiro.**

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

**Lição para o processo:** ao adicionar uma nova classe de teste, sempre
confirmar que `unittest.main()` está no **final real do arquivo** — não
basta ver "OK" na saída, é preciso conferir se o número de testes rodados
bate com o esperado.

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

---

## 🔮 Possível melhoria futura (não implementada)

Para cobrir os problemas de UX automaticamente, seria necessário
configurar testes end-to-end com **Playwright** ou **Selenium**
controlando um navegador real apontando para o app rodando localmente.
Isso é significativamente mais complexo de manter que `unittest` puro
e não foi implementado por ora — os testes manuais documentados acima
são o processo atual.
