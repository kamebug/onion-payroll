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

**Total: 31 testes, cobrindo o motor de cálculo inteiro.**

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
| Teclado do celular cobria campos no modal | Modal centralizado verticalmente, sem espaço reservado | 2.6 | Abrir modal de Histórico no celular, tocar em campo perto do fim |

---

## 📋 Processo recomendado para novos problemas

1. **Se for de cálculo** (números errados, lógica de negócio) →
   adicionar teste em `test_main.py` na classe apropriada
2. **Se for de UX/interface** (scroll, persistência, layout) →
   documentar aqui em "NÃO cobertos", já que não há teste automatizado
   confiável possível sem infraestrutura de browser automation
   (Selenium/Playwright, fora do escopo atual do projeto)
3. **Sempre** registrar a correção no `CHANGELOG.md` com a versão

---

## 🔮 Possível melhoria futura (não implementada)

Para cobrir os problemas de UX automaticamente, seria necessário
configurar testes end-to-end com **Playwright** ou **Selenium**
controlando um navegador real apontando para o app rodando localmente.
Isso é significativamente mais complexo de manter que `unittest` puro
e não foi implementado por ora — os testes manuais documentados acima
são o processo atual.
