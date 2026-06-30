# 🧅 Onion Payroll

> **PEEL YOUR PAYCHECK** — PWA para gerenciamento de turnos e previsão salarial para brasileiros trabalhando em fábricas no Japão.

Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

🌐 **https://kamebug.github.io/onion-payroll/**

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo
- **Três tipos de ciclo de trabalho:**
  - 🔄 **4×2** — 4 dias trabalho + 2 folga (padrão fábricas com turno fixo)
  - 📅 **5×2** — segunda a sexta (turno comercial)
  - 🔁 **Alternado Semanal** — 1 semana diurno + 1 semana noturno, automaticamente
- **Turno configurável** — defina entrada, saída, intervalo e início de hora extra
- **Feriados japoneses 2025-2026 embutidos** — aparecem automaticamente
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
- **Holerite discriminado** — dias normais, feriado e domingo mostrados separadamente
- **Desconto configurável** — Média Histórica (automática) ou Fixo em ¥
- **Registro de holerite real simplificado** — apenas 3 campos são obrigatórios (Total Bruto, Total Desconto, Líquido); o restante é opcional para registro pessoal
- **Build ID** no header — confirma se a versão está atualizada
- **Google Analytics** — acompanhamento de acessos

---

## 🎨 Tema Visual — Neo Petronas

| Token | Cor | Uso |
|---|---|---|
| Fundo | `#121212` | Background principal |
| Card | `#1E1E1E` | Painéis elevados |
| Accent | `#00D2C6` | Turquesa Petronas |
| Texto | `#F0F0F0` | Texto principal |

**Calendário — Paleta Google Calendar:**
| Cor | Tipo |
|---|---|
| 🟢 `#0F9D58` | Trabalho |
| 🔵 `#4285F4` | Folga |
| 🔴 `#C62828` | Domingo Trabalhado |
| 🟡 `#F4B400` | Feriado |
| 🟠 `#FF6D00` | 有休 Yukyu |
| 🟣 `#7B1FA2` | 欠勤 Falta |
| 🩵 `#00796B` | Saída Antecipada |

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

Roda 26 testes cobrindo cálculo de hora extra, ciclos de trabalho, descontos, feriados, domingo, falta, yukyu, abono e formatação de horário — sem precisar abrir o app. Recomendado antes de cada deploy.

### Deploy GitHub Pages

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"
```

O script gera um novo Build ID, faz o build limpo, copia para `docs/`, mantém o Google Analytics configurado e faz o push automaticamente.

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

Para que o cálculo de **Média Histórica** de desconto funcione, apenas três campos são obrigatórios:

| Campo | Uso |
|---|---|
| ⭐ 総支給額 Total Bruto | Base do cálculo |
| ⭐ 控除合計 Total Desconto | Base do cálculo |
| ⭐ 差引支給額 Salário Líquido | Conferência |

Os demais ~25 campos (dias de frequência, horas detalhadas, valores por categoria) são **opcionais** — servem apenas como registro pessoal de referência e não influenciam nenhum cálculo do app.

---

## 📁 Estrutura do Projeto

```
Onion Payroll/
├── main.py                  ← código principal
├── test_main.py              ← suite de testes automatizados
├── deploy.ps1                ← script de deploy automático
├── requirements.txt
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── manutencao.html
├── assets/
│   ├── logo_icon.png
│   └── feriados_corporativos_modelo.csv
└── docs/                     ← build PWA (gerado pelo deploy.ps1)
```

---

## ⚠️ Aviso Legal

Os valores exibidos são estimativas baseadas nas configurações inseridas pelo usuário. Este aplicativo não substitui o holerite oficial emitido pela empresa. Consulte o departamento de RH para esclarecimentos sobre sua remuneração.

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ 100% offline após primeiro carregamento
- ✅ Dados ficam no dispositivo do usuário

---

## 🧪 Qualidade

O motor de cálculo é coberto por 26 testes automatizados (`test_main.py`), validando ciclos de trabalho, descontos, feriados, domingos e casos extremos (saída antecipada, falta, yukyu, abono). Rode antes de cada deploy para garantir que nenhuma regra de negócio foi quebrada.
