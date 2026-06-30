"""
Onion Payroll — Factory Shift Manager
Compatível com Flet 0.85.x
Todas as correções de API aplicadas.
"""

import flet as ft
import json
import math
from datetime import date, datetime, timedelta
from typing import Optional

# ─────────────────────────────────────────────
#  BUSINESS LOGIC — Decoupled from UI
# ─────────────────────────────────────────────

def shisha_gofuuu(value: float) -> int:
    """四捨五入 — Japanese rounding: 0.5 rounds UP."""
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


def truncate_minutes(total_minutes: int, block: int) -> int:
    if block <= 1:
        return total_minutes
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


def calculate_shift_pay(
    jikyuu: int, shift_type: str, start_str: str = "", end_str: str = "",
    break_min: int = 65, block: int = 1, is_holiday: bool = False,
    yukyu_on_holiday: bool = False,
) -> dict:
    result = {
        "base_pay": 0, "overtime_pay": 0, "night_pay": 0, "holiday_pay": 0,
        "total_gross": 0, "net_minutes": 0, "overtime_minutes": 0,
        "night_minutes": 0, "regular_minutes": 0,
    }

    if shift_type == "absent":
        return result

    if yukyu_on_holiday and is_holiday:
        # Toggle 有休 em feriado: sempre 8h base fixo
        result["base_pay"] = shisha_gofuuu(jikyuu * 8)
        result["total_gross"] = result["base_pay"]
        return result

    if shift_type == "yukyu":
        if start_str and end_str:
            # Yukyu parcial: calcular pelo horário real, SEM OT e SEM noturno
            start_dt = parse_hhmm(start_str)
            end_dt   = parse_hhmm(end_str)
            if start_dt and end_dt:
                gross_min = minutes_between(start_dt, end_dt)
                net_min   = max(0, truncate_minutes(gross_min - break_min, block))
                result["net_minutes"] = net_min
                result["base_pay"]    = shisha_gofuuu((jikyuu / 60.0) * net_min)
                result["total_gross"] = result["base_pay"]
                return result
        # Sem horário ou horário inválido: 8h base fixo (padrão)
        result["base_pay"] = shisha_gofuuu(jikyuu * 8)
        result["total_gross"] = result["base_pay"]
        return result

    if shift_type == "night":
        default_start, default_end, ot_start_str = "20:35", "08:35", "06:35"
    elif shift_type in ("day", "holiday"):
        default_start, default_end, ot_start_str = "08:35", "20:35", "18:35"
    else:
        return result

    s_str = start_str if start_str else default_start
    e_str = end_str if end_str else default_end

    start_dt = parse_hhmm(s_str)
    end_dt   = parse_hhmm(e_str)
    ot_dt    = parse_hhmm(ot_start_str)

    if not start_dt or not end_dt or not ot_dt:
        return result

    gross_min = minutes_between(start_dt, end_dt)
    net_min   = max(0, truncate_minutes(gross_min - break_min, block))

    result["net_minutes"]      = net_min
    jikyuu_per_min             = jikyuu / 60.0
    # OT só existe se end_dt ultrapassou ot_dt dentro do mesmo contexto de turno
    # Usar diferença bruta sem wrap de 1 dia: se end_dt < ot_dt = sem OT
    _ot_raw = (end_dt - ot_dt).total_seconds() / 60
    # Se negativo, end_dt está antes de ot_dt (turno normal) — mas pode ser dia seguinte
    # Comparar via minutes_between do turno: ot_dt é posterior a start_dt no turno
    _start_to_ot  = minutes_between(start_dt, ot_dt)   # minutos do start ao limite OT
    _start_to_end = minutes_between(start_dt, end_dt)   # minutos do start ao fim real
    # OT só existe se o fim ultrapassou o limite OT dentro do turno
    if _start_to_end > _start_to_ot:
        ot_min = min(_start_to_end - _start_to_ot, net_min)
    else:
        ot_min = 0
    result["overtime_minutes"] = ot_min
    result["regular_minutes"]  = net_min - ot_min
    night_min                  = min(night_minutes_in_range(start_dt, end_dt), net_min)
    result["night_minutes"]    = night_min
    holiday_premium            = 0.35 if is_holiday else 0.0

    result["base_pay"]     = shisha_gofuuu(jikyuu_per_min * net_min)
    result["overtime_pay"] = shisha_gofuuu(jikyuu_per_min * ot_min * 0.25)
    result["night_pay"]    = shisha_gofuuu(jikyuu_per_min * night_min * 0.25)
    result["holiday_pay"]  = shisha_gofuuu(jikyuu_per_min * net_min * holiday_premium) if is_holiday else 0
    result["total_gross"]  = (result["base_pay"] + result["overtime_pay"]
                               + result["night_pay"] + result["holiday_pay"])
    return result


def generate_4x2_calendar(anchor_date: date, year: int, month: int) -> dict:
    result, first_day, last_day = {}, date(year, month, 1), date(year, month, 28)
    for d in range(28, 32):
        try:    last_day = date(year, month, d)
        except ValueError: break
    cursor = first_day
    while cursor <= last_day:
        delta = (cursor - anchor_date).days % 6
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


def compute_monthly_forecast(
    year: int, month: int, jikyuu: int, anchor_date: date, group: str,
    holiday_days: list, day_overrides: dict, odd_month_bonus: int, extra_bonus: int,
    deduction_mode: str, fixed_deduction: int, history_avg_pct: float, block: int,
    shift_type_cfg: str = "", cfg_start: str = "", cfg_end: str = "",
    cfg_break: int = 65, cfg_ot: str = "",
    cycle_type: str = "4x2",
    alt_start_day: str = "08:35", alt_end_day: str = "20:35",
    alt_start_night: str = "20:35", alt_end_night: str = "08:35",
    fixed_monthly_bonus: int = 0,  # adicional fixo todo mês (liderança, etc.)
) -> dict:
    # ── Seleção do tipo de ciclo ──────────────────────────────────
    _alt_shift_map = {}  # dia -> "day"/"night" (só usado se cycle_type=alternating)
    if cycle_type == "5x2":
        cycle = generate_weekly_calendar(year, month)
    elif cycle_type == "alternating":
        _alt_raw = generate_alternating_calendar(anchor_date, year, month)
        cycle = {d: status for d, (status, shift) in _alt_raw.items()}
        _alt_shift_map = {d: shift for d, (status, shift) in _alt_raw.items()}
    else:
        cycle = generate_4x2_calendar(anchor_date, year, month)

    _stype        = shift_type_cfg if shift_type_cfg else ("night" if group == "B" else "day")
    default_shift = _stype
    _start        = cfg_start if cfg_start else ("20:35" if _stype == "night" else "08:35")
    _end          = cfg_end   if cfg_end   else ("08:35" if _stype == "night" else "20:35")
    _break        = cfg_break if cfg_break else 65
    _ot           = cfg_ot    if cfg_ot    else ("06:35" if _stype == "night" else "18:35")
    total_base = total_ot = total_night = total_holiday = total_legal = total_abono = 0
    days_normal = days_holiday = days_legal = 0

    for day_num, cycle_status in cycle.items():
        # No modo alternado, o turno do dia muda conforme a semana
        if cycle_type == "alternating" and day_num in _alt_shift_map:
            _day_shift = _alt_shift_map[day_num]
            default_shift = _day_shift
            if _day_shift == "day":
                _start, _end, _ot = alt_start_day, alt_end_day, "18:35"
            else:
                _start, _end, _ot = alt_start_night, alt_end_night, "06:35"
        ov        = day_overrides.get(str(day_num), {})
        status    = ov.get("status", "normal")   # "normal","absent","yukyu","holiday","legal"
        start_str = ov.get("start", "")
        end_str   = ov.get("end", "")
        break_min = int(ov.get("break_min", _break) or _break)
        yukyu_hol = ov.get("yukyu_on_holiday", False)
        has_time  = bool(start_str)              # tem horário registrado manualmente
        day_abono = int(ov.get("abono", 0) or 0)   # abono/vale do dia
        is_holiday = day_num in holiday_days

        try:
            weekday = date(year, month, day_num).weekday()
            is_sunday = (weekday == 6)
        except Exception:
            is_sunday = False

        # ── Regras por STATUS (o que foi salvo no day_overrides) ──────
        #
        # "absent"  → falta → pular (¥0)
        # "yukyu"   → férias → 8h fixo sem OT/noturno
        # "holiday" → trabalho em feriado → +35%
        # "legal"   → trabalho no domingo → +35%
        # "normal"  → depende do ciclo e do dia da semana:
        #             ciclo=work + domingo → +35% automático
        #             ciclo=work           → turno normal
        #             ciclo=off + horário  → +35% (trabalhou na folga)
        #             ciclo=off + yukyu_hol→ yukyu
        #             ciclo=off            → não trabalhou → pular
        #             feriado + horário    → +35%
        #             feriado              → não trabalhou → pular

        if status == "absent":
            continue   # falta — ¥0, não entra no cálculo

        elif status == "yukyu":
            shift_type = "yukyu"

        elif status in ("holiday", "legal"):
            # Marcado manualmente como feriado/domingo
            shift_type = "holiday"

        elif is_sunday:
            # Domingo — folga legal obrigatória
            if cycle_status == "work" or has_time:
                shift_type = "holiday"   # +35% obrigatório
            else:
                continue   # domingo sem registro → não trabalhou

        elif cycle_status == "off":
            # Dia de folga no ciclo
            if has_time:
                shift_type = "holiday"   # trabalhou na folga → +35%
            elif yukyu_hol and is_holiday:
                shift_type = "yukyu"     # yukyu em feriado
            else:
                continue   # folga sem registro → não trabalhou

        elif is_holiday:
            # Feriado nacional/corporativo
            if has_time:
                shift_type = "holiday"   # trabalhou no feriado → +35%
            elif yukyu_hol:
                shift_type = "yukyu"
            else:
                continue   # feriado sem registro → não trabalhou

        elif status == "early":
            shift_type = default_shift   # horário real descontado automaticamente

        else:
            # Dia normal de trabalho
            shift_type = default_shift


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
        )
        if (is_sunday and not is_holiday) or status == "legal":
            total_legal += pay["total_gross"]
            days_legal  += 1
        elif status == "holiday" or (is_holiday and not is_sunday):
            total_holiday += pay["total_gross"]
            days_holiday  += 1
        else:
            total_base  += pay["base_pay"]
            total_ot    += pay["overtime_pay"]
            total_night += pay["night_pay"]
            if pay["base_pay"] > 0:
                days_normal += 1
        total_abono += day_abono

    applied_odd = odd_month_bonus if month % 2 == 1 else 0
    gross       = (total_base + total_ot + total_night + total_holiday + total_legal
                   + applied_odd + extra_bonus + total_abono + fixed_monthly_bonus)
    deductions  = (fixed_deduction if deduction_mode == "fixed"
                   else shisha_gofuuu(gross * history_avg_pct / 100))

    return {
        "base_pay": total_base, "overtime_pay": total_ot, "night_pay": total_night,
        "holiday_pay": total_holiday, "legal_holiday_pay": total_legal,
        "odd_bonus": applied_odd, "extra_bonus": extra_bonus,
        "gross": gross, "deductions": deductions, "net": gross - deductions,
        "days_normal": days_normal, "days_holiday": days_holiday, "days_legal": days_legal,
        "abono_total": total_abono,
        "fixed_monthly_bonus": fixed_monthly_bonus,
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
        width=360,
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
    "2025-09": [15, 22, 23],
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

DEFAULT_SETTINGS = {
    "jikyuu": 1500, "group": "B", "anchor_date": date.today().isoformat(),
    "odd_bonus": 50000, "deduction_mode": "historical", "fixed_deduction": 45000,
    "block": 1, "pin_enabled": False,
    "shift_type": "night", "shift_start": "20:35", "shift_end": "08:35",
    "shift_break": 65, "shift_ot": "06:35", "extra_bonus": 0,
    "fixed_monthly_bonus": 0,  # adicional fixo todo mês (ex: liderança)
    "cycle_type": "4x2",  # "4x2" | "5x2" | "alternating"
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
BUILD_ID       = "0000000000"   # atualizado automaticamente pelo deploy.ps1
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
WORK_COLOR     = "#1a3d2b"   # Trabalho — verde escuro saturado
OFF_COLOR      = "#1e2e4a"   # Folga — azul escuro saturado
HOL_COLOR      = "#4a1a1a"   # Feriado nacional — vermelho escuro

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
CAL_CORP       = "#3d2000"   # Feriado corp — marrom escuro
CAL_MODIF      = "#2d1a4a"   # Modificado — roxo escuro
CAL_TEXT_WORK  = "#86efac"   # verde claro
CAL_TEXT_OFF   = "#93c5fd"   # azul claro
CAL_TEXT_HOL   = "#fca5a5"   # vermelho claro
CAL_TEXT_CORP  = "#fdba74"   # laranja claro
CAL_TEXT_YUKYU = "#fb923c"   # laranja médio
CAL_TEXT_MODIF = "#c4b5fd"   # lilás claro
CAL_BORDER_WORK= "#22c55e"   # verde médio
CAL_BORDER_OFF = "#60a5fa"   # azul médio


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
    else:
        cycle = generate_4x2_calendar(anchor, view_year, view_month)
    month_key       = f"{view_year}-{view_month:02d}"
    month_overrides = overrides.get(month_key, {})
    month_holidays  = holidays.get(month_key, [])
    holidays_corp   = state.get("holidays_corp", {})
    month_hol_corp  = holidays_corp.get(month_key, [])

    # ── Day modal ────────────────────────────────────────────────────
    def open_day_modal(day_num: int):
        ov     = month_overrides.get(str(day_num), {})
        is_hol = day_num in month_holidays

        status_dd = ft.Dropdown(
            label="Status", value=ov.get("status", "normal"),
            options=[
                ft.dropdown.Option("normal",  "Trabalho Normal"),
                ft.dropdown.Option("early",   "Saída Antecipada — horário real"),
                ft.dropdown.Option("absent",  "Falta 欠勤"),
                ft.dropdown.Option("yukyu",   "有休 Yukyu — 8h sem 残業/noturno"),
                ft.dropdown.Option("holiday", "休出 Trabalho em Feriado (+35%)"),
                ft.dropdown.Option("legal",   "法定休出 Domingo/Folga Legal (+35%)"),
            ],
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )
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
            label="有休 em Feriado (+8h)",
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
            stype   = "night" if grp == "B" else "day"
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
                                              break_min=brk)
                    preview_text.value = (
                        f"有休 parcial: {pay['net_minutes']}min → "
                        f"{yen(pay['base_pay'])} (sem 残業/noturno)"
                    )
                else:
                    pay = calculate_shift_pay(jikyuu, "yukyu")
                    preview_text.value = (
                        f"有休 dia completo: {yen(pay['base_pay'])} "
                        f"(8h × ¥{jikyuu}/h, sem 残業/noturno)"
                    )

            elif is_off_day and not s:
                # Folga/feriado sem horário preenchido
                if yukyu_sw.value and is_hol_day:
                    pay = calculate_shift_pay(jikyuu, "yukyu")
                    preview_text.value = f"有休 em feriado: {yen(pay['base_pay'])} (8h base)"
                else:
                    preview_text.value = "Folga / feriado — sem trabalho registrado"

            elif is_off_day and s:
                # Trabalhou em folga/feriado → +35% holiday premium
                pay = calculate_shift_pay(jikyuu, "holiday",
                                          start_str=s, end_str=e,
                                          break_min=brk, is_holiday=True)
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
                pay = calculate_shift_pay(jikyuu, stype,
                                          start_str=s, end_str=e, break_min=brk)
                nm = pay["net_minutes"]
                parts = [f"base {yen(pay['base_pay'])}"]
                if pay["overtime_pay"]:
                    parts.append(f"残業 +{yen(pay['overtime_pay'])}")
                if pay["night_pay"]:
                    parts.append(f"深夜 +{yen(pay['night_pay'])}")
                suffix = " (saída antecipada)" if e and not pay["overtime_pay"] else ""
                # Calcular minutos extras solicitados
                try: extra_m = int(extra_min_f.value or 0)
                except: extra_m = 0
                if extra_m > 0:
                    extra_pay = shisha_gofuuu((jikyuu / 60.0) * extra_m * 1.25)
                    parts.append(f"延長 +{yen(extra_pay)}")
                    total_with_extra = pay['total_gross'] + extra_pay
                    preview_text.value = (
                        f"{nm}min+{extra_m}延長 → {' | '.join(parts)} = {yen(total_with_extra)}{suffix}"
                    )
                else:
                    preview_text.value = (
                        f"{nm}min → {' | '.join(parts)} = {yen(pay['total_gross'])}{suffix}"
                    )
            page.update()

        status_dd.on_change = lambda _: _update_preview()
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

        hol_text = ft.Container(
            content=ft.Text("🏭 Feriado da Empresa", size=11, color=DANGER),
            visible=is_hol,
            padding=ft.Padding(left=8, right=8, top=4, bottom=4),
            bgcolor="#FEE2E2", border_radius=8,
        )

        # Verificar tipo de feriado
        _hol_key   = f"{view_year}-{view_month:02d}"
        _jp_hols   = state.get("holidays", {}).get(_hol_key, [])
        _corp_hols = state.get("holidays_corp", {}).get(_hol_key, [])
        if day_num in _jp_hols:
            _hol_label = " 🏮 Feriado Nacional"
        elif day_num in _corp_hols:
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
                status_dd,
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
    C_HOL_JP  = HOL_COLOR     # vermelho escuro — feriado nacional
    C_HOL_CO  = CAL_CORP      # marrom escuro — feriado corporativo
    C_MODIF   = CAL_MODIF     # roxo escuro — modificado
    C_TODAY_B = "#00C2A8"     # borda turquesa hoje
    C_WHITE   = "#F9F9F9"     # texto claro sobre fundo escuro
    C_RED     = "#FF5252"     # domingo — vermelho brilhante
    C_BLUE    = "#40C4FF"     # sábado — azul brilhante

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
        elif is_hol:
            bg = C_HOL_JP        # Feriado nacional — vermelho
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
        elif is_hol:
            num_color = "#FFD740"   # amarelo dourado — feriado nacional
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
        elif is_hol:
            indicator  = "🎌"
            ind_color  = "#FFFFFF"
        else:
            indicator  = ""
            ind_color  = C_WHITE


        # ── Borda cinza claro ────────────────────────────────────────
        if is_today:
            border = ft.Border.all(2, "#00D2C6")
        else:
            border = ft.Border.all(1, "#D0D0D0")

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
                            ft.Text(indicator, size=scaled(8),
                                    color=ind_color),
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

    return ft.Column(
        controls=[nav_row, legend, ft.Container(height=2), header_row,
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

    ratios   = [e.get("ratio", 0) for e in history if e.get("ratio", 0) > 0]
    hist_avg = sum(ratios) / len(ratios) if ratios else 0.0
    hist_sem_dados = len(ratios) == 0

    try:
        anchor = date.fromisoformat(settings["anchor_date"])
    except Exception:
        anchor = today

    month_key = f"{view_year}-{view_month:02d}"
    # Mesclar feriados nacionais (embutidos/CSV) + corporativos da aba 🏭
    # para que ambos afetem o cálculo do holerite, não só a cor da célula
    _nat_hols  = holidays.get(month_key, [])
    _corp_hols = holidays_corp.get(month_key, [])
    _all_holidays_month = sorted(set(_nat_hols) | set(_corp_hols))
    try:
        data = compute_monthly_forecast(
            year=view_year, month=view_month,
            jikyuu=int(settings.get("jikyuu") or 1500),
            anchor_date=anchor, group=settings.get("group", "B"),
            holiday_days=_all_holidays_month,
            day_overrides=overrides.get(month_key, {}),
            odd_month_bonus=int(settings.get("odd_bonus") or 50000),
            extra_bonus=int(settings.get("extra_bonus") or 0),
            deduction_mode=settings.get("deduction_mode", "historical"),
            fixed_deduction=int(settings.get("fixed_deduction") or 0),
            history_avg_pct=hist_avg,
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
        )
    except Exception:
        data = {"gross": 0, "deductions": 0, "net": 0,
                "base_pay": 0, "overtime_pay": 0, "night_pay": 0,
                "holiday_pay": 0, "legal_holiday_pay": 0,
                "odd_bonus": 0, "extra_bonus": 0}

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
    if modo == "fixed":
        if fixed_val == 0:
            deduction_note = "Fixo: ¥0 (sem desconto)"
        else:
            deduction_note = f"Fixo: {yen(fixed_val)}"
    else:
        if hist_sem_dados:
            deduction_note = "Histórico: sem dados — desconto = ¥0"
        else:
            deduction_note = f"Média histórica: {hist_avg:.1f}%"

    # Bônus lidos das configurações — editáveis em ⚙️ Config
    # sem campos duplicados aqui

    return ft.Column(
        controls=[
            nav_row, month_hint,
            card(ft.Column(controls=[
                section_header("支給 VENCIMENTOS"),
                pay_row(f"Salário Base 基本給 ({data.get('days_normal',0)}d)",
                        data["base_pay"]),
                pay_row("Hora Extra 残業手当",
                        data["overtime_pay"],       color=WARNING,     small=True),
                pay_row("Adicional Noturno 深夜手当",
                        data["night_pay"],           color=ACCENT_LITE, small=True),
                pay_row(f"Feriado 休出手当 ({data.get('days_holiday',0)}d)",
                        data["holiday_pay"],         color=DANGER,      small=True),
                pay_row(f"Domingo 法定休出 ({data.get('days_legal',0)}d)",
                        data.get("legal_holiday_pay", 0), color="#EF9A9A", small=True),
                pay_row("Bônus Mês Ímpar 奇数月",
                        data["odd_bonus"],           color=SUCCESS,     small=True),
                pay_row("Adicional Fixo Mensal",
                        data.get("fixed_monthly_bonus", 0), color=SUCCESS, small=True),
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
                    "⚠️ Valores estimados. Não substitui o holerite oficial. Consulte seu RH.",
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
        f_zangyo    = _tf("残業手当 Hora Extra +25%", val=_v("zangyo"))
        f_yakin     = _tf("深夜手当 Ad.Noturno +25%", val=_v("yakin"))
        f_kyushu    = _tf("休出手当 Trab.Feriado +35%", val=_v("kyushutsu"))
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
        f_gross     = _tf_obrigatorio("総支給額 Total Bruto", val=_v("gross"))
        f_ded       = _tf_obrigatorio("控除合計 Total Desc.", val=_v("deductions"))
        f_net       = _tf_obrigatorio("差引支給額 Salário Líq.", val=_v("net"))

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
                "ratio": round(d/g*100, 2) if g else 0.0,
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
                    padding=ft.Padding(left=0, right=14, top=0, bottom=0)),

                # ── Campos obrigatórios PRIMEIRO — sem precisar rolar ──────
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("⭐ OBRIGATÓRIOS — necessários para o cálculo",
                                size=10, color=ACCENT, weight=ft.FontWeight.W_700),
                        _padded_row(f_gross, f_ded, f_net),
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
                            "⭐ Campos com estrela são obrigatórios para calcular o desconto histórico. "
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

    ratios    = [e.get("ratio", 0) for e in state["history"] if e.get("ratio", 0) > 0]
    avg_ratio = sum(ratios) / len(ratios) if ratios else None

    def _history_card(e):
        g  = e.get("gross", 0)
        d  = e.get("deductions", 0)
        n  = e.get("net", g - d)
        rt = e.get("ratio", 0)
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
                    ft.Row(controls=[
                        ft.Text(f"Desc: {rt:.1f}%", size=11, color=TEXT_MUTED),
                        ft.Text("✏️", size=12, color=TEXT_MUTED),
                    ], spacing=6),
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
                ft.Text("Taxa Média de Desconto", size=11, color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(
                    f"{avg_ratio:.1f}%" if avg_ratio else "— Sem dados ainda",
                    size=28, color=ACCENT_LITE, weight=ft.FontWeight.W_800,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text("Usada para prever descontos na aba Holerite", size=10,
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

    group_dd = ft.Dropdown(
        label="Grupo de Turno", value=settings.get("group", "B"),
        options=[
            ft.dropdown.Option("A", "Grupo A"),
            ft.dropdown.Option("B", "Grupo B"),
            ft.dropdown.Option("C", "Grupo C"),
        ],
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
    )
    group_dd.on_change = lambda e: [settings.__setitem__("group", e.control.value), save_json(page, KEY_SETTINGS, settings), refresh_all()]

    shift_type_dd = ft.Dropdown(
        label="Turno 勤務",
        value=settings.get("shift_type", "night"),
        options=[
            ft.dropdown.Option("night", "🌙 Noturno 夜勤"),
            ft.dropdown.Option("day",   "☀️ Diurno 昼勤"),
        ],
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
    )
    shift_type_dd.on_change = lambda e: [settings.__setitem__("shift_type", e.control.value), save_json(page, KEY_SETTINGS, settings), refresh_all()]

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
        _mem_cache[KEY_SETTINGS] = settings
        save_json(page, KEY_SETTINGS, settings)
        btn_4x2.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "4x2" else BG_SURFACE,
            color="#121212" if mode == "4x2" else TEXT_PRIMARY)
        btn_5x2.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "5x2" else BG_SURFACE,
            color="#121212" if mode == "5x2" else TEXT_PRIMARY)
        btn_alt.style = ft.ButtonStyle(
            bgcolor=ACCENT if mode == "alternating" else BG_SURFACE,
            color="#121212" if mode == "alternating" else TEXT_PRIMARY)
        btn_4x2.update(); btn_5x2.update(); btn_alt.update()
        # Alternar visibilidade direto, sem refresh_all() — sem scroll ao topo
        section_4x2_container.visible = (mode != "alternating")
        section_alt_container.visible = (mode == "alternating")
        section_4x2_container.update()
        section_alt_container.update()

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
        "Alternado", on_click=lambda _: _set_cycle_type("alternating"),
        style=ft.ButtonStyle(
            bgcolor=ACCENT if _cur_cycle == "alternating" else BG_SURFACE,
            color="#121212" if _cur_cycle == "alternating" else TEXT_PRIMARY),
        expand=1,
    )
    cycle_type_row = ft.Row([btn_4x2, btn_5x2, btn_alt], spacing=6)


    # Campos do turno alternado (dia/noite)
    alt_day_start_f = _tf_shift("☀️ Dia — Entrada", "shift_start_day", "08:35", is_time=True)
    alt_day_end_f   = _tf_shift("☀️ Dia — Saída",   "shift_end_day",   "20:35", is_time=True)
    alt_night_start_f = _tf_shift("🌙 Noite — Entrada", "shift_start_night", "20:35", is_time=True)
    alt_night_end_f   = _tf_shift("🌙 Noite — Saída",   "shift_end_night",   "08:35", is_time=True)

    shift_start_f = _tf_shift("Entrada 出勤", "shift_start", "20:35", is_time=True)
    shift_end_f   = _tf_shift("Saída 退勤",   "shift_end",   "08:35", is_time=True)
    shift_break_f = _tf_shift("Intervalo 休憩 (min)", "shift_break", "65", is_time=False)
    shift_ot_f    = _tf_shift("残業 Início Hora Extra (fim turno normal)", "shift_ot", "06:35", is_time=True)

    section_4x2_container = ft.Container(
        content=ft.Column(controls=[
            section_header("HORÁRIO DO TURNO 勤務時間"),
            ft.Row([shift_start_f, shift_end_f], spacing=8),
            ft.Row([shift_break_f, shift_ot_f], spacing=8),
        ], spacing=8, tight=True),
        visible=(settings.get("cycle_type", "4x2") != "alternating"),
    )
    section_alt_container = ft.Container(
        content=ft.Column(controls=[
            section_header("HORÁRIOS — TURNO ALTERNADO"),
            ft.Row([alt_day_start_f, alt_day_end_f], spacing=8),
            ft.Row([alt_night_start_f, alt_night_end_f], spacing=8),
            shift_break_f,
        ], spacing=8, tight=True),
        visible=(settings.get("cycle_type", "4x2") == "alternating"),
    )


    block_dd = ft.Dropdown(
        label="Arredondamento do Ponto",
        value=str(settings.get("block", 1)),
        options=[
            ft.dropdown.Option("1",  "Minuto a minuto"),
            ft.dropdown.Option("15", "Blocos de 15 minutos"),
            ft.dropdown.Option("30", "Blocos de 30 minutos"),
        ],
        bgcolor="#2A2A2A", color="#F0F0F0",
        border_color="#333333", focused_border_color="#00D2C6",
        label_style=ft.TextStyle(color="#A0A0A0"),
    )
    block_dd.on_change = lambda e: [settings.__setitem__("block", int(e.control.value)), save_json(page, KEY_SETTINGS, settings)]

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
            hint_text="2025-05-03,jp\n2025-08-13,corp\n2025-01-01",
            bgcolor="#2A2A2A", color="#F0F0F0",
            border_color="#333333", focused_border_color="#00D2C6",
            label_style=ft.TextStyle(color="#A0A0A0"),
        )

        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()

        def _processar(_=None):
            texto = csv_field.value or ""
            lines = texto.strip().splitlines()
            hols      = state["holidays"]
            hols_corp = state.get("holidays_corp", {})
            ok = 0
            for line in lines:
                parts = [p.strip() for p in line.strip().split(",")]
                if not parts or not parts[0]:
                    continue
                tipo = parts[1].lower() if len(parts) > 1 else "jp"
                try:
                    d  = date.fromisoformat(parts[0])
                    mk = f"{d.year}-{d.month:02d}"
                    if tipo == "corp":
                        if mk not in hols_corp: hols_corp[mk] = []
                        if d.day not in hols_corp[mk]:
                            hols_corp[mk].append(d.day); ok += 1
                    else:
                        if mk not in hols: hols[mk] = []
                        if d.day not in hols[mk]:
                            hols[mk].append(d.day); ok += 1
                except Exception:
                    pass
            save_json(page, KEY_HOLIDAYS, hols)
            save_json(page, "onion_holidays_corp", hols_corp)
            state["holidays_corp"] = hols_corp
            _close()
            refresh_all()

        panel = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text("Importar Feriados CSV", size=13,
                            color=TEXT_PRIMARY, weight=ft.FontWeight.W_700,
                            expand=True),
                    ft.TextButton("✕", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Cole o conteúdo do arquivo CSV abaixo:",
                        size=11, color=TEXT_SECONDARY),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("2025-05-03,jp   ← feriado nacional",
                                size=10, color=YEN_GOLD),
                        ft.Text("2025-08-13,corp ← feriado corporativo",
                                size=10, color=YEN_GOLD),
                        ft.Text("2025-01-01      ← sem tipo = jp",
                                size=10, color=TEXT_MUTED),
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
            bgcolor=BG_CARD, border_radius=14, padding=16, width=360,
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
            bgcolor=BG_CARD, border_radius=14, padding=16, width=320,
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
            card(ft.Column(controls=[
                section_header("CONFIGURAÇÃO DE SALÁRIO"),
                mk_field("Valor Hora 時給 (¥)",              "jikyuu"),
                ft.Row([group_dd, shift_type_dd], spacing=8),
                mk_field("Data Início Ciclo 4×2 (AAAA-MM-DD)", "anchor_date",
                         ft.KeyboardType.TEXT),
                mk_field("Bônus Padrão Mês Ímpar (¥)",        "odd_bonus"),
                mk_field("Adicional Fixo Mensal — Líder, etc. (¥)", "fixed_monthly_bonus"),
                ft.Text(
                    "Valor somado automaticamente TODO mês na previsão "
                    "(ex: adicional de liderança, função técnica fixa).",
                    size=9, color=TEXT_MUTED,
                ),
                block_dd,
                section_header("TIPO DE CICLO DE TRABALHO"),
                cycle_type_row,
                ft.Text(
                    "4×2: 4 dias trabalho + 2 folga (fábricas turno fixo)  |  "
                    "5×2: segunda a sexta (turno comercial)  |  "
                    "Alternado: 1 semana dia + 1 semana noite",
                    size=9, color=TEXT_MUTED,
                ),
                section_4x2_container,
                section_alt_container,
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("💡 Como funciona o cálculo:",
                                size=10, color=ACCENT, weight=ft.FontWeight.W_700),
                        ft.Text("• Entrada → Início 残業: horas normais (salário base)",
                                size=10, color=TEXT_SECONDARY),
                        ft.Text("• Início 残業 → Saída: hora extra +25%",
                                size=10, color=TEXT_SECONDARY),
                        ft.Text("• No modo Alternado, a semana define automaticamente dia ou noite",
                                size=10, color=TEXT_MUTED),
                    ], spacing=3, tight=True),
                    bgcolor=BG_SURFACE,
                    border_radius=8,
                    padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                    border=ft.Border.all(1, "#333333"),
                ),
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

            # ── Diagnóstico de Storage (temporário, para debug) ────────
            card(ft.Column(controls=[
                section_header("🔍 DIAGNÓSTICO DE ARMAZENAMENTO"),
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
            bgcolor=BG_CARD, border_radius=14, padding=16, width=320,
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

    ACCENT_LITE = "#00A896"
    TEXT_PRIMARY = "#F0F0F0"
    TEXT_SECONDARY = "#A0A0A0"
    TEXT_MUTED = "#94A3B8"
    BG_CARD = "#FFFFFF"
    BG_SURFACE = "#F8FAFC"
    ACCENT_DARK = "#007A6E"
    SUCCESS = "#00D2C6"
    WARNING = "#FFB74D"
    DANGER = "#EF5350"
    YEN_GOLD = "#F0F0F0"

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
                ft.Text(icon, size=18),
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
            ], spacing=0, tight=True),
        ], spacing=8)

    # ── Seções do manual ─────────────────────────────────────────────
    sections = ft.Column(
        controls=[

            # ── Início rápido ────────────────────────────────────────
            _title("🚀 Início Rápido"),
            _item("1️⃣", "Configure seu perfil",
                  "Abra ⚙️ Config. → insira seu Valor Hora (時給), escolha o Tipo de Ciclo (4×2, 5×2 ou Alternado) e a Data Início."),
            _item("2️⃣", "Importe os feriados",
                  "Feriados nacionais de 2025-2026 já vêm embutidos. Para feriados corporativos, acesse 🏭 Feriados e marque manualmente."),
            _item("3️⃣", "Acompanhe no Calendário",
                  "A aba 📅 gera automaticamente o ciclo escolhido. Toque em qualquer dia para registrar horários, faltas ou férias."),
            _item("4️⃣", "Consulte o Holerite",
                  "A aba 📋 mostra a previsão do mês selecionado — referente ao trabalho realizado naquele mês."),
            _item("5️⃣", "Registre o holerite real",
                  "Na aba 🕐 Histórico, registre com o mês do TRABALHO, não o mês em que você recebeu o pagamento. Apenas 3 campos são obrigatórios."),
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
                    _p("Domingo é folga legal obrigatória pela lei japonesa. Se trabalhou, o app aplica +35% automaticamente. Sem registro de horário = não trabalhado."),

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
                  "+25% sobre base"),
            _rule("深夜手当 Adicional Noturno", "Minutos entre 22:00 e 05:00",
                  "+25% sobre base"),
            _rule("休出手当 Trabalho em Folga/Feriado",
                  "Trabalhou em dia de folga ou feriado",
                  "+35% sobre base"),
            _rule("深夜 + 休出 Noturno em Feriado",
                  "Acumulam sobre a hora base",
                  "+60% total"),
            _p("Arredondamento: 四捨五入 — frações < 0.5 descartadas, ≥ 0.5 arredondadas para cima. Todos os valores em ¥ inteiro."),

            # ── Ponto diário ─────────────────────────────────────────
            _title("📅 Registrando o Ponto"),
            _item("Trabalho Normal", "Nenhuma alteração",
                  "Deixe em branco → usa o horário configurado em ⚙️ Config."),
            _item("有休 Yukyu — Célula Laranja", "8h base fixo sem hora extra e noturno",
                  "Com horário → paga as horas efetivas. Sem horário → 8h fixo."),
            _item("欠勤 Falta — Célula Roxa", "¥0 — não remunerada",
                  "O campo horário é ignorado. Falta = sem pagamento."),
            _item("Saída Antecipada — Célula Verde-azulado", "Preencha o horário de saída real",
                  "Hora extra = 0 se saiu antes do limite configurado. Cálculo pelo tempo real."),
            _item("延長 Minutos Extras Solicitados", "Campo numérico no modal",
                  "Minutos além do turno que a empresa pediu. Calculado separadamente com +25%."),
            _item("Abono / Vale / Bico extra (¥)", "Campo numérico no modal",
                  "Qualquer ganho extra do dia: vale, arubaito (バイト), gorjeta, ajuda de custo. Acumulado no holerite separadamente."),
            _item("Trabalho em Folga/Feriado", "Preencha Entrada e Saída",
                  "+35% automático. Vale para folga, feriado e domingo."),
            _item("有休 em Feriado Corporativo",
                  "Ative o toggle 有休 em Feriado",
                  "Injeta 8h base fixo mesmo sendo feriado da empresa."),

            # ── Cores do calendário ──────────────────────────────────
            _title("🎨 Cores do Calendário"),
            _color_legend(WORK_COLOR, "Verde — Dia de Trabalho",
                          "Turno normal conforme o ciclo escolhido"),
            _color_legend(OFF_COLOR, "Azul — Folga",
                          "Dias de descanso do ciclo"),
            _color_legend(CAL_SUNDAY_WORK, "Vermelho Escuro — Domingo Trabalhado",
                          "+35% automático quando o ciclo marca domingo como trabalho"),
            _color_legend(CAL_CORP, "Amarelo — Feriado",
                          "Feriados nacionais embutidos ou marcados na aba 🏭 Feriados"),
            _color_legend("#FF6D00", "Laranja — 有休 Yukyu",
                          "Dia de férias pagas registrado"),
            _color_legend("#7B1FA2", "Roxo — 欠勤 Falta",
                          "Dia de falta registrado"),
            _color_legend("#00796B", "Verde-azulado — Saída Antecipada",
                          "Horário customizado registrado manualmente"),

            # ── Bônus e Adicionais ────────────────────────────────────
            _title("💰 Bônus e Adicionais Mensais"),
            _item("Adicional Fixo Mensal", "Configure em ⚙️ Config.",
                  "Valor somado AUTOMATICAMENTE todo mês — ideal para função de líder, técnico ou qualquer adicional fixo recorrente. Configure uma vez e esqueça."),
            _item("Bônus Mês Ímpar 奇数月", "Configure em ⚙️ Config.",
                  "Valor somado apenas em meses ímpares (jan, mar, mai, jul, set, nov)."),
            _item("Abono Extra", "Configure em ⚙️ Config.",
                  "Valor pontual — edite manualmente quando precisar adicionar algo fora do padrão."),
            _item("Abono / Vale / Bico extra", "Campo no modal de ponto, por dia",
                  "Para valores específicos de UM dia — arubaito, gorjeta, vale-transporte extra."),

            # ── Descontos ────────────────────────────────────────────
            _title("🔢 Previsão de Descontos"),
            _item("📊 Média Histórica", "Botão em ⚙️ Config.",
                  "Taxa média calculada automaticamente a partir dos holerites reais registrados no Histórico."),
            _item("✏️ Desconto Fixo", "Botão em ⚙️ Config.",
                  "Usa o valor fixo em ¥ que você configurar, ignorando o histórico."),
            _item("⭐ Campos obrigatórios no Histórico", "Apenas 3 campos",
                  "Total Bruto, Total Desconto e Salário Líquido são essenciais. Os demais campos do modal são opcionais — só para seu registro pessoal."),
            _item("📅 Mês do Histórico", "Use o mês do TRABALHO",
                  "Se você recebeu o holerite em julho referente ao trabalho de junho, registre como '2026-06', não '2026-07'."),
            _item("✏️ Editar ou remover registro", "Toque em qualquer card do Histórico",
                  "Abre o registro para edição. Um botão Remover aparece quando estiver editando."),

            # ── CSV de feriados ──────────────────────────────────────
            _title("📄 Formato do CSV de Feriados"),
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("2025-05-03,jp   ← feriado nacional (vermelho)",
                            size=11, color=YEN_GOLD),
                    ft.Text("2025-08-13,corp ← feriado corporativo (laranja)",
                            size=11, color=YEN_GOLD),
                    ft.Text("2025-01-01      ← sem tipo = jp por padrão",
                            size=11, color=TEXT_SECONDARY),
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
                        "configurações inseridas pelo usuário. Este aplicativo "
                        "não substitui o holerite oficial emitido pela empresa. "
                        "Consulte o departamento de RH para esclarecimentos "
                        "sobre sua remuneração.",
                        size=11, color="#A0A0A0",
                    ),
                    ft.Text(
                        "Estimated values. This app does not replace the official "
                        "payslip issued by your employer.",
                        size=10, color="#757575", italic=True,
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
    _mem_cache[KEY_SETTINGS] = settings
    history   = load_json(page, KEY_HISTORY,   [])
    overrides = load_json(page, KEY_OVERRIDES, {})
    # Mesclar feriados embutidos com os importados pelo usuário
    _imported = load_json(page, KEY_HOLIDAYS, {})
    holidays  = {**JP_HOLIDAYS_BUILTIN}
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

    # Logo — desktop usa caminho absoluto, web usa src relativo (assets/)
    import os as _os
    _assets_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets")
    _logo_abs   = _os.path.join(_assets_dir, "logo_icon.png")
    _is_web     = hasattr(page, "web") and page.web

    if _is_web:
        # No modo web/PWA o Flet serve assets/ automaticamente
        logo = ft.Image(src="logo_icon.png",
                        width=scaled(72), height=scaled(72), fit="contain")
    elif _os.path.exists(_logo_abs):
        logo = ft.Image(src=_logo_abs,
                        width=scaled(72), height=scaled(72), fit="contain")
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
        animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1.0,
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
        state["holidays"]  = _mem_cache.get(KEY_HOLIDAYS,  {})

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

ft.app(target=main, assets_dir="assets")