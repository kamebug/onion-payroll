# 🧅 Onion Payroll

> **PEEL YOUR PAYCHECK** — PWA para gerenciamento de turnos e previsão salarial para brasileiros trabalhando em fábricas no Japão.

Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

🌐 **https://kamebug.github.io/onion-payroll/**

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo
- **Persistência confiável** — dados sobrevivem ao fechar o navegador (via `shared_preferences`)
- **Três tipos de ciclo de trabalho:**
  - 🔄 **4×2** — 4 dias trabalho + 2 folga (padrão fábricas com turno fixo)
  - 📅 **5×2** — segunda a sexta (turno comercial)
  - 🔁 **Alternado Semanal** — 1 semana diurno + 1 semana noturno, automaticamente
- **Turno configurável** — defina entrada, saída, intervalo e início de hora extra
- **Feriados japoneses 2025-2026 embutidos** — aparecem automaticamente
- **Feriados corporativos** afetam o cálculo, não só a cor do calendário
- **Cálculo conforme a lei japonesa:**
  - 残業手当 Hora Extra → +25%
  - 深夜手当 Adicional Noturno → +25% (22:00–05:00)
  - 休出手当 Trabalho em Folga/Feriado → +35%
  - 法定休日 Domingo → +35% automático
  - 四捨五入 Arredondamento japonês
- **Modal de ponto completo:**
  - 有休 Yukyu — laranja, 8h fixo sem hora extra/noturno
  - 欠勤 Falta — roxo, ¥0
  - Saída Antecipada — verde-azulado, calcula pelo horário real
  - 延長 Minutos extras solicitados
  - Abono / Vale / Bico extra — também serve para registrar arubaito (バイト)
- **Histórico editável** — toque em qualquer registro para editar ou remover
- **Holerite discriminado** — dias normais, feriado e domingo mostrados separadamente
- **Desconto configurável** — Média Histórica (automática) ou Fixo em ¥
- **Diagnóstico de armazenamento** integrado em ⚙️ Config para suporte
- **Build ID** no header — confirma se a versão está atualizada
- **Google Analytics** — acompanhamento de acessos

---

## ⚙️ Instalação e Uso

```bash
pip install flet==0.85.3
python main.py
```

### Rodar os testes automatizados

```bash
python test_main.py
```

28 testes cobrindo cálculo de hora extra, ciclos de trabalho, descontos, feriados (nacionais e corporativos), domingo, falta, yukyu, abono e formatação de horário. Recomendado antes de cada deploy.

### Deploy GitHub Pages

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"
```

---

## 🔧 Detalhes Técnicos — Persistência de Dados

O app usa **`page.shared_preferences`** (API assíncrona atual do Flet ≥ 0.80) para salvar dados localmente no dispositivo do usuário:

```python
await page.shared_preferences.set(key, value)
value = await page.shared_preferences.get(key)
```

`main()` é uma função `async`, e o boot do app aguarda (`await`) o carregamento completo dos dados salvos antes de montar a interface, garantindo que nada seja perdido.

**Atenção para desenvolvedores:** as APIs antigas `page.client_storage` e `page.eval_js` foram descontinuadas e **não devem ser usadas** — causam falha silenciosa de persistência no Flet 0.85+.

---

## 🕐 Referência de Turnos

### 4×2 e 5×2
| Turno | Entrada | Saída | OT começa | Intervalo |
|---|---|---|---|---|
| 🌙 Noturno | 20:35 | 08:35 | 06:35 | 65 min |
| ☀️ Diurno | 08:35 | 20:35 | 18:35 | 65 min |

### Alternado Semanal
Configure os dois horários (dia e noite) em ⚙️ Config. — o app alterna automaticamente a cada semana a partir da Data de Início do Ciclo.

---

## 📋 Registro de Holerite Real

Apenas três campos são obrigatórios para o cálculo de Média Histórica:

| Campo | Uso |
|---|---|
| ⭐ 総支給額 Total Bruto | Base do cálculo |
| ⭐ 控除合計 Total Desconto | Base do cálculo |
| ⭐ 差引支給額 Salário Líquido | Conferência |

Os demais ~25 campos são opcionais — apenas registro pessoal.

---

## 📁 Estrutura do Projeto

```
Onion Payroll/
├── main.py
├── test_main.py
├── deploy.ps1
├── requirements.txt
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── manutencao.html
├── assets/
└── docs/                     ← build PWA (gerado pelo deploy.ps1)
```

---

## ⚠️ Aviso Legal

Os valores exibidos são estimativas baseadas nas configurações inseridas pelo usuário. Este aplicativo não substitui o holerite oficial emitido pela empresa. Consulte o departamento de RH para esclarecimentos sobre sua remuneração.

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ 100% offline após primeiro carregamento
- ✅ Dados ficam no dispositivo do usuário, persistidos via `shared_preferences`

---

## 🧪 Qualidade

O motor de cálculo é coberto por 28 testes automatizados (`test_main.py`).
