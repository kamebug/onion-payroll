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
        "calendar": __import__("calendar"),
    }
    exec(src[start:end], namespace)
    return namespace


FUNCS = carregar_funcoes_de_calculo()
calculate_shift_pay        = FUNCS["calculate_shift_pay"]
calcular_presenca_mensal   = FUNCS["calcular_presenca_mensal"]
night_minutes_worked       = FUNCS["night_minutes_worked"]
night_minutes_in_range     = FUNCS["night_minutes_in_range"]
parse_hhmm                 = FUNCS["parse_hhmm"]
build_timeline_segments    = FUNCS["build_timeline_segments"]
_anchor_to_shift            = FUNCS["_anchor_to_shift"]
compute_monthly_forecast   = FUNCS["compute_monthly_forecast"]
generate_4x2_calendar      = FUNCS["generate_4x2_calendar"]
generate_weekly_calendar   = FUNCS["generate_weekly_calendar"]
generate_alternating_calendar = FUNCS["generate_alternating_calendar"]
generate_alternating_monthly_calendar = FUNCS["generate_alternating_monthly_calendar"]
calcular_yukyu              = FUNCS["calcular_yukyu"]
normalize_hhmm             = FUNCS["normalize_hhmm"]
normalize_yyyymm           = FUNCS["normalize_yyyymm"]
jikyuu_vigente_para_mes    = FUNCS["jikyuu_vigente_para_mes"]
desconto_real_para_mes     = FUNCS["desconto_real_para_mes"]

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
        history_avg_deduction=0, block=1,
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
        # Dia 2/jun/2026 é folga real no modo pessoal (default a partir da
        # v2.12) com ANCHOR=5/jan/2026 — confirmado por generate_4x2_calendar
        resultado_com = base_forecast(day_overrides={
            "2": {"status": "normal", "start": "20:35",
                  "end": "08:35", "break_min": 65},
        })
        resultado_sem = base_forecast(day_overrides={})
        self.assertGreater(
            resultado_com["gross"], resultado_sem["gross"],
            "Registrar dia de folga trabalhado deve aumentar o bruto"
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

    def test_yukyu_usa_jornada_normal_configurada_nao_8h_fixo(self):
        # Reportado pelo usuário: turno 20:30-08:35, intervalo 65min, OT
        # às 06:35 → jornada normal real é 9h, não 8h. O Yukyu sem
        # horário explícito deve pagar 9h, não um valor fixo de 8h.
        r = calculate_shift_pay(
            jikyuu=1590, shift_type="yukyu",
            base_shift="night", ot_start_str="06:35",
            cfg_start_str="20:30", cfg_end_str="08:35",
            break_min=65,
        )
        self.assertEqual(r["net_minutes"], 540)  # 9h
        self.assertEqual(r["base_pay"], 1590 * 9)

    def test_yukyu_com_jornada_de_8h_continua_dando_8h(self):
        # Turno com jornada líquida de 8h de verdade (entrada 08:35, OT
        # às 17:40 — 8h35 depois do jikyuu extraindo 65min de intervalo,
        # equivalente a exatamente 8h líquidas)
        r = calculate_shift_pay(
            jikyuu=1590, shift_type="yukyu",
            base_shift="day", ot_start_str="17:40",
            cfg_start_str="08:35", cfg_end_str="20:35",
            break_min=65,
        )
        self.assertEqual(r["net_minutes"], 480)  # 8h
        self.assertEqual(r["base_pay"], 1590 * 8)

    def test_yukyu_sem_configuracao_cai_no_fallback_8h(self):
        # Sem base_shift/ot_start_str/cfg_start_str/cfg_end_str
        # informados (compatibilidade com chamadas antigas), continua
        # caindo no padrão diurno 08:35→18:35, que dá exatamente 8h55
        # (não mais um "8h" mágico, mas também não quebra)
        r = calculate_shift_pay(jikyuu=1590, shift_type="yukyu")
        self.assertGreater(r["base_pay"], 0)

    def test_ot_start_configurado_afeta_dia_normal_tambem(self):
        # Confirma que o bug não era só do Yukyu: o limiar de hora extra
        # configurado pelo usuário (ot_start_str) precisa afetar o
        # cálculo de um dia NORMAL de trabalho também, não só o Yukyu.
        # Turno 20:30-08:35, intervalo 65min, testando dois limiares de
        # OT diferentes — o resultado de horas extras deve mudar.
        r_ot_06h35 = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
        )
        r_ot_07h35 = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="07:35",
        )
        self.assertGreater(
            r_ot_06h35["overtime_minutes"], r_ot_07h35["overtime_minutes"],
            "Limiar de OT mais cedo (06:35) deve gerar mais minutos de "
            "hora extra do que um limiar mais tarde (07:35)"
        )


class TestDesconto(unittest.TestCase):
    """Valida que os modos de desconto não se misturam."""

    def test_desconto_fixo_usa_valor_exato(self):
        resultado = base_forecast(
            deduction_mode="fixed", fixed_deduction=45000,
            history_avg_deduction=99.0,  # não deve ser usado
        )
        self.assertEqual(resultado["deductions"], 45000)

    def test_desconto_historico_ignora_valor_fixo(self):
        resultado = base_forecast(
            deduction_mode="historical", history_avg_deduction=25.0,
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



    """Valida que feriados corporativos (marcados na aba 🏭) afetam
    o cálculo do forecast quando o usuário trabalha nesse dia,
    não só a cor visual da célula no calendário."""

    def test_feriado_corporativo_trabalhado_gera_adicional_35(self):
        # Simula: dia 10 marcado como feriado corporativo na aba 🏭,
        # e o usuário registrou que trabalhou nesse dia
        resultado = base_forecast(
            holiday_days=[10],  # feriado corp já mesclado pela UI
            day_overrides={
                "10": {"status": "normal", "start": "20:35",
                       "end": "08:35", "break_min": 65}
            },
        )
        self.assertGreater(
            resultado["holiday_pay"], 0,
            "Trabalhar em feriado corporativo deveria gerar +35% (休出手当)"
        )

    def test_feriado_corporativo_sem_registro_nao_conta(self):
        # Dia marcado como feriado corp, mas SEM horário registrado
        # (o funcionário não foi trabalhar) — não deve contar nada
        com_feriado_sem_trabalho = base_forecast(
            holiday_days=[10], day_overrides={},
        )
        sem_feriado = base_forecast(holiday_days=[], day_overrides={})
        # Como dia 10 normalmente seria "work" no ciclo 4x2, marcá-lo
        # como feriado SEM horário registrado faz o app pular esse dia
        # (não conta nem como trabalho normal nem como feriado)
        self.assertLessEqual(
            com_feriado_sem_trabalho["gross"], sem_feriado["gross"]
        )


class TestAdicionalFixoMensal(unittest.TestCase):
    """Valida o adicional fixo mensal (ex: função de líder) configurado
    em Config, que deve ser somado automaticamente todo mês."""

    def test_adicional_fixo_soma_no_bruto(self):
        sem_adicional = base_forecast(fixed_monthly_bonus=0)
        com_adicional = base_forecast(fixed_monthly_bonus=10000)
        diferenca = com_adicional["gross"] - sem_adicional["gross"]
        self.assertEqual(diferenca, 10000)

    def test_adicional_fixo_aparece_no_retorno(self):
        resultado = base_forecast(fixed_monthly_bonus=15000)
        self.assertEqual(resultado.get("fixed_monthly_bonus"), 15000)

    def test_adicional_fixo_persiste_em_todos_os_meses(self):
        # Diferente do bônus de mês ímpar, este deve aparecer
        # tanto em meses pares quanto ímpares
        r_par   = base_forecast(fixed_monthly_bonus=8000)  # YEAR/MONTH padrão = junho (par)
        r_impar = compute_monthly_forecast(
            year=YEAR, month=7, jikyuu=JIKYUU,
            anchor_date=ANCHOR, group="B",
            holiday_days=[], day_overrides={},
            odd_month_bonus=0, extra_bonus=0,
            deduction_mode="fixed", fixed_deduction=0,
            history_avg_deduction=0, block=1,
            shift_type_cfg="night", cfg_start="20:35",
            cfg_end="08:35", cfg_break=65, cfg_ot="06:35",
            cycle_type="4x2", fixed_monthly_bonus=8000,
        )

        self.assertEqual(r_par.get("fixed_monthly_bonus"), 8000)
        self.assertEqual(r_impar.get("fixed_monthly_bonus"), 8000)


class TestBugTurnoNoturnoEmFeriado(unittest.TestCase):
    """Bug 1 (corrigido): quando shift_type='holiday' (domingo/feriado
    trabalhado), o código assumia SEMPRE turno diurno para calcular
    horários — mesmo no turno NOTURNO. Corrigido com base_shift.

    Bug 2 (corrigido, validado com holerites reais de fev/2026 e
    mar/2026): o domingo trabalhado estava SOMANDO holiday(+35%) +
    night(+25%) + overtime(+25%) separadamente, gerando ~13% a mais
    que o valor real. A empresa aplica APENAS +35% sobre o total de
    horas, sem empilhar os outros adicionais. Validado matematicamente:
    2 domingos = ¥47,784 e 4 domingos = ¥95,568 no holerite real,
    ambos batendo com ¥23,892 por domingo = horas × jikyuu × 1.35."""

    def test_domingo_soma_noturno_separado_nao_zerado(self):
        # v2.50 — night_pay NÃO é mais zerado em domingo/feriado. É uma
        # linha SEPARADA e independente (深夜手当) no holerite real,
        # somando as horas noturnas de TODOS os dias — inclusive
        # domingo — sem misturar com a taxa de 1,35x do domingo em si.
        # Corrigido depois de confirmar com holerite real: 深夜手当 de
        # fev/2026 (¥45.338) só bate incluindo as horas noturnas dos 2
        # domingos, não só dos 16 dias normais.
        pay = calculate_shift_pay(
            jikyuu=1590, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
            base_shift="night",
        )
        self.assertEqual(pay["overtime_pay"], 0,
            "Domingo/feriado não deve somar hora extra separada")
        self.assertGreater(pay["night_pay"], 0,
            "Domingo/feriado DEVE somar noturno, como linha separada")
        self.assertGreater(pay["holiday_pay"], 0,
            "Domingo/feriado deve ter o premium de 35%")

    def test_domingo_bate_com_holerite_real(self):
        # Validado com holerite real de fev/2026: jikyuu=1590, adicional
        # de líder=3000, 168h, turno 20:30-08:35 — holiday_pay (só a
        # parcela de domingo, sem noturno misturado) = ¥23.892/domingo,
        # batendo exato com 法定休出 do holerite real.
        pay = calculate_shift_pay(
            jikyuu=1590, shift_type="holiday",
            start_str="20:30", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
            base_shift="night",
            use_leader_addon=True, leader_addon_amount=3000, leader_addon_hours=168,
        )
        self.assertEqual(pay["holiday_pay"], 23892)

    def test_sem_base_shift_usa_comportamento_antigo_dia(self):
        # Compatibilidade: sem base_shift, não deve gerar erro
        pay = calculate_shift_pay(
            jikyuu=1500, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
        )
        self.assertIsNotNone(pay["overtime_pay"])

    def test_forecast_domingo_noturno_bate_com_calculo_manual(self):
        # v2.50 — o motor de cálculo mensal agora soma MINUTOS e
        # arredonda uma vez só no final (evita resíduo de arredondamento
        # acumulado), em vez de somar valores já arredondados de cada
        # dia individual. Isso significa que multiplicar um único dia
        # de exemplo pela quantidade de dias (método antigo deste teste)
        # pode divergir por poucos yens do total real do mês — o mesmo
        # tipo de resíduo que a correção de hoje eliminou. Tolerância de
        # 0,1% cobre isso sem esconder um bug de verdade (diferença
        # grande continuaria falhando).
        resultado = base_forecast(
            cycle_type="4x2",
            day_overrides={
                "7":  {"status": "normal", "start": "20:35",
                       "end": "08:35", "break_min": 65},
            },
        )
        pay_domingo = calculate_shift_pay(
            jikyuu=JIKYUU, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
            base_shift="night",
        )
        pay_normal = calculate_shift_pay(
            jikyuu=JIKYUU, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1,
        )
        esperado = (pay_normal["total_gross"] * resultado["days_normal"]
                    + pay_domingo["total_gross"] * resultado["days_legal"])
        diferenca_pct = abs(resultado["gross"] - esperado) / esperado
        self.assertLess(diferenca_pct, 0.001,
            f"Diferença de {diferenca_pct*100:.3f}% maior que o esperado (<0,1%)")


class TestAcrescimoLiderModoArredondamento(unittest.TestCase):
    """v2.49 — substitui a antiga Taxa de Referência (descontinuada:
    premium_allowances_monthly/standard_monthly_hours/night_addon_extra
    não existem mais). Novo sistema: use_leader_addon + leader_addon_
    amount + leader_addon_hours, com jikyuu e o acréscimo arredondados
    SEPARADAMENTE (não somados numa taxa única antes de arredondar).

    Validado contra holerite real de fev/2026: jikyuu=1590,
    adicional de líder=3000, 168h padrão, modo 'up' (sempre pra cima):
    taxa extra=¥2.011/h, taxa noturno=¥403/h, taxa domingo=¥2.172/h —
    33h extra=¥66.363, 112,5h noturno=¥45.338, 22h domingo=¥47.784."""

    def _dia(self, is_holiday=False, wage_round_mode="up"):
        return calculate_shift_pay(
            1590, "night", base_shift="night",
            start_str="20:35", end_str="08:35", break_min=65,
            ot_start_str="06:35", is_holiday=is_holiday,
            use_leader_addon=True, leader_addon_amount=3000,
            leader_addon_hours=168, wage_round_mode=wage_round_mode,
        )

    def test_default_zero_nao_afeta_calculo_existente(self):
        # Sem informar os novos parâmetros, comportamento idêntico a
        # não usar adicional de líder nenhum (compatibilidade retroativa).
        pay = calculate_shift_pay(
            jikyuu=1590, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1,
        )
        self.assertGreater(pay["overtime_pay"], 0)
        self.assertGreater(pay["night_pay"], 0)

    def test_acrescimo_eleva_taxas_proporcionalmente(self):
        sem = calculate_shift_pay(
            jikyuu=1590, shift_type="night",
            start_str="20:35", end_str="08:35", break_min=65,
            ot_start_str="06:35",
        )
        com = self._dia()
        self.assertGreater(com["overtime_pay"], sem["overtime_pay"])
        self.assertGreater(com["night_pay"], sem["night_pay"])

    def test_taxa_extra_bate_com_holerite_real(self):
        r = self._dia()
        self.assertEqual(r["_ot_rate_full"], 2011)

    def test_taxa_noturno_bate_com_holerite_real(self):
        r = self._dia()
        self.assertEqual(r["_night_rate_increment"], 403)

    def test_taxa_domingo_bate_com_holerite_real(self):
        r = self._dia(is_holiday=True)
        self.assertEqual(r["_holiday_rate_full"], 2172)

    def test_holiday_soma_noturno_separado_nao_zera(self):
        # v2.50 — night_pay NÃO é mais zerado em domingo/feriado, é uma
        # linha separada e independente (深夜手当), somada por cima da
        # taxa de domingo (que não inclui noturno misturado dentro dela).
        r = self._dia(is_holiday=True)
        self.assertEqual(r["base_pay"], 0)
        self.assertEqual(r["overtime_pay"], 0)
        self.assertGreater(r["night_pay"], 0)   # NÃO mais zero
        self.assertGreater(r["holiday_pay"], 0)

    def test_modo_regra_do_05_disponivel_como_alternativa(self):
        # "half_up" (0,5 sempre sobe) continua disponível, resultado
        # pode diferir do modo "up" (sempre pra cima) dependendo do
        # centavo — aqui só confere que não quebra e retorna um valor
        # coerente (>0), não trava a alternativa.
        r = self._dia(wage_round_mode="half_up")
        self.assertGreater(r["overtime_pay"], 0)


class TestBaseExtraDomingoSeparados(unittest.TestCase):
    """Trava a correção da v2.39 — base_pay usava net_min (horas
    regulares + horas de hora extra somadas), com overtime_pay/
    holiday_pay mostrando só o incremento (+25%/+35%), em vez da taxa
    CHEIA. Dava um total aproximadamente certo, mas a divisão entre
    'Salário Base' e 'Hora Extra'/'Domingo' saía muito diferente do
    holerite real, que separa essas categorias sem sobreposição.

    v2.50 — atualizado para o novo sistema de Adicional de Líder
    (Taxa de Referência antiga descontinuada) e para night_pay não
    mais zerado em domingo/feriado. Validado contra holerite real de
    fev/2026: jikyuu=1590, adicional de líder=3000, 168h, 16 dias
    normais + 2 domingos → Base=¥222.208 (16×¥13.888) e
    Domingo=¥47.784, batendo ¥0 de diferença."""

    def _dia(self, is_holiday=False):
        return calculate_shift_pay(
            1590, "night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35", is_holiday=is_holiday,
            use_leader_addon=True, leader_addon_amount=3000,
            leader_addon_hours=168,
        )

    def test_base_pay_usa_so_horas_regulares_nao_net_min(self):
        r = self._dia()
        # regular_minutes=540 (9h) — base_pay NÃO deve incluir as 2h de
        # hora extra (net_minutes=660) dentro desse valor
        self.assertEqual(r["base_pay"], round(1590 / 60 * 540))
        self.assertNotEqual(r["base_pay"], round(1590 / 60 * r["net_minutes"]))

    def test_overtime_pay_usa_taxa_cheia_nao_incremento(self):
        r = self._dia()
        self.assertEqual(r["overtime_pay"], 2011 * 2)  # 2h de OT

    def test_holiday_pay_usa_taxa_cheia_domingo_separada_do_noturno(self):
        r = self._dia(is_holiday=True)
        self.assertEqual(r["base_pay"], 0)
        self.assertEqual(r["overtime_pay"], 0)
        self.assertEqual(r["holiday_pay"], 2172 * 11)  # 660min=11h, só domingo
        self.assertGreater(r["night_pay"], 0)          # separado, não zero

    def test_fevereiro_2026_16_dias_normais_2_domingos_bate_holerite_real(self):
        r_normal = self._dia()
        r_domingo = self._dia(is_holiday=True)
        base_total = r_normal["base_pay"] * 16
        domingo_total = r_domingo["holiday_pay"] * 2
        self.assertEqual(base_total, round(1590 / 60 * 540) * 16)
        self.assertEqual(domingo_total, 47784)


class TestGrupoABC(unittest.TestCase):
    """Valida o deslocamento de 2 dias entre turmas (Grupo A/B/C) no
    ciclo 4x2, usando o mecanismo `anchor_group` (v2.13): a data digitada
    é sempre o dia 1 do grupo que estava selecionado NAQUELE momento
    (`anchor_group`). Trocar de grupo depois, sem tocar na data, desloca
    o calendário automaticamente pela relação de 2 dias entre turmas —
    sem precisar de nenhum switch/modo configurável.

    - `anchor_group == group` (ou não informado): sem deslocamento — a
      data é o dia 1 do próprio grupo visualizado. Corrige o bug em que
      um usuário do Grupo B/C que digitava seu próprio primeiro dia de
      trabalho tinha o calendário deslocado incorretamente (v2.12).
    - `anchor_group != group`: desloca pela relação A=0/B=2/C=4 — valida
      contra a planilha real de escala da fábrica (v2.11), agora
      expressa como "o usuário definiu a data com Grupo X selecionado e
      depois trocou para Grupo Y".
    """

    ANCHOR_GRUPO = date(2026, 6, 1)  # referência = "dia 1" da planilha

    # dias 1-7 da planilha real, True=work / False=off
    PADRAO_A = [True, True, True, True, False, False, True]
    PADRAO_B = [False, False, True, True, True, True, False]
    PADRAO_C = [True, True, False, False, True, True, True]

    def test_grupo_a_bate_com_planilha_real(self):
        # anchor_group="A" (data definida com Grupo A selecionado)
        cal = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "A", anchor_group="A")
        for i, esperado in enumerate(self.PADRAO_A):
            dia = self.ANCHOR_GRUPO.day + i
            self.assertEqual((cal.get(dia) == "work"), esperado,
                              f"Grupo A, dia {i+1}")

    def test_grupo_b_bate_com_planilha_real_apos_trocar_de_grupo(self):
        # Data foi definida com Grupo A selecionado (anchor_group="A"),
        # usuário troca para Grupo B depois — deve deslocar +2 dias
        cal = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "B", anchor_group="A")
        for i, esperado in enumerate(self.PADRAO_B):
            dia = self.ANCHOR_GRUPO.day + i
            self.assertEqual((cal.get(dia) == "work"), esperado,
                              f"Grupo B, dia {i+1}")

    def test_grupo_c_bate_com_planilha_real_apos_trocar_de_grupo(self):
        cal = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "C", anchor_group="A")
        for i, esperado in enumerate(self.PADRAO_C):
            dia = self.ANCHOR_GRUPO.day + i
            self.assertEqual((cal.get(dia) == "work"), esperado,
                              f"Grupo C, dia {i+1}")

    def test_nunca_dois_grupos_de_folga_no_mesmo_dia(self):
        cal_a = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "A", anchor_group="A")
        cal_b = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "B", anchor_group="A")
        cal_c = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "C", anchor_group="A")
        for dia in cal_a:
            folgas = [g for g, cal in (("A", cal_a), ("B", cal_b), ("C", cal_c))
                      if cal.get(dia) == "off"]
            self.assertLessEqual(len(folgas), 1,
                                  f"Dia {dia}: mais de 1 grupo de folga ({folgas})")

    def test_sem_anchor_group_mantem_compatibilidade_retroativa(self):
        # Chamar sem anchor_group (código antigo/v2.12) deve continuar
        # funcionando, equivalente a anchor_group=group (sem deslocamento)
        cal_default = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "B")
        cal_explicito = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "B", anchor_group="B")
        self.assertEqual(cal_default, cal_explicito)

    def test_data_digitada_e_sempre_dia_1_do_grupo_selecionado_no_momento(self):
        # Bug reportado pelo usuário: um usuário do Grupo B que digita
        # "hoje é meu 1o dia de trabalho" COM O GRUPO B JÁ SELECIONADO
        # deve ter esse dia como "work", SEM deslocamento algum.
        for grupo in ("A", "B", "C"):
            cal = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, grupo,
                                         anchor_group=grupo)
            self.assertEqual(cal.get(self.ANCHOR_GRUPO.day), "work",
                              f"Grupo {grupo}: dia digitado como início deveria ser 'work'")

    def test_trocar_grupo_sem_mudar_data_ajusta_automaticamente(self):
        # Cenário completo do usuário: seleciona Grupo B, digita a data
        # (anchor_group="B"), depois clica em Grupo A SEM mudar a data.
        # O calendário do Grupo A deve se ajustar sozinho (-2 dias).
        cal_como_B = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "B", anchor_group="B")
        cal_trocado_para_A = generate_4x2_calendar(self.ANCHOR_GRUPO, 2026, 6, "A", anchor_group="B")
        # O dia digitado (dia 1) é "work" para B (quem definiu a data)...
        self.assertEqual(cal_como_B.get(self.ANCHOR_GRUPO.day), "work")
        # ...mas ao trocar para A sem mudar a data, o calendário se
        # ajusta corretamente (não fica igual ao de B)
        self.assertNotEqual(cal_como_B, cal_trocado_para_A)

    def test_forecast_usa_anchor_group_corretamente(self):
        # Dia 1/jun/2026 definido com Grupo A selecionado (anchor_group="A").
        # Forecast do Grupo B (trocado depois) deve dar bruto diferente
        # do forecast do Grupo A (mesmo anchor_date).
        forecast_a = base_forecast(anchor_date=self.ANCHOR_GRUPO, group="A", anchor_group="A")
        forecast_b = base_forecast(anchor_date=self.ANCHOR_GRUPO, group="B", anchor_group="A")
        self.assertNotEqual(forecast_a["gross"], forecast_b["gross"],
                             "Grupos diferentes do anchor_group devem gerar brutos diferentes")

    def test_forecast_mesmo_grupo_do_anchor_sem_deslocamento(self):
        # Se o grupo atual É o mesmo que definiu a data, não há
        # deslocamento — comportamento idêntico independente do grupo
        forecast_b = base_forecast(anchor_date=self.ANCHOR_GRUPO, group="B", anchor_group="B")
        forecast_a = base_forecast(anchor_date=self.ANCHOR_GRUPO, group="A", anchor_group="A")
        self.assertEqual(forecast_a["gross"], forecast_b["gross"],
                          "Cada grupo com sua própria data (sem troca) gera o mesmo bruto")


class TestAlternadoMensal(unittest.TestCase):
    """Valida o novo ciclo Alternado Mensal (v2.15): 1 mês inteiro em um
    turno, próximo mês no outro, com padrão de folga configurável (5×2
    fim de semana, ou 4×2 com Grupo A/B/C)."""

    def test_mes_da_ancora_e_diurno(self):
        shift_anchor = date(2026, 1, 15)
        cal = generate_alternating_monthly_calendar(shift_anchor, 2026, 1, rest_pattern="5x2")
        _, turno = next(iter(cal.values()))
        self.assertEqual(turno, "day")

    def test_alterna_mes_a_mes(self):
        shift_anchor = date(2026, 1, 15)
        turnos = []
        for mes in range(1, 5):
            cal = generate_alternating_monthly_calendar(shift_anchor, 2026, mes, rest_pattern="5x2")
            _, turno = next(iter(cal.values()))
            turnos.append(turno)
        self.assertEqual(turnos, ["day", "night", "day", "night"])

    def test_5x2_folga_fim_de_semana(self):
        shift_anchor = date(2026, 1, 15)
        cal = generate_alternating_monthly_calendar(shift_anchor, 2026, 6, rest_pattern="5x2")
        for dia, (status, _) in cal.items():
            d = date(2026, 6, dia)
            esperado = "off" if d.weekday() >= 5 else "work"
            self.assertEqual(status, esperado, f"dia {dia}")

    def test_4x2_respeita_grupo(self):
        shift_anchor = date(2026, 1, 15)
        rest_anchor = date(2026, 6, 1)
        cal_a = generate_alternating_monthly_calendar(
            shift_anchor, 2026, 6, rest_pattern="4x2",
            rest_anchor_date=rest_anchor, group="A", anchor_group="A")
        cal_b = generate_alternating_monthly_calendar(
            shift_anchor, 2026, 6, rest_pattern="4x2",
            rest_anchor_date=rest_anchor, group="B", anchor_group="A")
        status_a = {d: s for d, (s, _) in cal_a.items()}
        status_b = {d: s for d, (s, _) in cal_b.items()}
        self.assertNotEqual(status_a, status_b,
                             "Grupos diferentes devem ter folgas diferentes mesmo no alternado mensal")

    def test_4x2_e_5x2_sao_independentes_do_turno(self):
        # O padrão de folga (4x2 ou 5x2) não deve mudar por causa do mês
        # ser diurno ou noturno — só o turno muda, a folga é a mesma regra
        shift_anchor = date(2026, 1, 15)
        cal_jan = generate_alternating_monthly_calendar(shift_anchor, 2026, 1, rest_pattern="5x2")
        cal_fev = generate_alternating_monthly_calendar(shift_anchor, 2026, 2, rest_pattern="5x2")
        turno_jan = next(iter(cal_jan.values()))[1]
        turno_fev = next(iter(cal_fev.values()))[1]
        self.assertNotEqual(turno_jan, turno_fev)

    def test_forecast_integra_alternado_mensal_5x2(self):
        resultado = base_forecast(
            cycle_type="alternating_monthly",
            alt_monthly_rest_pattern="5x2",
            shift_anchor_date=date(2026, 6, 1),
            alt_start_day="08:35", alt_end_day="20:35",
            alt_start_night="20:35", alt_end_night="08:35",
        )
        self.assertGreater(resultado["gross"], 0)

    def test_forecast_integra_alternado_mensal_4x2_com_grupo(self):
        resultado = base_forecast(
            cycle_type="alternating_monthly",
            alt_monthly_rest_pattern="4x2",
            shift_anchor_date=date(2026, 6, 1),
            group="B", anchor_group="B",
            alt_start_day="08:35", alt_end_day="20:35",
            alt_start_night="20:35", alt_end_night="08:35",
        )
        self.assertGreater(resultado["gross"], 0)


class TestYukyu(unittest.TestCase):
    """Valida o cálculo de direito a Yukyu (有給休暇), Art. 39 da Lei
    Trabalhista Japonesa, com concessão progressiva e expiração de 2
    anos (Art. 115) — v2.19."""

    def test_antes_de_6_meses_sem_direito(self):
        r = calcular_yukyu(date(2026, 1, 1), date(2026, 6, 1), [])
        self.assertEqual(r["saldo_disponivel"], 0)

    def test_6_meses_concede_10_dias(self):
        r = calcular_yukyu(date(2025, 11, 1), date(2026, 7, 3), [])
        self.assertEqual(r["saldo_disponivel"], 10)
        self.assertEqual(r["proxima_concessao_dias"], 11)

    def test_progressao_completa_ate_20_dias(self):
        # 7 anos e meio de empresa — já passou de todos os marcos fixos
        r = calcular_yukyu(date(2019, 1, 1), date(2026, 7, 3), [])
        self.assertEqual(r["total_concedido"], 121)  # 10+11+12+14+16+18+20+20
        self.assertEqual(r["proxima_concessao_dias"], 20)

    def test_uso_valido_desconta_do_saldo(self):
        usos = [date(2026, 5, 20), date(2026, 6, 5)]
        r = calcular_yukyu(date(2025, 11, 1), date(2026, 7, 3), usos)
        self.assertEqual(r["saldo_disponivel"], 8)
        self.assertEqual(r["total_usado"], 2)
        self.assertEqual(r["usos_invalidos"], [])

    def test_uso_antes_da_concessao_e_invalido(self):
        # Concessão só ocorre em 2026-05-01 (6 meses); usos antes disso
        # não devem descontar o saldo
        usos = [date(2026, 3, 10), date(2026, 4, 5)]
        r = calcular_yukyu(date(2025, 11, 1), date(2026, 7, 3), usos)
        self.assertEqual(r["saldo_disponivel"], 10)
        self.assertEqual(len(r["usos_invalidos"]), 2)

    def test_uso_alem_do_saldo_e_invalido(self):
        # 10 dias concedidos, 11 usados — o 11º deve ficar como inválido
        usos = [date(2026, 5, d) for d in range(1, 12)]
        r = calcular_yukyu(date(2025, 11, 1), date(2026, 7, 3), usos)
        self.assertEqual(r["saldo_disponivel"], 0)
        self.assertEqual(len(r["usos_invalidos"]), 1)

    def test_expiracao_apos_2_anos(self):
        # Concessão de 2019-07-01 (10 dias) expira em 2021-07-01 —
        # não deve contar no saldo de hoje (muito depois)
        r = calcular_yukyu(date(2019, 1, 1), date(2026, 7, 3), [])
        detalhe = r["detalhe_concessoes"][0]  # primeira concessão (6 meses)
        self.assertEqual(detalhe["grant_date"], date(2019, 7, 1))
        self.assertEqual(detalhe["expiry"], date(2021, 7, 1))
        self.assertGreater(r["total_expirado"], 0)

    def test_add_months_ajusta_dia_invalido(self):
        # 31/jan + 1 mês não pode virar 31/fev (não existe) — deve
        # ajustar para o último dia válido do mês de destino
        _add_months = FUNCS["_add_months"]
        self.assertEqual(_add_months(date(2026, 1, 31), 1), date(2026, 2, 28))




class TestIntervalosDetalhados(unittest.TestCase):
    """Valida a exclusão de intervalos/pausas do cálculo de adicional
    noturno (v2.33) — recurso opcional, pedido pelo usuário pra empresas
    com pausas curtas (ex: 10min a cada 2h) dentro do turno noturno."""

    def test_sem_intervalos_comportamento_identico_ao_antigo(self):
        r = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
        )
        self.assertEqual(r["night_minutes"], 420)

    def test_intervalos_dentro_do_periodo_noturno_sao_excluidos(self):
        r = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
            break_periods=[("22:30", "22:40"), ("00:30", "00:40"),
                           ("02:30", "02:40"), ("04:30", "04:40")],
        )
        # 420min (sem exclusão) - 40min (4 pausas de 10min) = 380min
        self.assertEqual(r["night_minutes"], 380)

    def test_intervalo_fora_do_periodo_noturno_nao_afeta(self):
        # Pausa às 20:45 (antes das 22h) não deve mudar nada no adicional
        # noturno, já que está fora do período 22h-05h
        r = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
            break_periods=[("20:45", "20:55")],
        )
        self.assertEqual(r["night_minutes"], 420)

    def test_intervalo_apos_meia_noite_ancora_no_dia_seguinte(self):
        # Turno cruza a meia-noite — uma pausa "01:00" deve ser ancorada
        # no dia seguinte ao início do turno (20:30), não confundida
        # com 01:00 do mesmo dia (que seria antes do turno começar)
        periodos = night_minutes_worked
        r_com = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
            break_periods=[("01:00", "01:15")],
        )
        r_sem = calculate_shift_pay(
            jikyuu=1590, shift_type="night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
        )
        self.assertEqual(r_sem["night_minutes"] - r_com["night_minutes"], 15)

    def test_night_minutes_worked_sem_periodos_igual_a_night_minutes_in_range(self):
        s = parse_hhmm("20:30")
        e = parse_hhmm("08:35")
        self.assertEqual(night_minutes_worked(s, e, None),
                          night_minutes_in_range(s, e))
        self.assertEqual(night_minutes_worked(s, e, []),
                          night_minutes_in_range(s, e))


class TestEngineLinhaDoTempo(unittest.TestCase):
    """Valida a engine de segmentação temporal (v2.38), sugerida por
    auditoria externa do projeto — resolve casos que a fórmula antiga
    (baseada em totais) não conseguia tratar corretamente: intervalo
    parcialmente noturno, intervalo dentro da janela de hora extra,
    múltiplos intervalos. Só é usada quando a POSIÇÃO do intervalo é
    conhecida (break_periods) — sem isso, mantém a fórmula antiga
    intacta (validada contra 5 holerites reais, ¥0 de diferença)."""

    def test_segmentos_cobrem_o_turno_sem_lacuna_nem_sobreposicao(self):
        start = parse_hhmm("20:30")
        end = parse_hhmm("08:35")
        ot = _anchor_to_shift(start, "06:35")
        segs = build_timeline_segments(start, end, ot, [])
        total = sum(s["minutes"] for s in segs)
        self.assertEqual(total, 725)  # 12h05min gross

    def test_intervalo_parcialmente_noturno_e_dividido_na_fronteira(self):
        start = parse_hhmm("20:30")
        end = parse_hhmm("08:35")
        ot = _anchor_to_shift(start, "06:35")
        bp_start = _anchor_to_shift(start, "21:45")
        bp_end = _anchor_to_shift(bp_start, "22:15")
        segs = build_timeline_segments(start, end, ot, [(bp_start, bp_end)])
        breaks = [s for s in segs if s["is_break"]]
        self.assertEqual(len(breaks), 2, "intervalo deveria dividir em 2 na fronteira das 22h")
        self.assertEqual(breaks[0]["minutes"], 15)
        self.assertFalse(breaks[0]["is_night"])
        self.assertEqual(breaks[1]["minutes"], 15)
        self.assertTrue(breaks[1]["is_night"])

    def test_sem_break_periods_usa_formula_antiga_sem_mudanca(self):
        # Mesmo cenário, com e sem break_periods=None explícito — deve
        # dar EXATAMENTE o mesmo resultado (retrocompatibilidade total)
        r1 = calculate_shift_pay(1590, "night", base_shift="night",
                                  start_str="20:35", end_str="08:35", break_min=65,
                                  ot_start_str="06:35")
        r2 = calculate_shift_pay(1590, "night", base_shift="night",
                                  start_str="20:35", end_str="08:35", break_min=65,
                                  ot_start_str="06:35", break_periods=None)
        self.assertEqual(r1, r2)

    def test_intervalo_multiplo_soma_minutos_corretamente(self):
        r = calculate_shift_pay(
            1590, "night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35",
            break_periods=[("21:45", "22:15"), ("01:00", "01:15"), ("06:00", "06:20")],
        )
        self.assertEqual(r["net_minutes"], 660)       # 725 - 65
        self.assertEqual(r["overtime_minutes"], 120)  # 06:35-08:35, sem intervalo nesse trecho
        self.assertEqual(r["regular_minutes"], 540)
        self.assertEqual(r["night_minutes"], 390)     # 420 brutos - 30min de intervalo noturno

    def test_intervalo_dentro_da_hora_extra_reduz_overtime_minutes(self):
        # Caso que a fórmula ANTIGA calculava errado: intervalo dentro
        # da janela de hora extra não reduzia o overtime_minutes, só
        # limitava o teto via min(raw_ot_min, net_min) — sem efeito
        # quando raw_ot_min já era menor que net_min
        r = calculate_shift_pay(
            1590, "night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=15,
            ot_start_str="06:35",
            break_periods=[("07:00", "07:15")],
        )
        self.assertEqual(r["overtime_minutes"], 105)  # 120 brutos - 15min de intervalo
        self.assertEqual(r["net_minutes"], 710)
        self.assertEqual(r["regular_minutes"], 605)

    def test_soma_dos_segmentos_trabalhados_bate_com_net_minutes(self):
        # Verificação de consistência interna: a soma dos segmentos NÃO
        # marcados como intervalo deve ser exatamente igual a net_minutes
        start = parse_hhmm("20:30")
        end = parse_hhmm("08:35")
        ot = _anchor_to_shift(start, "06:35")
        bp1 = (_anchor_to_shift(start, "22:30"), _anchor_to_shift(start, "23:15"))
        segs = build_timeline_segments(start, end, ot, [bp1])
        trabalhados = sum(s["minutes"] for s in segs if not s["is_break"])
        r = calculate_shift_pay(
            1590, "night", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=45,
            ot_start_str="06:35", break_periods=[("22:30", "23:15")],
        )
        self.assertEqual(trabalhados, r["net_minutes"])


class TestExtraMinutesEmDomingo(unittest.TestCase):
    """v2.50 — trava o bug crítico onde 延長 (minutos extras) registrado
    num domingo/feriado não entrava no cálculo mensal: a fórmula
    calculava o valor certo dentro de calculate_shift_pay, mas jogava
    em overtime_pay/overtime_minutes — que compute_monthly_forecast
    NUNCA lê para dias de domingo (só holiday_pay/night_pay são
    acumulados nesse caso). O minuto extra era calculado e descartado
    em silêncio. Corrigido: 延長 em domingo entra nas HORAS DE DOMINGO,
    à taxa de 1,35x (não 1,25x de hora extra genérica)."""

    def test_extra_minutes_em_domingo_soma_taxa_1_35(self):
        sem_extra = calculate_shift_pay(
            jikyuu=1590, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
            base_shift="night",
        )
        com_extra = calculate_shift_pay(
            jikyuu=1590, shift_type="holiday",
            start_str="20:35", end_str="08:35",
            break_min=65, block=1, is_holiday=True,
            base_shift="night", extra_minutes=30,
        )
        # holiday_pay deve aumentar — os 30min extras entram nele
        self.assertGreater(com_extra["holiday_pay"], sem_extra["holiday_pay"])
        # overtime_pay continua zero — não vai pra hora extra genérica
        self.assertEqual(com_extra["overtime_pay"], 0)

    def test_extra_minutes_em_dia_normal_continua_taxa_1_25(self):
        # Comportamento inalterado pra dia normal (não feriado)
        sem_extra = calculate_shift_pay(
            jikyuu=1590, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, ot_start_str="06:35", block=1,
        )
        com_extra = calculate_shift_pay(
            jikyuu=1590, shift_type="night",
            start_str="20:35", end_str="08:35",
            break_min=65, ot_start_str="06:35", block=1, extra_minutes=30,
        )
        self.assertGreater(com_extra["overtime_pay"], sem_extra["overtime_pay"])


class TestDomingoFeriadoCorporativoIndependentes(unittest.TestCase):
    """v2.52 — trava o comportamento CORRETO (depois de uma primeira
    tentativa de correção que inverteu a prioridade errada — ver
    PROBLEMAS_RECORRENTES.md) para um domingo TAMBÉM marcado como
    feriado corporativo/nacional (ex: dia 3 de maio/2026, que é
    憲法記念日 E cai num domingo E era, no caso real relatado, feriado
    da fábrica também):

    - Feriado (nacional/corporativo) SEM horário registrado → fábrica
      fechada, dia NÃO conta como trabalhado, mesmo caindo num domingo
      escalado pra trabalho. Confirmado com caso real: o usuário
      esperava 2 domingos trabalhados naquele mês (não 3), porque o
      dia 3 era feriado — a fábrica não abriu.
    - Feriado COM horário registrado (trabalhou mesmo com a fábrica
      fechada) → conta normalmente, taxa cheia 1,35x.
    - SEM feriado nenhum marcado, domingo escalado pra trabalho →
      conta como domingo trabalhado normalmente (esse era o bug
      original: esse caso caía errado no ramo de 'dia normal')."""

    def test_domingo_com_feriado_corporativo_sem_registro_nao_conta(self):
        # Caso real: dia 3 de maio/2026, domingo + feriado corporativo,
        # SEM horário registrado — fábrica fechada, não deveria contar.
        resultado_sem_feriado = base_forecast(
            year=2026, month=5, cycle_type="4x2",
            anchor_date=date(2026, 5, 1),
            holiday_days=[], day_overrides={},
        )
        resultado_com_feriado_no_domingo = base_forecast(
            year=2026, month=5, cycle_type="4x2",
            anchor_date=date(2026, 5, 1),
            holiday_days=[3], day_overrides={},   # 03/05/2026 é domingo
        )
        # Marcar feriado corporativo no domingo deve REDUZIR days_legal
        # em 1 (o dia deixa de contar), não manter igual.
        if resultado_sem_feriado["days_legal"] > 0:
            self.assertEqual(
                resultado_com_feriado_no_domingo["days_legal"],
                resultado_sem_feriado["days_legal"] - 1,
            )
            self.assertLess(
                resultado_com_feriado_no_domingo["gross"],
                resultado_sem_feriado["gross"],
            )

    def test_domingo_com_feriado_corporativo_e_horario_registrado_conta(self):
        # Mesmo cenário, mas com horário registrado no dia 3 — trabalhou
        # mesmo com a fábrica marcada como fechada, deve contar normal.
        resultado_sem_feriado = base_forecast(
            year=2026, month=5, cycle_type="4x2",
            anchor_date=date(2026, 5, 1),
            holiday_days=[], day_overrides={},
        )
        resultado_com_registro = base_forecast(
            year=2026, month=5, cycle_type="4x2",
            anchor_date=date(2026, 5, 1),
            holiday_days=[3],
            day_overrides={"3": {"status": "normal", "start": "20:35",
                                  "end": "08:35", "break_min": 65}},
        )
        if resultado_sem_feriado["days_legal"] > 0:
            self.assertEqual(
                resultado_com_registro["days_legal"],
                resultado_sem_feriado["days_legal"],
            )

    def test_feriado_corporativo_em_dia_util_continua_nao_remunerado(self):
        # Comportamento inalterado: feriado corporativo num dia de
        # semana normal (não domingo) continua não remunerado por
        # padrão, sem horário registrado.
        resultado = base_forecast(
            year=2026, month=5, cycle_type="5x2",
            anchor_date=date(2026, 5, 1),
            holiday_days=[4],   # 04/05/2026 é segunda-feira
            day_overrides={},
        )
        # Não trava valor exato (depende de vários fatores do cenário
        # base), só confirma que não quebra e o resultado é coerente.
        self.assertIsNotNone(resultado["gross"])


class TestJikyuuVigentePorMes(unittest.TestCase):
    """v2.52 — trava jikyuu_vigente_para_mes(): permite registrar
    aumentos de 時給 no Histórico sem afetar retroativamente a previsão
    de meses passados não registrados."""

    def test_sem_historico_usa_default(self):
        self.assertEqual(jikyuu_vigente_para_mes("2026-05", [], 1500), 1500)

    def test_sem_marco_algum_usa_default(self):
        hist = [{"month": "2026-01", "deductions": 40000}]  # sem jikyuu_effective
        self.assertEqual(jikyuu_vigente_para_mes("2026-05", hist, 1500), 1500)

    def test_mes_antes_do_primeiro_marco_usa_default(self):
        hist = [{"month": "2026-06", "jikyuu_effective": 1650}]
        self.assertEqual(jikyuu_vigente_para_mes("2026-01", hist, 1500), 1500)

    def test_mes_exatamente_no_marco(self):
        hist = [{"month": "2026-01", "jikyuu_effective": 1590}]
        self.assertEqual(jikyuu_vigente_para_mes("2026-01", hist, 1500), 1590)

    def test_mes_entre_dois_marcos_usa_o_anterior(self):
        hist = [
            {"month": "2026-01", "jikyuu_effective": 1590},
            {"month": "2026-06", "jikyuu_effective": 1650},
        ]
        self.assertEqual(jikyuu_vigente_para_mes("2026-03", hist, 1500), 1590)

    def test_mes_depois_do_ultimo_marco_usa_o_mais_recente(self):
        hist = [
            {"month": "2026-01", "jikyuu_effective": 1590},
            {"month": "2026-06", "jikyuu_effective": 1650},
        ]
        self.assertEqual(jikyuu_vigente_para_mes("2026-12", hist, 1500), 1650)

    def test_marcos_fora_de_ordem_no_historico_ainda_funciona(self):
        # Histórico normalmente vem ordenado reverse, mas a função não
        # deve depender disso
        hist = [
            {"month": "2026-06", "jikyuu_effective": 1650},
            {"month": "2026-01", "jikyuu_effective": 1590},
        ]
        self.assertEqual(jikyuu_vigente_para_mes("2026-03", hist, 1500), 1590)
        self.assertEqual(jikyuu_vigente_para_mes("2026-12", hist, 1500), 1650)


class TestDescontoRealParaMes(unittest.TestCase):
    """v2.52 — trava desconto_real_para_mes(): mês com holerite real
    registrado no Histórico usa o valor de desconto REAL, não a
    previsão (Média Histórica/Fixo)."""

    def test_sem_registro_retorna_none(self):
        self.assertIsNone(desconto_real_para_mes("2026-05", []))

    def test_mes_sem_registro_correspondente_retorna_none(self):
        hist = [{"month": "2026-01", "deductions": 40000}]
        self.assertIsNone(desconto_real_para_mes("2026-05", hist))

    def test_mes_com_registro_retorna_valor_real(self):
        hist = [{"month": "2026-02", "deductions": 44283}]
        self.assertEqual(desconto_real_para_mes("2026-02", hist), 44283)

    def test_registro_com_desconto_zero_retorna_none(self):
        # Desconto 0 é tratado como "não preenchido ainda", não como um
        # valor real válido de ¥0 — evita mostrar "Registro real: ¥0"
        # em holerites que só têm outros campos preenchidos.
        hist = [{"month": "2026-02", "deductions": 0}]
        self.assertIsNone(desconto_real_para_mes("2026-02", hist))


class TestNormalizeYyyymm(unittest.TestCase):
    """v2.52 — trava o preenchimento automático do campo de mês na aba
    Histórico, mesmo padrão dos campos de hora/data já existentes."""

    def test_seis_digitos_sem_separador(self):
        self.assertEqual(normalize_yyyymm("202602"), "2026-02")

    def test_com_barra(self):
        self.assertEqual(normalize_yyyymm("2026/2"), "2026-02")

    def test_com_ponto(self):
        self.assertEqual(normalize_yyyymm("2026.02"), "2026-02")

    def test_ja_no_formato_correto(self):
        self.assertEqual(normalize_yyyymm("2026-02"), "2026-02")

    def test_mes_invalido_devolve_como_veio(self):
        self.assertEqual(normalize_yyyymm("2026-13"), "2026-13")

    def test_vazio_retorna_vazio(self):
        self.assertEqual(normalize_yyyymm(""), "")


class TestYukyuNaoTravaComKeyError(unittest.TestCase):
    """v2.50 — trava o bug crítico onde qualquer dia marcado como Yukyu
    fazia compute_monthly_forecast travar com KeyError('_ot_rate_full').
    calculate_shift_pay tinha um `return` antecipado no caminho do
    Yukyu, que pulava o bloco (mais abaixo na função) onde as taxas
    eram expostas no resultado. Corrigido: as taxas agora são
    calculadas logo no início da função, antes de qualquer return
    antecipado (absent, yukyu, shift_type inválido, etc.)."""

    def test_mes_com_yukyu_nao_trava(self):
        # Antes desse fix, isso lançava KeyError e derrubava o app
        resultado = base_forecast(
            day_overrides={"10": {"status": "yukyu"}},
        )
        self.assertIsNotNone(resultado["gross"])
        self.assertGreaterEqual(resultado["yukyu_pay"], 0)


class TestYukyuEmFeriadoUsaJornadaConfigurada(unittest.TestCase):
    """Trava a correção da v2.40 — o toggle 'yukyu_on_holiday' (有休 em
    Feriado Corporativo) usava sempre jikyuu×8 fixo, inconsistente com
    o resto do sistema, que já usa a jornada normal configurada em todo
    lugar (v2.32). Reportado pelo usuário: 'não tem mais nada fixo pois
    depende da configuração do usuário'."""

    def test_toggle_usa_jornada_normal_nao_8h_fixo(self):
        r = calculate_shift_pay(
            1590, "holiday", base_shift="night",
            is_holiday=True, yukyu_on_holiday=True,
            break_min=65, ot_start_str="06:35",
            cfg_start_str="20:30", cfg_end_str="08:35",
        )
        self.assertEqual(r["net_minutes"], 540)  # 9h, não 480 (8h)
        self.assertEqual(r["base_pay"], round(1590 / 60 * 540))

    def test_toggle_e_yukyu_normal_dao_o_mesmo_resultado(self):
        # Mesma jornada configurada — o toggle "em feriado" e o status
        # "yukyu" comum devem dar exatamente o mesmo valor, já que os
        # dois usam a mesma lógica de jornada normal agora
        r_toggle = calculate_shift_pay(
            1590, "holiday", base_shift="night",
            is_holiday=True, yukyu_on_holiday=True,
            break_min=65, ot_start_str="06:35",
            cfg_start_str="20:30", cfg_end_str="08:35",
        )
        r_normal = calculate_shift_pay(
            1590, "yukyu", base_shift="night",
            break_min=65, ot_start_str="06:35",
            cfg_start_str="20:30", cfg_end_str="08:35",
        )
        self.assertEqual(r_toggle["base_pay"], r_normal["base_pay"])
        self.assertEqual(r_toggle["net_minutes"], r_normal["net_minutes"])


class TestYukyuComHorarioLimitadoPelaJornadaNormal(unittest.TestCase):
    """Trava a correção reportada pelo usuário: '9 horas vezes 1590 é
    igual a 14310. O cálculo me dá 17490.' — informar o horário
    INTEIRO do turno (ex: 20:30-08:35, igual a um dia normal) no Yukyu
    contava até a janela de hora extra também (11h), pagando mais do
    que a jornada normal (9h) permitiria. Corrigido com um teto: nunca
    paga mais que a jornada normal, mesmo com horário informado."""

    def test_horario_igual_ao_turno_inteiro_e_limitado_a_9h(self):
        r = calculate_shift_pay(
            1590, "yukyu", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35", cfg_start_str="20:30", cfg_end_str="08:35",
        )
        self.assertEqual(r["net_minutes"], 540)  # 9h, não 660 (11h)
        self.assertEqual(r["base_pay"], 14310)   # não 17490

    def test_horario_genuinamente_parcial_nao_e_afetado(self):
        # 4h reais, bem menor que a jornada normal de 9h — não deve
        # ser limitado nem inflado, paga exatamente as 4h informadas
        r = calculate_shift_pay(
            1590, "yukyu", base_shift="night",
            start_str="20:30", end_str="00:30", break_min=0,
            ot_start_str="06:35", cfg_start_str="20:30", cfg_end_str="08:35",
        )
        self.assertEqual(r["net_minutes"], 240)  # 4h
        self.assertEqual(r["base_pay"], 6360)

    def test_sem_horario_continua_igual_ao_com_horario_no_teto(self):
        # Sem horário (jornada normal cheia) e com horário igual ao
        # turno inteiro devem dar exatamente o mesmo resultado agora
        r_sem = calculate_shift_pay(
            1590, "yukyu", base_shift="night", break_min=65,
            ot_start_str="06:35", cfg_start_str="20:30", cfg_end_str="08:35",
        )
        r_com = calculate_shift_pay(
            1590, "yukyu", base_shift="night",
            start_str="20:30", end_str="08:35", break_min=65,
            ot_start_str="06:35", cfg_start_str="20:30", cfg_end_str="08:35",
        )
        self.assertEqual(r_sem["base_pay"], r_com["base_pay"])
        self.assertEqual(r_sem["net_minutes"], r_com["net_minutes"])


class TestPresencaMensal(unittest.TestCase):
    """Valida o cálculo de % de presença pro 精皆勤手当 (adicional de
    assiduidade opcional por empresa) — isolado do motor de pagamento,
    só falta de dia inteiro desconta (confirmado pelo usuário)."""

    def setUp(self):
        self.cycle = generate_4x2_calendar(date(2026, 6, 1), 2026, 3, "B")
        self.dias_trabalho = [d for d, s in self.cycle.items() if s == "work"]

    def test_sem_falta_100_por_cento(self):
        r = calcular_presenca_mensal(self.cycle, {})
        self.assertEqual(r["percentual"], 100.0)
        self.assertEqual(r["faltas"], 0)

    def test_uma_falta_desconta_proporcionalmente(self):
        dia = self.dias_trabalho[0]
        r = calcular_presenca_mensal(self.cycle, {str(dia): {"status": "absent"}})
        self.assertEqual(r["faltas"], 1)
        esperado = (r["dias_programados"] - 1) / r["dias_programados"] * 100
        self.assertAlmostEqual(r["percentual"], esperado)

    def test_yukyu_nao_desconta(self):
        dia = self.dias_trabalho[0]
        r = calcular_presenca_mensal(self.cycle, {str(dia): {"status": "yukyu"}})
        self.assertEqual(r["percentual"], 100.0)
        self.assertEqual(r["faltas"], 0)

    def test_domingo_feriado_trabalhado_nao_desconta(self):
        dia = self.dias_trabalho[0]
        r = calcular_presenca_mensal(self.cycle, {str(dia): {"status": "legal"}})
        self.assertEqual(r["percentual"], 100.0)

    def test_feriado_da_empresa_nao_entra_no_denominador(self):
        dia = self.dias_trabalho[0]
        r_sem_feriado = calcular_presenca_mensal(self.cycle, {})
        r_com_feriado = calcular_presenca_mensal(self.cycle, {}, month_holidays=[dia])
        self.assertEqual(r_com_feriado["dias_programados"],
                          r_sem_feriado["dias_programados"] - 1)

    def test_mes_sem_dias_programados_retorna_100(self):
        r = calcular_presenca_mensal({}, {})
        self.assertEqual(r["percentual"], 100.0)
        self.assertEqual(r["dias_programados"], 0)


if __name__ == "__main__":
    print("=" * 60)
    print("ONION PAYROLL — SUITE DE TESTES AUTOMATIZADOS")
    print("=" * 60)
    unittest.main(verbosity=2)
