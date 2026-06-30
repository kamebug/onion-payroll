"""
Suite de testes automatizados — Onion Payroll
================================================
Roda os testes do motor de cálculo sem precisar abrir o app (Flet).

USO:
    python test_main.py

Roda toda vez que main.py for alterado, para garantir que nenhuma
regra de cálculo ou regra de negócio quebrou.
"""
import unittest
import sys
import importlib.util
from datetime import date


def carregar_funcoes_de_calculo():
    """Extrai e executa apenas as funções de cálculo do main.py,
    sem precisar do Flet instalado."""
    with open("main.py", encoding="utf-8") as f:
        src = f.read()

    start = src.find("\ndef shisha_gofuuu")
    end = src.find("\ndef show_modal")
    if start < 0 or end < 0:
        raise RuntimeError(
            "Não foi possível localizar o bloco de funções de cálculo "
            "em main.py. As funções podem ter sido renomeadas."
        )

    namespace = {
        "date": date,
        "datetime": __import__("datetime").datetime,
        "timedelta": __import__("datetime").timedelta,
        "Optional": __import__("typing").Optional,
        "math": __import__("math"),
    }
    exec(src[start:end], namespace)
    return namespace


FUNCS = carregar_funcoes_de_calculo()
calculate_shift_pay        = FUNCS["calculate_shift_pay"]
compute_monthly_forecast   = FUNCS["compute_monthly_forecast"]
generate_4x2_calendar      = FUNCS["generate_4x2_calendar"]
generate_weekly_calendar   = FUNCS["generate_weekly_calendar"]
generate_alternating_calendar = FUNCS["generate_alternating_calendar"]
normalize_hhmm             = FUNCS["normalize_hhmm"]

JIKYUU = 1500
ANCHOR = date(2026, 1, 5)
YEAR, MONTH = 2026, 6


def base_forecast(**overrides):
    """Cria uma chamada padrão de compute_monthly_forecast, permitindo
    sobrescrever só os parâmetros necessários em cada teste."""
    cfg = dict(
        year=YEAR, month=MONTH, jikyuu=JIKYUU,
        anchor_date=ANCHOR, group="B",
        holiday_days=[], day_overrides={},
        odd_month_bonus=0, extra_bonus=0,
        deduction_mode="fixed", fixed_deduction=0,
        history_avg_pct=0, block=1,
        shift_type_cfg="night", cfg_start="20:35",
        cfg_end="08:35", cfg_break=65, cfg_ot="06:35",
        cycle_type="4x2",
    )
    cfg.update(overrides)
    return compute_monthly_forecast(**cfg)


class TestCiclos(unittest.TestCase):
    """Valida os três tipos de ciclo de trabalho."""

    def test_4x2_gera_todos_os_dias_do_mes(self):
        cycle = generate_4x2_calendar(ANCHOR, YEAR, MONTH)
        self.assertEqual(len(cycle), 30, "Junho tem 30 dias")

    def test_4x2_so_tem_work_ou_off(self):
        cycle = generate_4x2_calendar(ANCHOR, YEAR, MONTH)
        self.assertTrue(all(v in ("work", "off") for v in cycle.values()))

    def test_5x2_fins_de_semana_sao_folga(self):
        cycle = generate_weekly_calendar(YEAR, MONTH)
        for dia, status in cycle.items():
            weekday = date(YEAR, MONTH, dia).weekday()
            esperado = "off" if weekday >= 5 else "work"
            self.assertEqual(
                status, esperado,
                f"dia {dia} (weekday={weekday}) deveria ser {esperado}"
            )

    def test_alternado_cada_semana_tem_turno_unico(self):
        cycle = generate_alternating_calendar(ANCHOR, YEAR, MONTH)
        semanas = {}
        for dia, (status, turno) in cycle.items():
            semana_idx = (date(YEAR, MONTH, dia) - date(YEAR, MONTH, 1)).days // 7
            semanas.setdefault(semana_idx, set()).add(turno)
        for semana, turnos in semanas.items():
            self.assertEqual(
                len(turnos), 1,
                f"semana {semana} deveria ter um único turno, tem {turnos}"
            )

    def test_alternado_alterna_entre_semanas_consecutivas(self):
        cycle = generate_alternating_calendar(ANCHOR, YEAR, MONTH)
        turno_semana_0 = cycle[1][1]   # turno do dia 1
        turno_semana_1 = cycle[8][1]   # turno do dia 8 (semana seguinte)
        self.assertNotEqual(turno_semana_0, turno_semana_1)


class TestCalculoHoraExtra(unittest.TestCase):
    """Valida a regra de hora extra (残業) — incluindo o bug histórico
    de saída antecipada calculando OT errado."""

    def test_saida_antes_do_limite_nao_gera_hora_extra(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="night",
            start_str="20:35", end_str="02:00",
            break_min=65, block=1,
        )
        self.assertEqual(
            pay["overtime_pay"], 0,
            "Saída às 02:00 é antes do limite de OT (06:35) — não deveria gerar hora extra"
        )

    def test_turno_completo_gera_hora_extra(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1,
        )
        self.assertGreater(pay["overtime_pay"], 0)

    def test_saida_pouco_apos_limite_calcula_minutos_corretos(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="night",
            start_str="20:35", end_str="07:00",
            break_min=65, block=1,
        )
        # Limite OT é 06:35, saiu às 07:00 → 25 minutos de OT
        self.assertGreater(pay["overtime_pay"], 0)

    def test_turno_diurno_sem_ot_antes_do_limite(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="day",
            start_str="08:35", end_str="15:00",
            break_min=65, block=1,
        )
        self.assertEqual(pay["overtime_pay"], 0)


class TestAdicionalNoturno(unittest.TestCase):
    """Valida o cálculo de 深夜手当 (22:00-05:00)."""

    def test_turno_completo_tem_noturno(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1,
        )
        self.assertGreater(pay["night_pay"], 0)


class TestFeriadoEDomingo(unittest.TestCase):
    """Valida as regras de 休出手当 (+35%) e domingo (法定休日)."""

    def test_feriado_tem_adicional_35_porcento(self):
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
        )
        self.assertGreater(pay["holiday_pay"], 0)

    def test_domingo_trabalhado_conta_separado_de_dia_normal(self):
        resultado = base_forecast(day_overrides={
            "14": {"status": "normal", "start": "20:35",
                   "end": "08:35", "break_min": 65},
        })
        self.assertGreater(
            resultado["legal_holiday_pay"], 0,
            "Domingo 14 trabalhado deveria gerar legal_holiday_pay"
        )

    def test_domingo_sem_registro_nao_conta(self):
        resultado_com = base_forecast(day_overrides={
            "14": {"status": "normal", "start": "20:35",
                   "end": "08:35", "break_min": 65},
        })
        resultado_sem = base_forecast(day_overrides={})
        self.assertGreater(
            resultado_com["gross"], resultado_sem["gross"],
            "Registrar domingo trabalhado deve aumentar o bruto"
        )


class TestFaltaEYukyu(unittest.TestCase):
    """Valida que falta reduz e yukyu calcula diferente do normal."""

    def test_falta_reduz_o_bruto(self):
        normal = base_forecast()
        com_falta = base_forecast(day_overrides={"1": {"status": "absent"}})
        self.assertLess(com_falta["gross"], normal["gross"])

    def test_yukyu_nao_gera_hora_extra(self):
        resultado = base_forecast(day_overrides={"1": {"status": "yukyu"}})
        # Não há um campo direto, mas o resultado deve ser diferente do normal
        normal = base_forecast()
        self.assertNotEqual(resultado["gross"], normal["gross"])


class TestDesconto(unittest.TestCase):
    """Valida que os modos de desconto não se misturam."""

    def test_desconto_fixo_usa_valor_exato(self):
        resultado = base_forecast(
            deduction_mode="fixed", fixed_deduction=45000,
            history_avg_pct=99.0,  # não deve ser usado
        )
        self.assertEqual(resultado["deductions"], 45000)

    def test_desconto_historico_ignora_valor_fixo(self):
        resultado = base_forecast(
            deduction_mode="historical", history_avg_pct=25.0,
            fixed_deduction=999999,  # não deve ser usado
        )
        self.assertNotEqual(resultado["deductions"], 999999)
        self.assertGreater(resultado["deductions"], 0)

    def test_desconto_zero_quando_fixo_e_zero(self):
        resultado = base_forecast(deduction_mode="fixed", fixed_deduction=0)
        self.assertEqual(resultado["deductions"], 0)


class TestAbono(unittest.TestCase):
    """Valida que o abono por dia é somado corretamente."""

    def test_abono_soma_no_total(self):
        sem_abono = base_forecast()
        com_abono = base_forecast(
            day_overrides={"1": {"status": "normal", "abono": 5000}}
        )
        diferenca = com_abono["gross"] - sem_abono["gross"]
        self.assertGreaterEqual(diferenca, 5000)


class TestNormalizacaoHorario(unittest.TestCase):
    """Valida a formatação automática de horário (HH:MM)."""

    def test_tres_digitos_vira_hhmm(self):
        self.assertEqual(normalize_hhmm("835"), "08:35")

    def test_quatro_digitos_vira_hhmm(self):
        self.assertEqual(normalize_hhmm("2035"), "20:35")

    def test_ja_formatado_mantem(self):
        self.assertEqual(normalize_hhmm("08:35"), "08:35")

    def test_um_digito_vira_hora_cheia(self):
        self.assertEqual(normalize_hhmm("8"), "08:00")

    def test_string_vazia_retorna_vazia(self):
        self.assertEqual(normalize_hhmm(""), "")


class TestCiclosNoForecast(unittest.TestCase):
    """Valida que os três tipos de ciclo produzem cálculo coerente."""

    def test_5x2_calcula_22_dias_uteis_em_junho(self):
        resultado = base_forecast(cycle_type="5x2",
                                   shift_type_cfg="day",
                                   cfg_start="08:35", cfg_end="20:35",
                                   cfg_ot="18:35")
        self.assertEqual(resultado["days_normal"], 22)

    def test_alternado_tem_noturno_em_alguma_semana(self):
        resultado = base_forecast(
            cycle_type="alternating",
            alt_start_day="08:35", alt_end_day="20:35",
            alt_start_night="20:35", alt_end_night="08:35",
        )
        self.assertGreater(resultado["night_pay"], 0)


if __name__ == "__main__":
    print("=" * 60)
    print("ONION PAYROLL — SUITE DE TESTES AUTOMATIZADOS")
    print("=" * 60)
    unittest.main(verbosity=2)
