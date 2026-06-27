# 🧅 Onion Payroll — Gerenciador de Turnos

PWA (Progressive Web App) feito em **Python + Flet** para trabalhadores de turno em fábricas no Japão. Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo. Tudo salvo localmente via `localStorage`.
- **Ciclo 4×2 automático** — projeta 4 dias de trabalho e 2 de folga indefinidamente a partir de uma data âncora.
- **Cálculo conforme a lei japonesa:**
  - 残業手当 Hora Extra → +25% (últimas 2h do turno)
  - 深夜手当 Adicional Noturno → +25% (22:00–05:00)
  - 休出手当 Trabalho em Folga/Feriado → +35%
  - Noturno em feriado → acumulado +60%
  - 四捨五入 Arredondamento japonês (frações ≥ 0,5 arredondam para cima)
- **6 abas:** Calendário · Holerite · Histórico · Feriados · Config. · Ajuda
- **Ponto diário** — toque em qualquer dia para registrar horário real, falta ou férias
- **Inteligência de descontos** — aprende a taxa histórica de desconto para prever meses futuros
- **Feriados corporativos** — calendário anual editável direto no app, sem CSV
- **Preview ao vivo** — mostra o cálculo em tempo real ao digitar os horários

---

## 📁 Estrutura do Projeto

```
Onion Payroll/
├── main.py                              ← código principal (lógica + UI)
├── requirements.txt
├── README.md
├── DEPLOY_GITHUB_PAGES.md               ← guia de deploy como PWA
└── assets/
    ├── logo_icon.png                    ← ícone da cebola (256×256)
    ├── logo.png                         ← logo completo
    ├── logo.svg                         ← logo vetorial
    ├── feriados_japoneses_2025_2026.csv ← feriados nacionais
    └── feriados_corporativos_modelo.csv ← modelo de feriados da empresa
```

---

## ⚙️ Instalação

**Requisito:** Python 3.11+ e Flet 0.85.x

```bash
pip install flet==0.85.3
```

---

## ▶️ Rodar no Desktop

```bash
cd "Onion Payroll"
python main.py
```

---

## 🌐 Rodar como Web (rede local)

```bash
flet run --web --port 8550 main.py
```

Acesse no navegador: `http://localhost:8550`
Ou no celular (mesma rede Wi-Fi): `http://IP-DO-PC:8550`

---

## 📱 Deploy como PWA no GitHub Pages

Consulte o guia completo em [`DEPLOY_GITHUB_PAGES.md`](./DEPLOY_GITHUB_PAGES.md).

Resumo:
```bash
# 1. Gerar o build
flet build web --base-url /nome-do-repositorio

# 2. Copiar para docs/
Copy-Item -Path "build\web\*" -Destination "docs\" -Recurse -Force

# 3. Enviar para o GitHub
git add docs/
git commit -m "Deploy PWA"
git push
```

Depois ative em: **GitHub → Settings → Pages → Branch: main / Folder: /docs**

URL final: `https://seu-usuario.github.io/nome-do-repositorio`

---

## 🕐 Referência de Turnos

| Turno | Janela | Hora Extra | Intervalo |
|---|---|---|---|
| Noturno 夜勤 (Grupo B) | 20:35 → 08:35 (+1 dia) | 06:35 – 08:35 | 65 min |
| Diurno 昼勤 (Grupos A e C) | 08:35 → 20:35 | 18:35 – 20:35 | 65 min |

---

## 🎨 Cores do Calendário

| Cor | Significado |
|---|---|
| 🟩 Verde escuro | Dia de trabalho (ciclo 4×2) |
| 🟦 Azul escuro | Folga |
| 🟥 Vermelho escuro | Feriado nacional japonês |
| 🟧 Laranja escuro | Feriado corporativo |
| 🟪 Roxo | Dia modificado (ponto, falta ou férias registrados) |
| Número vermelho | Domingo |
| Número azul | Sábado |

---

## 📄 Formato do CSV de Feriados

```
2025-05-03,jp      ← feriado nacional (vermelho)
2025-08-13,corp    ← feriado corporativo (laranja)
2025-01-01         ← sem tipo = jp por padrão
```

Importe em: **⚙️ Config. → Importar Calendário da Fábrica (.csv)**

---

## 🏗️ Arquitetura do Código

A lógica de negócio é **totalmente separada** da interface:

| Função | Descrição |
|---|---|
| `shisha_gofuuu()` | Arredondamento 四捨五入 (retorna inteiro) |
| `calculate_shift_pay()` | Calcula pagamento de um único dia |
| `generate_4x2_calendar()` | Gera o ciclo 4×2 para um mês |
| `compute_monthly_forecast()` | Agrega todos os dias do mês |
| `night_minutes_in_range()` | Conta minutos entre 22:00 e 05:00 |
| `boot_load_storage()` | Carrega dados persistidos no startup |

---

## 💾 Chaves de Storage

Todos os dados são salvos localmente em JSON:

| Chave | Conteúdo |
|---|---|
| `onion_settings` | Valor hora, grupo, data âncora, modo de desconto |
| `onion_history` | Holerites reais registrados + taxas de desconto |
| `onion_overrides` | Pontos diários registrados por mês |
| `onion_holidays` | Feriados nacionais importados via CSV |
| `onion_holidays_corp` | Feriados corporativos marcados no app |

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ Dados ficam 100% no dispositivo do usuário
- ✅ Funciona offline após o primeiro carregamento
- ⚠️ Limpar dados do navegador apaga o histórico — use o backup via Git

---

## 📜 Licença

Uso pessoal. Desenvolvido para trabalhadores de turno em fábricas japonesas.
