"""
Onion Payroll — Factory Shift Manager
Compatível com Flet 0.85.x
Todas as correções de API aplicadas.
"""

import flet as ft
import json
import math
import calendar
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

# pyfetch só existe no modo web (Pyodide) — em modo desktop (python main.py
# local), essa importação falha e o app cai de volta pro JP_HOLIDAYS_BUILTIN
# sem tentar buscar nada pela rede. httpx NÃO é usado aqui de propósito:
# tem bugs conhecidos e reportados no próprio repositório do Flet quando
# usado dentro do Pyodide (issues #4926 e #4840).
try:
    from pyodide.http import pyfetch
except ImportError:
    pyfetch = None


class _ValueHolder:
    """Substituto mínimo para ft.Dropdown quando convertido para botões —
    mantém a mesma interface `.value` usada no resto do código, sem
    precisar reescrever todos os pontos de leitura."""
    def __init__(self, value=None):
        self.value = value

# ─────────────────────────────────────────────
#  BUSINESS LOGIC — Decoupled from UI
# ─────────────────────────────────────────────

def shisha_gofuuu(value: float, mode: str = "half_up") -> int:
    """Arredondamento de valores monetários.
    mode="up": sempre arredonda pra cima (ceiling) — NOVO PADRÃO do app
    mode="half_up": 四捨五入 clássico, 0,5 sempre sobe (comportamento anterior)
    """
    if mode == "up":
        return int(math.ceil(value))
    return int(math.floor(value + 0.5))


def normalize_hhmm(s: str) -> str:
    """Converte entrada livre para HH:MM.
    835 → 08:35 | 2035 → 20:35 | 8:35 → 08:35
    """
    if not s:
        return ""
    s = s.strip().replace(".", ":").replace(",", ":")
    if ":" in s:
        parts = s.split(":")
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]) if len(parts)>1 else 0:02d}"
        except:
            return s
    digits = "".join(c for c in s if c.isdigit())
    try:
        if len(digits) <= 2:
            return f"{int(digits):02d}:00"
        elif len(digits) == 3:
            return f"{int(digits[0]):02d}:{int(digits[1:]):02d}"
        else:
            return f"{int(digits[:-2]):02d}:{int(digits[-2:]):02d}"
    except:
        return s


def normalize_date(s: str) -> str:
    """Converte entrada livre de data para AAAA-MM-DD, sem exigir hífen.
    20260703 → 2026-07-03 | 2026/07/03 → 2026-07-03 | 2026.7.3 → 2026-07-03
    Já em AAAA-MM-DD → mantém (só normaliza zeros à esquerda).
    Entrada inválida → devolve como veio, sem travar o campo.
    """
    if not s:
        return ""
    s = s.strip().replace("/", "-").replace(".", "-")
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 3:
            try:
                ano, mes, dia = int(parts[0]), int(parts[1]), int(parts[2])
                date(ano, mes, dia)  # valida se a data existe de verdade
                return f"{ano:04d}-{mes:02d}-{dia:02d}"
            except (ValueError, IndexError):
                return s
        return s
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 8:  # AAAAMMDD
        try:
            ano, mes, dia = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
            date(ano, mes, dia)
            return f"{ano:04d}-{mes:02d}-{dia:02d}"
        except ValueError:
            return s
    return s


def jikyuu_vigente_para_mes(month_key: str, history: list, default: int) -> int:
    """時給 vigente pra um mês específico, com base nos marcos registrados
    no Histórico (campo "jikyuu_effective"). Procura o registro mais
    recente, IGUAL OU ANTERIOR ao mês sendo visto, que tenha esse campo
    preenchido — usa esse valor em vez do 時給 atual de ⚙️ Config. Sem
    nenhum marco encontrado, cai no valor default (comportamento de
    sempre, sem mudar nada pra quem não usa essa funcionalidade)."""
    marcos = [
        (e["month"], int(e["jikyuu_effective"]))
        for e in history
        if e.get("jikyuu_effective") and e.get("month", "") <= month_key
    ]
    if not marcos:
        return default
    marcos.sort(key=lambda x: x[0])
    return marcos[-1][1]


def desconto_real_para_mes(month_key: str, history: list) -> Optional[int]:
    """Valor de desconto REAL, se esse mês específico já tiver holerite
    registrado no Histórico (não é mais previsão, é dado conhecido).
    Retorna None se não houver registro pra esse mês exato — nesse caso,
    quem chamar deve usar a previsão normal (Média Histórica ou Fixo)."""
    registro = next((e for e in history if e.get("month") == month_key), None)
    if registro is not None and registro.get("deductions", 0) > 0:
        return int(registro["deductions"])
    return None


def normalize_yyyymm(s: str) -> str:
    """Converte entrada livre de mês para AAAA-MM, sem exigir hífen.
    202602 → 2026-02 | 2026/02 → 2026-02 | 2026.2 → 2026-02
    Já em AAAA-MM → mantém (só normaliza zero à esquerda).
    Entrada inválida → devolve como veio, sem travar o campo.
    """
    if not s:
        return ""
    s = s.strip().replace("/", "-").replace(".", "-")
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2:
            try:
                ano, mes = int(parts[0]), int(parts[1])
                if not (1 <= mes <= 12):
                    return s
                return f"{ano:04d}-{mes:02d}"
            except (ValueError, IndexError):
                return s
        return s
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 6:  # AAAAMM
        try:
            ano, mes = int(digits[:4]), int(digits[4:6])
            if not (1 <= mes <= 12):
                return s
            return f"{ano:04d}-{mes:02d}"
        except ValueError:
            return s
    return s


def parse_hhmm(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s.strip(), "%H:%M")
    except ValueError:
        return None


def minutes_between(start: datetime, end: datetime) -> int:
    delta = end - start
    if delta.total_seconds() < 0:
        delta += timedelta(days=1)
    return int(delta.total_seconds() // 60)


def truncate_minutes(total_minutes: int, block: int, round_mode: str = "truncate") -> int:
    """Arredonda minutos para o bloco informado.

    round_mode="truncate" (padrão, compatível com versões anteriores):
        sempre arredonda para BAIXO (ex: 22min em blocos de 15 -> 15min).
    round_mode="nearest": arredonda para o múltiplo mais próximo
        (ex: 22min em blocos de 15 -> 15min; 23min -> 30min). Algumas
        empresas usam essa regra (confirmado contra holerites reais onde
        370min -> 375min, não 360min). Ver MHLW 昭63.3.14 基発150号.
    """
    if block <= 1:
        return total_minutes
    if round_mode == "nearest":
        resto = total_minutes % block
        if resto >= block / 2:
            return total_minutes + (block - resto)
        return total_minutes - resto
    return (total_minutes // block) * block


def night_minutes_in_range(shift_start: datetime, shift_end: datetime) -> int:
    count = 0
    cursor = shift_start
    end = shift_end
    if end <= shift_start:
        end += timedelta(days=1)
    while cursor < end:
        if cursor.hour >= 22 or cursor.hour < 5:
            count += 1
        cursor += timedelta(minutes=1)
    return count


def _anchor_to_shift(base_start: datetime, time_str: str) -> Optional[datetime]:
    """Ancora um horário HH:MM ao 'dia lógico' do turno, relativo a
    base_start — mesma convenção de virada de meia-noite já usada em
    minutes_between(): se o horário informado for numericamente
    ANTERIOR ao início de referência, assume que é no dia seguinte
    (comum em intervalos de turnos noturnos que cruzam a meia-noite,
    ex: turno 20:30→08:35 com um intervalo às 01:00)."""
    dt = parse_hhmm(time_str)
    if dt is None:
        return None
    if dt < base_start:
        dt += timedelta(days=1)
    return dt


def night_minutes_worked(shift_start: datetime, shift_end: datetime,
                          break_periods: list = None) -> int:
    """Conta minutos entre 22:00-05:00 que caem dentro do turno,
    EXCLUINDO qualquer minuto que também caia dentro de um período de
    intervalo/pausa (break_periods).

    Sem isso, empresas que aplicam vários intervalos curtos (ex: 10min
    a cada 2h) durante o turno noturno tinham o adicional noturno
    inflado — a contagem antiga (`night_minutes_in_range`) não sabia
    diferenciar minuto trabalhado de minuto de pausa, só olhava o
    relógio.

    `break_periods`: lista de tuplas (start_dt, end_dt) já ancoradas
    (ver `_anchor_to_shift`). Se None ou vazia, comportamento IDÊNTICO
    a `night_minutes_in_range` (retrocompatível — recurso opcional,
    desligado por padrão).
    """
    count = 0
    cursor = shift_start
    end = shift_end
    if end <= shift_start:
        end += timedelta(days=1)
    while cursor < end:
        is_night = cursor.hour >= 22 or cursor.hour < 5
        is_break = False
        if break_periods:
            for bp_start, bp_end in break_periods:
                if bp_start <= cursor < bp_end:
                    is_break = True
                    break
        if is_night and not is_break:
            count += 1
        cursor += timedelta(minutes=1)
    return count


def build_timeline_segments(shift_start: datetime, shift_end: datetime,
                             ot_start: datetime = None,
                             break_periods: list = None) -> list:
    """Constrói a linha do tempo do turno como segmentos contínuos,
    cortando exatamente nos pontos onde alguma classificação muda:
    início/fim de intervalo, início da hora extra, e as fronteiras do
    adicional noturno (22h e 5h de cada dia tocado pelo turno).

    Ideia central (sugerida por auditoria externa do projeto): em vez de
    calcular direto "horas noturnas" e depois subtrair intervalo (que dá
    errado quando o intervalo cai PARCIALMENTE dentro do período
    noturno, ou quando cai dentro da janela de hora extra), primeiro
    representa o turno inteiro como uma sequência de pedaços de tempo,
    cada um já classificado (intervalo? noturno? hora extra?) — só
    DEPOIS soma os minutos de cada categoria. Elimina a necessidade de
    qualquer "min(x, net_min)" como rede de segurança — a matemática já
    fecha certo por construção, porque cada minuto do turno pertence a
    exatamente um segmento.

    Retorna lista de dicts: {"start", "end", "minutes", "is_break",
    "is_night", "is_overtime"}, em ordem cronológica, cobrindo o turno
    inteiro sem lacunas nem sobreposição.

    `break_periods`: lista de tuplas (start_dt, end_dt) já ancoradas.
    `ot_start`: datetime já ancorado (ou None, se não houver hora extra
    nesse turno — turno inteiro tratado como não-extra).
    """
    end = shift_end
    if end <= shift_start:
        end += timedelta(days=1)

    pontos = {shift_start, end}
    if ot_start and shift_start < ot_start < end:
        pontos.add(ot_start)

    # Fronteiras do adicional noturno (22h e 5h) em cada dia tocado
    dia_cursor = shift_start.replace(hour=0, minute=0, second=0, microsecond=0)
    while dia_cursor <= end:
        for hora in (5, 22):
            p = dia_cursor.replace(hour=hora)
            if shift_start < p < end:
                pontos.add(p)
        dia_cursor += timedelta(days=1)

    periodos_resolvidos = []
    if break_periods:
        for bp_start, bp_end in break_periods:
            if bp_start and bp_end:
                periodos_resolvidos.append((bp_start, bp_end))
                if shift_start < bp_start < end:
                    pontos.add(bp_start)
                if shift_start < bp_end < end:
                    pontos.add(bp_end)

    ordenados = sorted(p for p in pontos if shift_start <= p <= end)
    segmentos = []
    for i in range(len(ordenados) - 1):
        seg_ini, seg_fim = ordenados[i], ordenados[i + 1]
        if seg_ini >= seg_fim:
            continue
        meio = seg_ini + (seg_fim - seg_ini) / 2
        is_break = any(bs <= seg_ini and seg_fim <= be for bs, be in periodos_resolvidos)
        is_night = (meio.hour >= 22 or meio.hour < 5)
        is_overtime = bool(ot_start and seg_ini >= ot_start)
        minutos = int(round((seg_fim - seg_ini).total_seconds() / 60))
        segmentos.append({
            "start": seg_ini, "end": seg_fim, "minutes": minutos,
            "is_break": is_break, "is_night": is_night, "is_overtime": is_overtime,
        })
    return segmentos


def calcular_presenca_mensal(cycle: dict, day_overrides: dict,
                              month_holidays: list = None) -> dict:
    """Calcula a % de presença do mês, pro adicional de assiduidade
    opcional da empresa (精皆勤手当) — DIFERENTE da regra legal dos 80%
    do Yukyu (essa é sempre por período de 6 meses/1 ano, nunca mensal).

    Totalmente ISOLADA do motor de cálculo de pagamento — só lê o mesmo
    ciclo/overrides que compute_monthly_forecast já usa, sem alterar
    nenhum valor de holerite.

    Confirmado pelo usuário: só falta de dia inteiro (status="absent")
    desconta da porcentagem — dias de Yukyu, domingo/feriado trabalhado,
    e qualquer outro status contam como presença normalmente. Dias que
    são feriado da empresa também não entram no denominador (não é dia
    que a pessoa "deveria" comparecer).

    `cycle`: dict {dia: "work"|"off"} — o mesmo gerado por
        generate_4x2_calendar/generate_weekly_calendar/etc.
    `day_overrides`: dict {dia_str: {"status": ...}} — overrides do mês.
    `month_holidays`: lista de dias (int) que são feriado da empresa
        nesse mês — excluídos do denominador.

    Retorna: {"percentual", "dias_programados", "faltas", "presentes"}.
    Se não há dias programados no mês (ex: mês todo de folga), retorna
    100% — sem dias pra faltar, não há o que descontar.
    """
    month_holidays = month_holidays or []
    dias_programados = 0
    faltas = 0
    for day_num, cycle_status in cycle.items():
        if cycle_status != "work":
            continue
        if day_num in month_holidays:
            continue
        dias_programados += 1
        ov = day_overrides.get(str(day_num), {})
        if isinstance(ov, dict) and ov.get("status") == "absent":
            faltas += 1

    if dias_programados == 0:
        return {"percentual": 100.0, "dias_programados": 0, "faltas": 0, "presentes": 0}

    presentes = dias_programados - faltas
    percentual = (presentes / dias_programados) * 100
    return {
        "percentual": percentual, "dias_programados": dias_programados,
        "faltas": faltas, "presentes": presentes,
    }


def calculate_shift_pay(
    jikyuu: int, shift_type: str, start_str: str = "", end_str: str = "",
    break_min: int = 65, block: int = 1, is_holiday: bool = False,
    yukyu_on_holiday: bool = False, base_shift: str = "",
    round_mode: str = "truncate",
    wage_round_mode: str = "up",
    use_leader_addon: bool = False,
    leader_addon_amount: float = 0, leader_addon_hours: float = 168,
    ot_start_str: str = "",
    cfg_start_str: str = "", cfg_end_str: str = "",
    break_periods: list = None,
    night_interval_minutes: int = 0,  # minutos de intervalo dentro da
                                       # janela 22h-5h, descontados do
                                       # bruto (420min) de forma
                                       # simplificada, sem precisar saber
                                       # a posição exata do intervalo
    extra_minutes: int = 0,  # 延長 — minutos extras solicitados além do
                              # turno, à taxa cheia de hora extra (1,25x)
) -> dict:
    """
    shift_type: "night"|"day"|"holiday"|"yukyu"|"absent" — determina o
        PREMIUM aplicado (+35% se holiday).
    base_shift: "night"|"day" — determina os HORÁRIOS PADRÃO e o limiar
        de hora extra. Quando shift_type="holiday" (trabalho em feriado/
        domingo), o turno real do funcionário (noturno ou diurno) deve
        ser passado aqui, pois o feriado pode cair em QUALQUER turno.
        Se não informado, assume o mesmo valor de shift_type (compatível
        com chamadas antigas que não differenciavam).
    ot_start_str: horário configurado de início da hora extra (ex:
        "06:35"). Se não informado, cai no padrão "06:35"/"18:35" por
        turno (comportamento antigo).
    cfg_start_str, cfg_end_str: horário de entrada/saída CONFIGURADO
        pelo usuário (ex: "20:30"/"08:35") — usado, junto com
        `ot_start_str`, para calcular a JORNADA NORMAL do Yukyu sem
        horário explícito (ver abaixo). Sem isso, o Yukyu sempre usava
        8h fixo E o horário hardcoded "20:35"/"08:35" do turno padrão,
        ignorando a jornada real configurada (ex: turnos de 9h como
        20:30-08:35 com intervalo de 65min e OT às 06:35 — a jornada
        normal real é 9h, não 8h).
    break_periods: lista de (start_str, end_str) — horários HH:MM de
        cada intervalo/pausa dentro do turno (ex: [("22:30","22:40"),
        ("00:30","00:40")] para pausas curtas de 10min a cada 2h).
        Recurso OPCIONAL/avançado: se None ou vazia, o adicional
        noturno conta todo o intervalo 22h-05h sem excluir pausas
        (comportamento antigo). Quando informado, minutos de pausa que
        caem dentro de 22h-05h são excluídos do adicional noturno —
        sem isso, empresas com pausas curtas durante o turno noturno
        tinham o adicional inflado (pausa contada como se fosse
        trabalhada).

    wage_round_mode: "up" (padrão, sempre arredonda pra cima) ou
        "half_up" (0,5 sempre sobe — comportamento anterior à v2.49).
        Aplicado à taxa por hora de base, extra, noturno e feriado.

    use_leader_addon: quando True, separa o cálculo da taxa cheia
        (extra/noturno/domingo) em duas parcelas arredondadas
        INDIVIDUALMENTE — jikyuu puro + acréscimo do adicional de líder
        — em vez de somar os dois numa taxa só antes de arredondar uma
        vez. Baseado em fórmula confirmada por RH real: cada parcela é
        arredondada separadamente porque a diferença muda o resultado
        final. Default False = comportamento antigo (soma antes de
        arredondar).
    leader_addon_amount: valor do adicional fixo mensal (ex: リーダー手当)
        usado na parcela do acréscimo, quando use_leader_addon=True.
        Normalmente vem do mesmo campo "Adicional Fixo Mensal — Líder"
        que já soma no bruto do mês — não precisa duplicar o valor.
    leader_addon_hours: horas padrão usadas para transformar o
        adicional fixo mensal em ¥/hora (default 168h, do exemplo real
        de RH — pode variar por empresa, sempre confirmar).
    """
    result = {
        "base_pay": 0, "overtime_pay": 0, "night_pay": 0, "holiday_pay": 0,
        "total_gross": 0, "net_minutes": 0, "overtime_minutes": 0,
        "night_minutes": 0, "regular_minutes": 0,
    }

    # Taxas expostas no resultado — calculadas AQUI, bem no início da
    # função, antes de qualquer branch/return antecipado (absent, yukyu,
    # shift_type inválido, etc.) — bug real corrigido: essas chaves só
    # eram definidas mais abaixo, dentro do bloco is_holiday/else, então
    # qualquer dia de Yukyu (que retorna antes de chegar lá) travava
    # compute_monthly_forecast com KeyError ao tentar ler
    # pay["_ot_rate_full"]. CONSTANTES o mês inteiro (dependem só de
    # jikyuu/adicional/modo de arredondamento configurados, nunca do dia
    # específico ou do shift_type).
    _holiday_premium_fixo = 0.35
    addon_per_hour = (leader_addon_amount / leader_addon_hours
                       if (use_leader_addon and leader_addon_hours > 0) else 0.0)

    def _taxa_cheia(multiplicador: float) -> int:
        # Se use_leader_addon estiver ativo, jikyuu e o acréscimo do
        # adicional de líder são arredondados EM SEPARADO, cada um por
        # si, antes de somar — confirmado por RH real que o resultado
        # muda dependendo de arredondar tudo junto ou separado. Sem isso
        # ativo, comportamento idêntico a uma taxa só (jikyuu puro).
        parte_base = shisha_gofuuu(jikyuu * multiplicador, wage_round_mode)
        if use_leader_addon and addon_per_hour > 0:
            parte_addon = shisha_gofuuu(addon_per_hour * multiplicador, wage_round_mode)
            return parte_base + parte_addon
        return parte_base

    result["_ot_rate_full"]         = _taxa_cheia(1.25)
    result["_night_rate_increment"] = _taxa_cheia(0.25)
    result["_holiday_rate_full"]    = _taxa_cheia(1.0 + _holiday_premium_fixo)
    result["_jikyuu_per_min"]       = jikyuu / 60.0

    if shift_type == "absent":
        return result

    # v2.40: o toggle "有休 em Feriado Corporativo" também usa a jornada
    # normal configurada, igual ao Yukyu comum — nada mais fica com um
    # valor fixo hardcoded (nem 8h, nem qualquer outro), tudo depende da
    # configuração real do usuário (entrada, saída, intervalo, início da
    # hora extra). Antes calculava sempre jikyuu×8, inconsistente com o
    # resto do sistema, que já usa a jornada configurada em todo lugar.
    if yukyu_on_holiday and is_holiday:
        shift_type = "yukyu"

    # Determinar o turno EFETIVO para horários/limiar de OT — calculado
    # ANTES do branch de Yukyu, pra podermos usar a JORNADA NORMAL
    # configurada (não um valor fixo) mesmo quando o Yukyu é marcado sem
    # horário explícito.
    _effective_shift = base_shift if base_shift else shift_type

    if _effective_shift == "night":
        default_start, default_end, _default_ot = "20:35", "08:35", "06:35"
    elif _effective_shift in ("day", "holiday"):
        default_start, default_end, _default_ot = "08:35", "20:35", "18:35"
    elif shift_type == "yukyu":
        # Yukyu sem base_shift informado (turno real desconhecido aqui) —
        # cai no padrão diurno só como referência neutra de jornada.
        default_start, default_end, _default_ot = "08:35", "20:35", "18:35"
    else:
        return result

    # cfg_start_str/cfg_end_str (horário CONFIGURADO pelo usuário) tem
    # prioridade sobre o horário hardcoded do turno padrão — sem isso, o
    # Yukyu sem horário explícito usava "20:35"/"08:35" fixo mesmo que o
    # usuário tivesse configurado "20:30"/"08:35" (ou qualquer outro).
    default_start = cfg_start_str if cfg_start_str else default_start
    default_end   = cfg_end_str   if cfg_end_str   else default_end

    _ot_final = ot_start_str if ot_start_str else _default_ot

    if shift_type == "yukyu":
        # Jornada normal configurada (do início do turno até o início da
        # hora extra, descontando intervalo) — usada tanto como valor
        # padrão (sem horário informado) quanto como TETO máximo (com
        # horário informado). Sem esse teto, informar o horário do turno
        # INTEIRO (ex: 20:30-08:35, igual a um dia normal) contava até a
        # janela de hora extra também, pagando mais do que a jornada
        # normal — inconsistente com o Art. 39 §9: Yukyu paga o salário
        # do dia normal de trabalho, nunca mais que isso.
        _yk_start_dt = parse_hhmm(default_start)
        _yk_ot_dt    = parse_hhmm(_ot_final)
        if _yk_start_dt and _yk_ot_dt:
            _yk_gross_min = minutes_between(_yk_start_dt, _yk_ot_dt)
            _jornada_normal_min = max(0, truncate_minutes(_yk_gross_min - break_min, block, round_mode))
        else:
            _jornada_normal_min = None

        if start_str and end_str:
            # Yukyu parcial: calcular pelo horário real, SEM OT e SEM
            # noturno — mas nunca mais que a jornada normal (teto acima).
            start_dt = parse_hhmm(start_str)
            end_dt   = parse_hhmm(end_str)
            if start_dt and end_dt:
                gross_min = minutes_between(start_dt, end_dt)
                net_min   = max(0, truncate_minutes(gross_min - break_min, block, round_mode))
                if _jornada_normal_min is not None:
                    net_min = min(net_min, _jornada_normal_min)
                result["net_minutes"] = net_min
                result["base_pay"]    = shisha_gofuuu((jikyuu / 60.0) * net_min)
                result["total_gross"] = result["base_pay"]
                return result
        # Sem horário (ou horário inválido): jornada normal cheia. Não
        # mais um valor fixo de 8h — reflete o que a pessoa realmente
        # ganharia num dia comum de trabalho.
        if _jornada_normal_min is not None:
            result["net_minutes"] = _jornada_normal_min
            result["base_pay"]    = shisha_gofuuu((jikyuu / 60.0) * _jornada_normal_min)
        else:
            # Fallback final (não deveria ocorrer com horários válidos)
            result["base_pay"] = shisha_gofuuu(jikyuu * 8)
        result["total_gross"] = result["base_pay"]
        return result

    if _effective_shift not in ("night", "day", "holiday"):
        return result

    s_str = start_str if start_str else default_start
    e_str = end_str if end_str else default_end

    start_dt = parse_hhmm(s_str)
    end_dt   = parse_hhmm(e_str)
    ot_dt    = parse_hhmm(_ot_final)

    if not start_dt or not end_dt or not ot_dt:
        return result

    # Ancorar end_dt/ot_dt ao dia certo relativo ao início do turno — a
    # fórmula antiga não precisava disso (minutes_between() já resolve
    # a virada de meia-noite internamente, via diferença relativa), mas
    # a engine de linha do tempo (v2.38) compara datas diretamente, e
    # sem ancorar corretamente, QUALQUER horário "menor" que o de início
    # (ex: 06:35 vs entrada 20:30) seria interpretado como ainda no
    # MESMO dia, marcando o turno inteiro como hora extra por engano.
    # Ancorar aqui de uma vez é seguro pros dois caminhos (minutes_between
    # continua funcionando igual com datas já ancoradas).
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    if ot_dt <= start_dt:
        ot_dt += timedelta(days=1)

    # Resolver os intervalos informados (se houver) para datetime ancorado
    _resolved_periods = []
    if break_periods:
        for _bp_s, _bp_e in break_periods:
            _bs = _anchor_to_shift(start_dt, _bp_s)
            _be = _anchor_to_shift(_bs, _bp_e) if _bs else None
            if _bs and _be:
                _resolved_periods.append((_bs, _be))

    if _resolved_periods:
        # ── Engine de linha do tempo (v2.38) ──────────────────────
        # Quando a POSIÇÃO real do intervalo é conhecida (não só a
        # duração), constrói a linha do tempo do turno inteira, corta
        # nos pontos onde a classificação muda (intervalo, hora extra,
        # fronteiras do adicional noturno 22h/5h), e só então soma os
        # minutos de cada categoria. Isso resolve, por construção, casos
        # que a fórmula antiga (baseada em totais) não conseguia tratar
        # corretamente: intervalo parcialmente noturno, intervalo dentro
        # da janela de hora extra, múltiplos intervalos. Sugestão de
        # auditoria externa do projeto — ver PROBLEMAS_RECORRENTES.md.
        segmentos = build_timeline_segments(start_dt, end_dt, ot_dt, _resolved_periods)
        trabalhados = [s for s in segmentos if not s["is_break"]]
        net_min     = sum(s["minutes"] for s in trabalhados)
        raw_ot_min  = sum(s["minutes"] for s in trabalhados if s["is_overtime"])
        raw_night_min = sum(s["minutes"] for s in trabalhados if s["is_night"])
        result["net_minutes"] = net_min
        jikyuu_per_min = jikyuu / 60.0
        # Arredondamento por rubrica, igual ao caminho antigo — mas sem
        # precisar de nenhum "min(x, net_min)" como rede de segurança,
        # já que a soma dos segmentos nunca pode passar do total do turno
        ot_min    = truncate_minutes(raw_ot_min, block, round_mode)
        night_min = truncate_minutes(raw_night_min, block, round_mode)
        result["overtime_minutes"] = ot_min
        result["regular_minutes"]  = net_min - ot_min
        result["night_minutes"]    = night_min
    else:
        # ── Fórmula original (v2.9-v2.33) ─────────────────────────
        # Mantida INTACTA — validada contra 5 holerites reais (2021,
        # 2022, fev/mar/abr 2026) com ¥0 de diferença. Só entra aqui
        # quando não há informação de POSIÇÃO do intervalo (a maioria
        # dos usuários, que só configuram a duração) — sem essa
        # informação, a engine de linha do tempo não tem como saber
        # onde cortar, então não haveria ganho de precisão em trocar.
        gross_min = minutes_between(start_dt, end_dt)
        net_min   = max(0, truncate_minutes(gross_min - break_min, block, round_mode))

        result["net_minutes"]      = net_min
        jikyuu_per_min             = jikyuu / 60.0
        _start_to_ot  = minutes_between(start_dt, ot_dt)
        _start_to_end = minutes_between(start_dt, end_dt)
        if _start_to_end > _start_to_ot:
            raw_ot_min = _start_to_end - _start_to_ot
        else:
            raw_ot_min = 0
        # Hora extra arredondada SEPARADAMENTE a partir do valor bruto (não
        # derivada do net_min já truncado) — regra MHLW 昭63.3.14 基発150号:
        # cada rubrica é arredondada por dia, individualmente, antes de somar
        # o mês. Ainda limitada ao net_min como teto de sanidade.
        ot_min = min(truncate_minutes(raw_ot_min, block, round_mode), net_min)
        result["overtime_minutes"] = ot_min
        result["regular_minutes"]  = net_min - ot_min
        raw_night_min = night_minutes_in_range(start_dt, end_dt)
        # Desconto simplificado de intervalo dentro da janela noturna —
        # alternativa à posição exata (que exigiria a engine de linha do
        # tempo completa). Ex: 420min (7h) - 45min configurados = 375min
        # (6,25h). Default 0 = comportamento idêntico a antes.
        if night_interval_minutes > 0:
            raw_night_min = max(0, raw_night_min - night_interval_minutes)
        # Adicional noturno também arredondado separadamente a partir do bruto,
        # em vez de só herdar o cap do net_min sem arredondamento próprio.
        night_min                  = min(truncate_minutes(raw_night_min, block, round_mode), net_min)
        result["night_minutes"]    = night_min
    # IMPORTANTE: a taxa por HORA é arredondada pro yen mais próximo ANTES
    # de multiplicar pelas horas trabalhadas — não o valor total no final.
    # Confirmado com planilha de referência do usuário e validado contra
    # 5 holerites reais (2 jikyuu diferentes, 2 anos diferentes): bate
    # exato. Arredondar só no final (como antes) deixava um resíduo de
    # ~0,03%-0,14%, que parecia ruído mas era essa regra específica.
    #
    # v2.39: CORRIGIDO — base_pay usava net_min (horas regulares + horas
    # de hora extra somadas), com overtime_pay mostrando só o incremento
    # de 25%. Isso dava um TOTAL certo, mas a DIVISÃO entre "Salário
    # Base" e "Hora Extra" saía bem diferente do holerite real, que
    # separa 所定内 (só horas regulares) de 所定外 (só horas de hora
    # extra, à taxa CHEIA de 1,25x) como categorias sem sobreposição.
    # Mesma lógica pra domingo/feriado: 公出手当 no holerite real é a
    # taxa CHEIA (1,35x) sobre as horas trabalhadas nesse dia — nenhuma
    # dessas horas aparece em 基本給. Comparado direto contra os 5
    # holerites reais (fev/mar/abr 2026): confirma ¥0 de diferença tanto
    # no total quanto em cada rubrica individual, agora sim.
    if is_holiday:
        # holiday_pay = SÓ as horas trabalhadas × taxa cheia de domingo
        # (1,35x), sem noturno misturado dentro dessa linha — confere
        # exato com 公出手当/法定休出 do holerite real (¥23.892/domingo).
        #
        # night_pay, porém, é uma linha SEPARADA e INDEPENDENTE no
        # holerite (深夜手当) — soma as horas noturnas de TODOS os dias,
        # incluindo domingo/feriado, à taxa noturna normal (sem premium
        # de domingo misturado). NÃO deve ser zerada aqui — validado
        # contra holerite real: 2 domingos × 6,25h noturno + 16 dias
        # normais × 6,25h = 112,5h no total, batendo exato com os
        # ¥45.338 reais de 深夜手当 do mês.
        holiday_rate_full       = _taxa_cheia(1.0 + _holiday_premium_fixo)
        night_rate_increment    = _taxa_cheia(0.25)
        ot_rate_full            = _taxa_cheia(1.25)  # exposto p/ consistência, não usado hoje
        # 延長 em domingo/feriado entra NAS HORAS DE DOMINGO, à taxa de
        # 1,35x — não como hora extra genérica (1,25x). Bug real: antes
        # o 延長 sempre ia pra overtime_pay/overtime_minutes, que nem é
        # somado no total mensal em dias de domingo (só holiday_pay e
        # night_pay são lidos pra domingo em compute_monthly_forecast) —
        # o minuto extra era calculado aqui dentro e depois descartado.
        _holiday_min_total       = net_min + extra_minutes
        result["base_pay"]      = 0
        result["overtime_pay"]  = 0
        result["night_pay"]     = shisha_gofuuu(night_rate_increment * (night_min / 60.0), wage_round_mode)
        result["holiday_pay"]   = shisha_gofuuu(holiday_rate_full * (_holiday_min_total / 60.0), wage_round_mode)
        result["net_minutes"]   = _holiday_min_total
    else:
        # base_pay cobre SÓ as horas regulares — hora extra é 100%
        # coberta por overtime_pay à taxa cheia, sem sobreposição.
        result["base_pay"]      = shisha_gofuuu(jikyuu_per_min * result["regular_minutes"], wage_round_mode)
        ot_rate_full            = _taxa_cheia(1.25)
        night_rate_increment    = _taxa_cheia(0.25)
        holiday_rate_full       = _taxa_cheia(1.0 + _holiday_premium_fixo)  # exposto p/ consistência
        result["overtime_pay"]  = shisha_gofuuu(ot_rate_full * (ot_min / 60.0), wage_round_mode)
        result["night_pay"]     = shisha_gofuuu(night_rate_increment * (night_min / 60.0), wage_round_mode)
        result["holiday_pay"]   = 0

    # As chaves _ot_rate_full/_night_rate_increment/_holiday_rate_full/
    # _jikyuu_per_min já foram definidas no início da função (antes de
    # qualquer early-return) — não precisam ser reatribuídas aqui, os
    # valores são idênticos (mesma _taxa_cheia, mesmos parâmetros).

    # 延長 em dia NORMAL (não feriado) — hora extra genérica, à taxa
    # cheia de 1,25x, somada em overtime_pay/overtime_minutes.
    if extra_minutes > 0 and not is_holiday:
        _extra_rate = _taxa_cheia(1.25)
        extra_pay = shisha_gofuuu((_extra_rate / 60.0) * extra_minutes, wage_round_mode)
        result["overtime_pay"]     += extra_pay
        result["overtime_minutes"] = result.get("overtime_minutes", 0) + extra_minutes

    result["total_gross"]  = (result["base_pay"] + result["overtime_pay"]
                               + result["night_pay"] + result["holiday_pay"])
    return result


def generate_4x2_calendar(anchor_date: date, year: int, month: int, group: str = "A",
                           anchor_group: str = None) -> dict:
    """Ciclo 4x2 (4 dias trabalho + 2 folga) com 3 turmas rotativas.

    `anchor_date` é o dia 1 de trabalho do grupo `anchor_group` (o grupo
    que estava selecionado quando a data foi definida/alterada pela
    última vez). Ao trocar de grupo SEM alterar a data, o calendário do
    novo grupo é recalculado automaticamente pela relação de 2 dias entre
    turmas — confirmado contra planilha real de escala da fábrica (Grupo
    A folga qui/sex, B folga dom/sáb, C folga ter/qua, nunca duas turmas
    folgando juntas).

    Se `anchor_group` não for informado, assume igual a `group` (a data
    é o dia 1 do próprio grupo selecionado, sem deslocamento — caso mais
    comum: usuário nunca trocou de grupo depois de definir a data).
    """
    GROUP_OFFSET = {"A": 0, "B": 2, "C": 4}
    if anchor_group is None:
        anchor_group = group
    offset = GROUP_OFFSET.get(group, 0) - GROUP_OFFSET.get(anchor_group, 0)
    result, first_day, last_day = {}, date(year, month, 1), date(year, month, 28)
    for d in range(28, 32):
        try:    last_day = date(year, month, d)
        except ValueError: break
    cursor = first_day
    while cursor <= last_day:
        delta = ((cursor - anchor_date).days - offset) % 6
        if delta < 0:
            delta = (delta % 6 + 6) % 6
        result[cursor.day] = "work" if delta < 4 else "off"
        cursor += timedelta(days=1)
    return result


def generate_weekly_calendar(year: int, month: int) -> dict:
    """5x2 fixo: segunda a sexta = work, sábado/domingo = off."""
    result, first_day, last_day = {}, date(year, month, 1), date(year, month, 28)
    for d in range(28, 32):
        try:    last_day = date(year, month, d)
        except ValueError: break
    cursor = first_day
    while cursor <= last_day:
        # weekday(): 0=segunda ... 5=sábado, 6=domingo
        result[cursor.day] = "off" if cursor.weekday() >= 5 else "work"
        cursor += timedelta(days=1)
    return result


def generate_alternating_calendar(anchor_date: date, year: int, month: int) -> dict:
    """Alternado semanal: 1 semana inteira em um turno, próxima semana no outro.
    Retorna dict {day: ("work"|"off", "day"|"night")} indicando status e turno.
    Semanas contam a partir da segunda-feira da anchor_date.
    """
    result, first_day, last_day = {}, date(year, month, 1), date(year, month, 28)
    for d in range(28, 32):
        try:    last_day = date(year, month, d)
        except ValueError: break

    # Segunda-feira da semana da âncora
    anchor_monday = anchor_date - timedelta(days=anchor_date.weekday())

    cursor = first_day
    while cursor <= last_day:
        cursor_monday = cursor - timedelta(days=cursor.weekday())
        weeks_diff = (cursor_monday - anchor_monday).days // 7
        # Semana par = turno A (dia), semana ímpar = turno B (noite)
        shift = "day" if weeks_diff % 2 == 0 else "night"
        status = "off" if cursor.weekday() >= 5 else "work"
        result[cursor.day] = (status, shift)
        cursor += timedelta(days=1)
    return result


def generate_alternating_monthly_calendar(shift_anchor_date: date, year: int, month: int,
                                           rest_pattern: str = "5x2",
                                           rest_anchor_date: date = None,
                                           group: str = "A", anchor_group: str = None) -> dict:
    """Alternado mensal: 1 mês inteiro em um turno, próximo mês no outro.
    Retorna dict {day: ("work"|"off", "day"|"night")}.

    Duas datas independentes:
    - `shift_anchor_date`: qualquer dia do PRIMEIRO MÊS diurno — define a
      alternância dia/noite (meses contados a partir do mês dessa data).
    - `rest_anchor_date`: só usado quando rest_pattern="4x2" — é o
      `anchor_date` do padrão de folga 4×2 (mesmo mecanismo de Grupo A/B/C
      e `anchor_group` já usado no ciclo 4×2 puro). Se não informado,
      usa `shift_anchor_date` como referência.

    `rest_pattern`:
    - "5x2" (padrão): folga sábado/domingo, igual ao alternado semanal.
    - "4x2": folga conforme o ciclo 4×2 (4 dias trabalho + 2 folga),
      respeitando Grupo A/B/C — reaproveita `generate_4x2_calendar`.
    """
    result, first_day, last_day = {}, date(year, month, 1), date(year, month, 28)
    for d in range(28, 32):
        try:    last_day = date(year, month, d)
        except ValueError: break

    anchor_month_start = shift_anchor_date.replace(day=1)
    months_diff = (year - anchor_month_start.year) * 12 + (month - anchor_month_start.month)
    shift = "day" if months_diff % 2 == 0 else "night"

    if rest_pattern == "4x2":
        _rest_anchor = rest_anchor_date if rest_anchor_date else shift_anchor_date
        rest_cal = generate_4x2_calendar(_rest_anchor, year, month, group, anchor_group)
        cursor = first_day
        while cursor <= last_day:
            result[cursor.day] = (rest_cal.get(cursor.day, "off"), shift)
            cursor += timedelta(days=1)
    else:
        cursor = first_day
        while cursor <= last_day:
            status = "off" if cursor.weekday() >= 5 else "work"
            result[cursor.day] = (status, shift)
            cursor += timedelta(days=1)
    return result


def _add_months(d: date, months: int) -> date:
    """Soma `months` meses a uma data, ajustando o dia se o mês de
    destino for mais curto (ex: 31/jan + 1 mês = 28/fev, não erro)."""
    month_idx = d.month - 1 + months
    year = d.year + month_idx // 12
    month = month_idx % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calcular_yukyu(hire_date: date, today: date, usage_dates: list) -> dict:
    """Calcula o saldo de 有給休暇 (Yukyu) conforme Art. 39 da Lei
    Trabalhista Japonesa (労働基準法), para trabalhador de 5+ dias/semana
    (tabela cheia — não cobre 比例付与/proporcional de part-time).

    Concessões (meses desde a admissão → dias concedidos):
    6º mês=10, 1a6m=11, 2a6m=12, 3a6m=14, 4a6m=16, 5a6m=18, 6a6m+=20
    (permanece 20/ano a cada 12 meses depois de 6a6m).

    Cada concessão expira 2 anos após ser concedida (Art. 115) — o saldo
    é consumido na ordem mais antiga primeiro (FIFO), a mesma lógica que
    a legislação usa para não desperdiçar dias prestes a vencer.

    ⚠️ NÃO verifica a regra de 80% de presença no período aquisitivo —
    assume elegibilidade. Ver aba Ajuda para essa limitação documentada.

    `usage_dates`: lista de `date` — cada uma representa 1 dia de Yukyu
    já registrado no calendário (status="yukyu").
    """
    MARCOS_MESES_DIAS = [
        (6, 10), (18, 11), (30, 12), (42, 14),
        (54, 16), (66, 18), (78, 20),
    ]

    grants = []
    for meses, dias in MARCOS_MESES_DIAS:
        gd = _add_months(hire_date, meses)
        if gd <= today:
            grants.append((gd, dias))
    # Depois de 6a6m (78 meses), continua concedendo 20 dias a cada 12 meses
    meses_extra = 78 + 12
    while True:
        gd = _add_months(hire_date, meses_extra)
        if gd > today:
            break
        grants.append((gd, 20))
        meses_extra += 12

    grants.sort(key=lambda g: g[0])
    ledger = [
        {"grant_date": gd, "dias": dias, "expiry": _add_months(gd, 24), "usado": 0}
        for gd, dias in grants
    ]

    usos_invalidos = []
    for u in sorted(usage_dates):
        alvo = None
        for g in ledger:
            if g["grant_date"] <= u < g["expiry"] and g["usado"] < g["dias"]:
                alvo = g
                break
        if alvo:
            alvo["usado"] += 1
        else:
            usos_invalidos.append(u)

    saldo_disponivel = sum(g["dias"] - g["usado"] for g in ledger if g["expiry"] > today)
    total_concedido   = sum(g["dias"] for g in ledger)
    total_usado        = sum(g["usado"] for g in ledger)
    total_expirado      = sum(g["dias"] - g["usado"] for g in ledger if g["expiry"] <= today)

    proxima_concessao = None
    if grants:
        ultimo_marco_meses = None
        for meses, _ in MARCOS_MESES_DIAS:
            if _add_months(hire_date, meses) > today:
                ultimo_marco_meses = meses
                break
        if ultimo_marco_meses is None:
            # Já passou de todos os marcos fixos; próxima é a anual de 20
            m = 78
            while _add_months(hire_date, m) <= today:
                m += 12
            proxima_concessao = (_add_months(hire_date, m), 20)
        else:
            dias_marco = next(d for m, d in MARCOS_MESES_DIAS if m == ultimo_marco_meses)
            proxima_concessao = (_add_months(hire_date, ultimo_marco_meses), dias_marco)
    else:
        # Ainda nenhuma concessão — a próxima é a primeira (6 meses)
        proxima_concessao = (_add_months(hire_date, 6), 10)

    return {
        "saldo_disponivel": saldo_disponivel,
        "total_concedido": total_concedido,
        "total_usado": total_usado,
        "total_expirado": total_expirado,
        "usos_invalidos": usos_invalidos,
        "proxima_concessao_data": proxima_concessao[0] if proxima_concessao else None,
        "proxima_concessao_dias": proxima_concessao[1] if proxima_concessao else None,
        "detalhe_concessoes": ledger,
    }


def compute_monthly_forecast(
    year: int, month: int, jikyuu: int, anchor_date: date, group: str,
    holiday_days: list, day_overrides: dict, odd_month_bonus: int, extra_bonus: int,
    deduction_mode: str, fixed_deduction: int, history_avg_deduction: float, block: int,
    shift_type_cfg: str = "", cfg_start: str = "", cfg_end: str = "",
    cfg_break: int = 65, cfg_ot: str = "",
    cycle_type: str = "4x2",
    alt_start_day: str = "08:35", alt_end_day: str = "20:35",
    alt_start_night: str = "20:35", alt_end_night: str = "08:35",
    fixed_monthly_bonus: int = 0,  # adicional fixo todo mês (liderança, etc.)
    monthly_allowance: int = 0,  # abono mensal SEPARADO — nunca entra no
                                  # cálculo de arredondamento de extra/
                                  # noturno/domingo, só soma no bruto
    round_mode: str = "truncate",
    wage_round_mode: str = "up",
    use_leader_addon: bool = False, leader_addon_hours: float = 168,
    night_interval_minutes: int = 0,
    anchor_group: str = None,
    alt_monthly_rest_pattern: str = "5x2", shift_anchor_date: date = None,
    break_periods: list = None,
) -> dict:
    # ── Seleção do tipo de ciclo ──────────────────────────────────
    _alt_shift_map = {}  # dia -> "day"/"night" (só usado se cycle_type=alternating*)
    if cycle_type == "5x2":
        cycle = generate_weekly_calendar(year, month)
    elif cycle_type == "alternating":
        _alt_raw = generate_alternating_calendar(anchor_date, year, month)
        cycle = {d: status for d, (status, shift) in _alt_raw.items()}
        _alt_shift_map = {d: shift for d, (status, shift) in _alt_raw.items()}
    elif cycle_type == "alternating_monthly":
        _shift_anchor = shift_anchor_date if shift_anchor_date else anchor_date
        _alt_raw = generate_alternating_monthly_calendar(
            _shift_anchor, year, month,
            rest_pattern=alt_monthly_rest_pattern,
            rest_anchor_date=anchor_date, group=group, anchor_group=anchor_group,
        )
        cycle = {d: status for d, (status, shift) in _alt_raw.items()}
        _alt_shift_map = {d: shift for d, (status, shift) in _alt_raw.items()}
    else:
        cycle = generate_4x2_calendar(anchor_date, year, month, group, anchor_group)

    _stype        = shift_type_cfg if shift_type_cfg else ("night" if group == "B" else "day")
    default_shift = _stype
    _start        = cfg_start if cfg_start else ("20:35" if _stype == "night" else "08:35")
    _end          = cfg_end   if cfg_end   else ("08:35" if _stype == "night" else "20:35")
    _break        = cfg_break if cfg_break else 65
    _ot           = cfg_ot    if cfg_ot    else ("06:35" if _stype == "night" else "18:35")
    total_base = total_ot = total_night = total_holiday = total_legal = total_abono = 0
    total_yukyu = 0
    total_ot_min = total_night_min = total_regular_min = 0
    total_holiday_min = total_legal_min = total_yukyu_min = 0
    _rate_ot = _rate_night = _rate_holiday = _rate_base = 0
    days_normal = days_holiday = days_legal = days_yukyu = 0

    for day_num, cycle_status in cycle.items():
        # No modo alternado (semanal ou mensal), o turno do dia muda
        if cycle_type in ("alternating", "alternating_monthly") and day_num in _alt_shift_map:
            _day_shift = _alt_shift_map[day_num]
            default_shift = _day_shift
            if _day_shift == "day":
                _start, _end, _ot = alt_start_day, alt_end_day, (cfg_ot if cfg_ot else "18:35")
            else:
                _start, _end, _ot = alt_start_night, alt_end_night, (cfg_ot if cfg_ot else "06:35")
        ov        = day_overrides.get(str(day_num), {})
        status    = ov.get("status", "normal")   # "normal","absent","yukyu","holiday","legal"
        start_str = ov.get("start", "")
        end_str   = ov.get("end", "")
        break_min = int(ov.get("break_min", _break) or _break)
        yukyu_hol = ov.get("yukyu_on_holiday", False)
        has_time  = bool(start_str)              # tem horário registrado manualmente
        day_abono = int(ov.get("abono", 0) or 0)   # abono/vale do dia
        day_extra_min = int(ov.get("extra_minutes", 0) or 0)  # 延長 do dia
        is_holiday = day_num in holiday_days

        try:
            weekday = date(year, month, day_num).weekday()
            is_sunday = (weekday == 6)
        except Exception:
            is_sunday = False

        # ── Regras por STATUS (o que foi salvo no day_overrides) ──────
        # Reestruturado para tratar 3 sinais como INDEPENDENTES, sem
        # ordem de prioridade frágil entre eles:
        #   1. cycle_status — só a escala (4x2/5x2/alternado) decide se
        #      o dia É PREVISTO pra trabalho ou não. NUNCA alterado por
        #      feriado ou domingo.
        #   2. is_holiday / is_sunday — só CARACTERÍSTICAS do dia no
        #      calendário. NUNCA alteram a escala.
        #   3. status (override manual) — só isso define COMO calcular.
        #
        # "\"absent\"  → falta → pular (¥0)\n"
        # "\"yukyu\"   → férias → jornada normal configurada, sem OT/noturno\n"
        # "\"holiday\"/\"legal\" → marcado manualmente → taxa cheia 1,35x\n"
        # "\"normal\"  → depende SÓ da escala (cycle_status), nunca de\n"
        #              feriado sozinho:\n"
        #   escala=off  + sem registro         → não trabalhou → pular\n"
        #   escala=off  + horário/yukyu_hol    → trabalhou na folga\n"
        #   escala=work + domingo              → taxa cheia 1,35x (sempre,\n"
        #                                         independente de feriado\n"
        #                                         corporativo também marcado)\n"
        #   escala=work + feriado (sem domingo)+ sem registro → feriado\n"
        #                                         corporativo/nacional NÃO\n"
        #                                         remunerado por padrão\n"
        #   escala=work + feriado + horário    → trabalhou no feriado\n"
        #   escala=work (sem feriado/domingo)  → turno normal\n"

        if status == "absent":
            continue   # falta — ¥0, não entra no cálculo

        elif status == "yukyu":
            shift_type = "yukyu"

        elif status in ("holiday", "legal"):
            # Marcado manualmente como feriado/domingo
            shift_type = "holiday"

        elif cycle_status == "off":
            # Dia de folga na ESCALA — feriado/domingo aqui não mudam
            # nada, só um dia que já não era previsto pra trabalhar.
            if has_time:
                shift_type = "holiday"   # trabalhou na folga → +35%
            elif yukyu_hol and is_holiday:
                shift_type = "yukyu"     # yukyu em feriado
            else:
                continue   # folga sem registro → não trabalhou

        else:
            # Dia PREVISTO pra trabalho pela escala (cycle_status=="work").
            # ORDEM CORRIGIDA (v2.52): feriado (nacional/corporativo) SEM
            # horário registrado vence sobre domingo — fábrica fechada é
            # fábrica fechada, mesmo caindo num domingo. Só vira "domingo
            # trabalhado" se tiver horário registrado (trabalhou mesmo
            # com a fábrica fechada) ou se não houver feriado nenhum
            # marcado nesse dia. Confirmado com caso real: dia 3 de
            # maio/2026 era domingo E feriado corporativo — a fábrica
            # estava fechada, ninguém trabalhou, e o dia devia ficar
            # como "não trabalhou" (¥0), não como domingo pago. A versão
            # anterior desta correção invertia essa prioridade (domingo
            # sempre vencia), o que resolvia o bug original mas quebrava
            # esse caso — feriado corporativo passava a não ter nenhum
            # efeito nos domingos, mesmo quando a fábrica realmente
            # fechava.
            if is_holiday and has_time:
                shift_type = "holiday"   # trabalhou no feriado/domingo → +35%
            elif is_holiday and yukyu_hol:
                shift_type = "yukyu"     # yukyu em feriado
            elif is_holiday:
                continue   # feriado (nacional/corporativo) sem registro → fábrica fechada, não trabalhou
            elif is_sunday:
                shift_type = "holiday"   # domingo normal trabalhado, sem feriado marcado
            elif status == "early":
                shift_type = default_shift   # horário real descontado automaticamente
            else:
                shift_type = default_shift   # dia normal de trabalho


        # Horários: override manual > configuração do usuário > padrão
        eff_start = start_str if start_str else _start
        eff_end   = end_str   if end_str   else _end
        eff_break = break_min if break_min != 65 else _break
        # Domingo (法定休日) também conta como feriado para o cálculo +35%
        is_pay_holiday = is_holiday or is_sunday
        pay = calculate_shift_pay(
            jikyuu=jikyuu, shift_type=shift_type,
            start_str=eff_start, end_str=eff_end,
            break_min=eff_break, block=block,
            is_holiday=is_pay_holiday, yukyu_on_holiday=yukyu_hol,
            base_shift=default_shift,  # turno real do funcionário (night/day),
                                        # usado para horários/limiar de OT mesmo
                                        # quando shift_type="holiday"
            round_mode=round_mode,
            wage_round_mode=wage_round_mode,
            use_leader_addon=use_leader_addon,
            leader_addon_amount=fixed_monthly_bonus,
            leader_addon_hours=leader_addon_hours,
            night_interval_minutes=night_interval_minutes,
            extra_minutes=day_extra_min,
            ot_start_str=_ot,  # horário configurado de início da hora extra
            cfg_start_str=_start, cfg_end_str=_end,  # horário de entrada/saída configurado
            break_periods=break_periods,
        )
        if (is_sunday and status != "yukyu") or status == "legal":
            # total_legal recebe SÓ a parcela de domingo (holiday_pay,
            # taxa 1,35x) — não pay["total_gross"] inteiro, porque agora
            # que night_pay deixou de ser zerado em dias de domingo,
            # somar o total_gross aqui DUPLICARIA o valor do noturno
            # (uma vez aqui, outra vez em total_night logo abaixo).
            #
            # is_sunday sozinho (sem "and not is_holiday") — domingo tem
            # prioridade sobre feriado corporativo/nacional, igual à
            # decisão de shift_type acima. Bug real corrigido: a condição
            # antiga excluía um domingo TAMBÉM marcado como feriado
            # corporativo dessa agregação, e ele caía por engano no
            # bloco de "dia normal" mais abaixo, mesmo com shift_type
            # já corretamente definido como "holiday".
            total_legal_min += pay["net_minutes"]
            total_night_min += pay["night_minutes"]  # mesmo em domingo
            days_legal  += 1
        elif status == "holiday" or is_holiday:
            total_holiday_min += pay["net_minutes"]
            total_night_min += pay["night_minutes"]
            days_holiday  += 1
        elif shift_type == "yukyu":
            # Separado de total_base — sem isso, o valor do Yukyu ficava
            # misturado com dias normais de trabalho em "Salário Base",
            # sem como comparar com o holerite real (que mostra Yukyu
            # como rubrica própria, com dias e horas separados).
            total_yukyu_min += pay["net_minutes"]
            if pay["base_pay"] > 0:
                days_yukyu += 1
        else:
            total_regular_min += pay["regular_minutes"]
            total_ot_min      += pay["overtime_minutes"]
            total_night_min   += pay["night_minutes"]
            if pay["base_pay"] > 0:
                days_normal += 1
        total_abono += day_abono
        # Taxas — CONSTANTES o mês inteiro (não dependem do dia
        # específico, só de jikyuu/adicional/modo configurados).
        # Capturadas a cada iteração por simplicidade — sempre o mesmo
        # valor, sem custo real de recomputar.
        _rate_ot      = pay["_ot_rate_full"]
        _rate_night   = pay["_night_rate_increment"]
        _rate_holiday = pay["_holiday_rate_full"]
        _rate_base    = pay["_jikyuu_per_min"]

    # Totais finais — taxa (constante o mês inteiro) × MINUTOS TOTAIS do
    # mês, arredondado UMA VEZ aqui, em vez de somar valores já
    # arredondados de cada dia individual. Evita acumular resíduo de
    # poucos yens quando as horas de uma categoria ficam espalhadas em
    # vários dias — cada arredondamento "pra cima" separado soma mais do
    # que arredondar o total do mês de uma vez, exatamente como o
    # holerite real calcula (confirmado: 33h × ¥2.011/h = ¥66.363 exato,
    # não a soma de vários dias arredondados individualmente).
    total_base    = shisha_gofuuu(_rate_base * total_regular_min, wage_round_mode)
    total_ot      = shisha_gofuuu(_rate_ot * (total_ot_min / 60.0), wage_round_mode)
    total_night   = shisha_gofuuu(_rate_night * (total_night_min / 60.0), wage_round_mode)
    total_holiday = shisha_gofuuu(_rate_holiday * (total_holiday_min / 60.0), wage_round_mode)
    total_legal   = shisha_gofuuu(_rate_holiday * (total_legal_min / 60.0), wage_round_mode)
    total_yukyu   = shisha_gofuuu(_rate_base * total_yukyu_min, wage_round_mode)

    applied_odd = odd_month_bonus if month % 2 == 1 else 0
    gross       = (total_base + total_ot + total_night + total_holiday + total_legal
                   + total_yukyu
                   + applied_odd + extra_bonus + total_abono + fixed_monthly_bonus
                   + monthly_allowance)
    deductions  = (fixed_deduction if deduction_mode == "fixed"
                   else shisha_gofuuu(history_avg_deduction))

    return {
        "base_pay": total_base, "overtime_pay": total_ot, "night_pay": total_night,
        "holiday_pay": total_holiday, "legal_holiday_pay": total_legal,
        "yukyu_pay": total_yukyu, "days_yukyu": days_yukyu,
        "odd_bonus": applied_odd, "extra_bonus": extra_bonus,
        "gross": gross, "deductions": deductions, "net": gross - deductions,
        "days_normal": days_normal, "days_holiday": days_holiday, "days_legal": days_legal,
        "abono_total": total_abono,
        "fixed_monthly_bonus": fixed_monthly_bonus,
        "monthly_allowance": monthly_allowance,
        "regular_hours": round(total_regular_min / 60, 1),
        "overtime_hours": round(total_ot_min / 60, 1),
        "night_hours": round(total_night_min / 60, 1),
        "holiday_hours": round(total_holiday_min / 60, 1),
        "legal_hours": round(total_legal_min / 60, 1),
        "yukyu_hours": round(total_yukyu_min / 60, 1),
    }

# ─────────────────────────────────────────────
#  MODAL HELPER — compatível com Flet 0.85
# ─────────────────────────────────────────────

def show_modal(page: ft.Page, title: str, content: ft.Control,
               actions: list, bgcolor: str = "#FFFFFF"):
    """Exibe um modal usando page.overlay (compatível com Flet 0.85)."""
    def _close(_=None):
        if _overlay in page.overlay:
            page.overlay.remove(_overlay)
        page.update()

    # Injetar _close nos botões que têm on_click=None (marcador)
    for btn in actions:
        if hasattr(btn, '_close_marker'):
            btn.on_click = lambda _: _close()

    _panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(title, size=14, color="#1A2535",
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.TextButton("✕", on_click=lambda _: _close(),
                                      style=ft.ButtonStyle(color="#64748B")),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=1, color="#333333"),
                content,
                ft.Divider(height=1, color="#333333"),
                ft.Row(controls=actions,
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],
            spacing=10, tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=bgcolor,
        border_radius=16,
        padding=16,
        width=min(360, int((page.width or 420) * 0.92)),
        border=ft.Border.all(1, "#333333"),
        shadow=ft.BoxShadow(blur_radius=20, color="#00000088",
                            offset=ft.Offset(0, 4)),
    )

    _overlay = ft.Container(
        content=ft.Column(
            controls=[_panel],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#88000000",
        expand=True,
        alignment=ft.Alignment(0, 0),
        on_click=lambda _: _close(),
    )
    # Evitar fechar ao clicar no painel
    _panel.on_click = lambda e: e.stop_propagation() if hasattr(e, 'stop_propagation') else None

    page.overlay.append(_overlay)
    page.update()
    return _close


# ─────────────────────────────────────────────
#  STORAGE
# ─────────────────────────────────────────────

KEY_SETTINGS  = "onion_settings"
KEY_HISTORY   = "onion_history"
KEY_OVERRIDES = "onion_overrides"
KEY_HOLIDAYS  = "onion_holidays"


# Feriados japoneses 2025-2026 embutidos no app
JP_HOLIDAYS_BUILTIN = {
    "2025-01": [1, 13],
    "2025-02": [11, 23, 24],
    "2025-03": [20],
    "2025-04": [29],
    "2025-05": [3, 4, 5, 6],
    "2025-07": [21],
    "2025-08": [11],
    "2025-09": [15, 23],
    "2025-10": [13],
    "2025-11": [3, 23, 24],
    "2025-12": [31],
    "2026-01": [1, 12],
    "2026-02": [11, 23],
    "2026-03": [20],
    "2026-04": [29],
    "2026-05": [3, 4, 5, 6],
    "2026-07": [20],
    "2026-08": [11],
    "2026-09": [21, 22, 23],
    "2026-10": [12],
    "2026-11": [3, 23],
    "2026-12": [31],
}

# Nomes dos feriados nacionais — jp, romaji, pt. Datas móveis calculadas
# e verificadas contra o dia da semana real (Python datetime) e fontes
# oficiais, não digitadas de memória. Cobre só 2025-2026 (mesmo range do
# JP_HOLIDAYS_BUILTIN acima) — feriados buscados automaticamente via
# fetch_updated_holidays() para anos futuros não têm nome aqui ainda; o
# modal simplesmente não mostra nome nesse caso (sem erro).
JP_HOLIDAY_NAMES_BUILTIN = {
    "2025-01-01": ("元日", "Ganjitsu", "Ano Novo"),
    "2025-01-13": ("成人の日", "Seijin no Hi", "Dia da Maioridade"),
    "2025-02-11": ("建国記念の日", "Kenkoku Kinen no Hi", "Dia da Fundação Nacional"),
    "2025-02-23": ("天皇誕生日", "Tennō Tanjōbi", "Aniversário do Imperador"),
    "2025-02-24": ("振替休日", "Furikae Kyūjitsu", "Feriado Substituto"),
    "2025-03-20": ("春分の日", "Shunbun no Hi", "Equinócio de Primavera"),
    "2025-04-29": ("昭和の日", "Shōwa no Hi", "Dia de Shōwa"),
    "2025-05-03": ("憲法記念日", "Kenpō Kinenbi", "Dia da Constituição"),
    "2025-05-04": ("みどりの日", "Midori no Hi", "Dia do Verde"),
    "2025-05-05": ("こどもの日", "Kodomo no Hi", "Dia das Crianças"),
    "2025-05-06": ("振替休日", "Furikae Kyūjitsu", "Feriado Substituto"),
    "2025-07-21": ("海の日", "Umi no Hi", "Dia do Mar"),
    "2025-08-11": ("山の日", "Yama no Hi", "Dia da Montanha"),
    "2025-09-15": ("敬老の日", "Keirō no Hi", "Dia do Respeito aos Idosos"),
    "2025-09-23": ("秋分の日", "Shūbun no Hi", "Equinócio de Outono"),
    "2025-10-13": ("スポーツの日", "Supōtsu no Hi", "Dia do Esporte"),
    "2025-11-03": ("文化の日", "Bunka no Hi", "Dia da Cultura"),
    "2025-11-23": ("勤労感謝の日", "Kinrō Kansha no Hi", "Dia de Ação de Graças pelo Trabalho"),
    "2025-11-24": ("振替休日", "Furikae Kyūjitsu", "Feriado Substituto"),
    "2025-12-31": ("大晦日", "Ōmisoka", "Véspera de Ano Novo (não é feriado oficial, uso comum)"),
    "2026-01-01": ("元日", "Ganjitsu", "Ano Novo"),
    "2026-01-12": ("成人の日", "Seijin no Hi", "Dia da Maioridade"),
    "2026-02-11": ("建国記念の日", "Kenkoku Kinen no Hi", "Dia da Fundação Nacional"),
    "2026-02-23": ("天皇誕生日", "Tennō Tanjōbi", "Aniversário do Imperador"),
    "2026-03-20": ("春分の日", "Shunbun no Hi", "Equinócio de Primavera"),
    "2026-04-29": ("昭和の日", "Shōwa no Hi", "Dia de Shōwa"),
    "2026-05-03": ("憲法記念日", "Kenpō Kinenbi", "Dia da Constituição"),
    "2026-05-04": ("みどりの日", "Midori no Hi", "Dia do Verde"),
    "2026-05-05": ("こどもの日", "Kodomo no Hi", "Dia das Crianças"),
    "2026-05-06": ("振替休日", "Furikae Kyūjitsu", "Feriado Substituto"),
    "2026-07-20": ("海の日", "Umi no Hi", "Dia do Mar"),
    "2026-08-11": ("山の日", "Yama no Hi", "Dia da Montanha"),
    "2026-09-21": ("敬老の日", "Keirō no Hi", "Dia do Respeito aos Idosos"),
    "2026-09-22": ("国民の休日", "Kokumin no Kyūjitsu", "Feriado Nacional (dia entre dois feriados)"),
    "2026-09-23": ("秋分の日", "Shūbun no Hi", "Equinócio de Outono"),
    "2026-10-12": ("スポーツの日", "Supōtsu no Hi", "Dia do Esporte"),
    "2026-11-03": ("文化の日", "Bunka no Hi", "Dia da Cultura"),
    "2026-11-23": ("勤労感謝の日", "Kinrō Kansha no Hi", "Dia de Ação de Graças pelo Trabalho"),
    "2026-12-31": ("大晦日", "Ōmisoka", "Véspera de Ano Novo (não é feriado oficial, uso comum)"),
}


async def fetch_updated_holidays() -> Optional[dict]:
    """Busca holidays.json (gerado uma vez por ano por um GitHub Action,
    a partir do CSV oficial do Gabinete do Governo japonês) em tempo de
    execução. Só funciona no modo web (Pyodide) — em desktop, ou se a
    busca falhar/der timeout por qualquer motivo (offline, primeira
    visita sem cache, arquivo ainda não existe), retorna None e quem
    chamou continua usando JP_HOLIDAYS_BUILTIN como reserva. Nunca
    lança exceção — falha sempre em silêncio, de propósito.
    """
    if pyfetch is None:
        return None
    try:
        resp = await asyncio.wait_for(pyfetch("holidays.json", method="GET"), timeout=5)
        if resp.status != 200:
            return None
        data = await asyncio.wait_for(resp.json(), timeout=5)
        if not isinstance(data, dict) or not data:
            return None
        return data
    except Exception:
        return None


DEFAULT_SETTINGS = {
    "jikyuu": 1500, "group": "B", "anchor_date": date.today().isoformat(),
    "hire_date": None,  # Data de Admissão — separada de anchor_date (turno), usada só para Yukyu
    "odd_bonus": 50000, "deduction_mode": "historical", "fixed_deduction": 45000,
    "block": 1, "round_mode": "truncate", "pin_enabled": False,
    # v2.49: Taxa de Referência (premium_allowances_monthly/
    # premium_standard_hours/night_addon_extra) DESCONTINUADA — sempre
    # ficou escondida atrás de um switch desligado, nunca exposta na
    # tela. Substituída por wage_round_mode + use_leader_addon, que
    # reaproveitam o campo fixed_monthly_bonus já existente em vez de
    # duplicar o valor num campo separado.
    "wage_round_mode": "up", "use_leader_addon": False,
    "leader_addon_hours": 168,
    "night_interval_minutes": 0,
    "anchor_group": None,
    "cycle_type_confirmed": False,
    "disclaimer_accepted": False,
    "disclaimer_accepted_at": None,  # timestamp ISO de quando o usuário clicou Aceitar
    "break_periods_enabled": False,   # recurso avançado opcional (v2.33)
    "break_periods_detailed": [],     # lista de {"start":"HH:MM","end":"HH:MM"}
    "seikaikin_threshold_pct": 100,   # limiar do 精皆勤手当 (adicional de assiduidade, opcional por empresa)
    "shift_type": "night", "shift_start": "20:35", "shift_end": "08:35",
    "shift_break": 65, "shift_ot": "06:35", "extra_bonus": 0,
    "fixed_monthly_bonus": 0,  # adicional fixo todo mês (ex: liderança)
    "monthly_allowance": 0,  # abono mensal separado, não afeta arredondamento
    "cycle_type": "4x2",  # "4x2" | "5x2" | "alternating" | "alternating_monthly"
    "alt_monthly_rest_pattern": "5x2",  # "5x2" | "4x2" — só usado em alternating_monthly
    "shift_anchor_date": None,  # só usado em alternating_monthly (mês de referência diurno)
    "shift_start_day": "08:35", "shift_end_day": "20:35",
    "shift_start_night": "20:35", "shift_end_night": "08:35",
}


# Cache em memória — espelha o storage persistente
_mem_cache: dict = {}


def _has_shared_prefs(page: ft.Page) -> bool:
    """Verifica se page.shared_preferences existe (Flet >= 0.80)."""
    try:
        sp = page.shared_preferences
        return sp is not None
    except Exception:
        return False


def load_json(page: ft.Page, key: str, default):
    """Lê do cache em memória (já populado no boot, de forma síncrona
    a partir dos dados carregados via shared_preferences assíncrono)."""
    if key in _mem_cache:
        return _mem_cache[key]
    return default


def save_json(page: ft.Page, key: str, value):
    """Salva no cache em memória IMEDIATAMENTE (síncrono — a UI sempre
    reflete o dado mais recente), e dispara a gravação persistente em
    segundo plano via page.shared_preferences (API atual do Flet,
    assíncrona). Isso é 'fire and forget': não bloqueia a UI, mas
    garante persistência real em disco do dispositivo."""
    _mem_cache[key] = value
    serialized = json.dumps(value)

    async def _persist():
        try:
            if _has_shared_prefs(page):
                await page.shared_preferences.set(key, serialized)
        except Exception:
            pass

    try:
        page.run_task(_persist)
    except Exception:
        pass


def remove_storage(page: ft.Page, key: str):
    _mem_cache.pop(key, None)

    async def _remove():
        try:
            if _has_shared_prefs(page):
                await page.shared_preferences.remove(key)
        except Exception:
            pass

    try:
        page.run_task(_remove)
    except Exception:
        pass


async def boot_load_storage(page: ft.Page):
    """Lê todos os dados persistidos via shared_preferences (API atual
    do Flet >= 0.80, assíncrona) e popula o cache em memória.

    Esta função é async e DEVE ser aguardada (await) antes de montar
    a UI, garantindo que os dados salvos anteriormente estejam
    disponíveis assim que o app aparecer na tela."""
    if not _has_shared_prefs(page):
        return
    for key in (KEY_SETTINGS, KEY_HISTORY, KEY_OVERRIDES,
                KEY_HOLIDAYS, "onion_holidays_corp"):
        try:
            raw = await page.shared_preferences.get(key)
        except Exception:
            raw = None

        if raw and raw not in ("null", "undefined", None, ""):
            try:
                _mem_cache[key] = json.loads(raw)
            except Exception:
                pass


# ─────────────────────────────────────────────
#  TOKENS
# ─────────────────────────────────────────────

# ── Sistema de Cores — Onion Payroll ─────────────────────────────
#
# ESCALA DE CINZA WCAG
GRAY_50   = "#F9F9F9"
GRAY_100  = "#F0F0F0"
GRAY_200  = "#E0E0E0"
GRAY_300  = "#D1D1D1"
GRAY_400  = "#BDBDBD"
GRAY_600  = "#757575"
GRAY_800  = "#424242"
GRAY_900  = "#212121"

# PALETA PRINCIPAL
BG_DEEP        = "#121212"   # Fundo principal
BG_CARD        = "#1E1E1E"   # Cards e painéis elevados
BG_SURFACE     = "#2A2A2A"   # Inputs e superfícies

# ACENTOS — Petronas Cyan
ACCENT         = "#00D2C6"   # Destaque principal
BUILD_ID       = "2607111713"   # atualizado automaticamente pelo deploy.ps1
ACCENT_LITE    = "#5EEAD4"   # Turquesa claro
ACCENT_DARK    = "#009E94"   # Turquesa escuro

# CALENDÁRIO — Paleta Google Calendar oficial
# FUNDO das células = cor Google vibrante
# NÚMEROS = branco brilhante (#FFFFFF) sobre fundo colorido
WORK_COLOR     = "#0F9D58"   # Sage — verde Google (fundo célula trabalho)
OFF_COLOR      = "#4285F4"   # Peacock — azul Google (fundo célula folga)
HOL_COLOR      = "#DB4437"   # Tomato — vermelho Google (fundo feriado JP)
CAL_YUKYU      = "#FF6D00"   # Tangerine — laranja Google (yukyu 有休)
CAL_CORP       = "#F4B400"   # Banana — amarelo Google (fundo feriado corp)
CAL_MODIF      = "#7B1FA2"   # Grape — roxo Google (falta 欠勤)

# NÚMEROS — brancos brilhantes sobre fundo colorido
CAL_SUNDAY_WORK = "#C62828"  # Domingo trabalhado — vermelho escuro
CAL_TEXT_WORK  = "#FFFFFF"   # branco sobre verde
CAL_TEXT_OFF   = "#FFFFFF"   # branco sobre azul
CAL_TEXT_HOL   = "#FFFFFF"   # branco sobre vermelho
CAL_TEXT_CORP  = "#212121"   # escuro sobre amarelo (legibilidade)
CAL_TEXT_YUKYU = "#FFFFFF"   # branco sobre laranja
CAL_TEXT_MODIF = "#FFFFFF"   # branco sobre lilás
CAL_BORDER_WORK= "#34A853"   # borda verde mais clara
CAL_BORDER_OFF = "#669DF6"   # borda azul mais clara

# TEXTO
TEXT_PRIMARY   = "#F0F0F0"   # Texto principal
TEXT_SECONDARY = "#A0A0A0"   # Texto secundário
TEXT_MUTED     = "#D0D0D0"   # Texto hints — mais claro para contraste

# SEMÂNTICAS
SUCCESS        = "#00D2C6"   # Turquesa — valores positivos
WARNING        = "#FFB74D"   # Âmbar claro
DANGER         = "#EF5350"   # Vermelho
YEN_GOLD       = "#F0F0F0"   # Salário líquido — branco puro

# HEADER E NAV
HEADER_BG      = "#0A0A0A"   # Quase preto
NAV_BG         = "#0A0A0A"   # Quase preto
NAV_BORDER     = "#00D2C6"   # Linha turquesa


# FUNDO DO APP
BG_DEEP        = "#2c2c2a"   # Fundo principal — cinza escuro quente
BG_CARD        = "#404040"   # Cards — escuro como campo do chat
BG_SURFACE     = "#4a4a4a"   # Inputs — ligeiramente mais claro que o card

# ACENTOS
ACCENT         = "#00C2A8"   # Turquesa principal
ACCENT_LITE    = "#5EEAD4"   # Turquesa claro (sobre escuro)
ACCENT_DARK    = "#007A6E"   # Turquesa escuro

# CALENDÁRIO — cores dos dias
WORK_COLOR     = "#0F9D58"   # Trabalho — verde escuro saturado
OFF_COLOR      = "#4285F4"   # Folga — azul escuro saturado
HOL_COLOR      = "#DB4437"   # Feriado nacional — Tomato, vermelho Google vibrante (igual ao 1º bloco — estava escuro e quase invisível)

# TEXTO (sobre fundo escuro #2c2c2a)
TEXT_PRIMARY   = "#F9F9F9"   # Cinza 50 — máximo contraste
TEXT_SECONDARY = "#BDBDBD"   # Cinza 400 — legível e suave
TEXT_MUTED     = "#BDBDBD"   # Cinza 400 — dicas e hints (sobre fundo escuro)

# SEMÂNTICAS
SUCCESS        = "#34D399"   # Verde claro
WARNING        = "#FBB940"   # Âmbar claro
DANGER         = "#F87171"   # Vermelho claro
YEN_GOLD       = "#F0C040"   # Dourado — salário líquido

# HEADER E NAV
HEADER_BG      = "#212121"   # Cinza 900
NAV_BG         = "#212121"   # Cinza 900
NAV_BORDER     = "#00C2A8"   # Linha turquesa separadora

# CALENDÁRIO — texto e bordas
CAL_YUKYU      = "#4a2800"   # Yukyu — laranja escuro
CAL_CORP       = "#F4B400"   # Feriado corp — amarelo Google (Banana)
CAL_MODIF      = "#2d1a4a"   # Modificado — roxo escuro
CAL_TEXT_WORK  = "#C8F7DC"   # verde claro
CAL_TEXT_OFF   = "#DBEAFE"   # azul claro
CAL_TEXT_HOL   = "#fca5a5"   # vermelho claro
CAL_TEXT_CORP  = "#212121"   # escuro sobre amarelo (legibilidade)
CAL_TEXT_YUKYU = "#fb923c"   # laranja médio
CAL_TEXT_MODIF = "#c4b5fd"   # lilás claro
CAL_BORDER_WORK= "#7ade9f"   # verde médio
CAL_BORDER_OFF = "#a0c3ed"   # azul médio


def card(content, padding=16, margin=8):
    return ft.Container(
        content=content, bgcolor=BG_CARD, border_radius=16,
        padding=padding, margin=margin,
        border=ft.Border.all(1, "#333333"),
    )


def divider():
    return ft.Divider(height=1, color="#333333")


def yen(amount: int) -> str:
    return f"¥{amount:,}"


def section_header(title: str):
    return ft.Container(
        content=ft.Text(title, size=scaled(13), color=ACCENT_LITE,
                        weight=ft.FontWeight.W_600,
                        style=ft.TextStyle(letter_spacing=1.2)),
        padding=ft.Padding(left=4, right=0, top=10, bottom=6),
    )


# ─────────────────────────────────────────────
#  TAB 1 — CALENDAR
# ─────────────────────────────────────────────

def build_calendar_tab(page: ft.Page, state: dict, refresh_all):
    settings       = state["settings"]
    overrides      = state["overrides"]
    holidays       = state["holidays"]
    today          = date.today()
    view_year      = state.get("cal_year",  today.year)
    view_month     = state.get("cal_month", today.month)

    try:
        anchor = date.fromisoformat(settings["anchor_date"])
    except Exception:
        anchor = today

    _cycle_type = settings.get("cycle_type", "4x2")
    if _cycle_type == "5x2":
        cycle = generate_weekly_calendar(view_year, view_month)
    elif _cycle_type == "alternating":
        _alt_raw = generate_alternating_calendar(anchor, view_year, view_month)
        cycle = {d: status for d, (status, shift) in _alt_raw.items()}
    elif _cycle_type == "alternating_monthly":
        try:
            _shift_anchor = date.fromisoformat(settings.get("shift_anchor_date") or settings["anchor_date"])
        except Exception:
            _shift_anchor = anchor
        _alt_raw = generate_alternating_monthly_calendar(
            _shift_anchor, view_year, view_month,
            rest_pattern=settings.get("alt_monthly_rest_pattern", "5x2"),
            rest_anchor_date=anchor, group=settings.get("group", "A"),
            anchor_group=settings.get("anchor_group"),
        )
        cycle = {d: status for d, (status, shift) in _alt_raw.items()}
    else:
        cycle = generate_4x2_calendar(anchor, view_year, view_month, settings.get("group", "A"),
                                       settings.get("anchor_group"))
    month_key       = f"{view_year}-{view_month:02d}"
    month_overrides = overrides.get(month_key, {})
    month_holidays  = holidays.get(month_key, [])
    holidays_corp   = state.get("holidays_corp", {})
    month_hol_corp  = holidays_corp.get(month_key, [])

    # ── Day modal ────────────────────────────────────────────────────
    def open_day_modal(day_num: int):
        ov     = month_overrides.get(str(day_num), {})

        status_dd = _ValueHolder(ov.get("status", "normal"))
        # (chave, label PT principal, label JP secundário p/ localizar no
        # holerite real, descrição completa exibida abaixo)
        STATUS_OPCOES = [
            ("normal",  "Normal",             "",       "Preencha Entrada/Saída para horário real (inclusive saída antecipada)"),
            ("early",   "Saída Antecipada",   "",       "Saída Antecipada — horário real"),
            ("absent",  "Falta",              "欠勤",    "Falta 欠勤"),
            ("yukyu",   "Folga Remunerada",   "有休",    "有休 Yukyu — jornada normal, sem 残業/noturno"),
            ("holiday", "Feriado 1,35x",      "休出",    "休出 Trabalho em Feriado (taxa cheia 1,35x)"),
            ("legal",   "Domingo 1,35x",      "法定休出", "法定休出 Domingo/Folga Legal (taxa cheia 1,35x)"),
        ]
        status_desc = ft.Text(
            next((d for k, _, _, d in STATUS_OPCOES if k == status_dd.value), ""),
            size=10, color=TEXT_MUTED,
        )
        status_label = ft.Text("Status", size=12, color="#A0A0A0")

        def _status_btn_content(pt, jp, ativo):
            cor = "#121212" if ativo else TEXT_PRIMARY
            controls = [ft.Text(pt, size=12, weight=ft.FontWeight.W_600, color=cor)]
            if jp:
                controls.append(ft.Text(jp, size=9, color=cor if ativo else TEXT_MUTED))
            return ft.Column(controls=controls, spacing=0, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        _status_btns = {}
        for key, pt, jp, _desc in STATUS_OPCOES:
            ativo = (key == status_dd.value)
            btn = ft.FilledButton(
                content=_status_btn_content(pt, jp, ativo), data=key,
                style=ft.ButtonStyle(bgcolor=ACCENT if ativo else BG_SURFACE),
                expand=1,
            )
            _status_btns[key] = btn
        status_grid = ft.Column(controls=[
            ft.Row([_status_btns["normal"], _status_btns["early"]], spacing=6),
            ft.Row([_status_btns["absent"], _status_btns["yukyu"]], spacing=6),
            ft.Row([_status_btns["holiday"], _status_btns["legal"]], spacing=6),
        ], spacing=6)
        start_f = ft.TextField(
            label="Entrada (HH:MM)", value=ov.get("start", ""),
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
            expand=1,
        )
        end_f = ft.TextField(
            label="Saída (HH:MM)", value=ov.get("end", ""),
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
            expand=1,
        )
        break_f = ft.TextField(
            label="Intervalo (min)", value=str(ov.get("break_min", 65)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )
        yukyu_sw = ft.Switch(
            label="有休 em Feriado",
            value=ov.get("yukyu_on_holiday", False),
            active_color=ACCENT,
            label_text_style=ft.TextStyle(color=TEXT_SECONDARY, size=11),
        )
        extra_min_f = ft.TextField(
            label="延長 Minutos extras solicitados",
            hint_text="ex: 30",
            value=str(ov.get("extra_minutes", 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=BG_SURFACE, color=TEXT_PRIMARY,
            border_color="#333333", focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY, size=11),
        )
        abono_f = ft.TextField(
            label="Abono / Vale / Bico extra (¥)",
            hint_text="ex: arubaito, gorjeta, vale-transporte extra",
            value=str(ov.get("abono", 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=BG_SURFACE, color=TEXT_PRIMARY,
            border_color="#333333", focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY, size=11),
        )

        ov_ref = [None]
        preview_text = ft.Text("", size=11, color=ACCENT_LITE)

        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()

        def _update_preview(_=None):
            st      = status_dd.value or "normal"
            s       = start_f.value.strip()
            e       = end_f.value.strip()
            try:    brk = int(break_f.value or 65)
            except: brk = 65
            jikyuu  = int(state["settings"].get("jikyuu", 1500))
            grp     = state["settings"].get("group", "B")
            # Prefere o Turno explícito configurado (⚙️ Config) — a
            # heurística por grupo só entra como último recurso, igual
            # ao que compute_monthly_forecast já faz.
            stype   = state["settings"].get("shift_type") or ("night" if grp == "B" else "day")
            ot_cfg  = state["settings"].get("shift_ot") or ("06:35" if stype == "night" else "18:35")
            cfg_start = state["settings"].get("shift_start") or ("20:35" if stype == "night" else "08:35")
            cfg_end   = state["settings"].get("shift_end")   or ("08:35" if stype == "night" else "20:35")
            _wage_rm  = state["settings"].get("wage_round_mode", "up")
            _use_addon = bool(state["settings"].get("use_leader_addon", False))
            _addon_amt = int(state["settings"].get("fixed_monthly_bonus") or 0)
            _addon_hrs = float(state["settings"].get("leader_addon_hours") or 168)
            _night_int_min = int(state["settings"].get("night_interval_minutes") or 0)
            is_hol_day = day_num in month_holidays
            cycle_st   = cycle.get(day_num, "off")
            is_off_day = (cycle_st == "off") or is_hol_day

            if st == "absent":
                preview_text.value = "欠勤: ¥0 — falta não remunerada"

            elif st == "yukyu":
                if s and e:
                    # Yukyu parcial: horas reais, sem 残業/noturno
                    pay = calculate_shift_pay(jikyuu, "yukyu",
                                              start_str=s, end_str=e,
                                              break_min=brk, wage_round_mode=_wage_rm)
                    preview_text.value = (
                        f"有休 parcial: {pay['net_minutes']}min → "
                        f"{yen(pay['base_pay'])} (sem 残業/noturno)"
                    )
                else:
                    # Sem horário: usa a JORNADA NORMAL configurada (não
                    # mais 8h fixo) — precisa do base_shift/ot_start_str/
                    # cfg_start_str/cfg_end_str reais pra bater com o que
                    # compute_monthly_forecast calcula de verdade.
                    pay = calculate_shift_pay(jikyuu, "yukyu",
                                              break_min=brk, base_shift=stype,
                                              ot_start_str=ot_cfg,
                                              cfg_start_str=cfg_start, cfg_end_str=cfg_end,
                                              wage_round_mode=_wage_rm)
                    _horas_yk = pay["net_minutes"] / 60
                    preview_text.value = (
                        f"有休 dia completo: {yen(pay['base_pay'])} "
                        f"({_horas_yk:g}h × ¥{jikyuu}/h, sem 残業/noturno)"
                    )

            elif is_off_day and not s:
                # Folga/feriado sem horário preenchido
                if yukyu_sw.value and is_hol_day:
                    pay = calculate_shift_pay(jikyuu, "yukyu",
                                              break_min=brk, base_shift=stype,
                                              ot_start_str=ot_cfg,
                                              cfg_start_str=cfg_start, cfg_end_str=cfg_end,
                                              wage_round_mode=_wage_rm)
                    _horas_yk = pay["net_minutes"] / 60
                    preview_text.value = f"有休 em feriado: {yen(pay['base_pay'])} ({_horas_yk:g}h base)"
                else:
                    preview_text.value = "Folga / feriado — sem trabalho registrado"

            elif is_off_day and s:
                # Trabalhou em folga/feriado → +35% holiday premium
                # base_shift = turno real do funcionário (night/day),
                # necessário para o limiar de OT correto mesmo em feriado
                pay = calculate_shift_pay(jikyuu, "holiday",
                                          start_str=s, end_str=e,
                                          break_min=brk, is_holiday=True,
                                          base_shift=stype, ot_start_str=ot_cfg,
                                          cfg_start_str=cfg_start, cfg_end_str=cfg_end,
                                          wage_round_mode=_wage_rm,
                                          use_leader_addon=_use_addon,
                                          leader_addon_amount=_addon_amt,
                                          leader_addon_hours=_addon_hrs,
                                          night_interval_minutes=_night_int_min)
                nm = pay["net_minutes"]
                parts = [f"base {yen(pay['base_pay'])}",
                         f"休出 +{yen(pay['holiday_pay'])}"]
                if pay["overtime_pay"]:
                    parts.append(f"残業 +{yen(pay['overtime_pay'])}")
                if pay["night_pay"]:
                    parts.append(f"深夜 +{yen(pay['night_pay'])}")
                preview_text.value = (
                    f"Folga/feriado trabalhado — "
                    f"{nm}min → {' | '.join(parts)} = {yen(pay['total_gross'])}"
                )

            else:
                # Dia de trabalho normal (com ou sem horário customizado)
                try: extra_m = int(extra_min_f.value or 0)
                except: extra_m = 0
                pay = calculate_shift_pay(jikyuu, stype,
                                          start_str=s, end_str=e, break_min=brk,
                                          ot_start_str=ot_cfg,
                                          cfg_start_str=cfg_start, cfg_end_str=cfg_end,
                                          wage_round_mode=_wage_rm,
                                          use_leader_addon=_use_addon,
                                          leader_addon_amount=_addon_amt,
                                          leader_addon_hours=_addon_hrs,
                                          night_interval_minutes=_night_int_min,
                                          extra_minutes=extra_m)
                nm = pay["net_minutes"]
                parts = [f"base {yen(pay['base_pay'])}"]
                if pay["overtime_pay"]:
                    parts.append(f"残業 +{yen(pay['overtime_pay'])}")
                if pay["night_pay"]:
                    parts.append(f"深夜 +{yen(pay['night_pay'])}")
                suffix = " (saída antecipada)" if e and not pay["overtime_pay"] else ""
                if extra_m > 0:
                    suffix += f" [inclui {extra_m}min de 延長]"
                preview_text.value = (
                    f"{nm}min → {' | '.join(parts)} = {yen(pay['total_gross'])}{suffix}"
                    )
            page.update()

        def _set_status(key):
            status_dd.value = key
            status_desc.value = next((d for k, _, _, d in STATUS_OPCOES if k == key), "")
            for k, pt, jp, _desc in STATUS_OPCOES:
                btn = _status_btns[k]
                ativo = (k == key)
                btn.content = _status_btn_content(pt, jp, ativo)
                btn.style = ft.ButtonStyle(bgcolor=ACCENT if ativo else BG_SURFACE)
                btn.update()
            status_desc.update()
            _update_preview()
        for _key, _btn in _status_btns.items():
            _btn.on_click = (lambda k: lambda _: _set_status(k))(_key)

        def _norm_time(field):
            def _do(_):
                field.value = normalize_hhmm(field.value)
                field.update()
                _update_preview()
            return _do

        start_f.on_blur     = _norm_time(start_f)
        end_f.on_blur       = _norm_time(end_f)
        break_f.on_blur     = lambda _: _update_preview()
        extra_min_f.on_blur = lambda _: _update_preview()
        abono_f.on_blur     = lambda _: _update_preview()
        _update_preview()

        def _save(_=None):
            try: extra_m = int(extra_min_f.value or 0)
            except: extra_m = 0
            entry = {
                "status":           status_dd.value,
                "start":            start_f.value.strip(),
                "end":              end_f.value.strip(),
                "break_min":        int(break_f.value or 65),
                "yukyu_on_holiday": yukyu_sw.value,
                "extra_minutes":    extra_m,
                "abono":            int(abono_f.value or 0),
            }
            if month_key not in overrides:
                overrides[month_key] = {}
            overrides[month_key][str(day_num)] = entry
            save_json(page, KEY_OVERRIDES, overrides)
            _close()
            refresh_all()

        def _remove(_=None):
            if month_key in overrides and str(day_num) in overrides[month_key]:
                del overrides[month_key][str(day_num)]
                save_json(page, KEY_OVERRIDES, overrides)
            _close()
            refresh_all()

        # Verificar tipo de feriado ANTES de montar o texto de exibição —
        # hol_text tinha um bug: sempre mostrava "🏭 Feriado da Empresa",
        # mesmo quando era feriado NACIONAL, porque a distinção certa só
        # era calculada depois, pra outra coisa.
        _hol_key   = f"{view_year}-{view_month:02d}"
        _jp_hols   = state.get("holidays", {}).get(_hol_key, [])
        _corp_hols = state.get("holidays_corp", {}).get(_hol_key, [])
        _is_jp_hol   = day_num in _jp_hols
        _is_corp_hol = day_num in _corp_hols

        if _is_jp_hol:
            _hol_date_key = f"{view_year}-{view_month:02d}-{day_num:02d}"
            _hol_names = JP_HOLIDAY_NAMES_BUILTIN.get(_hol_date_key)
            if _hol_names:
                _jp_name, _romaji_name, _pt_name = _hol_names
                hol_text = ft.Container(
                    content=ft.Column(controls=[
                        ft.Text(f"🏮 {_jp_name}", size=13,
                                weight=ft.FontWeight.W_700, color=HOL_COLOR),
                        ft.Text(_romaji_name, size=11, color="#6B4A4A", italic=True),
                        ft.Text(_pt_name, size=12, color="#3D2020",
                                weight=ft.FontWeight.W_600),
                    ], spacing=2, tight=True),
                    visible=True,
                    padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                    bgcolor="#FEE2E2", border_radius=8,
                    border=ft.Border.all(1, HOL_COLOR),
                )
            else:
                # Feriado nacional buscado automaticamente (ano futuro,
                # fora do range 2025-2026 da tabela de nomes) — mostra
                # só o rótulo genérico, sem nome específico.
                hol_text = ft.Container(
                    content=ft.Text("🏮 Feriado Nacional", size=11, color=DANGER),
                    visible=True,
                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                    bgcolor="#FEE2E2", border_radius=8,
                )
        elif _is_corp_hol:
            hol_text = ft.Container(
                content=ft.Text("🏭 Feriado da Empresa", size=11, color=DANGER),
                visible=True,
                padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                bgcolor="#FEE2E2", border_radius=8,
            )
        else:
            hol_text = ft.Container(visible=False)

        if _is_jp_hol:
            _hol_label = " 🏮 Feriado Nacional"
        elif _is_corp_hol:
            _hol_label = " 🏭 Feriado Corporativo"
        else:
            _hol_label = ""

        panel = ft.Container(
            content=ft.Column(controls=[
                # Título
                ft.Row(controls=[
                    ft.Text(f"{view_year}/{view_month:02d}/{day_num:02d}{_hol_label} — Ponto",
                            size=13, color=TEXT_PRIMARY,
                            weight=ft.FontWeight.W_700, expand=True),
                    ft.TextButton("✕", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color="#333333"),
                hol_text,
                status_label,
                status_grid,
                status_desc,
                # Entrada e Saída na mesma linha com expand
                ft.Row([start_f, end_f], spacing=8),
                break_f,
                yukyu_sw,
                extra_min_f,
                abono_f,
                # Preview
                ft.Container(
                    content=preview_text,
                    bgcolor=BG_SURFACE, border_radius=6,
                    padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                ),
                ft.Divider(height=1, color="#333333"),
                ft.Row(controls=[
                    ft.TextButton("Remover", on_click=_remove,
                                  style=ft.ButtonStyle(color=DANGER)),
                    ft.FilledButton("Salvar", on_click=_save,
                                    style=ft.ButtonStyle(bgcolor=ACCENT, color="#121212")),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10, tight=True),
            bgcolor=BG_CARD, border_radius=14,
            padding=ft.Padding(left=16, right=16, top=14, bottom=14),
            # Largura adaptativa baseada na escala
            width=min(380, int(((page.width or page.window_width or 420)) * 0.92)),
            border=ft.Border.all(1, "#333333"),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        bg = ft.Container(
            content=ft.Column(
                controls=[ft.Container(height=20), panel],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor="#CC000000", expand=True, blur=ft.Blur(4, 4),
            alignment=ft.Alignment(0, -1),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    # Cores do calendário novo
    C_WORK    = WORK_COLOR    # verde escuro — trabalho
    C_OFF     = OFF_COLOR     # azul escuro  — folga
    C_HOL_CO  = CAL_CORP      # marrom escuro — feriado corporativo
    C_MODIF   = CAL_MODIF     # roxo escuro — modificado
    C_TODAY_B = "#00C2A8"     # borda turquesa hoje
    C_WHITE   = "#F9F9F9"     # texto claro sobre fundo escuro
    C_RED     = "#FF5252"     # domingo — vermelho brilhante
    C_BLUE    = "#90CAF9"     # sábado — azul brilhante

    # ── Day cell ─────────────────────────────────────────────────────
    def day_cell(day_num: int):
        is_hol   = day_num in month_holidays
        cycle_st = cycle.get(day_num, "off")
        ov       = month_overrides.get(str(day_num), {})
        status   = ov.get("status", "normal")
        has_time = bool(ov.get("start") or ov.get("end"))
        yukyu_hol = ov.get("yukyu_on_holiday", False)

        # Dia da semana: 0=Dom,1=Seg…6=Sáb (grade começa no domingo)
        weekday_col = (date(view_year, view_month, day_num).weekday() + 1) % 7

        is_sunday   = (weekday_col == 0)
        is_saturday = (weekday_col == 6)
        is_today    = (day_num == today.day
                       and view_month == today.month
                       and view_year  == today.year)

        # ── Determinar fundo da célula por status ───────────────────
        is_corp_hol = day_num in month_hol_corp
        modified    = (status in ("absent", "yukyu") or has_time or yukyu_hol)

        if status == "absent":
            bg = "#7B1FA2"       # 欠勤 Falta — roxo Google Grape
        elif status == "yukyu":
            bg = "#FF6D00"       # 有休 Yukyu — laranja Google Tangerine
        elif status == "early" or has_time or yukyu_hol:
            bg = "#00796B"       # Saiu mais cedo / horário customizado
        elif is_corp_hol:
            bg = C_HOL_CO        # Feriado corporativo — amarelo
        elif cycle_st == "off":
            bg = C_OFF           # Folga — azul
        elif is_sunday:
            bg = CAL_SUNDAY_WORK # Domingo trabalhado — vermelho escuro
        else:
            bg = C_WORK          # Trabalho — verde

        # ── Cor do número — branco sobre fundos coloridos ───────────
        if is_today and not modified:
            num_color = ACCENT
        elif status == "absent":
            num_color = "#FFFFFF"
        elif status == "yukyu":
            num_color = "#FFFFFF"
        elif has_time or yukyu_hol:
            num_color = "#FFFFFF"
        elif is_corp_hol:
            num_color = CAL_TEXT_CORP
        elif cycle_st == "off":
            if is_sunday:
                num_color = C_RED
            elif is_saturday:
                num_color = C_BLUE
            else:
                num_color = CAL_TEXT_OFF
        elif is_sunday and cycle_st == "work":
            num_color = "#FFFFFF"   # branco sobre vermelho escuro
        elif is_sunday:
            num_color = C_RED       # domingo folga — vermelho brilhante
            num_color = C_BLUE
        else:
            num_color = CAL_TEXT_WORK

        # ── Indicador pequeno (canto superior direito) ───────────────
        if status == "absent":
            indicator = "欠"
            ind_color  = "#EF9A9A"
        elif status == "yukyu":
            indicator = "有"
            ind_color  = "#FFE082"
        elif yukyu_hol:
            indicator = "有"
            ind_color  = "#FFE082"
        elif status == "early":
            indicator  = "↓"
            ind_color  = "#FFFFFF"
        elif has_time:
            indicator  = "●"
            ind_color  = "#FFFFFF"
        elif is_corp_hol:
            indicator  = "🏭"
            ind_color  = "#212121"
        else:
            indicator  = ""
            ind_color  = C_WHITE

        # Bandeira de feriado nacional — INDEPENDENTE do indicador acima,
        # aparece junto (não troca, soma) quando o dia também tem outro
        # status/indicador.
        indicators_row = [ft.Text(indicator, size=scaled(8), color=ind_color)] if indicator else []
        if is_hol:
            indicators_row.append(ft.Text("🎌", size=scaled(8)))

        # ── Borda cinza claro (vermelha se feriado nacional, turquesa se hoje) ─
        if is_hol:
            border = ft.Border.all(2, HOL_COLOR)
        elif is_today:
            border = ft.Border.all(2, "#00D2C6")
        else:
            border = ft.Border.all(1, "#E5E7EB")

        # No 0.85 o GestureDetector precisa de expand=True ou o Container
        # precisa de on_click direto. Usamos um ElevatedButton sem estilo
        # para garantir o tap, envolto num Container fixo.
        def _tap_handler(e, d=day_num):
            open_day_modal(d)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(str(day_num), size=scaled(14),
                                    color=num_color,
                                    weight=ft.FontWeight.W_800),
                            ft.Column(controls=indicators_row, spacing=0, tight=True,
                                      horizontal_alignment=ft.CrossAxisAlignment.END),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=0, tight=True,
            ),
            bgcolor=bg, border_radius=8,
            padding=ft.Padding(left=5, right=5, top=5, bottom=5),
            border=border,
            width=scaled(46), height=scaled(48),
            on_click=_tap_handler,
            ink=True,
            ink_color="#00D2C633",
        )

    # ── Grid — semana começa no DOMINGO ─────────────────────────────
    # Python: Mon=0 … Sun=6  →  domingo na coluna 0: offset = (weekday+1)%7
    py_weekday    = date(view_year, view_month, 1).weekday()  # 0=Mon
    first_col     = (py_weekday + 1) % 7                      # 0=Dom, 1=Seg…
    # Cores dos cabeçalhos: Dom=vermelho, Sáb=azul, resto=secundário
    day_names     = ["日", "月", "火", "水", "木", "金", "土"]
    # Dom=vermelho, Seg–Sex=branco, Sáb=azul
    day_colors    = [DANGER, TEXT_PRIMARY, TEXT_PRIMARY,
                     TEXT_PRIMARY, TEXT_PRIMARY, TEXT_PRIMARY, "#60A5FA"]
    header_row    = ft.Row(
        controls=[ft.Container(
            content=ft.Text(d, size=scaled(11), color=day_colors[i],
                            text_align=ft.TextAlign.CENTER,
                            weight=ft.FontWeight.W_700),
            width=scaled(46)) for i, d in enumerate(day_names)],
        spacing=4,
    )

    last_day_num = 28
    for d in range(28, 32):
        try:    date(view_year, view_month, d); last_day_num = d
        except ValueError: break

    weeks, current_week = [], [ft.Container(width=scaled(46), height=scaled(48))] * first_col
    for day_num in range(1, last_day_num + 1):
        current_week.append(day_cell(day_num))
        if len(current_week) == 7:
            weeks.append(ft.Row(controls=list(current_week), spacing=4))
            current_week = []
    if current_week:
        while len(current_week) < 7:
            current_week.append(ft.Container(width=scaled(46), height=scaled(48)))
        weeks.append(ft.Row(controls=current_week, spacing=4))

    def _go_prev(_):
        m, y = view_month - 1, view_year
        if m < 1: m, y = 12, y - 1
        state["cal_month"] = m
        state["cal_year"]  = y
        refresh_all()

    def _go_next(_):
        m, y = view_month + 1, view_year
        if m > 12: m, y = 1, y + 1
        state["cal_month"] = m
        state["cal_year"]  = y
        refresh_all()

    nav_row = ft.Row(
        controls=[
            ft.TextButton("‹", on_click=_go_prev, style=ft.ButtonStyle(color=ACCENT)),
            ft.Text(f"{view_year}/{view_month:02d}", size=16, color=TEXT_PRIMARY,
                    weight=ft.FontWeight.W_700, expand=True,
                    text_align=ft.TextAlign.CENTER),
            ft.TextButton("›", on_click=_go_next, style=ft.ButtonStyle(color=ACCENT)),
        ],
    )

    def _leg(color, label):
        return ft.Row([
            ft.Container(
                width=scaled(14), height=scaled(14),
                bgcolor=color, border_radius=3,
                border=ft.Border.all(1, "#D0D0D0"),
            ),
            ft.Text(label, size=scaled(10), color="#F0F0F0",
                    weight=ft.FontWeight.W_600),
        ], spacing=5, tight=True)


    legend = ft.Row(
        controls=[
            ft.Column(controls=[
                _leg(WORK_COLOR,      "Trabalho"),
                _leg(CAL_SUNDAY_WORK, "Domingo Trabalhado"),
                _leg("#FF6D00",       "有休 Yukyu"),
                _leg("#00796B",       "Saída Antecipada"),
            ], spacing=4, tight=True),
            ft.Column(controls=[
                _leg(OFF_COLOR,  "Folga"),
                _leg(CAL_CORP,   "Feriado Corporativo"),
                _leg("#7B1FA2",  "欠勤 Falta"),
            ], spacing=4, tight=True),
        ],
        spacing=16,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    group_badge = None
    _mostra_grupo = (_cycle_type == "4x2" or
                      (_cycle_type == "alternating_monthly"
                       and settings.get("alt_monthly_rest_pattern", "5x2") == "4x2"))
    if _mostra_grupo:
        _grupo_atual = settings.get("group", "A")
        _grupo_ref   = settings.get("anchor_group")
        _badge_txt   = f"📅 Escala do Grupo {_grupo_atual}"
        if _grupo_ref and _grupo_ref != _grupo_atual:
            _badge_txt += f"  (calculada a partir do Grupo {_grupo_ref})"
        group_badge = ft.Container(
            content=ft.Text(_badge_txt, size=11, color=ACCENT, weight=ft.FontWeight.W_600),
            padding=ft.Padding(left=8, right=8, top=4, bottom=4),
            bgcolor="#1A2E2C", border_radius=6,
            margin=ft.Padding(left=0, right=0, top=0, bottom=4),
        )

    # Barra de presença — 精皆勤手当 (adicional de assiduidade opcional
    # por empresa). Recalculada a cada renderização, então atualiza
    # sozinha assim que o modal do dia salva uma falta (o app já chama
    # refresh_all() depois de salvar, sem precisar de nada especial aqui).
    _presenca      = calcular_presenca_mensal(cycle, month_overrides, month_holidays)
    _limiar_pct    = float(settings.get("seikaikin_threshold_pct") or 100)
    _pct_atual     = _presenca["percentual"]
    _cor_presenca  = "#2ECC71" if _pct_atual >= _limiar_pct else "#E74C3C"
    _pct_int       = max(0, min(100, round(_pct_atual)))
    presenca_bar = ft.Container(
        content=ft.Column(controls=[
            ft.Row(controls=[
                ft.Text("📋 Assiduidade do Mês", size=11, color=TEXT_SECONDARY,
                        weight=ft.FontWeight.W_600, expand=True),
                ft.Text(f"{_pct_atual:.1f}% (limite {_limiar_pct:.0f}%)",
                        size=11, color=_cor_presenca, weight=ft.FontWeight.W_700),
            ]),
            ft.Container(
                height=10, border_radius=5, bgcolor="#333333",
                content=ft.Row(controls=[
                    ft.Container(bgcolor=_cor_presenca, border_radius=5, expand=_pct_int),
                    ft.Container(expand=(100 - _pct_int)),
                ], spacing=0),
            ),
        ], spacing=4, tight=True),
        padding=ft.Padding(left=8, right=8, top=6, bottom=6),
        bgcolor="#1A1A1A", border_radius=6,
        margin=ft.Padding(left=0, right=0, top=0, bottom=4),
    )

    return ft.Column(
        controls=[nav_row, *([group_badge] if group_badge else []),
                  presenca_bar, legend,
                  ft.Container(height=2), header_row,
                  ft.Container(height=2), *weeks],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
    )


# ─────────────────────────────────────────────
#  TAB 2 — HOLERITE
# ─────────────────────────────────────────────

def build_holerite_tab(page: ft.Page, state: dict, refresh_all):
    settings     = state["settings"]
    overrides    = state["overrides"]
    holidays     = state["holidays"]
    holidays_corp = state.get("holidays_corp", {})
    history      = state["history"]
    today        = date.today()
    view_year  = state.get("hol_year",  today.year)
    view_month = state.get("hol_month", today.month)

    deducoes_hist = [e.get("deductions", 0) for e in history if e.get("deductions", 0) > 0]
    hist_avg = sum(deducoes_hist) / len(deducoes_hist) if deducoes_hist else 0.0
    hist_sem_dados = len(deducoes_hist) == 0

    try:
        anchor = date.fromisoformat(settings["anchor_date"])
    except Exception:
        anchor = today

    month_key = f"{view_year}-{view_month:02d}"

    # 時給 vigente pra esse mês — ver jikyuu_vigente_para_mes() no topo
    # do arquivo pra a lógica completa e testável isoladamente.
    _jikyuu_efetivo = jikyuu_vigente_para_mes(
        month_key, history, int(settings.get("jikyuu") or 1500))

    # Mesclar feriados nacionais (embutidos/CSV) + corporativos da aba 🏭
    # para que ambos afetem o cálculo do holerite, não só a cor da célula
    _nat_hols  = holidays.get(month_key, [])
    _corp_hols = holidays_corp.get(month_key, [])
    _all_holidays_month = sorted(set(_nat_hols) | set(_corp_hols))
    try:
        data = compute_monthly_forecast(
            year=view_year, month=view_month,
            jikyuu=_jikyuu_efetivo,
            anchor_date=anchor, group=settings.get("group", "B"),
            holiday_days=_all_holidays_month,
            day_overrides=overrides.get(month_key, {}),
            odd_month_bonus=int(settings.get("odd_bonus") or 50000),
            extra_bonus=int(settings.get("extra_bonus") or 0),
            deduction_mode=settings.get("deduction_mode", "historical"),
            fixed_deduction=int(settings.get("fixed_deduction") or 0),
            history_avg_deduction=hist_avg,
            block=int(settings.get("block") or 1),
            shift_type_cfg=settings.get("shift_type", ""),
            cfg_start=settings.get("shift_start", ""),
            cfg_end=settings.get("shift_end", ""),
            cfg_break=int(settings.get("shift_break") or 65),
            cfg_ot=settings.get("shift_ot", ""),
            cycle_type=settings.get("cycle_type", "4x2"),
            alt_start_day=settings.get("shift_start_day", "08:35"),
            alt_end_day=settings.get("shift_end_day", "20:35"),
            alt_start_night=settings.get("shift_start_night", "20:35"),
            alt_end_night=settings.get("shift_end_night", "08:35"),
            fixed_monthly_bonus=int(settings.get("fixed_monthly_bonus") or 0),
            monthly_allowance=int(settings.get("monthly_allowance") or 0),
            round_mode=settings.get("round_mode", "truncate"),
            wage_round_mode=settings.get("wage_round_mode", "up"),
            use_leader_addon=bool(settings.get("use_leader_addon", False)),
            leader_addon_hours=float(settings.get("leader_addon_hours") or 168),
            night_interval_minutes=int(settings.get("night_interval_minutes") or 0),
            anchor_group=settings.get("anchor_group"),
            alt_monthly_rest_pattern=settings.get("alt_monthly_rest_pattern", "5x2"),
            shift_anchor_date=(date.fromisoformat(settings["shift_anchor_date"])
                                if settings.get("shift_anchor_date") else None),
            break_periods=(
                [(bp.get("start", ""), bp.get("end", ""))
                 for bp in settings.get("break_periods_detailed", [])]
                if settings.get("break_periods_enabled") else None
            ),
        )
    except Exception:
        data = {"gross": 0, "deductions": 0, "net": 0,
                "base_pay": 0, "overtime_pay": 0, "night_pay": 0,
                "holiday_pay": 0, "legal_holiday_pay": 0,
                "odd_bonus": 0, "extra_bonus": 0}

    # Se esse mês específico já tem holerite real registrado no
    # Histórico, o desconto deixa de ser uma previsão e vira o valor
    # REAL conhecido — ver desconto_real_para_mes() no topo do arquivo.
    _desconto_real = desconto_real_para_mes(month_key, history)
    _eh_registro_real = _desconto_real is not None
    if _eh_registro_real:
        data["deductions"] = _desconto_real
        data["net"] = data["gross"] - data["deductions"]

    def _go_prev(_):
        m, y = view_month - 1, view_year
        if m < 1: m, y = 12, y - 1
        state["hol_month"] = m; state["hol_year"] = y
        refresh_all()

    def _go_next(_):
        m, y = view_month + 1, view_year
        if m > 12: m, y = 1, y + 1
        state["hol_month"] = m; state["hol_year"] = y
        refresh_all()

    nav_row = ft.Row(
        controls=[
            ft.TextButton("‹", on_click=_go_prev, style=ft.ButtonStyle(color=ACCENT)),
            ft.Text(f"{view_year}/{view_month:02d}", size=16, color=TEXT_PRIMARY,
                    weight=ft.FontWeight.W_700, expand=True,
                    text_align=ft.TextAlign.CENTER),
            ft.TextButton("›", on_click=_go_next, style=ft.ButtonStyle(color=ACCENT)),
        ],
    )

    month_hint = ft.Container(
        content=ft.Text(
            "📅 Previsão do trabalho realizado neste mês. "
            "Você costuma receber este valor no holerite do mês seguinte.",
            size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER,
        ),
        padding=ft.Padding(left=8, right=8, top=2, bottom=6),
    )

    def pay_row(lbl, amt, color=TEXT_PRIMARY, small=False):
        return ft.Row(
            controls=[
                ft.Text(lbl, size=12 if small else 13,
                        color=TEXT_SECONDARY if small else TEXT_PRIMARY),
                ft.Text(yen(amt), size=12 if small else 14,
                        color=color, weight=ft.FontWeight.W_600),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    modo = settings.get("deduction_mode", "historical")
    fixed_val = int(settings.get("fixed_deduction") or 0)
    if _eh_registro_real:
        deduction_note = f"📋 Registro real: {yen(data['deductions'])}"
    elif modo == "fixed":
        if fixed_val == 0:
            deduction_note = "Fixo: ¥0 (sem desconto)"
        else:
            deduction_note = f"Fixo: {yen(fixed_val)}"
    else:
        if hist_sem_dados:
            deduction_note = "Histórico: sem dados — desconto = ¥0"
        else:
            deduction_note = f"Média histórica: {yen(round(hist_avg))}"

    # Bônus lidos das configurações — editáveis em ⚙️ Config
    # sem campos duplicados aqui

    return ft.Column(
        controls=[
            nav_row, month_hint,
            card(ft.Column(controls=[
                section_header("支給 VENCIMENTOS"),
                pay_row(f"Salário Base 基本給 ({data.get('days_normal',0)}d, {data.get('regular_hours',0):.2f}h)",
                        data["base_pay"]),
                pay_row(f"Yukyu 有給休暇 ({data.get('days_yukyu',0)}d, {data.get('yukyu_hours',0):.2f}h)",
                        data.get("yukyu_pay", 0),     color="#FFB74D",   small=True),
                pay_row(f"Hora Extra 残業手当 ({data.get('overtime_hours',0):.2f}h)",
                        data["overtime_pay"],       color=WARNING,     small=True),
                pay_row(f"Adicional Noturno 深夜手当 ({data.get('night_hours',0):.2f}h)",
                        data["night_pay"],           color=ACCENT_LITE, small=True),
                pay_row(f"Feriado 休出手当 ({data.get('days_holiday',0)}d, {data.get('holiday_hours',0):.2f}h)",
                        data["holiday_pay"],         color=DANGER,      small=True),
                pay_row(f"Domingo 法定休出 ({data.get('days_legal',0)}d, {data.get('legal_hours',0):.2f}h)",
                        data.get("legal_holiday_pay", 0), color="#EF9A9A", small=True),
                pay_row("Bônus Mês Ímpar 奇数月",
                        data["odd_bonus"],           color=SUCCESS,     small=True),
                pay_row("Adicional Fixo Mensal",
                        data.get("fixed_monthly_bonus", 0), color=SUCCESS, small=True),
                pay_row("Abono Mensal (separado)",
                        data.get("monthly_allowance", 0), color=SUCCESS, small=True),
                pay_row("Abono Extra",
                        data["extra_bonus"],         color=SUCCESS,     small=True),
                pay_row("Abono/Vale do Dia",
                        data.get("abono_total", 0),  color=SUCCESS,     small=True),
                divider(),
                pay_row("TOTAL BRUTO 総支給額",       data["gross"],        color=YEN_GOLD),
            ], spacing=8, tight=True)),

            card(ft.Column(controls=[
                section_header("控除 DESCONTOS"),
                ft.Row(
                    controls=[
                        ft.Text(f"Total de Descontos ({settings.get('deduction_mode','historical')})", size=13, color=TEXT_PRIMARY),
                        ft.Column(
                            controls=[
                                ft.Text(yen(data["deductions"]), size=14,
                                        color=DANGER, weight=ft.FontWeight.W_600),
                                ft.Text(deduction_note, size=10, color=TEXT_MUTED),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=0, tight=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ], spacing=8, tight=True)),

            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("差引支給額 SALÁRIO LÍQUIDO", size=scaled(12), color=ACCENT_LITE,
                                style=ft.TextStyle(letter_spacing=1.2),
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(yen(data["net"]), size=scaled(34), color=YEN_GOLD,
                                weight=ft.FontWeight.W_900,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4, tight=True,
                ),
                bgcolor=BG_CARD, border_radius=20, padding=20, margin=8,
                border=ft.Border.all(2, ACCENT_DARK),
                alignment=ft.Alignment(0, 0),
            ),
            ft.Container(
                content=ft.Text(
                    "⚠️ Valores estimados, fornecidos \"como está\", sem garantias. "
                    "Não substitui o holerite oficial nem consultoria profissional. "
                    "Detalhes em ❓ Ajuda.",
                    size=10, color=TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                    italic=True,
                ),
                padding=ft.Padding(left=8, right=8, top=4, bottom=4),
            ),
        ],
        spacing=0, scroll=ft.ScrollMode.AUTO,
    )


# ─────────────────────────────────────────────
#  TAB 3 — HISTORY
# ─────────────────────────────────────────────

def build_history_tab(page: ft.Page, state: dict, refresh_all):
    history = state["history"]

    def open_log_modal(_, edit_entry=None):
        # Campos do holerite japonês baseados no modelo real
        # Cada campo: label JP + PT, teclado numérico
        # edit_entry: se fornecido, pré-preenche os campos para edição
        ee = edit_entry or {}

        def _tf(lbl, kb=ft.KeyboardType.NUMBER, val=""):
            return ft.TextField(
                label=lbl, value=val, keyboard_type=kb,
                bgcolor="#2A2A2A", color="#F0F0F0",
                border_color="#333333", focused_border_color="#00D2C6",
                label_style=ft.TextStyle(color="#A0A0A0", size=9),
                text_size=13, dense=True, expand=1,
            )

        def _tf_obrigatorio(lbl, kb=ft.KeyboardType.NUMBER, val=""):
            """Campo destacado — essencial para o cálculo de desconto histórico."""
            return ft.TextField(
                label=f"⭐ {lbl}", value=val, keyboard_type=kb,
                bgcolor="#1A2E2C", color="#F0F0F0",
                border_color=ACCENT, focused_border_color=ACCENT,
                border_width=2,
                label_style=ft.TextStyle(color=ACCENT, size=9, weight=ft.FontWeight.W_700),
                text_size=13, dense=True, expand=1,
            )

        def _sec(t, color=ACCENT_LITE):
            return ft.Container(
                content=ft.Text(t, size=11, color=color,
                                weight=ft.FontWeight.W_700),
                padding=ft.Padding(left=0, right=0, top=8, bottom=2),
            )

        def _row(*fields):
            return ft.Row(list(fields), spacing=6)

        # ── Mês ──────────────────────────────────────────────────────
        month_f = _tf("Mês 月 (AAAA-MM)", ft.KeyboardType.TEXT,
                      ee.get("month", date.today().strftime("%Y-%m")))

        def _blur_month_f(e):
            v = normalize_yyyymm(e.control.value.strip())
            e.control.value = v
            e.control.update()
        month_f.on_blur = _blur_month_f

        def _v(key, default=""):
            v = ee.get(key, default)
            return str(v) if v else default

        # ── 勤怠 Frequência ──────────────────────────────────────────
        f_dias      = _tf("平日出勤 Dias Úteis", val=_v("dias_uteis"))
        f_kyujitsu  = _tf("所休出 Trab.Folga", val=_v("dias_kyujitsu"))
        f_hokyujitsu= _tf("法休出 Trab.Feriado", val=_v("dias_hokyu"))
        f_kekkin    = _tf("欠勤 Faltas", val=_v("dias_falta"))
        f_yukyu     = _tf("有休 Férias Pagas", val=_v("dias_yukyu"))
        f_tokyu     = _tf("特休有給 Lic.Especial", val=_v("dias_tokyu"))
        f_chikoku   = _tf("遅早 Atrasos/Saídas", val=_v("dias_chikoku"))
        f_kyugyo    = _tf("休業 Afastamento", val=_v("dias_kyugyo"))

        # ── 時間 Horas ───────────────────────────────────────────────
        f_shonai    = _tf("所定内 Hrs Normal", val=_v("h_shonai"))
        f_shogai    = _tf("所定外 Hrs Extra Pad.", val=_v("h_shogai"))
        f_hochgai   = _tf("法定外 Hrs Extra Legal", val=_v("h_hochgai"))
        f_shinyam   = _tf("深夜 Hrs Noturnas", val=_v("h_shinya"))
        f_kyushutsu = _tf("所休出 Hrs Folga Trab.", val=_v("h_kyushu"))
        f_hokyu_h   = _tf("法休出 Hrs Feriado Trab.", val=_v("h_hokyu"))
        f_60h       = _tf("60h超時間 Hrs +60h/mês", val=_v("h_60"))
        f_yukyu_h   = _tf("有休時間 Hrs Férias", val=_v("h_yukyu"))
        f_jitsuro   = _tf("実働時間 Hrs Efetivas", val=_v("h_jitsuro"))
        f_kojo_h    = _tf("控除時間 Hrs Desconto", val=_v("h_kojo"))

        # ── 支給 Vencimentos ─────────────────────────────────────────
        f_kihon     = _tf("基本給 Salário Base", val=_v("kihon"))
        f_shonai_k  = _tf("所定内金額 Val.Normal", val=_v("shonai_k"))
        f_shogai_k  = _tf("所定外手当 HE Padrão", val=_v("shogai_k"))
        f_zangyo    = _tf("残業手当 Hora Extra 1,25x", val=_v("zangyo"))
        f_yakin     = _tf("深夜手当 Ad.Noturno +25%", val=_v("yakin"))
        f_kyushu    = _tf("休出手当 Trab.Feriado 1,35x", val=_v("kyushutsu"))
        f_kanri     = _tf("管理手当 Ad.Gestão", val=_v("kanri"))
        f_gijutsu   = _tf("技術手当 Ad.Técnico", val=_v("gijutsu"))
        f_leader    = _tf("リーダー手当 Ad.Líder", val=_v("leader"))
        f_seisan    = _tf("精算金 Acerto", val=_v("seisan"))
        f_hosho     = _tf("報奨金 Bônus", val=_v("hosho"))
        f_tsukkin   = _tf("通勤手当 V.Transporte", val=_v("tsukkin"))
        f_ta_teate  = _tf("他手当 Outros Ad.", val=_v("ta_teate"))
        f_ikkin     = _tf("一時金 Gratificação", val=_v("ikkin"))
        f_60h_teate = _tf("60h超手当 Ad.+60h", val=_v("teate_60"))

        # ── 控除 Descontos ───────────────────────────────────────────
        f_kenpo     = _tf("健康保険 Plano Saúde", val=_v("kenpo"))
        f_kaigo     = _tf("介護保険 Seg.Enfermagem", val=_v("kaigo"))
        f_nenkin    = _tf("厚生年金 Previdência", val=_v("nenkin"))
        f_koyo      = _tf("雇用保険 Seg.Desemprego", val=_v("koyo"))
        f_shotoku   = _tf("所得税 Imp.de Renda", val=_v("shotoku"))
        f_jumin     = _tf("住民税 Imp.Municipal", val=_v("jumin"))
        f_ta_kojo   = _tf("他控除 Outros Desc.", val=_v("ta_kojo"))

        # ── Totais ───────────────────────────────────────────────────
        f_gross     = _tf("総支給額 Total Bruto", val=_v("gross"))
        f_ded       = _tf_obrigatorio("控除合計 Total Desc.", val=_v("deductions"))
        f_net       = _tf("差引支給額 Salário Líq.", val=_v("net"))

        # ── 時給 vigente a partir deste mês (opcional) ─────────────────
        # Marca esse mês como o início de um novo 時給 — a previsão
        # (aba Holerite) de qualquer mês SEM registro passa a usar esse
        # valor em vez do 時給 atual configurado em ⚙️ Config, contanto
        # que esse registro seja o marco mais recente igual ou anterior
        # ao mês sendo visto. Sem isso, um aumento de salário mudaria
        # retroativamente a previsão de meses passados não registrados.
        f_jikyuu_novo = _tf("時給 Jikyuu — Valor por Hora a partir deste mês (¥, opcional)",
                            val=_v("jikyuu_effective"))

        ov_ref = [None]

        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()

        def _vi(f):
            try: return int(f.value or 0)
            except: return 0

        def _vf(f):
            """Lê campo como float — para horas (ex: 155.5)"""
            try:
                v = (f.value or "0").replace(",", ".")
                return float(v)
            except: return 0.0

        def _remove_entry(_=None):
            if edit_entry:
                state["history"] = [e for e in state["history"]
                                     if e.get("month") != edit_entry.get("month")]
                save_json(page, KEY_HISTORY, state["history"])
            _close()
            refresh_all()

        def _save(_=None):
            # Validação: mês é obrigatório, sem ele o registro fica
            # invisível/inconsistente na lista do histórico
            _month_val = month_f.value.strip()
            if not _month_val:
                month_f.border_color = DANGER
                month_f.helper_text = "Campo obrigatório — formato AAAA-MM"
                month_f.update()
                return

            g, d = _vi(f_gross), _vi(f_ded)
            entry = {
                "month":        _month_val,
                "gross": g, "deductions": d,
                "net":   _vi(f_net),
                # Frequência
                "dias_uteis":    _vi(f_dias),
                "dias_kyujitsu": _vi(f_kyujitsu),
                "dias_hokyu":    _vi(f_hokyujitsu),
                "dias_falta":    _vi(f_kekkin),
                "dias_yukyu":    _vi(f_yukyu),
                "dias_tokyu":    _vi(f_tokyu),
                "dias_chikoku":  _vi(f_chikoku),
                "dias_kyugyo":   _vi(f_kyugyo),
                # Horas
                "h_shonai":   _vf(f_shonai),
                "h_shogai":   _vf(f_shogai),
                "h_hochgai":  _vi(f_hochgai),
                "h_shinya":   _vi(f_shinyam),
                "h_kyushu":   _vi(f_kyushutsu),
                "h_hokyu":    _vi(f_hokyu_h),
                "h_60":       _vi(f_60h),
                "h_yukyu":    _vi(f_yukyu_h),
                "h_jitsuro":  _vf(f_jitsuro),
                "h_kojo":     _vi(f_kojo_h),
                # Vencimentos
                "kihon":      _vi(f_kihon),
                "shonai_k":   _vi(f_shonai_k),
                "shogai_k":   _vi(f_shogai_k),
                "zangyo":     _vi(f_zangyo),
                "yakin":      _vi(f_yakin),
                "kyushutsu":  _vi(f_kyushu),
                "kanri":      _vi(f_kanri),
                "gijutsu":    _vi(f_gijutsu),
                "leader":     _vi(f_leader),
                "seisan":     _vi(f_seisan),
                "hosho":      _vi(f_hosho),
                "tsukkin":    _vi(f_tsukkin),
                "ta_teate":   _vi(f_ta_teate),
                "ikkin":      _vi(f_ikkin),
                "teate_60":   _vi(f_60h_teate),
                # Descontos
                "kenpo":      _vi(f_kenpo),
                "kaigo":      _vi(f_kaigo),
                "nenkin":     _vi(f_nenkin),
                "koyo":       _vi(f_koyo),
                "shotoku":    _vi(f_shotoku),
                "jumin":      _vi(f_jumin),
                "ta_kojo":    _vi(f_ta_kojo),
                # 時給 vigente a partir deste mês (opcional) — vazio se
                # não houve mudança de salário nesse mês
                "jikyuu_effective": _vi(f_jikyuu_novo),
            }
            # Remove tanto o mês antigo (se editando e mudou o mês) quanto
            # qualquer registro existente com o novo mês (evita duplicar)
            # Usa state["history"] (não a variável local "history") para
            # garantir que pegamos a lista mais atual, inclusive se o
            # usuário salvar múltiplos registros na mesma sessão.
            _old_month = edit_entry.get("month") if edit_entry else None
            state["history"] = [
                e for e in state["history"]
                if e.get("month") != entry["month"] and e.get("month") != _old_month
            ]
            state["history"].append(entry)
            state["history"].sort(key=lambda x: x["month"], reverse=True)
            save_json(page, KEY_HISTORY, state["history"])
            _close()
            refresh_all()

        # ── Layout do painel ─────────────────────────────────────────
        # page.width funciona no web, window_width só no desktop
        win_w = (page.width or page.window_width or 420)
        win_h = (page.height or page.window_height or 760)
        if not win_w or win_w < 100: win_w = 420
        if not win_h or win_h < 100: win_h = 760

        # Solução definitiva: padding nos campos internos + scroll na Column
        # A barra de scroll ocupa ~12px no lado direito
        # Adicionamos padding_right nos campos via wrapper por linha
        def _padded_row(*fields):
            return ft.Container(
                content=ft.Row(list(fields), spacing=4, wrap=False),
                padding=ft.Padding(left=0, right=14, top=0, bottom=0),
            )

        content = ft.Column(
            controls=[
                ft.Container(month_f,
                    padding=ft.Padding(left=0, right=14, top=6, bottom=0)),

                # ── Campo obrigatório PRIMEIRO — sem precisar rolar ────────
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("⭐ OBRIGATÓRIO — necessário para o cálculo",
                                size=10, color=ACCENT, weight=ft.FontWeight.W_700),
                        ft.Container(f_ded,
                            padding=ft.Padding(left=0, right=14, top=0, bottom=0)),
                    ], spacing=4, tight=True),
                    bgcolor="#1A2E2C",
                    border_radius=10,
                    border=ft.Border.all(1, ACCENT),
                    padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                    margin=ft.Padding(left=0, right=0, top=4, bottom=8),
                ),

                ft.Container(
                    content=ft.Text(
                        "Os campos abaixo são opcionais — apenas para seu registro pessoal.",
                        size=10, color=TEXT_MUTED,
                    ),
                    padding=ft.Padding(left=0, right=0, top=0, bottom=6),
                ),

                _sec("💰 TOTAIS (opcional)"),
                _padded_row(f_gross, f_net),

                _sec("📈 MUDANÇA DE 時給 Jikyuu — Valor por Hora (opcional)"),
                _padded_row(f_jikyuu_novo),
                ft.Container(
                    ft.Text(
                        "Só preencha se o 時給 (Jikyuu, valor por hora) "
                        "mudou A PARTIR deste mês (ex: aumento de "
                        "salário). A previsão de qualquer mês sem "
                        "registro passa a usar esse valor, em vez do "
                        "時給 atual de ⚙️ Config — evita que um aumento "
                        "futuro mude retroativamente a previsão de meses "
                        "passados que você não registrou aqui. Deixe "
                        "vazio se não houve mudança nesse mês.",
                        size=9, color=TEXT_MUTED,
                    ),
                    padding=ft.Padding(left=0, right=0, top=0, bottom=6),
                ),

                _sec("勤怠 FREQUÊNCIA / DIAS"),
                _padded_row(f_dias, f_kyujitsu, f_hokyujitsu),
                _padded_row(f_kekkin, f_yukyu, f_tokyu),
                _padded_row(f_chikoku, f_kyugyo),
                _sec("時間 HORAS TRABALHADAS"),
                _padded_row(f_shonai, f_shogai, f_hochgai),
                _padded_row(f_shinyam, f_kyushutsu, f_hokyu_h),
                _padded_row(f_60h, f_yukyu_h, f_jitsuro),
                ft.Container(f_kojo_h,
                    padding=ft.Padding(left=0, right=14, top=0, bottom=0)),
                _sec("支給 VENCIMENTOS"),
                _padded_row(f_kihon, f_shonai_k, f_shogai_k),
                _padded_row(f_zangyo, f_yakin, f_kyushu),
                _padded_row(f_kanri, f_gijutsu, f_leader),
                _padded_row(f_seisan, f_hosho, f_tsukkin),
                _padded_row(f_ta_teate, f_ikkin, f_60h_teate),
                _sec("控除 DESCONTOS"),
                _padded_row(f_kenpo, f_kaigo, f_nenkin),
                _padded_row(f_koyo, f_shotoku, f_jumin),
                ft.Container(f_ta_kojo,
                    padding=ft.Padding(left=0, right=14, top=0, bottom=0)),
                ft.Container(height=40),  # espaço extra no final p/ teclado não cobrir
            ],
            spacing=5, tight=True,
            scroll=ft.ScrollMode.ALWAYS,
        )
        panel_w = min(int(win_w * 0.95), 480)
        panel_h = min(int(win_h * 0.94), 760)  # mais alto — sobra espaço quando teclado abre

        panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[
                        ft.Text("給与明細 Registrar Holerite Real",
                                size=13, color=TEXT_PRIMARY,
                                weight=ft.FontWeight.W_700, expand=True),
                        ft.TextButton("✕", on_click=_close,
                                      style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        content=ft.Text(
                            "⭐ Só o Total de Desconto é obrigatório para calcular o desconto histórico. "
                            "Os demais são opcionais — apenas para seu registro pessoal.",
                            size=10, color=TEXT_MUTED,
                        ),
                        padding=ft.Padding(left=0, right=0, top=2, bottom=4),
                    ),
                    ft.Divider(height=1, color="#333333"),
                    ft.Container(
                        content=content,
                        expand=True,
                    ),
                    ft.Divider(height=1, color="#333333"),
                    ft.Row(controls=[
                        ft.TextButton("Remover", on_click=_remove_entry,
                                      style=ft.ButtonStyle(color=DANGER))
                        if edit_entry else ft.Container(),
                        ft.Row(controls=[
                            ft.TextButton("Cancelar", on_click=_close,
                                          style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                            ft.FilledButton("Salvar", on_click=_save,
                                            style=ft.ButtonStyle(bgcolor=ACCENT, color="#121212")),
                        ], spacing=8),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ],
                spacing=8, tight=True, expand=True,
            ),
            bgcolor=BG_CARD,
            border_radius=14,
            padding=ft.Padding(left=16, right=16, top=14, bottom=14),
            width=panel_w,
            height=panel_h,
            border=ft.Border.all(1, "#333333"),
        )

        bg = ft.Container(
            content=ft.Column(
                controls=[panel],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#CC000000", expand=True, blur=ft.Blur(4, 4),
            alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    deducoes    = [e.get("deductions", 0) for e in state["history"] if e.get("deductions", 0) > 0]
    avg_deducao = sum(deducoes) / len(deducoes) if deducoes else None

    def _history_card(e):
        g  = e.get("gross", 0)
        d  = e.get("deductions", 0)
        n  = e.get("net", g - d)
        subs = []
        for key, lbl in [("zangyo","残業"), ("yakin","深夜"),
                          ("kyushutsu","休出"), ("kihon","基本給")]:
            v = e.get(key, 0)
            if v: subs.append(f"{lbl}:{yen(v)}")
        sub_txt = "  ".join(subs) if subs else ""
        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text(e.get("month",""), size=13,
                            color=ACCENT_LITE, weight=ft.FontWeight.W_700),
                    ft.Text("✏️", size=12, color=TEXT_MUTED),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row(controls=[
                    ft.Column(controls=[
                        ft.Text("総支給額 Bruto", size=9, color=TEXT_MUTED),
                        ft.Text(yen(g), size=12, color=YEN_GOLD,
                                weight=ft.FontWeight.W_700),
                    ], spacing=1, tight=True),
                    ft.Column(controls=[
                        ft.Text("控除合計 Desc.", size=9, color=TEXT_MUTED),
                        ft.Text(yen(d), size=12, color=DANGER,
                                weight=ft.FontWeight.W_700),
                    ], spacing=1, tight=True,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Column(controls=[
                        ft.Text("差引支給額 Líq.", size=9, color=TEXT_MUTED),
                        ft.Text(yen(n), size=12, color=SUCCESS,
                                weight=ft.FontWeight.W_700),
                    ], spacing=1, tight=True,
                      horizontal_alignment=ft.CrossAxisAlignment.END),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(sub_txt, size=10, color=TEXT_MUTED) if sub_txt else ft.Container(height=0),
            ], spacing=4, tight=True),
            bgcolor=BG_CARD, border_radius=16,
            padding=12, margin=4,
            border=ft.Border.all(1, "#333333"),
            on_click=lambda _, entry=e: open_log_modal(None, edit_entry=entry),
            ink=True, ink_color="#00D2C633",
        )
    # Usar state["history"] (não a variável local "history") para
    # garantir que a lista renderizada é sempre a mais atual
    history_cards = [_history_card(e) for e in state["history"][:24]]

    avg_widget = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Desconto Médio", size=11, color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(
                    yen(round(avg_deducao)) if avg_deducao else "— Sem dados ainda",
                    size=28, color=ACCENT_LITE, weight=ft.FontWeight.W_800,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text("Usado para prever descontos na aba Holerite", size=10,
                        color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4, tight=True,
        ),
        bgcolor=BG_CARD, border_radius=16, padding=16, margin=8,
        border=ft.Border.all(1, "#333333"),
        alignment=ft.Alignment(0, 0),
    )

    empty = ft.Container(
        content=ft.Text("Sem histórico ainda.\nToque em 'Registrar Holerite Real' para começar.",
                        size=13, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
        padding=32, alignment=ft.Alignment(0, 0),
    )

    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("給与明細 Histórico", size=16, color=TEXT_PRIMARY,
                            weight=ft.FontWeight.W_700, expand=True),
                    ft.FilledButton("+ Registrar Holerite Real",
                                    on_click=open_log_modal,
                                    style=ft.ButtonStyle(bgcolor=ACCENT, color="#121212")),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=ft.Text(
                    "💡 Use o mês a que se refere o trabalho (ex: o holerite "
                    "que você recebe em julho normalmente é do trabalho de junho — "
                    "registre como '2026-06').",
                    size=10, color=TEXT_MUTED,
                ),
                padding=ft.Padding(left=0, right=0, top=2, bottom=6),
            ),
            avg_widget,
            section_header("MESES ANTERIORES"),
            *(history_cards if history_cards else [empty]),
        ],
        spacing=4, scroll=ft.ScrollMode.AUTO,
    )


# ─────────────────────────────────────────────
#  TAB 4 — SETTINGS
# ─────────────────────────────────────────────

def build_settings_tab(page: ft.Page, state: dict, refresh_all):
    settings = state["settings"]

    # ── Diagnóstico de Storage ──────────────────────────────────────
    _diag_result = ft.Text("Toque em 'Testar Agora' para diagnosticar.",
                            size=11, color=TEXT_MUTED, selectable=True)

    def _run_diagnostic(_=None):
        import datetime as _dt
        ts = _dt.datetime.now().strftime("%H:%M:%S")

        async def _do_diag():
            lines = []
            try:
                sp = page.shared_preferences
                lines.append(f"1) shared_preferences existe: {'sim' if sp is not None else 'NAO'}")
            except Exception as e:
                lines.append(f"1) shared_preferences ERRO: {e}")

            try:
                await page.shared_preferences.set("onion_diag_test", f"teste_{ts}")
                lines.append("2) shared_preferences.set(): OK")
            except Exception as e:
                lines.append(f"2) shared_preferences.set() ERRO: {e}")

            try:
                v = await page.shared_preferences.get("onion_diag_test")
                lines.append(f"3) shared_preferences.get(): '{v}'")
            except Exception as e:
                lines.append(f"3) shared_preferences.get() ERRO: {e}")

            lines.append("")
            lines.append(f"Historico em memoria: {len(state.get('history', []))} registro(s)")
            lines.append(f"Hora do teste: {ts}")

            _diag_result.value = "\n".join(lines)
            _diag_result.update()

        page.run_task(_do_diag)

    diag_content_col = ft.Column(controls=[
        ft.FilledButton(
            "Testar Agora",
            on_click=_run_diagnostic,
            style=ft.ButtonStyle(bgcolor="#444444"),
        ),
        ft.Container(
            content=_diag_result,
            bgcolor="#1a1a1a", border_radius=8,
            padding=10,
        ),
        ft.Text(
            "1) Toque em Testar Agora e leia o resultado.\n"
            "2) Feche o app/Chrome completamente.\n"
            "3) Reabra e toque em Testar Agora de novo.\n"
            "4) Se o teste 3 ou 5 mostrar valor vazio/None na "
            "segunda vez, identificamos qual storage falha.",
            size=9, color=TEXT_MUTED,
        ),
    ], spacing=8, tight=True, visible=False)

    def _toggle_diag(e):
        diag_content_col.visible = e.control.value
        diag_content_col.update()
    diag_switch_toggle = ft.Switch(
        value=False, active_color=ACCENT, on_change=lambda e: _toggle_diag(e),
    )
    diag_switch = ft.Row(controls=[
        diag_switch_toggle,
        ft.Text("Mostrar ferramentas de diagnóstico (uso avançado/suporte)",
                size=12, color=TEXT_SECONDARY, expand=True),
    ], spacing=8)

    def _save():
        save_json(page, KEY_SETTINGS, settings)
        # Não chama refresh_all() — evita scroll voltar ao topo

    def mk_field(label_str, key, kb=ft.KeyboardType.NUMBER):
        def _blur(e):
            v = e.control.value.strip()
            # Converter para int se for campo numérico
            if kb == ft.KeyboardType.NUMBER:
                try: v = int(v or 0)
                except: v = 0
                e.control.value = str(v)
                e.control.update()
            settings[key] = v
            save_json(page, KEY_SETTINGS, settings)
            # Sem refresh_all() — sem scroll ao topo
        return ft.TextField(
            label=label_str, value=str(settings.get(key, "")),
            keyboard_type=kb, bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
            on_blur=_blur,
        )

    _group_val = [settings.get("group", "B")]
    def _set_group(g):
        _group_val[0] = g
        settings["group"] = g
        save_json(page, KEY_SETTINGS, settings)
        for gv, btn in (("A", btn_group_a), ("B", btn_group_b), ("C", btn_group_c)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if g == gv else BG_SURFACE,
                color="#121212" if g == gv else TEXT_PRIMARY,
            )
            btn.update()
        if not anchor_date_field.visible:
            anchor_date_field.visible = True
            anchor_date_hint.visible = False
            anchor_date_field.update()
            anchor_date_hint.update()
        # Sem refresh_all() — evita scroll ao topo. As outras abas
        # (Calendário, Holerite) leem `settings["group"]` fresco na
        # próxima vez que forem abertas, sem precisar forçar agora.

    _cur_group = settings.get("group", "B")
    btn_group_a = ft.FilledButton(
        "Grupo A", on_click=lambda _: _set_group("A"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_group == "A" else BG_SURFACE,
            color="#121212" if _cur_group == "A" else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_group_b = ft.FilledButton(
        "Grupo B", on_click=lambda _: _set_group("B"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_group == "B" else BG_SURFACE,
            color="#121212" if _cur_group == "B" else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_group_c = ft.FilledButton(
        "Grupo C", on_click=lambda _: _set_group("C"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_group == "C" else BG_SURFACE,
            color="#121212" if _cur_group == "C" else TEXT_PRIMARY,
        ), expand=1,
    )
    group_label = ft.Text("Grupo de Turno", size=12, color="#A0A0A0")
    group_row = ft.Row(controls=[btn_group_a, btn_group_b, btn_group_c], spacing=6)

    # ── Data de início do ciclo — grava automaticamente qual grupo estava
    # selecionado no momento em que a data foi definida. Trocar de grupo
    # DEPOIS, sem tocar na data, recalcula o calendário sozinho usando a
    # relação de 2 dias entre turmas — sem precisar de switch nenhum.
    def _blur_anchor_date(e):
        v = normalize_date(e.control.value.strip())
        e.control.value = v
        e.control.update()
        settings["anchor_date"] = v
        settings["anchor_group"] = settings.get("group", "A")
        save_json(page, KEY_SETTINGS, settings)

    _tem_anchor_group = settings.get("anchor_group") is not None
    anchor_date_hint = ft.Text(
        "👆 Selecione seu grupo acima primeiro — a data será o 1º dia "
        "de trabalho DESSE grupo específico.",
        size=11, color=WARNING, italic=True,
        visible=not _tem_anchor_group,
    )
    anchor_date_field = ft.TextField(
        label="Data Início Ciclo 4×2 (AAAA-MM-DD)",
        value=str(settings.get("anchor_date", "")),
        keyboard_type=ft.KeyboardType.TEXT,
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
        on_blur=_blur_anchor_date,
        visible=_tem_anchor_group,
    )

    _shift_type_val = [settings.get("shift_type", "night")]
    def _set_shift_type(st):
        _shift_type_val[0] = st
        settings["shift_type"] = st
        save_json(page, KEY_SETTINGS, settings)
        for sv, btn in (("night", btn_shift_night), ("day", btn_shift_day)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if st == sv else BG_SURFACE,
                color="#121212" if st == sv else TEXT_PRIMARY,
            )
            btn.update()

    _cur_shift_type = settings.get("shift_type", "night")
    btn_shift_night = ft.FilledButton(
        "🌙 Noturno 夜勤", on_click=lambda _: _set_shift_type("night"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_shift_type == "night" else BG_SURFACE,
            color="#121212" if _cur_shift_type == "night" else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_shift_day = ft.FilledButton(
        "☀️ Diurno 昼勤", on_click=lambda _: _set_shift_type("day"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_shift_type == "day" else BG_SURFACE,
            color="#121212" if _cur_shift_type == "day" else TEXT_PRIMARY,
        ), expand=1,
    )
    shift_type_label = ft.Text("Turno 勤務", size=12, color="#A0A0A0")
    shift_type_row = ft.Row(controls=[btn_shift_night, btn_shift_day], spacing=6)

    def _tf_shift(lbl, key, hint="HH:MM", is_time=True):
        f = ft.TextField(
            label=lbl, value=str(settings.get(key, "")),
            hint_text=hint,
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
            expand=1,
        )
        def _blur(e, k=key, _is_time=is_time):
            if _is_time:
                v = normalize_hhmm(e.control.value)
                e.control.value = v
                e.control.update()
            else:
                try: v = int(e.control.value or 65)
                except: v = 65
                e.control.value = str(v)
                e.control.update()
                v = str(v)
            settings[k] = v
            save_json(page, KEY_SETTINGS, settings)
        f.on_blur = _blur
        return f


    # ── Tipo de Ciclo de Trabalho ─────────────────────────────────
    def _set_cycle_type(mode):
        settings["cycle_type"] = mode
        settings["cycle_type_confirmed"] = True
        _mem_cache[KEY_SETTINGS] = settings
        save_json(page, KEY_SETTINGS, settings)
        for m, btn in (("4x2", btn_4x2), ("5x2", btn_5x2),
                       ("alternating", btn_alt), ("alternating_monthly", btn_alt_monthly)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if mode == m else BG_SURFACE,
                color="#121212" if mode == m else TEXT_PRIMARY)
            btn.update()
        # Alternar visibilidade direto, sem refresh_all() — sem scroll ao topo
        _is_alt_any = mode in ("alternating", "alternating_monthly")
        section_4x2_container.visible = not _is_alt_any
        section_alt_container.visible = _is_alt_any
        shift_type_picker_container.visible = not _is_alt_any
        rest_pattern_row_container.visible = (mode == "alternating_monthly")
        shift_anchor_date_container.visible = (mode == "alternating_monthly")
        section_4x2_container.update()
        section_alt_container.update()
        shift_type_picker_container.update()
        rest_pattern_row_container.update()
        shift_anchor_date_container.update()
        # Revela as etapas seguintes (2, 3 e 4) — etapa 3 (Grupo) só no 4×2
        # puro OU no Alternado Mensal com padrão de folga 4×2
        step2_turno_container.visible = True
        step3_grupo_container.visible = (
            mode == "4x2"
            or (mode == "alternating_monthly"
                and settings.get("alt_monthly_rest_pattern", "5x2") == "4x2")
        )
        step4_salario_container.visible = True
        step2_turno_container.update()
        step3_grupo_container.update()
        step4_salario_container.update()

    def _set_rest_pattern(pattern):
        settings["alt_monthly_rest_pattern"] = pattern
        save_json(page, KEY_SETTINGS, settings)
        for p, btn in (("4x2", btn_rest_4x2), ("5x2", btn_rest_5x2)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if pattern == p else BG_SURFACE,
                color="#121212" if pattern == p else TEXT_PRIMARY)
            btn.update()
        step3_grupo_container.visible = (pattern == "4x2")
        step3_grupo_container.update()

    _cur_cycle = settings.get("cycle_type", "4x2")
    btn_4x2 = ft.FilledButton(
        "4×2", on_click=lambda _: _set_cycle_type("4x2"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_cycle == "4x2" else BG_SURFACE,
            color="#121212" if _cur_cycle == "4x2" else TEXT_PRIMARY),
        expand=1,
    )
    btn_5x2 = ft.FilledButton(
        "5×2", on_click=lambda _: _set_cycle_type("5x2"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_cycle == "5x2" else BG_SURFACE,
            color="#121212" if _cur_cycle == "5x2" else TEXT_PRIMARY),
        expand=1,
    )
    btn_alt = ft.FilledButton(
        "Alternado Semanal", on_click=lambda _: _set_cycle_type("alternating"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_cycle == "alternating" else BG_SURFACE,
            color="#121212" if _cur_cycle == "alternating" else TEXT_PRIMARY),
        expand=1,
    )
    btn_alt_monthly = ft.FilledButton(
        "Alternado Mensal", on_click=lambda _: _set_cycle_type("alternating_monthly"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_cycle == "alternating_monthly" else BG_SURFACE,
            color="#121212" if _cur_cycle == "alternating_monthly" else TEXT_PRIMARY),
        expand=1,
    )
    cycle_type_row = ft.Column(controls=[
        ft.Row([btn_4x2, btn_5x2], spacing=6),
        ft.Row([btn_alt, btn_alt_monthly], spacing=6),
    ], spacing=6)

    # Sub-escolha: padrão de folga do Alternado Mensal (só aparece nesse modo)
    _cur_rest = settings.get("alt_monthly_rest_pattern", "5x2")
    btn_rest_4x2 = ft.FilledButton(
        "Folga 4×2 (c/ Grupo)", on_click=lambda _: _set_rest_pattern("4x2"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_rest == "4x2" else BG_SURFACE,
            color="#121212" if _cur_rest == "4x2" else TEXT_PRIMARY),
        expand=1,
    )
    btn_rest_5x2 = ft.FilledButton(
        "Folga 5×2 (fim de semana)", on_click=lambda _: _set_rest_pattern("5x2"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_rest == "5x2" else BG_SURFACE,
            color="#121212" if _cur_rest == "5x2" else TEXT_PRIMARY),
        expand=1,
    )
    rest_pattern_row_container = ft.Container(
        content=ft.Column(controls=[
            ft.Text("Padrão de Folga (Alternado Mensal)", size=12, color="#A0A0A0"),
            ft.Row([btn_rest_4x2, btn_rest_5x2], spacing=6),
        ], spacing=8, tight=True),
        visible=(_cur_cycle == "alternating_monthly"),
    )

    # Data de referência do mês diurno (só no Alternado Mensal)
    def _blur_shift_anchor(e):
        v = normalize_date(e.control.value.strip())
        e.control.value = v
        e.control.update()
        settings["shift_anchor_date"] = v
        save_json(page, KEY_SETTINGS, settings)
    shift_anchor_date_container = ft.Container(
        content=ft.Column(controls=[
            ft.Text(
                "Qualquer dia dentro do 1º MÊS que você trabalhou de dia "
                "— o app calcula a alternância a partir daí.",
                size=11, color=TEXT_MUTED, italic=True,
            ),
            ft.TextField(
                label="Data de Referência — Mês Diurno (AAAA-MM-DD)",
                value=str(settings.get("shift_anchor_date") or ""),
                keyboard_type=ft.KeyboardType.TEXT,
                bgcolor="#2A2A2A", color="#F0F0F0",
                border_color="#333333", focused_border_color="#00D2C6",
                label_style=ft.TextStyle(color="#A0A0A0"),
                on_blur=_blur_shift_anchor,
            ),
        ], spacing=6, tight=True),
        visible=(_cur_cycle == "alternating_monthly"),
    )


    # Campos do turno alternado (dia/noite)
    alt_day_start_f = _tf_shift("☀️ Dia — Entrada", "shift_start_day", "08:35", is_time=True)
    alt_day_end_f   = _tf_shift("☀️ Dia — Saída",   "shift_end_day",   "20:35", is_time=True)
    alt_night_start_f = _tf_shift("🌙 Noite — Entrada", "shift_start_night", "20:35", is_time=True)
    alt_night_end_f   = _tf_shift("🌙 Noite — Saída",   "shift_end_night",   "08:35", is_time=True)

    shift_start_f = _tf_shift("Entrada 出勤", "shift_start", "20:35", is_time=True)
    shift_end_f   = _tf_shift("Saída 退勤",   "shift_end",   "08:35", is_time=True)
    shift_break_f = _tf_shift("Intervalo 休憩 (min)", "shift_break", "65", is_time=False)
    shift_ot_f    = _tf_shift("残業 Início Hora Extra (fim turno normal)", "shift_ot", "06:35", is_time=True)

    # v2.33 tentou adicionar "Intervalos Detalhados" (avançado) aqui —
    # removido na v2.35 porque o usuário reportou que a aba Config
    # parou de abrir depois dessa mudança, e não foi possível identificar
    # a causa exata sem acesso a teste real do Flet (só stub/mock, que
    # não pega toda classe de incompatibilidade de API). Priorizando
    # estabilidade: a aba volta a abrir garantido, sem esse recurso.
    # O motor de cálculo (calculate_shift_pay com break_periods) continua
    # funcionando — só a UI de configuração foi removida. Ver
    # PROBLEMAS_RECORRENTES.md.

    section_4x2_container = ft.Container(
        content=ft.Column(controls=[
            section_header("HORÁRIO DO TURNO 勤務時間"),
            ft.Row([shift_start_f, shift_end_f], spacing=8),
            ft.Row([shift_break_f, shift_ot_f], spacing=8),
        ], spacing=8, tight=True),
        visible=(settings.get("cycle_type", "4x2") not in ("alternating", "alternating_monthly")),
    )
    section_alt_container = ft.Container(
        content=ft.Column(controls=[
            section_header("HORÁRIOS — TURNO ALTERNADO"),
            ft.Row([alt_day_start_f, alt_day_end_f], spacing=8),
            ft.Row([alt_night_start_f, alt_night_end_f], spacing=8),
            ft.Row([shift_break_f, shift_ot_f], spacing=8),
        ], spacing=8, tight=True),
        visible=(settings.get("cycle_type", "4x2") in ("alternating", "alternating_monthly")),
    )

    # ═══ Wizard por etapas (v2.14) ═══════════════════════════════════
    # Etapa 2, 3 e 4 só aparecem depois que o usuário escolhe o tipo de
    # ciclo pela primeira vez (settings["cycle_type_confirmed"]) — força
    # a ordem de preenchimento sem incomodar quem já configurou antes.
    _cur_cycle_confirmed = bool(settings.get("cycle_type_confirmed", False))

    shift_type_picker_container = ft.Container(
        content=ft.Column(controls=[shift_type_label, shift_type_row], spacing=8, tight=True),
        visible=(settings.get("cycle_type", "4x2") not in ("alternating", "alternating_monthly")),
    )

    step2_turno_container = card(ft.Column(controls=[
        section_header("2️⃣ HORÁRIO DO TURNO"),
        shift_type_picker_container,
        section_4x2_container,
        section_alt_container,
        shift_anchor_date_container,
        ft.Container(
            content=ft.Column(controls=[
                ft.Text("💡 Como funciona o cálculo:",
                        size=10, color=ACCENT, weight=ft.FontWeight.W_700),
                ft.Text("• Entrada → Início 残業: horas normais (salário base)",
                        size=10, color=TEXT_SECONDARY),
                ft.Text("• Início 残業 → Saída: hora extra à taxa de 1,25x",
                        size=10, color=TEXT_SECONDARY),
                ft.Text("• No modo Alternado, a semana define automaticamente dia ou noite",
                        size=10, color=TEXT_MUTED),
            ], spacing=3, tight=True),
            bgcolor=BG_SURFACE,
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            border=ft.Border.all(1, "#333333"),
        ),
    ], spacing=12, tight=True))
    step2_turno_container.visible = _cur_cycle_confirmed

    step3_grupo_container = card(ft.Column(controls=[
        section_header("3️⃣ GRUPO DE TURNO"),
        group_label,
        group_row,
        anchor_date_hint,
        anchor_date_field,
    ], spacing=12, tight=True))
    _cur_cycle_val = settings.get("cycle_type", "4x2")
    step3_grupo_container.visible = (
        _cur_cycle_confirmed
        and (_cur_cycle_val == "4x2"
             or (_cur_cycle_val == "alternating_monthly"
                 and settings.get("alt_monthly_rest_pattern", "5x2") == "4x2"))
    )

    def _blur_hire_date(e):
        v = normalize_date(e.control.value.strip())
        e.control.value = v
        e.control.update()
        settings["hire_date"] = v
        save_json(page, KEY_SETTINGS, settings)
        refresh_all()  # recalcula e mostra o novo saldo de Yukyu na hora

    def _computar_yukyu_saldo():
        hd = settings.get("hire_date")
        if not hd:
            return None
        try:
            hire = date.fromisoformat(hd)
        except Exception:
            return None
        usage_dates = []
        for month_key, dias in state.get("overrides", {}).items():
            try:
                ano_s, mes_s = month_key.split("-")
                ano, mes = int(ano_s), int(mes_s)
            except Exception:
                continue
            for dia_str, ov in dias.items():
                if isinstance(ov, dict) and ov.get("status") == "yukyu":
                    try:
                        usage_dates.append(date(ano, mes, int(dia_str)))
                    except Exception:
                        pass
        return calcular_yukyu(hire, date.today(), usage_dates)

    def _montar_texto_yukyu():
        _yukyu = _computar_yukyu_saldo()
        if not _yukyu:
            return "Preencha a Data de Admissão acima para calcular seu saldo."
        hoje = date.today()
        # Só concessões AINDA ATIVAS (não expiradas) — evita lista longa
        # e sem utilidade prática pra quem tem muitos anos de empresa.
        # O histórico completo de concessões já expiradas não importa
        # mais pro saldo de hoje, então não precisa poluir a tela.
        ativas = sorted(
            (g for g in _yukyu["detalhe_concessoes"] if g["expiry"] > hoje),
            key=lambda g: g["grant_date"],
        )
        _linhas = [f"Saldo disponível: {_yukyu['saldo_disponivel']} dias"]
        for g in ativas:
            _linhas.append(
                f"  • {g['grant_date'].isoformat()}: +{g['dias']}d "
                f"(usado {g['usado']}, expira {g['expiry'].isoformat()})"
            )
        if ativas:
            _prox_exp = min(ativas, key=lambda g: g["expiry"])
            _restante = _prox_exp["dias"] - _prox_exp["usado"]
            _linhas.append(
                f"Próxima expiração: {_prox_exp['expiry'].isoformat()} "
                f"({_restante} dia(s) em risco se não usados até lá)"
            )
        if _yukyu["proxima_concessao_data"]:
            _linhas.append(
                f"Próxima concessão: {_yukyu['proxima_concessao_data'].isoformat()} "
                f"(+{_yukyu['proxima_concessao_dias']} dias)"
            )
        if _yukyu["usos_invalidos"]:
            _linhas.append(
                f"⚠️ {len(_yukyu['usos_invalidos'])} dia(s) marcados como Yukyu no "
                f"calendário sem saldo disponível na época — confira o histórico."
            )
        return "\n".join(_linhas)

    def _blur_hire_date(e):
        v = normalize_date(e.control.value.strip())
        e.control.value = v
        e.control.update()
        settings["hire_date"] = v
        save_json(page, KEY_SETTINGS, settings)
        # Atualização direcionada, sem refresh_all() — evita o scroll
        # voltar ao topo (mesmo cuidado já aplicado em todo o Config)
        yukyu_texto_widget.value = _montar_texto_yukyu()
        yukyu_texto_widget.update()

    hire_date_field = ft.TextField(
        label="Data de Admissão (AAAA-MM-DD)",
        value=str(settings.get("hire_date") or ""),
        keyboard_type=ft.KeyboardType.TEXT,
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
        on_blur=_blur_hire_date,
    )

    yukyu_texto_widget = ft.Text(_montar_texto_yukyu(), size=11, color=TEXT_SECONDARY)

    yukyu_summary = ft.Container(
        content=ft.Column(controls=[
            ft.Text("🌴 Direito a Yukyu (有給休暇)", size=13, color=ACCENT,
                    weight=ft.FontWeight.W_700),
            yukyu_texto_widget,
            ft.Text(
                "⚠️ Não verifica a regra de 80% de presença — assume que "
                "você tem direito. Ver ❓ Ajuda para detalhes.",
                size=9, color=TEXT_MUTED, italic=True,
            ),
        ], spacing=4, tight=True),
        bgcolor=BG_SURFACE, border_radius=8, padding=10,
        margin=ft.Padding(left=0, right=0, top=8, bottom=0),
    )

    step4_salario_container = card(ft.Column(controls=[
        section_header("4️⃣ CONFIGURAÇÃO DE SALÁRIO"),
        mk_field("時給 Jikyuu — Valor por Hora (¥)",  "jikyuu"),
        ft.Text(
            "⚠️ Se seu 時給 (Jikyuu, valor por hora) mudou (aumento de "
            "salário), esse valor vale SEMPRE, inclusive pra meses "
            "passados sem registro. Pra manter a previsão de meses "
            "anteriores ao aumento correta, registre em 📋 Histórico o "
            "mês em que o aumento começou, preenchendo o campo "
            "\"時給 Jikyuu — Valor por Hora a partir deste mês\".",
            size=9, color=TEXT_MUTED,
        ),
        mk_field("Bônus Padrão Mês Ímpar (¥)",        "odd_bonus"),
        mk_field("Adicional Fixo Mensal — Líder, etc. (¥)", "fixed_monthly_bonus"),
        ft.Text(
            "Valor somado automaticamente TODO mês na previsão "
            "(ex: adicional de liderança, função técnica fixa). "
            "⚠️ Esse valor também é usado no cálculo de Extra/Noturno/"
            "Domingo se \"Usar Adicional de Líder no Arredondamento\" "
            "estiver ativo (⚙️ Config).",
            size=9, color=TEXT_MUTED,
        ),
        mk_field("Abono Mensal — separado (¥)", "monthly_allowance"),
        ft.Text(
            "Outro valor somado automaticamente TODO mês, mas "
            "SEPARADO do Adicional de Líder acima — nunca entra no "
            "cálculo de Extra/Noturno/Domingo, mesmo com o "
            "arredondamento ativado. Use pra qualquer abono fixo que "
            "não deva afetar essa taxa.",
            size=9, color=TEXT_MUTED,
        ),
        hire_date_field,
        yukyu_summary,
        mk_field("Limiar Assiduidade — seikaikin teate (%)", "seikaikin_threshold_pct"),
        ft.Text(
            "Percentual mínimo de presença no mês pra manter o adicional "
            "de assiduidade da sua empresa (opcional, cada empresa define "
            "o seu — não é exigência de lei). Só falta de dia inteiro "
            "desconta. Mostrado como barra na aba Calendário.",
            size=9, color=TEXT_MUTED,
        ),
    ], spacing=12, tight=True))
    step4_salario_container.visible = _cur_cycle_confirmed








    # Dropdown causava o mesmo bug que o seletor de desconto tinha antes
    # de virar botão: a seleção não fixava e a página voltava ao topo.
    # Corrigido usando o mesmo padrão de botões (sem refresh_all()).
    _block_val = [int(settings.get("block", 1))]

    def _set_block(value):
        _block_val[0] = value
        settings["block"] = value
        save_json(page, KEY_SETTINGS, settings)
        for v, btn in ((1, btn_block_1), (15, btn_block_15), (30, btn_block_30)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if value == v else BG_SURFACE,
                color="#121212" if value == v else TEXT_PRIMARY,
            )
            btn.update()
        round_mode_label.visible = value > 1
        round_mode_row.visible = value > 1
        round_mode_label.update()
        round_mode_row.update()

    _cur_block = int(settings.get("block", 1))
    btn_block_1 = ft.FilledButton(
        "1 min", on_click=lambda _: _set_block(1),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_block == 1 else BG_SURFACE,
            color="#121212" if _cur_block == 1 else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_block_15 = ft.FilledButton(
        "15 min", on_click=lambda _: _set_block(15),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_block == 15 else BG_SURFACE,
            color="#121212" if _cur_block == 15 else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_block_30 = ft.FilledButton(
        "30 min", on_click=lambda _: _set_block(30),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_block == 30 else BG_SURFACE,
            color="#121212" if _cur_block == 30 else TEXT_PRIMARY,
        ), expand=1,
    )
    block_label = ft.Text("Arredondamento do Ponto", size=12, color="#A0A0A0")
    block_row = ft.Row(controls=[btn_block_1, btn_block_15, btn_block_30], spacing=6)

    # ── Regra de arredondamento (truncar/mais próximo) — também botões ──
    def _set_round_mode(mode):
        settings["round_mode"] = mode
        save_json(page, KEY_SETTINGS, settings)
        for m, btn in (("truncate", btn_round_trunc), ("nearest", btn_round_nearest)):
            btn.style = ft.ButtonStyle(
                bgcolor=ACCENT if mode == m else BG_SURFACE,
                color="#121212" if mode == m else TEXT_PRIMARY,
            )
            btn.update()

    _cur_round = settings.get("round_mode", "truncate")
    btn_round_trunc = ft.FilledButton(
        "Truncar", on_click=lambda _: _set_round_mode("truncate"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_round == "truncate" else BG_SURFACE,
            color="#121212" if _cur_round == "truncate" else TEXT_PRIMARY,
        ), expand=1,
    )
    btn_round_nearest = ft.FilledButton(
        "Mais Próximo", on_click=lambda _: _set_round_mode("nearest"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_round == "nearest" else BG_SURFACE,
            color="#121212" if _cur_round == "nearest" else TEXT_PRIMARY,
        ), expand=1,
    )
    round_mode_label = ft.Text("Regra de Arredondamento", size=12, color="#A0A0A0",
                                visible=(_cur_block > 1))
    round_mode_row = ft.Row(
        controls=[btn_round_trunc, btn_round_nearest], spacing=6,
        visible=(_cur_block > 1),
    )

    # ── Modo de Arredondamento (geral) ────────────────────────────────
    # Afeta Salário Base, Hora Extra, Noturno e Feriado/Domingo — NÃO
    # afeta a Média Histórica de desconto (essa continua sempre na
    # regra do 0,5). Padrão "Sempre pra cima" a partir da v2.49 —
    # comportamento antigo (0,5 sobe) continua disponível pra quem
    # precisar recalibrar contra um holerite real específico.
    wage_round_help = ft.Text(
        "Como arredondar a taxa por hora (base, extra, noturno, "
        "feriado/domingo). \"Sempre pra cima\" é o padrão atual do "
        "app. Troque pra \"Regra do 0,5\" se seu holerite bater melhor "
        "com o arredondamento clássico (0,5 sempre sobe, resto trunca).",
        size=11, color="#A0A0A0", italic=True,
    )

    def _set_wage_round(mode):
        settings["wage_round_mode"] = mode
        _mem_cache[KEY_SETTINGS] = settings
        save_json(page, KEY_SETTINGS, settings)
        btn_wage_up.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "up" else BG_SURFACE,
            color="#121212" if mode == "up" else TEXT_PRIMARY,
        )
        btn_wage_half.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "half_up" else BG_SURFACE,
            color="#121212" if mode == "half_up" else TEXT_PRIMARY,
        )
        btn_wage_up.update()
        btn_wage_half.update()

    _cur_wage_round = settings.get("wage_round_mode", "up")
    btn_wage_up = ft.FilledButton(
        "⬆️ Sempre pra Cima",
        on_click=lambda _: _set_wage_round("up"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_wage_round == "up" else BG_SURFACE,
            color="#121212" if _cur_wage_round == "up" else TEXT_PRIMARY,
        ),
        expand=1,
    )
    btn_wage_half = ft.FilledButton(
        "🔄 Regra do 0,5",
        on_click=lambda _: _set_wage_round("half_up"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_wage_round == "half_up" else BG_SURFACE,
            color="#121212" if _cur_wage_round == "half_up" else TEXT_PRIMARY,
        ),
        expand=1,
    )
    wage_round_row = ft.Row(controls=[btn_wage_up, btn_wage_half], spacing=8)

    # ── Adicional de Líder no Arredondamento ──────────────────────────
    # Desligado por padrão. Reaproveita o campo "Adicional Fixo Mensal
    # — Líder" (que já soma no bruto) em vez de duplicar o valor —
    # quando ligado, esse mesmo valor também entra na taxa por hora de
    # extra/noturno/domingo, separado do jikyuu e arredondado
    # individualmente (conforme o Modo de Arredondamento acima).
    leader_addon_help = ft.Text(
        "⚠️ Regra confirmada por um RH específico — pode não valer pra "
        "sua empresa. \"Horas Padrão\" (ex: 168h) também varia — "
        "confirme com seu RH ou compare com um holerite real antes de "
        "confiar no resultado. Deixe desligado se não tiver certeza.",
        size=11, color="#A0A0A0", italic=True,
    )
    leader_addon_hours_f = ft.TextField(
        label="Horas Padrão para este Cálculo",
        value=str(settings.get("leader_addon_hours", 168)),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
        visible=bool(settings.get("use_leader_addon", False)),
    )
    def _save_leader_addon_hours(e):
        try:
            settings["leader_addon_hours"] = float(leader_addon_hours_f.value or 168)
        except ValueError:
            settings["leader_addon_hours"] = 168
        save_json(page, KEY_SETTINGS, settings)
    leader_addon_hours_f.on_change = _save_leader_addon_hours

    # ── Intervalo dentro da janela noturna (simplificado) ─────────────
    # Alternativa simples à posição exata do intervalo (que exigiria
    # saber HORÁRIO de início/fim de cada pausa). Aqui só a DURAÇÃO
    # total do intervalo que cai dentro de 22h-5h é descontada da
    # janela cheia (7h = 420min) — aplicado igual todo dia com turno
    # noturno completo. Default 0 = comportamento idêntico a antes
    # (desconta nada, janela cheia).
    def _calc_night_result_text(minutos: int) -> str:
        resultado_min = max(0, 420 - minutos)
        return f"7h (420min) − {minutos}min = {resultado_min/60:g}h de adicional noturno por dia"

    night_interval_result = ft.Text(
        _calc_night_result_text(int(settings.get("night_interval_minutes", 0))),
        size=11, color=ACCENT_LITE,
    )
    night_interval_help = ft.Text(
        "Quantos minutos do SEU intervalo caem dentro do período "
        "noturno (22h-5h)? Descontado da janela cheia de 7h, aplicado "
        "todo dia com turno noturno completo. Não sabe a posição exata "
        "do intervalo? Deixe em 0 (sem desconto, comportamento padrão).",
        size=11, color="#A0A0A0", italic=True,
    )
    night_interval_f = ft.TextField(
        label="Minutos de Intervalo no Período Noturno",
        value=str(settings.get("night_interval_minutes", 0)),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
    )
    def _save_night_interval(e):
        try:
            minutos = int(night_interval_f.value or 0)
        except ValueError:
            minutos = 0
        settings["night_interval_minutes"] = minutos
        save_json(page, KEY_SETTINGS, settings)
        night_interval_result.value = _calc_night_result_text(minutos)
        night_interval_result.update()
    night_interval_f.on_change = _save_night_interval

    def _toggle_leader_addon(e):
        settings["use_leader_addon"] = e.control.value
        save_json(page, KEY_SETTINGS, settings)
        leader_addon_hours_f.visible = e.control.value
        leader_addon_hours_f.update()
    leader_addon_switch = ft.Switch(
        value=bool(settings.get("use_leader_addon", False)), active_color=ACCENT,
        on_change=_toggle_leader_addon,
    )
    leader_addon_row = ft.Row(controls=[
        leader_addon_switch,
        ft.Text("Usar Adicional de Líder no arredondamento de extra/noturno/domingo",
                size=12, color=TEXT_SECONDARY, expand=True),
    ], spacing=8)

    # Escondido por enquanto (a pedido do usuário) — código mantido
    # intacto, só não aparece na tela. Para reativar: trocar visible=False
    # por visible=True abaixo.
    hidden_advanced_container = card(ft.Column(controls=[
        section_header("AVANÇADO (desativado)"),
        block_label,
        block_row,
        round_mode_label,
        round_mode_row,
    ], spacing=12, tight=True))
    hidden_advanced_container.visible = False

    _ded_mode_val = [settings.get("deduction_mode", "historical")]

    def _set_ded_mode(mode):
        import sys
        _ded_mode_val[0] = mode
        settings["deduction_mode"] = mode
        _mem_cache[KEY_SETTINGS] = settings
        save_json(page, KEY_SETTINGS, settings)
        print(f"[DED_CHANGE] modo={mode}", file=sys.stderr)
        # Atualizar visual dos botões
        btn_hist.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "historical" else BG_SURFACE,
            color="#121212" if mode == "historical" else TEXT_PRIMARY,
        )
        btn_fix.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "fixed" else BG_SURFACE,
            color="#121212" if mode == "fixed" else TEXT_PRIMARY,
        )
        btn_hist.update()
        btn_fix.update()
        # Não chama refresh_all() — evita scroll ao topo
        # O holerite lerá o novo modo na próxima vez que abrir a aba

    _cur = settings.get("deduction_mode", "historical")
    btn_hist = ft.FilledButton(
        "📊 Média Histórica",
        on_click=lambda _: _set_ded_mode("historical"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur == "historical" else BG_SURFACE,
            color="#121212" if _cur == "historical" else TEXT_PRIMARY,
        ),
        expand=1,
    )
    btn_fix = ft.FilledButton(
        "✏️ Desconto Fixo",
        on_click=lambda _: _set_ded_mode("fixed"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur == "fixed" else BG_SURFACE,
            color="#121212" if _cur == "fixed" else TEXT_PRIMARY,
        ),
        expand=1,
    )
    ded_mode_dd = ft.Row(controls=[btn_hist, btn_fix], spacing=8)
    pin_switch = ft.Switch(
        label="Ativar Bloqueio PIN / Biométrico",
        value=settings.get("pin_enabled", False),
        active_color=ACCENT,
        label_text_style=ft.TextStyle(color=TEXT_SECONDARY),
    )
    pin_switch.on_change = lambda e: [settings.__setitem__("pin_enabled", e.control.value), save_json(page, KEY_SETTINGS, settings)]

    def _import_csv(_):
        """No PWA, FilePicker não funciona — usar textarea para colar o CSV."""
        ov_ref = [None]

        csv_field = ft.TextField(
            label="Cole o conteúdo do CSV aqui",
            multiline=True, min_lines=6, max_lines=12,
            hint_text="2025-08-13\n2025-12-25",
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )

        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()

        def _processar(_=None):
            # Só feriados corporativos aqui — os nacionais se atualizam
            # sozinhos automaticamente (busca em tempo de execução),
            # não precisam mais de importação manual via CSV.
            texto = csv_field.value or ""
            lines = texto.strip().splitlines()
            hols_corp = state.get("holidays_corp", {})
            ok = 0
            for line in lines:
                data_str = line.strip().split(",")[0].strip()
                if not data_str:
                    continue
                try:
                    d  = date.fromisoformat(data_str)
                    mk = f"{d.year}-{d.month:02d}"
                    if mk not in hols_corp: hols_corp[mk] = []
                    if d.day not in hols_corp[mk]:
                        hols_corp[mk].append(d.day); ok += 1
                except Exception:
                    pass
            save_json(page, "onion_holidays_corp", hols_corp)
            state["holidays_corp"] = hols_corp
            _close()
            refresh_all()

        panel = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text("Importar Feriados Corporativos (CSV)", size=13,
                            color=TEXT_PRIMARY, weight=ft.FontWeight.W_700,
                            expand=True),
                    ft.TextButton("✕", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Cole uma data por linha (feriados nacionais já se atualizam sozinhos, não precisam ser importados):",
                        size=11, color=TEXT_SECONDARY),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("2025-08-13  ← aniversário da fábrica",
                                size=10, color=YEN_GOLD),
                        ft.Text("2025-12-25  ← recesso de fim de ano",
                                size=10, color=YEN_GOLD),
                    ], spacing=2, tight=True),
                    bgcolor=BG_SURFACE, border_radius=6,
                    padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                ),
                csv_field,
                ft.Row(controls=[
                    ft.TextButton("Cancelar", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                    ft.FilledButton("Importar", on_click=_processar,
                                    style=ft.ButtonStyle(bgcolor=ACCENT, color="#121212")),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10, tight=True),
            bgcolor=BG_CARD, border_radius=14, padding=16,
            width=min(360, int((page.width or 420) * 0.92)),
            border=ft.Border.all(1, "#333333"),
        )
        bg = ft.Container(
            content=ft.Column(controls=[panel],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    def _clear_all(_):
        ov_ref = [None]
        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()
        def _confirm(_=None):
            for k in (KEY_SETTINGS, KEY_HISTORY, KEY_OVERRIDES,
                      KEY_HOLIDAYS, "onion_holidays_corp"):
                remove_storage(page, k)
            # Bug corrigido (v2.21): refresh_all() só atualiza
            # state["settings"] se _mem_cache tiver algo — depois de
            # remove_storage() o cache fica vazio, então sem isto a tela
            # continuaria mostrando os valores ANTIGOS até um reload
            # completo do app, mesmo já tendo apagado o storage de verdade.
            state["settings"]  = dict(DEFAULT_SETTINGS)
            state["history"]   = []
            state["overrides"] = {}
            state["holidays"]  = {}
            state["holidays_corp"] = {}
            _mem_cache[KEY_SETTINGS] = state["settings"]
            _close()
            refresh_all()
        panel = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text("Apagar Todos os Dados?", size=14,
                            color=DANGER, weight=ft.FontWeight.W_700, expand=True),
                    ft.TextButton("✕", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Isso apaga permanentemente configurações, histórico e feriados.",
                        size=12, color=TEXT_SECONDARY),
                ft.Row(controls=[
                    ft.TextButton("Cancelar", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                    ft.FilledButton("Apagar Tudo", on_click=_confirm,
                                    style=ft.ButtonStyle(bgcolor=DANGER)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=12, tight=True),
            bgcolor=BG_CARD, border_radius=14, padding=16,
            width=min(320, int((page.width or 420) * 0.92)),
            border=ft.Border.all(1, DANGER),
        )
        bg = ft.Container(
            content=ft.Column(controls=[panel],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()


    return ft.Column(
        controls=[
            ft.Text("⚙️  Configurações", size=scaled(16),
                    color=TEXT_PRIMARY, weight=ft.FontWeight.W_700),
            ft.Container(height=4),

            # ═══ ETAPA 1 — Tipo de Ciclo (sempre visível, primeiro) ═══
            card(ft.Column(controls=[
                section_header("1️⃣ TIPO DE CICLO DE TRABALHO"),
                cycle_type_row,
                ft.Text(
                    "4×2: 4 dias trabalho + 2 folga (fábricas turno fixo)  |  "
                    "5×2: segunda a sexta (turno comercial)  |  "
                    "Alternado Semanal: 1 semana dia + 1 semana noite  |  "
                    "Alternado Mensal: 1 mês dia + 1 mês noite",
                    size=9, color=TEXT_MUTED,
                ),
                rest_pattern_row_container,
            ], spacing=12, tight=True)),

            # ═══ ETAPA 2 — Horário do Turno (só após escolher o ciclo) ═══
            step2_turno_container,

            # ═══ ETAPA 3 — Grupo A/B/C + Data (só no ciclo 4×2) ═══
            step3_grupo_container,

            # ═══ ETAPA 4 — Configuração de Salário (só após etapa 1) ═══
            step4_salario_container,

            # ═══ Escondidos por enquanto — mantidos no código, desligados ═══
            # Arredondamento do ponto e taxa de referência elevada (v2.9/v2.10).
            # Reativar: trocar visible=False por visible=True no container
            # `hidden_advanced_container` logo abaixo.
            hidden_advanced_container,

            card(ft.Column(controls=[
                section_header("ARREDONDAMENTO DE SALÁRIO"),
                wage_round_help,
                wage_round_row,
                ft.Container(height=4),
                leader_addon_row,
                leader_addon_help,
                leader_addon_hours_f,
                ft.Container(height=4),
                night_interval_help,
                night_interval_f,
                night_interval_result,
            ], spacing=12, tight=True)),

            card(ft.Column(controls=[
                section_header("CONFIGURAÇÃO DE DESCONTOS"),
                ded_mode_dd,
                mk_field("Valor de Desconto Fixo (¥)", "fixed_deduction"),
            ], spacing=12, tight=True)),

            card(ft.Column(controls=[
                section_header("SEGURANÇA"),
                pin_switch,
            ], spacing=12, tight=True)),

            card(ft.Column(controls=[
                section_header("GERENCIAMENTO DE DADOS"),
                ft.FilledButton(
                    "Importar Calendário da Fábrica (.csv)",
                    icon="upload",
                    on_click=_import_csv,
                    style=ft.ButtonStyle(bgcolor=ACCENT_DARK),
                ),
                ft.Text("Formato: AAAA-MM-DD por linha (feriados)",
                        size=10, color=TEXT_MUTED),
                ft.Container(height=4),
                ft.OutlinedButton(
                    "Apagar Todos os Dados Locais",
                    icon="delete",
                    on_click=_clear_all,
                    style=ft.ButtonStyle(
                        color=DANGER,
                        side=ft.BorderSide(1, DANGER),   # FIX: ft.BorderSide direto
                    ),
                ),
            ], spacing=10, tight=True)),

            card(ft.Column(controls=[
                section_header("TERMOS E LICENÇA"),
                ft.Text(
                    f"✅ Termos aceitos em: {settings.get('disclaimer_accepted_at') or '—'}",
                    size=11, color=TEXT_SECONDARY,
                ),
                ft.Text(
                    "Projeto distribuído sob Licença MIT — código aberto, "
                    "gratuito, fornecido \"como está\", sem garantias. Veja o "
                    "arquivo LICENSE no repositório do GitHub.",
                    size=10, color=TEXT_MUTED,
                ),
            ], spacing=8, tight=True)),

            # ── Diagnóstico de Storage (temporário, para debug) ────────
            # Escondido atrás de switch — só quem está debugando um
            # problema de persistência precisa ver isso no dia a dia.
            card(ft.Column(controls=[
                section_header("🔍 DIAGNÓSTICO DE ARMAZENAMENTO"),
                diag_switch,
                diag_content_col,
            ], spacing=8, tight=True)),
        ],
        spacing=0, scroll=ft.ScrollMode.AUTO,
    )


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

# Escala global — ajustada conforme tamanho da janela
SCALE = 1.0

def scaled(value: int) -> int:
    """Aplica escala global a tamanhos de UI."""
    return int(value * SCALE)


# ─────────────────────────────────────────────
#  TAB 5 — FERIADOS CORPORATIVOS
# ─────────────────────────────────────────────

def build_holidays_tab(page: ft.Page, state: dict, refresh_all):
    """Gerenciador inline de feriados corporativos."""
    hols_corp  = state.get("holidays_corp", {})
    today      = date.today()
    view_year  = state.get("hol_corp_year", today.year)

    # Coletar todos os feriados do ano selecionado
    year_days = []
    for mk, days in sorted(hols_corp.items()):
        y, m = mk.split("-")
        if int(y) == view_year:
            for d in sorted(days):
                year_days.append((int(m), d))
    year_days.sort()

    ov_ref = [None]

    def _close_ov(_=None):
        if ov_ref[0] and ov_ref[0] in page.overlay:
            page.overlay.remove(ov_ref[0])
        page.update()

    def _remove_day(m, d, _=None):
        mk = f"{view_year}-{m:02d}"
        hc = state.get("holidays_corp", {})
        if mk in hc and d in hc[mk]:
            hc[mk].remove(d)
            if not hc[mk]:
                del hc[mk]
        state["holidays_corp"] = hc
        save_json(page, "onion_holidays_corp", hc)
        refresh_all()

    def _open_add(_=None):
        date_f = ft.TextField(
            label="Data (AAAA-MM-DD)",
            value=f"{view_year}-01-01",
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )
        note_f = ft.TextField(
            label="Descrição (opcional)",
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )
        def _save(_=None):
            try:
                d = date.fromisoformat(date_f.value.strip())
                mk = f"{d.year}-{d.month:02d}"
                hc = state.get("holidays_corp", {})
                if mk not in hc:
                    hc[mk] = []
                if d.day not in hc[mk]:
                    hc[mk].append(d.day)
                    hc[mk].sort()
                state["holidays_corp"] = hc
                save_json(page, "onion_holidays_corp", hc)
            except Exception:
                pass
            _close_ov()
            refresh_all()

        panel = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text("Adicionar Feriado Corporativo", size=13,
                            color=TEXT_PRIMARY, weight=ft.FontWeight.W_700,
                            expand=True),
                    ft.TextButton("✕", on_click=_close_ov,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                date_f, note_f,
                ft.Row(controls=[
                    ft.TextButton("Cancelar", on_click=_close_ov,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                    ft.FilledButton("Adicionar", on_click=_save,
                                    style=ft.ButtonStyle(bgcolor="#F97316")),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10, tight=True),
            bgcolor=BG_CARD, border_radius=14, padding=16,
            width=min(320, int((page.width or 420) * 0.92)),
            border=ft.Border.all(1, "#F97316"),
        )
        bg = ft.Container(
            content=ft.Column(controls=[panel],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#CC000000", expand=True, alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    # ── Navegação de ano ─────────────────────────────────────────────
    def _prev_year(_):
        state["hol_corp_year"] = view_year - 1
        refresh_all()
    def _next_year(_):
        state["hol_corp_year"] = view_year + 1
        refresh_all()

    month_names_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                      "Jul","Ago","Set","Out","Nov","Dez"]
    month_names_jp = ["1月","2月","3月","4月","5月","6月",
                      "7月","8月","9月","10月","11月","12月"]

    # ── Mini calendário mensal clicável ──────────────────────────────
    def _month_grid(m):
        mk = f"{view_year}-{m:02d}"
        hc = hols_corp.get(mk, [])
        last_d = 28
        for d in range(28, 32):
            try: date(view_year, m, d); last_d = d
            except ValueError: break

        first_col = (date(view_year, m, 1).weekday() + 1) % 7
        cells = [ft.Container(width=28, height=28)] * first_col

        for d in range(1, last_d + 1):
            is_corp = d in hc
            wc = (date(view_year, m, d).weekday() + 1) % 7
            num_c = "#EF4444" if wc == 0 else ("#60A5FA" if wc == 6 else "#E8EDF2")
            bg_c = "#B45309" if is_corp else "#1a1a2e"

            def _toggle(e, _d=d, _m=m, _cell=None):
                _mk = f"{view_year}-{_m:02d}"
                hc2 = state.get("holidays_corp", {})
                if _mk not in hc2:
                    hc2[_mk] = []
                if _d in hc2[_mk]:
                    hc2[_mk].remove(_d)
                    _is_now_corp = False
                else:
                    hc2[_mk].append(_d)
                    hc2[_mk].sort()
                    _is_now_corp = True
                if _mk in hc2 and not hc2[_mk]:
                    del hc2[_mk]
                state["holidays_corp"] = hc2
                save_json(page, "onion_holidays_corp", hc2)
                # Atualizar só a célula clicada sem reconstruir a aba inteira
                if e.control:
                    e.control.bgcolor = "#B45309" if _is_now_corp else "#0d1520"
                    e.control.border = (ft.Border.all(1, "#F59E0B") if _is_now_corp
                                        else ft.Border.all(1, "#333333"))
                    if e.control.content:
                        e.control.content.color = ("#E8EDF2" if _is_now_corp
                                                    else ("#EF4444" if (date(view_year,_m,_d).weekday()+1)%7==0
                                                    else ("#60A5FA" if (date(view_year,_m,_d).weekday()+1)%7==6
                                                    else "#E8EDF2")))
                    e.control.update()

            cells.append(ft.Container(
                content=ft.Text(str(d), size=9, color=num_c,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.W_700 if is_corp else ft.FontWeight.NORMAL),
                bgcolor=bg_c, border_radius=4,
                width=28, height=28,
                alignment=ft.Alignment(0, 0),
                border=ft.Border.all(1, "#F97316") if is_corp else ft.Border.all(1, "#2a1a3a"),
                on_click=_toggle, ink=True,
            ))

        while len(cells) % 7 != 0:
            cells.append(ft.Container(width=28, height=28))

        rows = [ft.Row(controls=cells[i:i+7], spacing=2)
                for i in range(0, len(cells), 7)]

        corp_count = len(hc)
        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text(f"{month_names_jp[m-1]} {month_names_pt[m-1]}",
                            size=11, color=ACCENT_LITE,
                            weight=ft.FontWeight.W_700),
                    ft.Text(f"🟧 {corp_count}", size=10, color="#F59E0B")
                    if corp_count else ft.Container(),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                *rows,
            ], spacing=2, tight=True),
            bgcolor=BG_CARD, border_radius=10,
            padding=ft.Padding(left=8, right=8, top=8, bottom=8),
            margin=ft.Padding(left=0, right=0, top=4, bottom=4),
            border=ft.Border.all(1, "#2a1a3a"),
        )

    # Instrução
    instruction = ft.Container(
        content=ft.Text(
            "Toque em qualquer dia para marcar/desmarcar como feriado corporativo 🟧",
            size=11, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER,
        ),
        padding=ft.Padding(left=8, right=8, top=4, bottom=4),
    )

    # Total do ano
    total_corp = sum(len(v) for k, v in hols_corp.items()
                     if k.startswith(str(view_year)))

    return ft.Column(
        controls=[
            ft.Row(controls=[
                ft.TextButton("‹", on_click=_prev_year,
                              style=ft.ButtonStyle(color=ACCENT)),
                ft.Text(f"Feriados Corporativos {view_year}",
                        size=15, color=TEXT_PRIMARY,
                        weight=ft.FontWeight.W_700, expand=True,
                        text_align=ft.TextAlign.CENTER),
                ft.TextButton("›", on_click=_next_year,
                              style=ft.ButtonStyle(color=ACCENT)),
            ]),
            instruction,
            ft.Container(
                content=ft.Text(f"Total: {total_corp} dia(s) em {view_year}",
                                size=12, color="#F59E0B",
                                text_align=ft.TextAlign.CENTER),
                visible=total_corp > 0,
            ),
            *[_month_grid(m) for m in range(1, 13)],
        ],
        spacing=2,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )



# ─────────────────────────────────────────────
#  TAB 6 — AJUDA / MANUAL
# ─────────────────────────────────────────────

def build_help_tab(page: ft.Page, state: dict, refresh_all):
    # Paleta local removida (v2.18) — usava cores claras (fundo branco)
    # desalinhadas do tema escuro do resto do app. Agora herda as
    # constantes globais (ACCENT_LITE, TEXT_PRIMARY, BG_CARD, etc.),
    # iguais às usadas em todas as outras abas.

    def _title(t):
        return ft.Container(
            content=ft.Text(t, size=15, color=YEN_GOLD,
                            weight=ft.FontWeight.W_800),
            padding=ft.Padding(left=0, right=0, top=12, bottom=4),
        )

    def _sec(t):
        return ft.Container(
            content=ft.Text(t, size=12, color=ACCENT_LITE,
                            weight=ft.FontWeight.W_700),
            padding=ft.Padding(left=0, right=0, top=10, bottom=2),
        )

    def _p(t, color=TEXT_SECONDARY):
        return ft.Text(t, size=12, color=color)

    def _item(icon, label, desc):
        return ft.Container(
            content=ft.Row(controls=[
                ft.Container(content=ft.Text(icon, size=13, weight=ft.FontWeight.W_600),
                             width=100),
                ft.Column(controls=[
                    ft.Text(label, size=12, color=TEXT_PRIMARY,
                            weight=ft.FontWeight.W_600),
                    ft.Text(desc, size=11, color="#E0E0E0"),
                ], spacing=1, tight=True, expand=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor="#2A2A2A", border_radius=8,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            margin=ft.Padding(left=0, right=0, top=2, bottom=2),
        )

    def _example(titulo, linhas):
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(titulo, size=11, color=ACCENT_LITE, weight=ft.FontWeight.W_700),
                ft.Text("\n".join(linhas), size=11, color="#D0D0D0",
                        font_family="monospace", selectable=True),
            ], spacing=4, tight=True),
            bgcolor="#1C1C1C", border_radius=6,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            margin=ft.Padding(left=0, right=0, top=2, bottom=6),
        )

    def _rule(jp, pt, calc, color=TEXT_PRIMARY):
        return ft.Container(
            content=ft.Row(controls=[
                ft.Column(controls=[
                    ft.Text(jp, size=11, color=color,
                            weight=ft.FontWeight.W_700),
                    ft.Text(pt, size=10, color="#E0E0E0"),
                ], spacing=1, tight=True, expand=2),
                ft.Text(calc, size=11, color=YEN_GOLD,
                        text_align=ft.TextAlign.RIGHT, expand=1),
            ]),
            bgcolor="#2A2A2A", border_radius=6,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            margin=ft.Padding(left=0, right=0, top=2, bottom=2),
        )

    def _color_legend(color, label, desc):
        return ft.Row(controls=[
            ft.Container(width=14, height=14, bgcolor=color,
                         border_radius=3,
                         border=ft.Border.all(1, "#333333")),
            ft.Column(controls=[
                ft.Text(label, size=11, color=TEXT_PRIMARY,
                        weight=ft.FontWeight.W_600),
                ft.Text(desc, size=10, color=TEXT_SECONDARY),
            ], spacing=0, tight=True, expand=True),
        ], spacing=8)

    # ── Seções do manual ─────────────────────────────────────────────
    APP_URL = "https://kamebug.github.io/onion-payroll/"
    FEEDBACK_URL = APP_URL + "feedback.html?build=" + BUILD_ID
    COMPARTILHAR_URL = APP_URL + "compartilhar.html"
    # v2.37: trocado ft.Text(selectable=True) por ft.TextField(read_only=True)
    # — sugestão do usuário, ainda não testada antes nesta conversa.
    # TextField é widget de INPUT nativo (usado em dezenas de lugares
    # já comprovados no app), diferente de Text/SelectableText — pode
    # integrar melhor com o menu nativo de Copiar/Selecionar do sistema
    # operacional (Android/iOS) do que um Text simplesmente selecionável.

    share_section = ft.Container(
        content=ft.Column(controls=[
            _title("📤 Compartilhar o Onion Payroll"),
            _p("Indique pra um colega peelar o próprio contracheque também — link do app e vídeo de apresentação (30s), com botão de copiar de verdade."),
            ft.FilledButton(
                "Compartilhar",
                icon="share",
                url=COMPARTILHAR_URL,
                style=ft.ButtonStyle(bgcolor=ACCENT_DARK),
            ),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=12, bgcolor=BG_CARD, border_radius=12,
        margin=ft.Padding(left=0, right=0, top=0, bottom=10),
    )

    sections = ft.Column(
        controls=[
            share_section,

            # ── Relatar Problema ──────────────────────────────────────
            _title("🐛 Encontrou um Problema?"),
            _p("Se algo não funcionou como esperado — cálculo estranho, tela travando, ou qualquer coisa fora do lugar — me conta. Isso ajuda a corrigir mais rápido."),
            ft.FilledButton(
                "Relatar Problema",
                icon="bug_report",
                url=FEEDBACK_URL,
                style=ft.ButtonStyle(bgcolor=ACCENT_DARK),
            ),

            # ── Início rápido ────────────────────────────────────────
            _title("🚀 Início Rápido"),
            _item("1️⃣", "Configure seu perfil",
                  "Abra ⚙️ Config. → insira seu 時給 Jikyuu (Valor por Hora), escolha o Tipo de Ciclo (4×2, 5×2 ou Alternado) e a Data Início."),
            _item("2️⃣", "Importe os feriados",
                  "Feriados nacionais já vêm embutidos, e se atualizam sozinhos automaticamente quando o app tem conexão com a internet. Para feriados corporativos, acesse 🏭 Feriados e marque manualmente."),
            _item("3️⃣", "Acompanhe no Calendário",
                  "A aba 📅 gera automaticamente o ciclo escolhido. Toque em qualquer dia para registrar horários, faltas ou férias."),
            _item("4️⃣", "Consulte o Holerite",
                  "A aba 📋 mostra a previsão do mês selecionado — referente ao trabalho realizado naquele mês."),
            _item("5️⃣", "Registre o holerite real",
                  "Na aba 🕐 Histórico, registre com o mês do TRABALHO, não o mês em que você recebeu o pagamento. Só o Total de Desconto é obrigatório."),
            _item("⚠️", "Atenção ao mês",
                  "No Japão o holerite geralmente chega no mês seguinte ao trabalho. Se você trabalhou em junho e recebeu o pagamento em julho, registre como '2026-06' no Histórico."),

            # ── Grupos de turno ──────────────────────────────────────
            _title("👥 Grupo (identificação da equipe)"),
            _p("O Grupo (A/B/C...) serve apenas para identificar sua equipe — não afeta o cálculo. O turno (🌙/☀️) e os horários são configurados separadamente em ⚙️ Config."),

                    # ── Configuração de turno ────────────────────────────────
                    _title("⚙️ Configuração de Turno"),
                    _item("Grupo + Turno 🌙☀️", "Configure em ⚙️ Config.",
                          "Grupo identifica sua equipe. Turno define os horários padrão: entrada, saída, intervalo e início de hora extra. Todos os dias sem registro usam esses horários."),

                    _title("📅 Domingo — 法定休日 Folga Legal"),
                    _p("Domingo é folga legal obrigatória pela lei japonesa. Se trabalhou, o app aplica a taxa cheia de 1,35x sobre essas horas (não soma em cima da base). Sem registro de horário = não trabalhado."),

            # ── Tipos de Ciclo ─────────────────────────────────────────
            _title("🔄 Tipos de Ciclo de Trabalho"),
            _p("Escolha em ⚙️ Config. o padrão que sua empresa usa:"),
            _item("4×2 (四勤二休)", "4 dias de trabalho + 2 dias de folga",
                  "Padrao de fabricas com turno fixo. Cicla automaticamente a partir da Data Inicio."),
            _item("5×2", "Segunda a sexta-feira, fim de semana livre",
                  "Padrao de turno comercial. Sabado e domingo sao sempre folga."),
            _item("Alternado Semanal", "1 semana inteira diurno, proxima semana inteira noturno",
                  "Configure os dois horarios (dia e noite) - o app alterna automaticamente a cada semana."),
            ft.Container(
                content=ft.Row(controls=[
                    ft.Container(content=ft.Text("T", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a5c1a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Container(content=ft.Text("T", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a5c1a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Container(content=ft.Text("T", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a5c1a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Container(content=ft.Text("T", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a5c1a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Container(content=ft.Text("F", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a2a4a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Container(content=ft.Text("F", size=11,
                        color="#ffffff", text_align=ft.TextAlign.CENTER),
                        bgcolor="#1a2a4a", border_radius=4,
                        width=28, height=28, alignment=ft.Alignment(0,0)),
                    ft.Text("→ repete", size=11, color=TEXT_MUTED),
                ], spacing=4),
                padding=ft.Padding(left=0, right=0, top=6, bottom=6),
            ),

            # ── Adicionais (Lei Trabalhista Japonesa) ────────────────
            _title("💴 Adicionais (Lei Trabalhista 労働基準法)"),
            _rule("残業手当 Hora Extra", "Horas após o limite do turno",
                  "Taxa cheia 1,25x (separado da base)"),
            _rule("深夜手当 Adicional Noturno", "Minutos entre 22:00 e 05:00",
                  "+25% sobre base"),
            _rule("休出手当・法定休出 Folga/Feriado/Domingo",
                  "Trabalhou em dia de folga, feriado ou domingo",
                  "Taxa cheia 1,35x (único adicional)"),
            _p("⚠️ Domingo e feriado trabalhado recebem 1,35x sobre as horas trabalhadas nesse dia — essas horas não aparecem separadamente em 'Salário Base', e não soma noturno nem hora extra por cima, mesmo que o horário caia na madrugada. Mesma lógica para hora extra: as horas de 残業 saem 100% da linha 'Salário Base' e vão para 'Hora Extra' à taxa cheia de 1,25x — nunca as duas linhas juntas para a mesma hora. Validado com holerites reais da empresa."),

            # ── Ponto diário ─────────────────────────────────────────
            _title("📅 Registrando o Ponto"),
            _item("Trabalho Normal", "Nenhuma alteração",
                  "Deixe em branco → usa o horário configurado em ⚙️ Config."),
            _item("有休 Yukyu", "Célula laranja — jornada normal, sem extra/noturno",
                  "Com horário → paga as horas efetivas. Sem horário → usa a jornada normal configurada em ⚙️ Config (entrada até o início da hora extra, menos intervalo) — não é mais um valor fixo de 8h."),
            _item("欠勤 Falta — Célula Roxa", "¥0 — não remunerada",
                  "O campo horário é ignorado. Falta = sem pagamento."),
            _item("Saída Antecipada", "Célula verde-azulado",
                  "Preencha o horário de saída real. Hora extra = 0 se saiu antes do limite configurado."),
            _item("延長 Min. Extras", "Campo numérico no modal",
                  "Minutos além do turno que a empresa pediu. Calculado separadamente à taxa cheia de 1,25x."),
            _item("Abono / Vale / Bico extra (¥)", "Campo numérico no modal",
                  "Qualquer ganho extra do dia: vale, arubaito (バイト), gorjeta, ajuda de custo. Acumulado no holerite separadamente."),
            _item("Trabalho em Folga/Feriado", "Preencha Entrada e Saída",
                  "Taxa cheia 1,35x sobre essas horas. Vale para folga, feriado e domingo."),
            _item("有休 em Feriado Corporativo",
                  "Ative o toggle 有休 em Feriado, sem preencher horário",
                  "Usa a jornada normal configurada (igual ao Yukyu comum) — não injeta mais 8h fixo. Se preencher Entrada/Saída, conta como trabalho no feriado (taxa cheia), não Yukyu."),

            # ── Direito a Yukyu ──────────────────────────────────────
            _title("🌴 Direito a Yukyu (有給休暇)"),
            _p("Baseado no Art. 39 da Lei Trabalhista Japonesa (労働基準法). Preencha a 'Data de Admissão' em ⚙️ Config (Etapa 4) — diferente da 'Data de Início do Ciclo', que é sobre o turno, não sobre quando você foi contratado."),
            _example("Progressão dos dias concedidos (tabela cheia, 5+ dias/semana):", [
                "6 meses      → 10 dias",
                "1 ano 6m     → 11 dias",
                "2 anos 6m    → 12 dias",
                "3 anos 6m    → 14 dias",
                "4 anos 6m    → 16 dias",
                "5 anos 6m    → 18 dias",
                "6 anos 6m+   → 20 dias (teto)",
            ]),
            _item("Expiração de 2 anos", "Art. 115 da Lei Trabalhista",
                  "Cada concessão vale só 2 anos. O app consome o saldo mais antigo primeiro (FIFO), pra não desperdiçar dias prestes a vencer."),
            _item("Desconto automático", "Marque 有休 no calendário",
                  "Cada dia marcado como Yukyu (célula laranja) desconta 1 dia do saldo, automaticamente, na próxima vez que você abrir ⚙️ Config."),
            _item("Uso sem saldo disponível", "Aparece um aviso ⚠️ no resumo",
                  "Acontece se você marcar Yukyu antes de completar 6 meses, ou além do que já foi concedido — confira o histórico nesses casos."),
            _p("⚠️ Duas limitações desta versão: (1) não verifica a regra de 80% de presença no período aquisitivo — assume que você tem direito; (2) cobre só a tabela cheia (5+ dias/semana) — não calcula o proporcional (比例付与) de quem trabalha part-time."),

            # ── Assiduidade mensal (精皆勤手当) ─────────────────────────
            _title("📋 Assiduidade do Mês (精皆勤手当 — seikaikin teate)"),
            _p("Diferente da regra dos 80% do Yukyu (que é por período de 6 meses/1 ano, nunca mensal), o seikaikin teate (精皆勤手当) é um adicional OPCIONAL que cada empresa decide se paga — não existe exigência de lei. Por isso o limiar (ex: 94%) e o que conta como falta variam de empresa pra empresa."),
            _example("Fórmula usada nesta versão:", [
                "presença = trabalhados",
                "  ÷ programados no mês",
                "  × 100",
            ]),
            _item("Limiar configurável", "⚙️ Config, Etapa 4",
                  "Cada empresa define o próprio percentual mínimo — não existe um valor padrão da lei. Ajuste pro que a sua empresa usa (o app não sabe esse número sozinho)."),
            _item("Interpretação de falta é sua", "O app não define isso sozinho",
                  "Cada empresa trata 'falta' de um jeito diferente, e o app não tenta adivinhar as regras da sua empresa — ele só conta o que VOCÊ marcar como Falta no calendário. Vale confirmar com o RH o que conta oficialmente antes de marcar, principalmente se sua empresa também descontar atraso ou saída antecipada (isso o app ainda não rastreia)."),
            _item("O total de dias muda todo mês", "Não é um número fixo",
                  "O cálculo usa os dias programados DAQUELE mês específico, que variam com feriados e o seu ciclo de trabalho — então a mesma 1 falta pesa diferente dependendo do mês."),
            _example("Exemplo — a mesma 1 falta em meses diferentes:", [
                "20 dias programados:",
                "  19/20 = 95,0%",
                "15 dias programados:",
                "  14/15 = 93,3%",
            ]),
            _item("Yukyu não desconta", "Art. 136 da Lei Trabalhista",
                  "Usar férias remuneradas não pode ser tratado como falta pra esse adicional — protegido por lei, mesmo esse sendo um benefício opcional da empresa."),
            _item("Feriado da empresa", "Não entra no cálculo",
                  "Dias de feriado corporativo não contam nem como dia programado nem como falta — não é um dia que você deveria comparecer de qualquer forma."),
            _p("📅 A barra de progresso fica na aba Calendário, no topo — fica verde quando está dentro do limiar configurado, vermelha quando fica abaixo."),

            # ── Cores do calendário ──────────────────────────────────
            _title("🎨 Cores do Calendário"),
            _color_legend(WORK_COLOR, "Verde — Dia de Trabalho",
                          "Turno normal conforme o ciclo escolhido"),
            _color_legend(OFF_COLOR, "Azul — Folga",
                          "Dias de descanso do ciclo"),
            _color_legend(CAL_SUNDAY_WORK, "Vermelho Escuro — Domingo Trabalhado",
                          "Taxa cheia 1,35x quando o ciclo marca domingo como trabalho"),
            _color_legend(CAL_CORP, "Amarelo — Feriado",
                          "Feriados nacionais embutidos ou marcados na aba 🏭 Feriados"),
            _color_legend("#FF6D00", "Laranja — 有休 Yukyu",
                          "Dia de férias pagas registrado"),
            _color_legend("#7B1FA2", "Roxo — 欠勤 Falta",
                          "Dia de falta registrado"),
            _color_legend("#00796B", "Verde-azulado — Saída Antecipada",
                          "Horário customizado registrado manualmente"),

            # ── Bônus e Adicionais ────────────────────────────────────
            # ── Mudança de 時給 ────────────────────────────────────────
            _title("📈 Mudança de 時給 Jikyuu — Valor por Hora (Aumento de Salário)"),
            _item("時給 Jikyuu — a partir deste mês", "Campo em 📋 Histórico, opcional.",
                  "O 時給 (Jikyuu, valor por hora) configurado em ⚙️ Config vale sempre, inclusive retroativamente pra meses passados sem registro — se você teve um aumento, a previsão de meses ANTES do aumento ficaria errada sem esse campo. Ao registrar um holerite real no Histórico, preencha \"時給 Jikyuu — Valor por Hora a partir deste mês\" com o novo valor, no mês em que o aumento começou. A previsão de qualquer mês sem registro passa a usar automaticamente o 時給 vigente na época — o marco mais recente igual ou anterior ao mês sendo visto. Sem preencher nada, o app usa sempre o 時給 atual de Config, mesmo pra meses passados."),
            _item("Desconto — Registro Real vs Previsão", "Automático, aba Holerite.",
                  "Ao registrar um holerite real no Histórico, o mês correspondente na aba Holerite deixa de usar a previsão de desconto (Média Histórica ou Fixo, conforme configurado em ⚙️ Config) e passa a mostrar o valor REAL registrado — já é um dado conhecido, não precisa mais estimar. A nota abaixo do valor muda pra \"📋 Registro real\". Meses sem registro continuam usando a previsão normalmente."),

            _title("💰 Bônus e Adicionais Mensais"),
            _item("Adicional Fixo Mensal", "Configure em ⚙️ Config.",
                  "Valor somado AUTOMATICAMENTE todo mês — ideal para função de líder, técnico ou qualquer adicional fixo recorrente. Configure uma vez e esqueça. Também pode ser usado no Arredondamento de Salário (abaixo), sem precisar duplicar o valor em outro campo."),
            _item("Abono Mensal (separado)", "Configure em ⚙️ Config.",
                  "Igual ao Adicional Fixo Mensal (soma todo mês automaticamente), mas NUNCA entra no cálculo de Extra/Noturno/Domingo, mesmo com o Arredondamento com Adicional de Líder ativado. Use pra qualquer abono fixo que não deva afetar essa taxa."),
            _item("Bônus Mês Ímpar 奇数月", "Configure em ⚙️ Config.",
                  "Valor somado apenas em meses ímpares (jan, mar, mai, jul, set, nov)."),
            _item("Abono Extra", "Configure em ⚙️ Config.",
                  "Valor pontual — edite manualmente quando precisar adicionar algo fora do padrão."),

            # ── Arredondamento de Salário ──────────────────────────────
            _title("🔢 Arredondamento de Salário"),
            _item("Modo de Arredondamento", "Botões em ⚙️ Config.",
                  "\"Sempre pra Cima\" (padrão) arredonda toda taxa por hora pra cima, sem exceção. \"Regra do 0,5\" volta ao arredondamento clássico (0,5 sempre sobe, resto trunca) — troque se seu holerite bater melhor com esse modo. Afeta Salário Base, Hora Extra, Noturno e Feriado/Domingo. Não afeta a Média Histórica de desconto, que sempre usa a Regra do 0,5."),
            _p("A taxa (時給 × multiplicador) é arredondada para o yen ANTES de multiplicar pelas horas — não depois. Exemplo com o padrão \"Sempre pra Cima\":"),
            _example("Exemplo — hora extra, 時給=¥1.430, 30h trabalhadas:", [
                "Taxa: 1.430 × 1,25",
                "= 1.787,50 ¥/hora",
                "Arred. (sempre pra cima):",
                "1.788 ¥/hora",
                "Total: 1.788 × 30",
                "= ¥53.640",
            ]),
            _item("Usar Adicional de Líder no Arredondamento", "Switch em ⚙️ Config, desligado por padrão.",
                  "Quando ativado, separa o cálculo da taxa de Extra/Noturno/Domingo em duas partes — jikyuu puro e o acréscimo do Adicional Fixo Mensal — cada uma arredondada individualmente antes de somar, em vez de somar tudo numa taxa só. Regra confirmada por um RH específico — pode não valer pra toda empresa. Revela o campo \"Horas Padrão para este Cálculo\" (ex: 168h), que também varia por empresa — confirme sempre com seu RH ou compare com um holerite real."),
            _item("Minutos de Intervalo no Período Noturno", "Campo em ⚙️ Config, padrão 0.",
                  "Desconta a duração do seu intervalo (que cai dentro de 22h-5h) da janela noturna cheia de 7h, aplicado todo dia com turno noturno completo — ex: 45min de intervalo dentro do período = 6,25h de adicional noturno por dia, em vez de 7h. Não sabe a posição exata do seu intervalo? Deixe em 0 (sem desconto)."),
            _item("Abono / Vale / Bico extra", "Campo no modal de ponto, por dia",
                  "Para valores específicos de UM dia — arubaito, gorjeta, vale-transporte extra."),

            # ── Descontos ────────────────────────────────────────────
            _title("🔢 Previsão de Descontos"),
            _item("📊 Média Histórica", "Botão em ⚙️ Config.",
                  "Valor médio em ¥ calculado automaticamente a partir dos descontos reais registrados no Histórico — não é mais uma porcentagem do bruto, é a média dos valores em ienes já pagos."),
            _item("✏️ Desconto Fixo", "Botão em ⚙️ Config.",
                  "Usa o valor fixo em ¥ que você configurar, ignorando o histórico."),
            _item("⭐ Campo obrigatório", "Apenas 1 campo",
                  "Total de Desconto é essencial — é o valor usado para calcular a média histórica. Total Bruto e Salário Líquido são opcionais, só para seu registro pessoal (não entram no cálculo)."),
            _item("📅 Mês do Histórico", "Use o mês do TRABALHO",
                  "Se você recebeu o holerite em julho referente ao trabalho de junho, registre como '2026-06', não '2026-07'."),
            _item("✏️ Editar registro", "Toque em qualquer card",
                  "Abre o registro para edição. Um botão Remover aparece quando estiver editando."),

            # ── CSV de feriados ──────────────────────────────────────
            _title("📄 Formato do CSV de Feriados Corporativos"),
            _p("Feriados nacionais se atualizam sozinhos automaticamente — esse CSV é só para feriados da sua empresa (recessos, aniversário da fábrica, etc.)."),
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("2025-08-13  ← aniversário da fábrica",
                            size=11, color=YEN_GOLD),
                    ft.Text("2025-12-25  ← recesso de fim de ano",
                            size=11, color=YEN_GOLD),
                ], spacing=2, tight=True),
                bgcolor="#333333", border_radius=8,
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
            ),

            # ── Privacidade ──────────────────────────────────────────
            _title("🔒 Privacidade e Dados"),
            _p("✅ 100% offline — nenhum dado sai do seu dispositivo."),
            _p("✅ Tudo salvo localmente via localStorage do navegador."),
            _p("✅ Sem conta, sem servidor, sem nuvem."),
            _p("⚠️  Limpar dados do navegador apaga o histórico do app."),
            _p("💡 Use ⚙️ Config. → Apagar Dados para reset completo."),

            ft.Container(height=20),
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("⚠️  Aviso Legal", size=12,
                            color="#FFB74D", weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Os valores exibidos são estimativas baseadas nas "
                        "configurações inseridas por você. Este aplicativo NÃO "
                        "substitui o holerite oficial emitido pela empresa e não "
                        "é elaborado por advogado, contador ou despachante "
                        "trabalhista. Consulte o RH ou um profissional "
                        "qualificado para esclarecimentos oficiais.\n\n"
                        "O app é gratuito, sem fins lucrativos, 100% offline, e "
                        "fornecido \"como está\", sem garantias — o desenvolvedor "
                        "não se responsabiliza por decisões tomadas com base nos "
                        "valores calculados.",
                        size=11, color="#A0A0A0",
                    ),
                    ft.Text(
                        "Estimated values, provided \"as is\" without warranties. "
                        "This app does not replace the official payslip issued "
                        "by your employer.",
                        size=10, color="#757575", italic=True,
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        f"✅ Você aceitou estes termos em: "
                        f"{state.get('settings', {}).get('disclaimer_accepted_at') or '—'}",
                        size=10, color="#00D2C6",
                    ),
                    ft.Text(
                        "Projeto de código aberto sob Licença MIT — veja o "
                        "arquivo LICENSE no repositório do GitHub.",
                        size=10, color="#757575",
                    ),
                ], spacing=6, tight=True),
                bgcolor="#2A2A2A", border_radius=10,
                padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                border=ft.Border.all(1, "#FFB74D"),
                margin=ft.Padding(left=0, right=0, top=8, bottom=0),
            ),
            ft.Container(height=20),
        ],
        spacing=2, tight=True,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.Column(
        controls=[
            ft.Row(controls=[
                ft.Text("❓  Manual de Uso", size=16,
                        color=TEXT_PRIMARY, weight=ft.FontWeight.W_800,
                        expand=True),
                ft.Text("v2.1", size=10, color=TEXT_MUTED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=sections,
                expand=True,
            ),
        ],
        spacing=8,
        expand=True,
    )


async def main(page: ft.Page):
    global SCALE
    page.title            = "Onion Payroll"
    page.theme_mode       = ft.ThemeMode.DARK
    page.bgcolor          = BG_DEEP
    page.padding          = 0
    page.spacing          = 0

    # Janela redimensionável pelo usuário
    try:
        page.window_width          = 420
        page.window_height         = 760
        page.window_min_width      = 340
        page.window_min_height     = 500
        page.window_resizable      = True
        page.window_maximizable    = True
    except Exception:
        pass   # ambiente web ignora config de janela

    # Detectar se é desktop (janela grande) e ajustar escala
    try:
        w = page.window_width or 400
    except Exception:
        w = 400
    if w > 900:
        SCALE = 1.8
    elif w > 600:
        SCALE = 1.4
    else:
        SCALE = 1.0

    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#00D2C6",
            on_primary="#121212",
            secondary="#009E94",
            surface="#1E1E1E",
            on_surface="#F0F0F0",
        ),
    )

    await boot_load_storage(page)

    _raw_s   = load_json(page, KEY_SETTINGS, {})
    settings = {**DEFAULT_SETTINGS, **(_raw_s if isinstance(_raw_s, dict) else {})}
    # Migração v2.14: quem já usava o app antes do wizard por etapas não
    # deve ver as etapas 2/3/4 sumirem — se já existe um cycle_type salvo
    # de verdade (não só o default), trata como "já confirmado".
    if isinstance(_raw_s, dict) and "cycle_type" in _raw_s and "cycle_type_confirmed" not in _raw_s:
        settings["cycle_type_confirmed"] = True
    # Migração v2.36 REVERTIDA na v2.37 — aplicava ¥2.720 pra qualquer
    # usuário com o campo em 0, mas isso inclui usuários NOVOS de
    # empresas diferentes cujo valor correto de verdade É 0. Sem forma
    # confiável de diferenciar "usuário antigo desta empresa específica"
    # de "usuário novo de outra empresa" sem a tela visível, a correção
    # segura é não migrar nada — cada instalação fica com 0 (neutro) até
    # decidirmos uma forma de calibração que não dependa de hardcode.
    _mem_cache[KEY_SETTINGS] = settings
    history   = load_json(page, KEY_HISTORY,   [])
    overrides = load_json(page, KEY_OVERRIDES, {})
    # Feriados nacionais: tenta buscar a versão atualizada (gerada 1x/ano
    # por GitHub Action a partir do CSV oficial do governo) — se falhar
    # por qualquer motivo, cai de volta pro JP_HOLIDAYS_BUILTIN fixo.
    # Nunca bloqueia o boot do app por mais de alguns segundos (timeout
    # interno em fetch_updated_holidays).
    _updated_holidays = await fetch_updated_holidays()
    holidays = _updated_holidays if _updated_holidays else {**JP_HOLIDAYS_BUILTIN}
    # Mesclar com os feriados corporativos importados pelo usuário
    _imported = load_json(page, KEY_HOLIDAYS, {})
    for mk, days in _imported.items():
        if mk not in holidays:
            holidays[mk] = []
        for d in days:
            if d not in holidays[mk]:
                holidays[mk].append(d)

    today = date.today()
    state = {
        "settings":      settings,
        "history":       history,
        "overrides":     overrides,
        "holidays":      holidays,
        "cal_year":      today.year,
        "cal_month":     today.month,
        "hol_year":      today.year,
        "hol_month":     today.month,
        "extra_bonus":   0,
        "hol_odd_bonus": int(settings.get("odd_bonus", 50000)),
        "active_tab":    0,
        "holidays_corp": load_json(page, "onion_holidays_corp", {}),
    }

    def _iniciar_app():
        """Constrói e mostra a interface principal do app."""
        # Logo — desktop usa caminho absoluto, web usa src relativo (assets/)
        import os as _os
        _assets_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets")
        _logo_abs   = _os.path.join(_assets_dir, "logo_icon.png")
        _is_web     = hasattr(page, "web") and page.web

        _logo_box = scaled(72)

        def _wrap_logo(img_src: str) -> ft.Container:
            """Envolve a logo num Container com cantos arredondados e um
            fundo levemente mais claro que o header, para suavizar o
            contraste contra imagens com fundo transparente."""
            return ft.Container(
                content=ft.Image(src=img_src, width=_logo_box - 12,
                                  height=_logo_box - 12, fit="contain"),
                width=_logo_box, height=_logo_box,
                border_radius=14, bgcolor=BG_CARD,
                alignment=ft.Alignment(0, 0),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            )

        if _is_web:
            # No modo web/PWA o Flet serve assets/ automaticamente
            logo = _wrap_logo("logo_icon.png")
        elif _os.path.exists(_logo_abs):
            logo = _wrap_logo(_logo_abs)
        else:
            logo = ft.Text("🧅", size=36)
        title_col = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("ONION ", size=scaled(17), weight=ft.FontWeight.W_900,
                                color="#FFFFFF",
                                style=ft.TextStyle(letter_spacing=2.0)),
                        ft.Text("PAYROLL", size=scaled(17), weight=ft.FontWeight.W_900,
                                color=ACCENT,
                                style=ft.TextStyle(letter_spacing=2.0)),
                    ],
                    spacing=0, tight=True,
                ),
                ft.Row([
                    ft.Text("PEEL YOUR PAYCHECK", size=scaled(8), color=TEXT_SECONDARY,
                            style=ft.TextStyle(letter_spacing=2.5)),
                    ft.Text(f"#{BUILD_ID}", size=scaled(7), color="#444444",
                            style=ft.TextStyle(letter_spacing=1.0)),
                ], spacing=6, tight=True),
            ],
            spacing=2, tight=True,
        )
        header = ft.Container(
            content=ft.Row(controls=[ft.Row([logo, ft.Container(width=10), title_col])]),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=[HEADER_BG, "#0A1A18"],
            ),
            padding=ft.Padding(left=16, right=16, top=10, bottom=10),
            border=ft.Border(bottom=ft.BorderSide(2, ACCENT)),
        )

        content_area = ft.Container(
            expand=True,
            bgcolor=BG_DEEP,
            padding=ft.Padding(left=scaled(12), right=scaled(12), top=scaled(8), bottom=scaled(8)),
        )

        tab_defs = [
            ("Calendário", "📅"),
            ("Holerite",   "📋"),
            ("Histórico",  "🕐"),
            ("Feriados",   "🏭"),
            ("Config.",    "⚙️"),
            ("Ajuda",      "❓"),
        ]
        nav_buttons = []

        def _make_nav(idx, lbl, icon):
            def _tap(_):
                state["active_tab"] = idx
                refresh_all()
            return ft.GestureDetector(
                on_tap=_tap,
                content=ft.Container(
                    content=ft.Column(
                        controls=[ft.Text(icon, size=22), ft.Text(lbl, size=10)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2, tight=True,
                    ),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                    padding=ft.Padding(left=0, right=0, top=4, bottom=4),
                ),
                expand=True,
            )

        for i, (lbl, ico) in enumerate(tab_defs):
            nav_buttons.append(_make_nav(i, lbl, ico))

        nav_bar = ft.Container(
            content=ft.Row(
                controls=nav_buttons,
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=NAV_BG,
            height=scaled(65),
            padding=ft.Padding(left=8, right=0, top=0, bottom=0),
            border=ft.Border(top=ft.BorderSide(2, NAV_BORDER)),
        )

        def refresh_all():
            tab = state["active_tab"]
            # Usar settings do _mem_cache — preserva mudanças feitas via __setitem__
            _cached = _mem_cache.get(KEY_SETTINGS)
            if _cached and isinstance(_cached, dict):
                state["settings"] = _cached
            # Sempre ler diretamente do _mem_cache para garantir o dado mais
            # recente, evitando qualquer inconsistência de closures antigas
            state["history"]   = _mem_cache.get(KEY_HISTORY,   [])
            state["overrides"] = _mem_cache.get(KEY_OVERRIDES, {})
            # NÃO reler state["holidays"] de _mem_cache.get(KEY_HOLIDAYS) —
            # bug real corrigido: KEY_HOLIDAYS ("onion_holidays") nunca é
            # gravado em lugar nenhum do código atual (a importação de CSV
            # corporativa usa uma chave diferente, "onion_holidays_corp"),
            # então essa linha sempre lia um cache vazio e ZERAVA os
            # feriados nacionais (buscados/embutidos no boot do app) a
            # cada troca de aba ou ação — só os feriados corporativos
            # (armazenados em state["holidays_corp"], não afetado por essa
            # linha) continuavam aparecendo. state["holidays"] já é
            # montado corretamente uma vez no boot (main()) e não precisa
            # ser "atualizado" a partir de um cache que ninguém escreve.

            builders = [build_calendar_tab, build_holerite_tab,
                        build_history_tab,  build_holidays_tab,
                        build_settings_tab, build_help_tab]
            inner = builders[tab](page, state, refresh_all)

            if isinstance(inner, ft.Column):
                inner.expand = True

            content_area.content = inner

            for i, btn in enumerate(nav_buttons):
                try:
                    col = btn.content.content  # Container → Column
                    active = (i == tab)
                    col.controls[0].color = ACCENT if active else TEXT_MUTED
                    col.controls[1].color = ACCENT if active else "#475569"
                    col.controls[1].weight = ft.FontWeight.W_700 if active else ft.FontWeight.NORMAL
                except Exception:
                    pass

            page.update()

        main_layout = ft.Column(
            controls=[header, content_area, nav_bar],
            spacing=0,
            expand=True,
        )

        page.add(main_layout)
        refresh_all()

    # ── Disclaimer de primeiro uso (v2.29) ─────────────────────
    # "Clickwrap": só mostra 1 vez, salvo em settings. Recusar
    # bloqueia o app nesta sessão (recarregar a página = nova chance,
    # sem travar o usuário definitivamente sem saída).
    if settings.get("disclaimer_accepted"):
        _iniciar_app()
        return

    def _aceitar_disclaimer(e):
        settings["disclaimer_accepted"] = True
        settings["disclaimer_accepted_at"] = datetime.now().isoformat(timespec="seconds")
        _mem_cache[KEY_SETTINGS] = settings
        save_json(page, KEY_SETTINGS, settings)
        page.clean()
        _iniciar_app()

    def _recusar_disclaimer(e):
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column(controls=[logo_disclaimer], alignment=ft.MainAxisAlignment.CENTER,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0), expand=True, bgcolor=BG_DEEP,
            )
        )
        page.update()

    logo_disclaimer = ft.Container(
        content=ft.Image(src="logo_icon.png", width=88, height=88, fit="contain"),
        width=100, height=100, border_radius=20, bgcolor=BG_CARD,
        alignment=ft.Alignment(0, 0), clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    page.add(
        ft.Container(
            expand=True, bgcolor=BG_DEEP,
            padding=ft.Padding(left=20, right=20, top=20, bottom=12),
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=ft.Image(src="logo_icon.png", width=70, height=70, fit="contain"),
                        width=80, height=80, border_radius=18, bgcolor=BG_CARD,
                        alignment=ft.Alignment(0, 0), clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Container(height=6),
                    ft.Row(
                        controls=[
                            ft.Image(src="logo_icon.png", width=26, height=26, fit="contain"),
                            ft.Text("Onion Payroll", size=22, weight=ft.FontWeight.W_800, color="#FFFFFF"),
                        ],
                        spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text("Antes de continuar", size=13, color=TEXT_SECONDARY),
                    ft.Container(height=8),
                    ft.Container(
                        bgcolor=BG_CARD, border_radius=12, padding=12,
                        content=ft.Column(spacing=5, controls=[
                            ft.Text("⚠️ Aviso Legal", size=14, weight=ft.FontWeight.W_700, color=WARNING),
                            ft.Text(
                                "Os valores exibidos são estimativas baseadas nas "
                                "configurações inseridas por você. Este aplicativo "
                                "NÃO substitui o holerite oficial emitido pela empresa "
                                "e não é elaborado por advogado, contador ou despachante "
                                "trabalhista. Consulte o departamento de RH ou um "
                                "profissional qualificado para esclarecimentos oficiais "
                                "sobre sua remuneração.\n\n"
                                "O app é gratuito, sem fins lucrativos, 100% offline "
                                "(nenhum dado sai do seu dispositivo) e fornecido "
                                "\"como está\", sem garantias — o desenvolvedor não se "
                                "responsabiliza por decisões tomadas com base nos "
                                "valores calculados.",
                                size=12, color=TEXT_PRIMARY,
                            ),
                        ]),
                    ),
                    ft.Container(height=10),
                    ft.FilledButton(
                        "Aceitar e Continuar", on_click=_aceitar_disclaimer,
                        style=ft.ButtonStyle(bgcolor=ACCENT, color="#121212"),
                        width=280,
                    ),
                    ft.Container(height=4),
                    ft.TextButton(
                        "Recusar", on_click=_recusar_disclaimer,
                        style=ft.ButtonStyle(color=TEXT_MUTED),
                    ),
                ],
            ),
        )
    )

ft.app(target=main, assets_dir="assets")
