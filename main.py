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
    ot_min                     = max(0, min(minutes_between(ot_dt, end_dt), net_min))
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


def compute_monthly_forecast(
    year: int, month: int, jikyuu: int, anchor_date: date, group: str,
    holiday_days: list, day_overrides: dict, odd_month_bonus: int, extra_bonus: int,
    deduction_mode: str, fixed_deduction: int, history_avg_pct: float, block: int,
) -> dict:
    cycle         = generate_4x2_calendar(anchor_date, year, month)
    default_shift = "night" if group == "B" else "day"
    total_base = total_ot = total_night = total_holiday = 0

    for day_num, cycle_status in cycle.items():
        ov           = day_overrides.get(str(day_num), {})
        status       = ov.get("status", "")
        start_str    = ov.get("start", "")
        end_str      = ov.get("end", "")
        break_min    = int(ov.get("break_min", 65))
        yukyu_hol    = ov.get("yukyu_on_holiday", False)
        is_holiday   = day_num in holiday_days

        # ── Determinar shift_type ─────────────────────────────────
        #
        # status="absent" → falta, ¥0, independente de horário
        # status="yukyu"  → 8h base fixo, sem OT/noturno
        # cycle="off" ou feriado:
        #   sem horário → não trabalhou, pular (exceto yukyu_hol)
        #   com horário → trabalhou nesse dia → +35% holiday premium
        #                 (horas reais inseridas; OT e noturno acumulam)
        # cycle="work" → turno normal, usa horário padrão ou customizado
        #   saída antecipada: end_str preenchido antes do limite →
        #   ot_min=0 automaticamente (não ultrapassou o limiar)

        if status == "absent":
            shift_type = "absent"         # falta: ¥0 sempre

        elif status == "yukyu":
            shift_type = "yukyu"          # 8h base, sem OT, sem noturno

        elif cycle_status == "off" or is_holiday:
            if not start_str:
                # Não trabalhou nesse dia
                if yukyu_hol and is_holiday:
                    # Toggle 有休 em feriado → injeta 8h base
                    shift_type = "yukyu"
                else:
                    continue              # folga/feriado não trabalhado → pular
            else:
                # Trabalhou em folga/feriado → premium +35%
                # Horas calculadas pelos horários reais inseridos
                shift_type = "holiday"

        else:
            # Dia de trabalho normal (ciclo "work")
            # Horário padrão do grupo OU customizado (saída antecipada etc.)
            # OT só ocorre se end_str ultrapassar o limiar (06:35/18:35)
            shift_type = default_shift

        pay = calculate_shift_pay(
            jikyuu=jikyuu, shift_type=shift_type, start_str=start_str,
            end_str=end_str, break_min=break_min, block=block,
            is_holiday=is_holiday, yukyu_on_holiday=yukyu_hol,
        )
        total_base    += pay["base_pay"]
        total_ot      += pay["overtime_pay"]
        total_night   += pay["night_pay"]
        total_holiday += pay["holiday_pay"]

    applied_odd = odd_month_bonus if month % 2 == 1 else 0
    gross       = total_base + total_ot + total_night + total_holiday + applied_odd + extra_bonus
    deductions  = (fixed_deduction if deduction_mode == "fixed"
                   else shisha_gofuuu(gross * history_avg_pct / 100))

    return {
        "base_pay": total_base, "overtime_pay": total_ot, "night_pay": total_night,
        "holiday_pay": total_holiday, "odd_bonus": applied_odd, "extra_bonus": extra_bonus,
        "gross": gross, "deductions": deductions, "net": gross - deductions,
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
                ft.Divider(height=1, color="#E2E8ED"),
                content,
                ft.Divider(height=1, color="#E2E8ED"),
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
        border=ft.Border.all(1, "#D1DBE3"),
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

DEFAULT_SETTINGS = {
    "jikyuu": 1500, "group": "B", "anchor_date": date.today().isoformat(),
    "odd_bonus": 50000, "deduction_mode": "historical", "fixed_deduction": 45000,
    "block": 1, "pin_enabled": False,
}


# Cache em memória — espelha o storage persistente
_mem_cache: dict = {}


def _has_client_storage(page: ft.Page) -> bool:
    """Verifica se page.client_storage existe (modo PWA/web WASM)."""
    try:
        cs = page.client_storage
        return cs is not None
    except Exception:
        return False


def load_json(page: ft.Page, key: str, default):
    """Lê do cache em memória (já populado no boot)."""
    if key in _mem_cache:
        return _mem_cache[key]
    return default


def save_json(page: ft.Page, key: str, value):
    """Salva no cache + persiste no storage disponível."""
    _mem_cache[key] = value
    serialized = json.dumps(value)
    # Modo PWA/WASM: usa client_storage nativo
    if _has_client_storage(page):
        try:
            page.client_storage.set(key, serialized)
            return
        except Exception:
            pass
    # Modo servidor web: usa localStorage via eval_js
    try:
        safe = serialized.replace("\\", "\\\\").replace("`", "\\`")
        page.eval_js(f"localStorage.setItem(\'{key}\', `{safe}`)")
    except Exception:
        pass  # modo desktop — só memória


def remove_storage(page: ft.Page, key: str):
    _mem_cache.pop(key, None)
    if _has_client_storage(page):
        try:
            page.client_storage.remove(key)
            return
        except Exception:
            pass
    try:
        page.eval_js(f"localStorage.removeItem(\'{key}\')")
    except Exception:
        pass


def boot_load_storage(page: ft.Page):
    """Lê todos os dados persistidos e popula o cache."""
    for key in (KEY_SETTINGS, KEY_HISTORY, KEY_OVERRIDES,
                KEY_HOLIDAYS, "onion_holidays_corp"):
        raw = None
        # Tentar client_storage (PWA/WASM)
        if _has_client_storage(page):
            try:
                raw = page.client_storage.get(key)
            except Exception:
                pass
        # Tentar eval_js localStorage (servidor web)
        if raw is None:
            try:
                raw = page.eval_js(f"localStorage.getItem(\'{key}\')")
            except Exception:
                pass
        if raw and raw not in ("null", "undefined", None, ""):
            try:
                _mem_cache[key] = json.loads(raw)
            except Exception:
                pass


# ─────────────────────────────────────────────
#  TOKENS
# ─────────────────────────────────────────────

# ── Tema Claro Corporativo ───────────────────────────────────────
BG_DEEP        = "#F0F4F7"   # Fundo principal — cinza claro
BG_CARD        = "#FFFFFF"   # Cards — branco puro
BG_SURFACE     = "#F8FAFC"   # Inputs e superfícies internas
ACCENT         = "#00C2A8"   # Destaque turquesa
ACCENT_LITE    = "#00A896"   # Versão escura do accent (sobre claro)
ACCENT_DARK    = "#007A6E"   # Versão mais escura
WORK_COLOR     = "#D1FAE5"   # Trabalho — verde claro
OFF_COLOR      = "#DBEAFE"   # Folga — azul claro
HOL_COLOR      = "#FEE2E2"   # Feriado nacional — vermelho claro
TEXT_PRIMARY   = "#1A2535"   # Texto principal — quase preto
TEXT_SECONDARY = "#64748B"   # Texto secundário — cinza médio
TEXT_MUTED     = "#94A3B8"   # Texto terciário — cinza claro
SUCCESS        = "#059669"   # Verde escuro sobre fundo claro
WARNING        = "#D97706"   # Âmbar escuro sobre fundo claro
DANGER         = "#DC2626"   # Vermelho escuro sobre fundo claro
YEN_GOLD       = "#92610A"   # Dourado escuro sobre fundo claro

# Cores específicas do header e nav (escuros)
HEADER_BG      = "#1A2535"
NAV_BG         = "#1A2535"
NAV_BORDER     = "#00C2A8"

# Cores do calendário
CAL_YUKYU      = "#FED7AA"   # Yukyu — laranja claro
CAL_CORP       = "#FFEDD5"   # Feriado corporativo — laranja suave
CAL_MODIF      = "#F3E8FF"   # Modificado — lilás claro
CAL_TEXT_WORK  = "#065F46"   # Texto nos dias de trabalho
CAL_TEXT_OFF   = "#1D4ED8"   # Texto nos dias de folga
CAL_TEXT_HOL   = "#991B1B"   # Texto feriado nacional
CAL_TEXT_CORP  = "#7C2D12"   # Texto feriado corporativo
CAL_TEXT_YUKYU = "#9A3412"   # Texto yukyu
CAL_TEXT_MODIF = "#7E22CE"   # Texto modificado
CAL_BORDER_WORK= "#6EE7B7"   # Borda dias de trabalho
CAL_BORDER_OFF = "#93C5FD"   # Borda dias de folga


def card(content, padding=16, margin=8):
    return ft.Container(
        content=content, bgcolor=BG_CARD, border_radius=16,
        padding=padding, margin=margin,
        border=ft.Border.all(1, "#D1DBE3"),
    )


def divider():
    return ft.Divider(height=1, color="#E2E8ED")


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

    cycle           = generate_4x2_calendar(anchor, view_year, view_month)
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
                ft.dropdown.Option("normal", "Trabalho Normal"),
                ft.dropdown.Option("absent", "Falta (欠勤)"),
                ft.dropdown.Option("yukyu",  "Férias/Folga (有休)"),
            ],
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
        )
        start_f = ft.TextField(
            label="Entrada (HH:MM)", value=ov.get("start", ""),
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
            expand=1,
        )
        end_f = ft.TextField(
            label="Saída (HH:MM)", value=ov.get("end", ""),
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
            expand=1,
        )
        break_f = ft.TextField(
            label="Intervalo (min)", value=str(ov.get("break_min", 65)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
        )
        yukyu_sw = ft.Switch(
            label="有休 em Feriado (+8h)",
            value=ov.get("yukyu_on_holiday", False),
            active_color=ACCENT,
            label_text_style=ft.TextStyle(color=TEXT_SECONDARY, size=11),
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
                    # Yukyu parcial: horas reais, sem OT/noturno
                    pay = calculate_shift_pay(jikyuu, "yukyu",
                                              start_str=s, end_str=e,
                                              break_min=brk)
                    preview_text.value = (
                        f"有休 parcial: {pay['net_minutes']}min → "
                        f"{yen(pay['base_pay'])} (sem OT/noturno)"
                    )
                else:
                    pay = calculate_shift_pay(jikyuu, "yukyu")
                    preview_text.value = (
                        f"有休 dia completo: {yen(pay['base_pay'])} "
                        f"(8h × ¥{jikyuu}/h, sem OT/noturno)"
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
                preview_text.value = (
                    f"{nm}min → {' | '.join(parts)} = {yen(pay['total_gross'])}{suffix}"
                )
            page.update()

        status_dd.on_change = lambda _: _update_preview()
        start_f.on_blur     = lambda _: _update_preview()
        end_f.on_blur       = lambda _: _update_preview()
        break_f.on_blur     = lambda _: _update_preview()
        _update_preview()

        def _save(_=None):
            entry = {
                "status":           status_dd.value,
                "start":            start_f.value.strip(),
                "end":              end_f.value.strip(),
                "break_min":        int(break_f.value or 65),
                "yukyu_on_holiday": yukyu_sw.value,
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

        panel = ft.Container(
            content=ft.Column(controls=[
                # Título
                ft.Row(controls=[
                    ft.Text(f"{view_year}/{view_month:02d}/{day_num:02d} — Ponto",
                            size=13, color=TEXT_PRIMARY,
                            weight=ft.FontWeight.W_700, expand=True),
                    ft.TextButton("✕", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color="#E2E8ED"),
                hol_text,
                status_dd,
                # Entrada e Saída na mesma linha com expand
                ft.Row([start_f, end_f], spacing=8),
                break_f,
                yukyu_sw,
                # Preview
                ft.Container(
                    content=preview_text,
                    bgcolor="#F0F9FF", border_radius=6,
                    padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                ),
                ft.Divider(height=1, color="#E2E8ED"),
                ft.Row(controls=[
                    ft.TextButton("Remover", on_click=_remove,
                                  style=ft.ButtonStyle(color=DANGER)),
                    ft.FilledButton("Salvar", on_click=_save,
                                    style=ft.ButtonStyle(bgcolor=ACCENT)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10, tight=True),
            bgcolor=BG_CARD, border_radius=14,
            padding=ft.Padding(left=16, right=16, top=14, bottom=14),
            # Largura adaptativa baseada na escala
            width=min(380, int((page.window_width or 420) * 0.92)),
            border=ft.Border.all(1, "#D1DBE3"),
        )
        bg = ft.Container(
            content=ft.Column(
                controls=[panel],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#88000022", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    # Cores do calendário novo
    C_WORK    = "#D1FAE5"   # verde claro — trabalho
    C_OFF     = "#DBEAFE"   # azul claro  — folga
    C_HOL_JP  = "#FEE2E2"   # vermelho claro — feriado nacional
    C_HOL_CO  = "#FFEDD5"   # laranja suave  — feriado corporativo
    C_MODIF   = "#F3E8FF"   # lilás claro    — yukyu/falta/modificado
    C_TODAY_B = "#00C2A8"   # borda turquesa hoje
    C_WHITE   = "#1A2535"   # "branco" = texto escuro sobre fundo claro
    C_RED     = "#EF4444"   # domingo
    C_BLUE    = "#3B82F6"   # sábado

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

        # ── Determinar fundo ─────────────────────────────────────────
        # Prioridade: modificado > feriado corporativo > feriado japonês
        #             > folga > trabalho
        is_corp_hol = day_num in month_hol_corp
        modified    = (status in ("absent", "yukyu") or has_time or yukyu_hol)

        if modified:
            bg = C_MODIF
        elif is_corp_hol:
            bg = C_HOL_CO   # laranja — feriado corporativo
        elif is_hol:
            bg = C_HOL_JP   # vermelho — feriado japonês/nacional
        elif cycle_st == "off":
            bg = C_OFF
        else:
            bg = C_WORK

        # ── Cor do número ────────────────────────────────────────────
        if is_today and not modified:
            num_color = ACCENT
        elif modified:
            # Cor específica por tipo de modificação
            if status == "absent":
                num_color = "#7E22CE"   # roxo escuro
            elif status == "yukyu":
                num_color = "#9A3412"   # laranja escuro
            else:
                num_color = "#7E22CE"
        elif is_corp_hol:
            num_color = "#7C2D12"       # marrom
        elif is_hol:
            num_color = "#991B1B"       # vermelho escuro
        elif cycle_st == "off":
            if is_sunday:
                num_color = C_RED
            elif is_saturday:
                num_color = C_BLUE
            else:
                num_color = CAL_TEXT_OFF
        elif is_sunday:
            num_color = C_RED
        elif is_saturday:
            num_color = C_BLUE
        else:
            num_color = CAL_TEXT_WORK

        # ── Indicador pequeno (canto superior direito) ───────────────
        if modified:
            if status == "absent":   indicator = "欠"
            elif status == "yukyu":  indicator = "有"
            elif yukyu_hol:          indicator = "有"
            else:                    indicator = "✎"
            ind_color = "#00C2A8"
        elif is_corp_hol:
            indicator = "●"
            ind_color = "#F59E0B"
        elif is_hol:
            indicator = "●"
            ind_color = "#EF4444"
        elif cycle_st == "work":
            indicator = ""
            ind_color = C_WHITE
        else:
            indicator = ""
            ind_color = C_WHITE

        # ── Borda ────────────────────────────────────────────────────
        if is_today:
            border = ft.Border.all(2, YEN_GOLD)
        elif modified:
            border = ft.Border.all(1, "#00C2A8")
        else:
            border = ft.Border.all(1, "#2a1a3a")

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
                            ft.Text(str(day_num), size=scaled(13),
                                    color=num_color,
                                    weight=ft.FontWeight.W_700),
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
            ft.Container(width=scaled(10), height=scaled(10),
                         bgcolor=color, border_radius=3),
            ft.Text(label, size=scaled(9), color=TEXT_SECONDARY),
        ], spacing=3)

    legend = ft.Row(
        controls=[
            _leg("#D1FAE5", "Trabalho"),
            _leg("#DBEAFE", "Folga"),
            _leg("#FEE2E2", "Feriado"),
            _leg("#FFEDD5", "Corp."),
            _leg("#F3E8FF", "Modif."),
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.CENTER,
        wrap=True,
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
    settings  = state["settings"]
    overrides = state["overrides"]
    holidays  = state["holidays"]
    history   = state["history"]
    today     = date.today()
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
    data = compute_monthly_forecast(
        year=view_year, month=view_month,
        jikyuu=int(settings.get("jikyuu") or 1500),
        anchor_date=anchor, group=settings.get("group", "B"),
        holiday_days=holidays.get(month_key, []),
        day_overrides=overrides.get(month_key, {}),
        odd_month_bonus=int(state.get("hol_odd_bonus") or settings.get("odd_bonus") or 50000),
        extra_bonus=int(state.get("extra_bonus") or 0),
        deduction_mode=settings.get("deduction_mode", "historical"),
        fixed_deduction=int(settings.get("fixed_deduction") or 0),
        history_avg_pct=hist_avg,
        block=int(settings.get("block") or 1),
    )

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

    return ft.Column(
        controls=[
            nav_row, ft.Container(height=4),
            card(ft.Column(controls=[
                section_header("支給 VENCIMENTOS"),
                pay_row("Salário Base (基本給)",          data["base_pay"]),
                pay_row("Hora Extra 残業手当",          data["overtime_pay"], color=WARNING,     small=True),
                pay_row("Adicional Noturno 深夜手当",        data["night_pay"],    color=ACCENT_LITE, small=True),
                pay_row("Trabalho em Feriado 休出手当",      data["holiday_pay"],  color=DANGER,      small=True),
                pay_row("Bônus Mês Ímpar 奇数月",     data["odd_bonus"],    color=SUCCESS,     small=True),
                pay_row("Abono Extra",            data["extra_bonus"],  color=SUCCESS,     small=True),
                divider(),
                pay_row("TOTAL BRUTO 総支給額",       data["gross"],        color=YEN_GOLD),
            ], spacing=8, tight=True)),

            card(ft.Column(controls=[
                section_header("控除 DESCONTOS"),
                ft.Row(
                    controls=[
                        ft.Text("Total de Descontos", size=13, color=TEXT_PRIMARY),
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
        ],
        spacing=0, scroll=ft.ScrollMode.AUTO,
    )


# ─────────────────────────────────────────────
#  TAB 3 — HISTORY
# ─────────────────────────────────────────────

def build_history_tab(page: ft.Page, state: dict, refresh_all):
    history = state["history"]

    def open_log_modal(_):
        # Campos do holerite japonês baseados no modelo real
        # Cada campo: label JP + PT, teclado numérico
        def _tf(lbl, kb=ft.KeyboardType.NUMBER, val=""):
            return ft.TextField(
                label=lbl, value=val, keyboard_type=kb,
                bgcolor="#F8FAFC", color="#1A2535",
                border_color=ACCENT_DARK, focused_border_color=ACCENT,
                label_style=ft.TextStyle(color=TEXT_SECONDARY, size=9),
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
                      date.today().strftime("%Y-%m"))

        # ── 勤怠 Frequência ──────────────────────────────────────────
        f_dias      = _tf("平日出勤 Dias Úteis")
        f_kyujitsu  = _tf("所休出 Trab.Folga")
        f_hokyujitsu= _tf("法休出 Trab.Feriado")
        f_kekkin    = _tf("欠勤 Faltas")
        f_yukyu     = _tf("有休 Férias Pagas")
        f_tokyu     = _tf("特休有給 Lic.Especial")
        f_chikoku   = _tf("遅早 Atrasos/Saídas")
        f_kyugyo    = _tf("休業 Afastamento")

        # ── 時間 Horas ───────────────────────────────────────────────
        f_shonai    = _tf("所定内 Hrs Normal")
        f_shogai    = _tf("所定外 Hrs Extra Pad.")
        f_hochgai   = _tf("法定外 Hrs Extra Legal")
        f_shinyam   = _tf("深夜 Hrs Noturnas")
        f_kyushutsu = _tf("所休出 Hrs Folga Trab.")
        f_hokyu_h   = _tf("法休出 Hrs Feriado Trab.")
        f_60h       = _tf("60h超時間 Hrs +60h/mês")
        f_yukyu_h   = _tf("有休時間 Hrs Férias")
        f_jitsuro   = _tf("実働時間 Hrs Efetivas")
        f_kojo_h    = _tf("控除時間 Hrs Desconto")

        # ── 支給 Vencimentos ─────────────────────────────────────────
        f_kihon     = _tf("基本給 Salário Base")
        f_shonai_k  = _tf("所定内金額 Val.Normal")
        f_shogai_k  = _tf("所定外手当 HE Padrão")
        f_zangyo    = _tf("残業手当 Hora Extra +25%")
        f_yakin     = _tf("深夜手当 Ad.Noturno +25%")
        f_kyushu    = _tf("休出手当 Trab.Feriado +35%")
        f_kanri     = _tf("管理手当 Ad.Gestão")
        f_gijutsu   = _tf("技術手当 Ad.Técnico")
        f_leader    = _tf("リーダー手当 Ad.Líder")
        f_seisan    = _tf("精算金 Acerto")
        f_hosho     = _tf("報奨金 Bônus")
        f_tsukkin   = _tf("通勤手当 V.Transporte")
        f_ta_teate  = _tf("他手当 Outros Ad.")
        f_ikkin     = _tf("一時金 Gratificação")
        f_60h_teate = _tf("60h超手当 Ad.+60h")

        # ── 控除 Descontos ───────────────────────────────────────────
        f_kenpo     = _tf("健康保険 Plano Saúde")
        f_kaigo     = _tf("介護保険 Seg.Enfermagem")
        f_nenkin    = _tf("厚生年金 Previdência")
        f_koyo      = _tf("雇用保険 Seg.Desemprego")
        f_shotoku   = _tf("所得税 Imp.de Renda")
        f_jumin     = _tf("住民税 Imp.Municipal")
        f_ta_kojo   = _tf("他控除 Outros Desc.")

        # ── Totais ───────────────────────────────────────────────────
        f_gross     = _tf("総支給額 Total Bruto")
        f_ded       = _tf("控除合計 Total Desc.")
        f_net       = _tf("差引支給額 Salário Líq.")

        ov_ref = [None]

        def _close(_=None):
            if ov_ref[0] in page.overlay:
                page.overlay.remove(ov_ref[0])
            page.update()

        def _vi(f):
            try: return int(f.value or 0)
            except: return 0

        def _save(_=None):
            g, d = _vi(f_gross), _vi(f_ded)
            entry = {
                "month":        month_f.value.strip(),
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
                "h_shonai":   _vi(f_shonai),
                "h_shogai":   _vi(f_shogai),
                "h_hochgai":  _vi(f_hochgai),
                "h_shinya":   _vi(f_shinyam),
                "h_kyushu":   _vi(f_kyushutsu),
                "h_hokyu":    _vi(f_hokyu_h),
                "h_60":       _vi(f_60h),
                "h_yukyu":    _vi(f_yukyu_h),
                "h_jitsuro":  _vi(f_jitsuro),
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
            state["history"] = [e for e in history
                                 if e.get("month") != entry["month"]]
            state["history"].append(entry)
            state["history"].sort(key=lambda x: x["month"], reverse=True)
            save_json(page, KEY_HISTORY, state["history"])
            _close()
            refresh_all()

        # ── Layout do painel ─────────────────────────────────────────
        win_w = page.window_width or 420
        win_h = page.window_height or 760

        content = ft.Column(
            controls=[
                month_f,
                _sec("勤怠 FREQUÊNCIA / DIAS"),
                _row(f_dias, f_kyujitsu, f_hokyujitsu),
                _row(f_kekkin, f_yukyu, f_tokyu),
                _row(f_chikoku, f_kyugyo),
                _sec("時間 HORAS TRABALHADAS"),
                _row(f_shonai, f_shogai, f_hochgai),
                _row(f_shinyam, f_kyushutsu, f_hokyu_h),
                _row(f_60h, f_yukyu_h, f_jitsuro),
                f_kojo_h,
                _sec("支給 VENCIMENTOS"),
                _row(f_kihon, f_shonai_k, f_shogai_k),
                _row(f_zangyo, f_yakin, f_kyushu),
                _row(f_kanri, f_gijutsu, f_leader),
                _row(f_seisan, f_hosho, f_tsukkin),
                _row(f_ta_teate, f_ikkin, f_60h_teate),
                _sec("控除 DESCONTOS"),
                _row(f_kenpo, f_kaigo, f_nenkin),
                _row(f_koyo, f_shotoku, f_jumin),
                f_ta_kojo,
                _sec("TOTAIS"),
                _row(f_gross, f_ded, f_net),
                # Espaço extra no final para a barra não cobrir o último campo
                ft.Container(height=8),
            ],
            spacing=5, tight=True,
            scroll=ft.ScrollMode.ALWAYS,
        )

        # Wrapper com padding direito para a barra de scroll não sobrepor campos
        content = ft.Container(
            content=content,
            padding=ft.Padding(left=0, right=14, top=0, bottom=0),
        )

        panel_w = min(int(win_w * 0.95), 480)
        panel_h = min(int(win_h * 0.88), 700)

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
                    ft.Divider(height=1, color="#E2E8ED"),
                    ft.Container(content=content,
                                 expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE),
                    ft.Divider(height=1, color="#E2E8ED"),
                    ft.Row(controls=[
                        ft.TextButton("Cancelar", on_click=_close,
                                      style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                        ft.FilledButton("Salvar", on_click=_save,
                                        style=ft.ButtonStyle(bgcolor=ACCENT)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ],
                spacing=8, tight=True, expand=True,
            ),
            bgcolor=BG_CARD,
            border_radius=14,
            padding=ft.Padding(left=16, right=16, top=14, bottom=14),
            width=panel_w,
            height=panel_h,
            border=ft.Border.all(1, "#D1DBE3"),
        )

        bg = ft.Container(
            content=ft.Column(
                controls=[panel],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#88000022", expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ov_ref[0] = bg
        page.overlay.append(bg)
        page.update()

    ratios    = [e.get("ratio", 0) for e in history if e.get("ratio", 0) > 0]
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
        return card(
            ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text(e.get("month",""), size=13,
                            color=ACCENT_LITE, weight=ft.FontWeight.W_700),
                    ft.Text(f"Desc: {rt:.1f}%", size=11, color=TEXT_MUTED),
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
            padding=12, margin=4,
        )
    history_cards = [_history_card(e) for e in history[:24]]

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
        border=ft.Border.all(1, "#D1DBE3"),
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
                    ft.FilledButton("Registrar Holerite Real", icon="add",
                                    on_click=open_log_modal,
                                    style=ft.ButtonStyle(bgcolor=ACCENT)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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

    def _save():
        save_json(page, KEY_SETTINGS, settings)
        refresh_all()

    def mk_field(label_str, key, kb=ft.KeyboardType.NUMBER):
        def _blur(e):
            settings[key] = e.control.value.strip()
            _save()
        return ft.TextField(
            label=label_str, value=str(settings.get(key, "")),
            keyboard_type=kb, bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
            on_blur=_blur,
        )

    group_dd = ft.Dropdown(
        label="Grupo de Turno", value=settings.get("group", "B"),
        options=[
            ft.dropdown.Option("A", "Grupo A"),
            ft.dropdown.Option("B", "Grupo B"),
            ft.dropdown.Option("C", "Grupo C"),
        ],
        bgcolor="#F8FAFC", color="#1A2535",
        border_color=ACCENT_DARK, focused_border_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
    )
    group_dd.on_change = lambda e: [settings.__setitem__("group", e.control.value), _save()]

    block_dd = ft.Dropdown(
        label="Arredondamento do Ponto",
        value=str(settings.get("block", 1)),
        options=[
            ft.dropdown.Option("1",  "Minuto a minuto"),
            ft.dropdown.Option("15", "Blocos de 15 minutos"),
            ft.dropdown.Option("30", "Blocos de 30 minutos"),
        ],
        bgcolor="#F8FAFC", color="#1A2535",
        border_color=ACCENT_DARK, focused_border_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
    )
    block_dd.on_change = lambda e: [settings.__setitem__("block", int(e.control.value)), _save()]

    ded_mode_dd = ft.Dropdown(
        label="Modo de Desconto",
        value=settings.get("deduction_mode", "historical"),
        options=[
            ft.dropdown.Option("historical", "Usar Média Histórica"),
            ft.dropdown.Option("fixed",      "Desconto Fixo Manual"),
        ],
        bgcolor="#F8FAFC", color="#1A2535",
        border_color=ACCENT_DARK, focused_border_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
    )
    ded_mode_dd.on_change = lambda e: [settings.__setitem__("deduction_mode", e.control.value), _save()]

    pin_switch = ft.Switch(
        label="Ativar Bloqueio PIN / Biométrico",
        value=settings.get("pin_enabled", False),
        active_color=ACCENT,
        label_text_style=ft.TextStyle(color=TEXT_SECONDARY),
    )
    pin_switch.on_change = lambda e: [settings.__setitem__("pin_enabled", e.control.value), _save()]

    def _import_csv(_):
        """No PWA, FilePicker não funciona — usar textarea para colar o CSV."""
        ov_ref = [None]

        csv_field = ft.TextField(
            label="Cole o conteúdo do CSV aqui",
            multiline=True, min_lines=6, max_lines=12,
            hint_text="2025-05-03,jp\n2025-08-13,corp\n2025-01-01",
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
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
                    bgcolor="#F0F9FF", border_radius=6,
                    padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                ),
                csv_field,
                ft.Row(controls=[
                    ft.TextButton("Cancelar", on_click=_close,
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY)),
                    ft.FilledButton("Importar", on_click=_processar,
                                    style=ft.ButtonStyle(bgcolor=ACCENT)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10, tight=True),
            bgcolor=BG_CARD, border_radius=14, padding=16, width=360,
            border=ft.Border.all(1, "#D1DBE3"),
        )
        bg = ft.Container(
            content=ft.Column(controls=[panel],
                              alignment=ft.MainAxisAlignment.CENTER,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#88000022", expand=True, alignment=ft.Alignment(0, 0),
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
                _mem_cache.pop(k, None)
                try: page.eval_js(f"localStorage.removeItem('{k}')")
                except: pass
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
            bgcolor="#88000022", expand=True, alignment=ft.Alignment(0, 0),
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
                group_dd,
                mk_field("Data Início Ciclo 4×2 (AAAA-MM-DD)", "anchor_date",
                         ft.KeyboardType.TEXT),
                mk_field("Bônus Padrão Mês Ímpar (¥)",        "odd_bonus"),
                block_dd,
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
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
        )
        note_f = ft.TextField(
            label="Descrição (opcional)",
            bgcolor="#F8FAFC", color="#1A2535",
            border_color=ACCENT_DARK, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
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
            bgcolor="#88000022", expand=True, alignment=ft.Alignment(0, 0),
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
                                        else ft.Border.all(1, "#D1DBE3"))
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
    TEXT_PRIMARY = "#1A2535"
    TEXT_SECONDARY = "#64748B"
    TEXT_MUTED = "#94A3B8"
    BG_CARD = "#FFFFFF"
    BG_SURFACE = "#F8FAFC"
    ACCENT_DARK = "#007A6E"
    SUCCESS = "#059669"
    WARNING = "#D97706"
    DANGER = "#DC2626"
    YEN_GOLD = "#92610A"

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
                    ft.Text(desc, size=11, color=TEXT_SECONDARY),
                ], spacing=1, tight=True, expand=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=BG_SURFACE, border_radius=8,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            margin=ft.Padding(left=0, right=0, top=2, bottom=2),
        )

    def _rule(jp, pt, calc, color=TEXT_PRIMARY):
        return ft.Container(
            content=ft.Row(controls=[
                ft.Column(controls=[
                    ft.Text(jp, size=11, color=color,
                            weight=ft.FontWeight.W_700),
                    ft.Text(pt, size=10, color=TEXT_SECONDARY),
                ], spacing=1, tight=True, expand=2),
                ft.Text(calc, size=11, color=YEN_GOLD,
                        text_align=ft.TextAlign.RIGHT, expand=1),
            ]),
            bgcolor=BG_SURFACE, border_radius=6,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            margin=ft.Padding(left=0, right=0, top=2, bottom=2),
        )

    def _color_legend(color, label, desc):
        return ft.Row(controls=[
            ft.Container(width=14, height=14, bgcolor=color,
                         border_radius=3),
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
                  "Abra ⚙️ Config. → insira seu Valor Hora (時給), Grupo (A/B/C) e a Data Início do ciclo 4×2."),
            _item("2️⃣", "Importe os feriados",
                  "Em ⚙️ Config. → Importar CSV, use os arquivos incluídos na pasta assets/. Ou acesse 🏭 Feriados para marcar feriados corporativos manualmente."),
            _item("3️⃣", "Acompanhe no Calendário",
                  "A aba 📅 gera automaticamente o ciclo 4x2. Toque em qualquer dia para registrar horários, faltas ou férias."),
            _item("4️⃣", "Consulte o Holerite",
                  "A aba 📋 mostra a previsão do mês com todos os adicionais calculados automaticamente."),
            _item("5️⃣", "Registre o holerite real",
                  "Na aba 🕐 Histórico, toque em 'Registrar Holerite Real' para salvar os valores do contracheque físico."),

            # ── Grupos de turno ──────────────────────────────────────
            _title("👥 Grupos de Turno"),
            _item("Grupo A", "Turno Diurno",
                  "Horário padrão: 08:35 → 20:35. OT após 18:35."),
            _item("Grupo B", "Turno Noturno",
                  "Horário padrão: 20:35 → 08:35 (+1 dia). OT após 06:35."),
            _item("Grupo C", "Turno Diurno",
                  "Igual ao Grupo A. Use para equipes diferentes no mesmo turno."),

            # ── Ciclo 4×2 ────────────────────────────────────────────
            _title("🔄 Ciclo 4×2 (四勤二休)"),
            _p("O sistema projeta automaticamente 4 dias de trabalho seguidos de 2 dias de folga, ciclando indefinidamente a partir da Data Início configurada."),
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
                  "Deixe em branco → usa o horário padrão do seu grupo."),
            _item("Saída Antecipada", "Preencha só a Saída (HH:MM)",
                  "OT = 0 se saiu antes do limiar. Cálculo pelo tempo real."),
            _item("有休 Férias Pagas", "Sem horário → 8h base fixo",
                  "Com horário → paga as horas efetivas (sem OT/noturno)."),
            _item("欠勤 Falta", "¥0 — não remunerada",
                  "O campo horário é ignorado para faltas."),
            _item("Trabalho em Folga/Feriado", "Preencha Entrada e Saída",
                  "Status 'Normal' + horário → +35% automático."),
            _item("有休 em Feriado Corporativo",
                  "Ative o toggle 有休 em Feriado",
                  "Injeta 8h base fixo mesmo sendo feriado da empresa."),

            # ── Cores do calendário ──────────────────────────────────
            _title("🎨 Cores do Calendário"),
            _color_legend("#1a5c1a", "Verde — Dia de Trabalho",
                          "Turno normal do ciclo 4×2"),
            _color_legend("#1a2a4a", "Azul escuro — Folga",
                          "Dias de descanso do ciclo"),
            _color_legend("#6a1010", "Vermelho — Feriado Nacional",
                          "Importado via CSV (tipo jp)"),
            _color_legend("#B45309", "Laranja — Feriado Corporativo",
                          "Marcado na aba 🏭 Feriados"),
            _color_legend("#3a1060", "Roxo — Modificado",
                          "Dia com ponto, falta ou férias registrados"),

            # ── Descontos ────────────────────────────────────────────
            _title("🔢 Previsão de Descontos"),
            _item("Modo Histórico", "Taxa média calculada automaticamente",
                  "Baseada nos holerites reais que você registrou no Histórico."),
            _item("Modo Fixo", "Valor fixo em ¥",
                  "Configure em ⚙️ Config. → Configuração de Descontos."),

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
                bgcolor="#0d0d1a", border_radius=8,
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


def main(page: ft.Page):
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
            primary="#00C2A8",
            on_primary="#FFFFFF",
            secondary="#007A6E",
            surface="#FFFFFF",
            on_surface="#1A2535",
        ),
    )

    boot_load_storage(page)

    settings  = load_json(page, KEY_SETTINGS,  DEFAULT_SETTINGS)
    history   = load_json(page, KEY_HISTORY,   [])
    overrides = load_json(page, KEY_OVERRIDES, {})
    holidays  = load_json(page, KEY_HOLIDAYS,  {})

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

    # Logo — Flet 0.85 não suporta src_base64
    # Usa src= com caminho direto para o arquivo na pasta assets/
    import os as _os
    _assets_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets")
    _logo_file  = None
    for _fname in ("logo_icon.png", "logo.png", "logo.svg"):
        _candidate = _os.path.join(_assets_dir, _fname)
        if _os.path.exists(_candidate):
            _logo_file = _fname
            break
    if _logo_file:
        logo = ft.Image(src=_logo_file,
                        width=scaled(48), height=scaled(48), fit="contain")
    else:
        logo = ft.Text("🧅", size=36)
    title_col = ft.Column(
        controls=[
            ft.Text("ONION PAYROLL", size=scaled(16), weight=ft.FontWeight.W_800,
                    color=TEXT_PRIMARY,
                    style=ft.TextStyle(letter_spacing=1.5)),
            ft.Text("DESCASQUE SEU SALÁRIO", size=scaled(9), color=ACCENT_LITE,
                    style=ft.TextStyle(letter_spacing=2.0)),
        ],
        spacing=0, tight=True,
    )
    header = ft.Container(
        content=ft.Row(controls=[ft.Row([logo, ft.Container(width=10), title_col])]),
        bgcolor=HEADER_BG,
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
        state["settings"]  = load_json(page, KEY_SETTINGS,  DEFAULT_SETTINGS)
        state["history"]   = load_json(page, KEY_HISTORY,   [])
        state["overrides"] = load_json(page, KEY_OVERRIDES, {})
        state["holidays"]  = load_json(page, KEY_HOLIDAYS,  {})

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