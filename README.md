# 🧅 Onion Payroll — Gerenciador de Turnos

> **PEEL YOUR PAYCHECK** — PWA para gerenciamento de turnos e previsão salarial para brasileiros trabalhando em fábricas no Japão.

Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo
- **Ciclo 4×2 automático** — projeta 4 dias de trabalho e 2 de folga
- **Turno configurável** — defina entrada, saída, intervalo e início de OT
- **Diurno/Noturno** — campo separado do grupo de equipe
- **Cálculo conforme a lei japonesa:**
  - 残業手当 Hora Extra → +25%
  - 深夜手当 Adicional Noturno → +25% (22:00–05:00)
  - 休出手当 Trabalho em Folga/Feriado → +35%
  - 法定休日 Domingo → +35% automático (folga legal obrigatória)
  - 四捨五入 Arredondamento japonês
- **Minutos extras solicitados** — campo 延長 no registro de ponto
- **有休 Yukyu** — célula laranja, 8h fixo sem OT/noturno
- **欠勤 Falta** — célula roxa, ¥0
- **6 abas:** Calendário · Holerite · Histórico · Feriados · Config. · Ajuda
- **Disclaimer legal** — valores estimados, não substitui holerite oficial

---

## 🎨 Tema Visual

**Neo Petronas** — interface dark premium inspirada em fintechs modernas:

| Token | Cor | Uso |
|---|---|---|
| Fundo | `#121212` | Background principal |
| Card | `#1E1E1E` | Painéis elevados |
| Accent | `#00D2C6` | Turquesa Petronas |
| Texto | `#F0F0F0` | Texto principal |

**Calendário** — paleta Google Calendar:
- 🟢 `#0F9D58` Trabalho · 🔵 `#4285F4` Folga · 🔴 `#DB4437` Feriado
- 🟠 `#FF6D00` Yukyu · 🟡 `#F4B400` Corp. · 🟣 `#7B1FA2` Falta

---

## 📁 Estrutura do Projeto

```
Onion Payroll/
├── main.py                              ← código principal
├── deploy.ps1                           ← script de deploy automático
├── requirements.txt
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── manutencao.html                      ← página de manutenção
├── assets/
│   ├── logo_icon.png                    ← cebola sem fundo (256×256)
│   ├── logo.png                         ← logo completo
│   ├── feriados_japoneses_2025_2026.csv
│   └── feriados_corporativos_modelo.csv
└── docs/                                ← build PWA (gerado pelo deploy.ps1)
```

---

## ⚙️ Instalação

```bash
pip install flet==0.85.3
```

## ▶️ Rodar no Desktop

```bash
cd "Onion Payroll"
python main.py
```

## 🚀 Deploy GitHub Pages

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"
```

O script: cria pasta limpa → build → copia docs/ → push automático.

---

## 🕐 Referência de Turnos

| Turno | Padrão | OT começa | Intervalo |
|---|---|---|---|
| 🌙 Noturno 夜勤 | 20:35 → 08:35 | 06:35 | 65 min |
| ☀️ Diurno 昼勤 | 08:35 → 20:35 | 18:35 | 65 min |

Configurável em ⚙️ Config. → Horário do Turno.

---

## 📄 Formato CSV de Feriados

```
2025-05-03,jp      ← feriado nacional (vermelho)
2025-08-13,corp    ← feriado corporativo (amarelo)
2025-01-01         ← sem tipo = jp
```

---

## 💾 Chaves de Storage

| Chave | Conteúdo |
|---|---|
| `onion_settings` | Valor hora, grupo, turno, horários, âncora |
| `onion_history` | Holerites reais + taxas de desconto |
| `onion_overrides` | Pontos diários por mês |
| `onion_holidays` | Feriados nacionais (CSV) |
| `onion_holidays_corp` | Feriados corporativos (app) |

---

## ⚠️ Aviso Legal

Os valores exibidos são estimativas baseadas nas configurações inseridas pelo usuário. Este aplicativo não substitui o holerite oficial emitido pela empresa. Consulte o departamento de RH para esclarecimentos sobre sua remuneração.

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ 100% offline após primeiro carregamento
- ✅ Dados ficam no dispositivo do usuário

---

## 📜 Licença

Uso pessoal. Desenvolvido para trabalhadores de turno em fábricas japonesas.
