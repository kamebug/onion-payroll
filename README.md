# 🧅 Onion Payroll

> **PEEL YOUR PAYCHECK** — PWA para gerenciamento de turnos e previsão salarial para brasileiros trabalhando em fábricas no Japão.

Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

🌐 **https://kamebug.github.io/onion-payroll/**

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo
- **Ciclo 4×2 automático** — projeta 4 dias de trabalho e 2 de folga
- **Turno configurável** — defina entrada, saída, intervalo e início de OT
- **Diurno/Noturno** — campo separado do grupo de equipe
- **Feriados japoneses 2025-2026 embutidos** — aparecem automaticamente
- **Cálculo conforme a lei japonesa:**
  - 残業手当 Hora Extra → +25%
  - 深夜手当 Adicional Noturno → +25% (22:00–05:00)
  - 休出手当 Trabalho em Folga/Feriado → +35%
  - 法定休日 Domingo → +35% automático
  - 四捨五入 Arredondamento japonês
- **Modal de ponto completo:**
  - 有休 Yukyu — laranja, 8h fixo
  - 欠勤 Falta — roxo, ¥0
  - Saída Antecipada — verde-azulado, horário real
  - 延長 Minutos extras solicitados
  - Abono / Vale do dia
- **Holerite discriminado** — dias normais / feriado / domingo separados
- **Desconto configurável** — Média Histórica ou Fixo em ¥
- **Build ID** no header — confirma versão atualizada
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
| 🟡 `#F4B400` | Feriado Corporativo |
| 🟠 `#FF6D00` | 有休 Yukyu |
| 🟣 `#7B1FA2` | 欠勤 Falta |
| 🩵 `#00796B` | Saída Antecipada |

---

## ⚙️ Instalação e Uso

```bash
pip install flet==0.85.3
python main.py
```

### Deploy GitHub Pages

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"
```

---

## 🕐 Referência de Turnos

| Turno | Entrada | Saída | OT começa | Intervalo |
|---|---|---|---|---|
| 🌙 Noturno | 20:35 | 08:35 | 06:35 | 65 min |
| ☀️ Diurno | 08:35 | 20:35 | 18:35 | 65 min |

Configurável em ⚙️ Config. → Horário do Turno.

---

## ⚠️ Aviso Legal

Os valores exibidos são estimativas baseadas nas configurações inseridas pelo usuário. Este aplicativo não substitui o holerite oficial emitido pela empresa. Consulte o departamento de RH para esclarecimentos sobre sua remuneração.

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ 100% offline após primeiro carregamento
- ✅ Dados ficam no dispositivo do usuário
