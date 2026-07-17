# 🧅 Onion Payroll

> **PEEL YOUR PAYCHECK** — PWA para gerenciamento de turnos e previsão salarial para brasileiros trabalhando em fábricas no Japão.

Calcula automaticamente salário base, hora extra, adicional noturno e trabalho em feriados conforme a **Lei Trabalhista Japonesa (労働基準法)**.

🌐 **https://kamebug.github.io/onion-payroll/**

---

## ✨ Funcionalidades

- **100% offline e privado** — nenhum dado sai do dispositivo
- **Persistência confiável** — dados sobrevivem ao fechar o navegador (via `shared_preferences`)
- **Quatro tipos de ciclo de trabalho:**
  - 🔄 **4×2** — 4 dias trabalho + 2 folga (padrão fábricas com turno fixo). **Grupo A/B/C**: selecione seu grupo, depois digite a data — aquele dia vira o 1º dia de trabalho DESSE grupo. Trocar de grupo depois, sem mexer na data, ajusta o calendário sozinho (relação de 2 dias entre turmas, validada contra escala real da fábrica — nunca duas turmas de folga no mesmo dia)
  - 📅 **5×2** — segunda a sexta (turno comercial)
  - 🔁 **Alternado Semanal** — 1 semana diurno + 1 semana noturno, automaticamente
  - 🔁 **Alternado Mensal** — 1 mês diurno + 1 mês noturno, com padrão de folga configurável (5×2 fim de semana, ou 4×2 com Grupo A/B/C)
- **Turno configurável** — defina entrada, saída, intervalo e início de hora extra
- **Feriados japoneses se atualizam sozinhos** — buscados automaticamente uma vez por ano (GitHub Action + fonte oficial do governo), com reserva embutida se estiver offline. Aparecem com moldura vermelha no calendário e nome completo (japonês/romaji/português) ao tocar no dia
- **Feriados corporativos** afetam o cálculo, não só a cor do calendário
- **Cálculo conforme a lei japonesa:**
  - 残業手当 Hora Extra → +25%
  - 深夜手当 Adicional Noturno → +25% (22:00–05:00)
  - 休出手当 Trabalho em Folga/Feriado → +35%
  - 法定休日 Domingo → +35% automático
  - 四捨五入 Arredondamento japonês — aplicado à taxa por hora, antes de multiplicar pelas horas
- **Modo de Arredondamento configurável** — "Sempre pra Cima" (padrão) ou "Regra do 0,5" (clássica), aplicado à taxa por hora de base, extra, noturno e feriado
- **Adicional de Líder no arredondamento** — para empresas que separam jikyuu e adicional fixo mensal em duas parcelas arredondadas individualmente no cálculo de hora extra/noturno/domingo, reaproveitando o campo de Adicional Fixo Mensal já existente. Escondido atrás de um switch desligado por padrão — não polui a tela de quem não precisa
- **Abono Mensal separado** — soma automaticamente no bruto todo mês, igual ao Adicional Fixo Mensal, mas nunca entra no cálculo de arredondamento de extra/noturno/domingo
- **Mudança de 時給 sem afetar meses passados** — registre no Histórico o mês em que um aumento de salário começou; a previsão de meses anteriores continua usando o 時給 antigo automaticamente
- **Desconto real substitui a previsão** — mês com holerite real registrado no Histórico usa o valor de desconto conhecido, em vez de estimar via Média Histórica/Fixo
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
- **Compartilhar o app** — QR code + link copiável + vídeo de apresentação (30s) na aba ❓ Ajuda, pra indicar pra colegas
- **Interface bilíngue nos botões de status** — português como texto principal, japonês como legenda (pra localizar a rubrica no holerite real)
- **Direito a Yukyu calculado automaticamente** — a partir da Data de Admissão, segue a progressão da Lei Trabalhista Japonesa (Art. 39: 6m=10, 1a6m=11 ... 6a6m+=20 dias), com expiração de 2 anos (Art. 115) e desconto automático a cada dia marcado como Yukyu no calendário
- **Configuração guiada por etapas** — ⚙️ Config em wizard: tipo de ciclo → horário do turno → grupo (só no 4×2) → salário. Cada etapa só aparece depois da anterior fazer sentido

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

119 testes cobrindo cálculo de hora extra, ciclos de trabalho (incluindo o deslocamento entre turmas Grupo A/B/C), descontos, feriados (nacionais e corporativos), domingo, falta, yukyu, abono, formatação de horário e arredondamento por categoria — validados contra 5 holerites reais. Recomendado antes de cada deploy.

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

### Alternado Mensal
Mesma configuração de horários do Alternado Semanal (dia e noite), mas a
alternância é mensal — configure a **Data de Referência — Mês Diurno**
(qualquer dia do primeiro mês trabalhado de dia). Escolha também o
**Padrão de Folga**:
- **5×2** — folga sábado/domingo (padrão)
- **4×2** — folga em blocos de 4+2 dias, com Grupo A/B/C e sua própria
  Data de Início do Ciclo (independente da Data de Referência — Mês
  Diurno)

---

## 🌴 Direito a Yukyu (有給休暇)

Configure a **Data de Admissão** em ⚙️ Config (separada da "Data de
Início do Ciclo", que é sobre o turno) e o app calcula automaticamente
seu saldo de Yukyu, seguindo o Art. 39 da Lei Trabalhista Japonesa.
Pode digitar sem hífen (`20260703`, `2026/07/03`, `2026.7.3`) — o campo
normaliza sozinho para AAAA-MM-DD:

```
6 meses de empresa → 10 dias
1 ano e 6 meses    → 11 dias
2 anos e 6 meses   → 12 dias
3 anos e 6 meses   → 14 dias
4 anos e 6 meses   → 16 dias
5 anos e 6 meses   → 18 dias
6 anos e 6 meses+  → 20 dias (teto, todo ano depois disso)
```

Cada concessão expira **2 anos** depois de ser dada (Art. 115) — o app
consome o saldo mais antigo primeiro, pra não desperdiçar dias prestes
a vencer. Toda vez que você marca um dia como "Folga Remunerada 有休"
no calendário, o saldo desconta automaticamente. O resumo mostra só as
concessões **ainda ativas** (não expiradas), cada uma com a data exata
(ex: `2026-05-01: +10d, expira 2028-05-01`), e uma linha de "Próxima
expiração" — sem listar o histórico completo desde a admissão.

**Limitações desta versão:**
- Cobre só a tabela cheia (5+ dias/semana) — não calcula o proporcional
  de part-time (比例付与)
- Não verifica a regra de 80% de presença no período aquisitivo — assume
  que você tem direito

---

## 🔢 Arredondamento

Dois mecanismos diferentes, independentes entre si:

**1. Arredondamento do Ponto** (⚙️ Config, opcional) — arredonda os
minutos trabalhados em blocos de 15 ou 30 min, com regra "Truncar"
(sempre pra baixo) ou "Mais Próximo". Só importa perto da borda entre
blocos: 22min em blocos de 15 vira 15min nos dois modos; 23min vira
15min truncando mas 30min no modo "mais próximo".

**2. Arredondamento da Taxa por Hora** (⚙️ Config → "Modo de
Arredondamento") — a taxa (時給 × multiplicador) é arredondada para o
yen **antes** de multiplicar pelas horas, não depois. Duas opções:

- **Sempre pra Cima** (padrão a partir da v2.49) — arredonda pra cima
  sem exceção, mesmo com centavos baixos (ex: 22,01 → 23)
- **Regra do 0,5** (comportamento anterior) — 0,5 sempre sobe, resto
  trunca

Exemplo com "Sempre pra Cima" (時給=¥1.430, 30h de hora extra):

```
Taxa bruta = 1.430 × 1,25 = 1.787,50 ¥/hora
Arredondada = 1.788 ¥/hora  (sempre pra cima)
Total = 1.788 × 30 = ¥53.640
```

---

## 📈 Arredondamento com Adicional de Líder

Algumas empresas calculam Hora Extra, Noturno e Domingo/Feriado usando
uma taxa por hora **maior** que o 時給 puro, incluindo o Adicional de
Líder (ou similar) — com o jikyuu e o acréscimo do adicional
arredondados **separadamente**, não somados numa taxa só.

Em ⚙️ Config → **"Usar Adicional de Líder no Arredondamento"** (switch
desligado por padrão — a maioria não precisa mexer aqui), é possível
ativar esse cálculo. Reaproveita o valor já configurado em "Adicional
Fixo Mensal — Líder" (o mesmo que soma no bruto do mês) — não precisa
preencher em dois lugares.

### Exemplo real (confirmado por RH)

時給=¥1.590, Adicional de Líder=¥3.000/mês, Horas Padrão=168h, 33h de
hora extra:

```
1) Taxa do jikyuu:     1.590 × 1,25              = ¥1.988 (arredondado)
2) Taxa do adicional:  (3.000 ÷ 168) × 1,25       = ¥23    (arredondado)
3) Taxa final:         1.988 + 23                 = ¥2.011
4) Total:               2.011 × 33h                = ¥66.363
```

⚠️ **Regra confirmada por um RH específico — pode não valer pra sua
empresa.** O valor de "Horas Padrão" (168h no exemplo) também varia —
confirme sempre com seu RH ou compare com um holerite real antes de
confiar no resultado. Deixe desligado se não tiver certeza.

Isso substitui o antigo mecanismo "Taxa de Referência" (calibração
manual livre) — descontinuado a partir da v2.49.

---

## 📋 Registro de Holerite Real

Apenas um campo é obrigatório para o cálculo de Média Histórica:

| Campo | Uso |
|---|---|
| ⭐ 控除合計 Total Desconto | Base do cálculo — a Média Histórica é a média em ¥ dos valores já registrados, não uma porcentagem do bruto |

`総支給額 Total Bruto` e `差引支給額 Salário Líquido` são opcionais — só
para conferência pessoal, não entram no cálculo. Os demais ~24 campos
também são opcionais.

**Por que a mudança:** o desconto (INSS/imposto/etc.) tende a variar
pouco em valor absoluto entre os holerites — calculá-lo como
porcentagem do bruto e reaplicar sobre o bruto previsto inflava o
valor em meses com mais hora extra/bônus. A partir de agora, a Média
Histórica é simplesmente a média dos valores em ¥ já registrados.

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

Os valores exibidos são estimativas baseadas nas configurações inseridas por você. Este aplicativo NÃO substitui o holerite oficial emitido pela empresa e não é elaborado por advogado, contador ou despachante trabalhista. Consulte o RH ou um profissional qualificado para esclarecimentos oficiais sobre sua remuneração.

O app é gratuito, sem fins lucrativos, 100% offline, e fornecido "como está", sem garantias — o desenvolvedor não se responsabiliza por decisões tomadas com base nos valores calculados.

**Tela de aceite no primeiro uso:** antes de abrir o app pela primeira vez, esse aviso aparece por completo com botões "Aceitar e Continuar" / "Recusar". Recusar mostra só a logo, sem acesso ao app — recarregar a página dá uma nova chance. A escolha de aceitar fica salva (com data e hora), não pergunta de novo depois disso. O critério de aceite é exclusivamente esse clique — não há inferência a partir de dados já registrados.

**Licença:** projeto de código aberto sob [Licença MIT](LICENSE) — gratuito, sem garantias, uso e modificação livres.

---

## 🔒 Privacidade

- ✅ Sem conta, sem servidor, sem nuvem
- ✅ 100% offline após primeiro carregamento
- ✅ Dados ficam no dispositivo do usuário, persistidos via `shared_preferences`

---

## 🧪 Qualidade

O motor de cálculo é coberto por 119 testes automatizados (`test_main.py`),
incluindo validação direta contra 5 holerites reais de dois contratos
diferentes (2021-2022 e 2026).
