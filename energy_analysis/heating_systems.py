
from support_functions.help_functions import (get_noise_type, get_coefficients, get_noise_value, validate_case_parameters,
                            get_noise_value_constants, get_value_from_sheet, get_value_from_sheet_no_header,
                            selected_variable_costs, get_hdd_rad)
from models import  calculate


noisematrix = None

def read_param_eff(params, case, constants, params_type, noisematrix, year):
    """
    Compute “η” (eta) efficiencies for space-heating and DHW
    ──────────────────────────────────────────────────────────
    * η p  : efficiency referred to **primary energy** (kWhp delivered per kWht useful)
    * η f  : efficiency referred to **fuel / combustible** input
    * η e  : efficiency referred to **electric** input
    * η s  : efficiency of the **solar** share
    * suffix “_dhw” = the same four efficiencies, but for Domestic-Hot-Water production
    Returned as a dict so downstream code can choose the one that matches the
    supply vector being costed (electricity, gas, pellet, solar, …).
    """
    common_params = case["common_params"]
    # -------------------------------------------------------
    # 1.  Read auxiliary data & coefficients
    # -------------------------------------------------------
    noise_type = get_noise_type(params_type)               # Identifies which noise-branch to use
    coefficients = get_coefficients(constants, params_type, noisematrix, case)     # Generic physical constants
    efficiency_coefficients = get_effitiency_coefs(constants, params_type, noisematrix, case)

    conversion      = coefficients["eta_conv"]             # elec → primary energy conversion η
    regulation_eff  = efficiency_coefficients["regul_eff"] # room-stat / controller quality
    distribution_eff= efficiency_coefficients["distr_eff"] # pipework / duct losses

    # “Emitter” = terminal unit (radiator, FCU, floor panels, …)
    emitter_eff = (constants.heating_dhw["table3"]
                   [params["emitter_type"] - 1]["efficiency"]
                   + get_noise_value(noisematrix, case,
                                     noise_type, "emitter_eff"))

    solar_fraction  = (params["solar_frac"]
                       + get_noise_value(noisematrix, case,
                                         noise_type, "solar_frac"))

    # Boiler / burner base efficiency (if system is a burner)
    generator_eff   = (constants.heating_dhw["table1"]
                       [params["burner_type"] - 1]["efficiency"]
                       + get_noise_value(noisematrix, case,
                                         noise_type, "generator_eff"))

    pellet_eff          = efficiency_coefficients["pellet_eff"]
    heat_pump_eff       = efficiency_coefficients["hp_eff"]       # reference COP
    heat_pump_dhw_eff   = efficiency_coefficients["hp_dhw_eff"]   # DHW COP

    # -------------------------------------------------------
    # 2.  Weather-dependent modifiers for heat-pump COP
    # -------------------------------------------------------
    hdd_rad_params   = get_hdd_rad(common_params, constants,
                                   noisematrix, case, year)
    t_base           = efficiency_coefficients["t_base"]          # base outdoor temp
    t_med            = t_base - hdd_rad_params["hdd"] / hdd_rad_params["tday"]

    # Empirical constants used by EN 14825 / 15316 HP performance curves
    etac             = 0.6
    chi              = min(0.75 * heat_pump_eff / 3.5, 1 / etac)
    dhw_chi          = min(0.75 * heat_pump_dhw_eff / 3.5, 1 / etac)

    # ΔT terms for evaporator / condenser
    dteva, dtcond = 10, 15
    dhw_dteva, dhw_dtcond = 12, 6

    # Seasonal COPs
    heat_pump_copr     = chi * etac * (t_med + 273 + dteva) / (t_base - t_med + dteva + dtcond)
    heat_pump_dhw_copr = dhw_chi * etac * (t_med + 273 + dhw_dteva) / (50 - t_med + dhw_dteva + dhw_dtcond)

    # -------------------------------------------------------
    # 3.  Select generator efficiency according to heating system
    # -------------------------------------------------------
    if params['heating_type'] == 1:           # 1 = gas/diesel burner
        eta_genp = generator_eff
        eta_genf = generator_eff              # same number, but viewed as “fuel input”
        eta_gene = 1e12                       # ≫1 so electric share is ~0
    elif params['heating_type'] == 2:         # 2 = pellet stove
        eta_genp = pellet_eff
        eta_genf = pellet_eff
        eta_gene = 1e12
    elif params['heating_type'] == 3:         # 3 = heat-pump
        eta_genp = heat_pump_copr * conversion   # primary-energy view
        eta_genf = 1e12                           # no fuel
        eta_gene = heat_pump_copr                # electric input
    else:
        raise Exception("Invalid heating type")

    # -------------------------------------------------------
    # 4.  Global (building-level) heating efficiencies η
    # -------------------------------------------------------
    eta_p = (regulation_eff * distribution_eff *
             eta_genp * emitter_eff / (1 - solar_fraction))
    eta_f = (regulation_eff * distribution_eff *
             eta_genf * emitter_eff / (1 - solar_fraction))
    eta_e = (regulation_eff * distribution_eff *
             eta_gene * emitter_eff / (1 - solar_fraction))
    eta_s = (distribution_eff * emitter_eff / solar_fraction)     # solar portion

    # -------------------------------------------------------
    # 5.  Same logic for DHW
    # -------------------------------------------------------
    solar_dhw_fraction = (params["DHW_solar_frac"]
                           + get_noise_value(noisematrix, case,
                                             noise_type, "DHW_solar_frac"))

    emitter_dhw_eff = (constants.heating_dhw["table2"]
                       [params["DHW_burner_type"]]["efficiency"]
                       + get_noise_value(noisematrix, case,
                                         noise_type, "emitter_dhw_eff"))

    electric_boiler_dhw_eff = (constants.heating_dhw["table2"][0]["efficiency"]
                               + get_noise_value(noisematrix, case,
                                                 noise_type, "electric_boiler_dhw_eff"))

    # Choose DHW generator efficiencies
    if params['DHW_type'] == 0:            # use same generator as heating
        eta_dhw_genp = eta_genp
        eta_dhw_genf = eta_genf
        eta_dhw_gene = eta_gene
        solar_dhw_fraction = solar_fraction
    elif params['DHW_type'] == 1:          # electric boiler
        eta_dhw_genp = electric_boiler_dhw_eff * conversion
        eta_dhw_genf = 1e12
        eta_dhw_gene = electric_boiler_dhw_eff
    elif params['DHW_type'] == 2:          # gas burner DHW
        eta_dhw_genp = emitter_dhw_eff
        eta_dhw_genf = emitter_dhw_eff
        eta_dhw_gene = 1e12
    elif params['DHW_type'] == 3:          # DHW heat-pump
        eta_dhw_genp = heat_pump_dhw_copr * conversion
        eta_dhw_genf = 1e12
        eta_dhw_gene = heat_pump_dhw_copr
    else:
        raise Exception("Invalid dhw type")

    eta_dhw_p = distribution_eff * eta_dhw_genp / (1 - solar_dhw_fraction)
    eta_dhw_f = distribution_eff * eta_dhw_genf / (1 - solar_dhw_fraction)
    eta_dhw_e = distribution_eff * eta_dhw_gene / (1 - solar_dhw_fraction)
    eta_dhw_s = distribution_eff / solar_dhw_fraction            # purely solar DHW

    # -------------------------------------------------------
    # 6.  Return a tidy dict
    # -------------------------------------------------------
    return {
        "eta_p":      eta_p,       # heating – primary
        "eta_f":      eta_f,       # heating – fuel
        "eta_e":      eta_e,       # heating – electric
        "eta_s":      eta_s,       # heating – solar
        "eta_dhw_p":  eta_dhw_p,   # DHW – primary
        "eta_dhw_f":  eta_dhw_f,   # DHW – fuel
        "eta_dhw_e":  eta_dhw_e,   # DHW – electric
        "eta_dhw_s":  eta_dhw_s,   # DHW – solar
    }



def get_effitiency_coefs(constants, params_type, noisematrix, case):
    noise_type = get_noise_type(params_type)
    regul_eff = get_value_from_sheet_no_header(constants.heating_dhw["table4"], 'regulation_mean_efficiency') + \
        get_noise_value_constants(noisematrix, "regul_eff")
    distr_eff = get_value_from_sheet_no_header(constants.heating_dhw["table4"], 'distribution_mean_efficiency') + \
        get_noise_value_constants(noisematrix, "distr_eff")
    pellet_eff = get_value_from_sheet(constants.heating_dhw["table1"], 'heating', 'pellet stove', 'efficiency') + \
        get_noise_value(noisematrix, case, noise_type, "pellet_eff")
    hp_eff = get_value_from_sheet(constants.heating_dhw["table1"], 'heating', 'heat pump', 'efficiency') + \
        get_noise_value(noisematrix, case, noise_type, "hp_eff")
    hp_dhw_eff = get_value_from_sheet(constants.heating_dhw["table2"], 'plant_type', 'heat_pump', 'efficiency') + \
        get_noise_value(noisematrix, case, noise_type, "hp_dhw_eff")
    t_base = get_value_from_sheet(constants.other_thermal_data, 'description', 'Tb-base temperature for HDD [°C]',
                                  'value')
    p = {
        "regul_eff": regul_eff,
        "distr_eff": distr_eff,
        "pellet_eff": pellet_eff,
        "hp_eff": hp_eff,
        "hp_dhw_eff": hp_dhw_eff,
        "t_base": t_base
    }  # todo: add fixed constants to Constants table and use that JSON param here
    return p


def heating_efficiency(case, constants, noisematrix, year):
    # Dictionary to store efficiency results for current and planned parameters
    calc_dispersed_eff = {}

    for params_type in ["current_params", "planned_params"]:
        calc_dispersed_eff[params_type] = {}
        cdec = calc_dispersed_eff[params_type]
        params = case[params_type]

        validate_case_parameters(params)

        # Step 1: Get heat loss breakdown (annual + monthly)
        dhr = calculate(params, case, constants, noisematrix, params_type, year)

        # Step 2: Get system efficiencies
        rper = read_param_eff(params, case, constants, params_type, noisematrix, year)

        # Step 3: Annual delivered space heating demand
        qd_annual = (
            dhr["q_v"] + dhr["q_w"] + dhr["q_floor"] + dhr["q_roof"] + dhr["q_win"]
            - dhr["qsg"] - dhr["q_is"]
        )
        qd_annual = max(qd_annual, 0)

        # Step 4: Annual delivered + final energy by vector
        cdec["selq_d"] = qd_annual
        cdec["selq_p"] = qd_annual / rper["eta_p"]
        cdec["selq_f"] = qd_annual / rper["eta_f"]
        cdec["selq_e"] = qd_annual / rper["eta_e"]
        cdec["selq_s"] = qd_annual / rper["eta_s"]

        # Step 5: Annual DHW delivered + final energy
        qd_dhw = dhr["q_dhw"]
        cdec["selqDHW_d"] = qd_dhw
        cdec["selqDHW_p"] = qd_dhw / rper["eta_dhw_p"]
        cdec["selqDHW_f"] = qd_dhw / rper["eta_dhw_f"]
        cdec["selqDHW_e"] = qd_dhw / rper["eta_dhw_e"]
        cdec["selqDHW_s"] = qd_dhw / rper["eta_dhw_s"]

        # Step 6: Monthly delivered heat (space + DHW)
        # Monthly heat losses already prorated by calculate()
        # Total useful space heating per month
        qd_monthly = [
            qv + qw + qf + qr + qw_ - qis - qsg
            for qv, qw, qf, qr, qw_, qis, qsg in zip(
                dhr["q_v_monthly"], dhr["q_w_monthly"], dhr["q_floor_monthly"],
                dhr["q_roof_monthly"], dhr["q_win_monthly"],
                dhr["q_is_monthly"], dhr["qsg_monthly"] if "qsg_monthly" in dhr else [0]*12
            )
        ]
        qd_monthly = [max(q, 0) for q in qd_monthly]  # no negative heating

        cdec["selq_d_monthly"] = qd_monthly
        cdec["selq_p_monthly"] = [q / rper["eta_p"] for q in qd_monthly]
        cdec["selq_f_monthly"] = [q / rper["eta_f"] for q in qd_monthly]
        cdec["selq_e_monthly"] = [q / rper["eta_e"] for q in qd_monthly]
        cdec["selq_s_monthly"] = [q / rper["eta_s"] for q in qd_monthly]

        # Step 7: Monthly DHW load (flat or same proration as space heating)
        q_dhw_monthly = dhr["q_dhw_monthly"]
        cdec["selqDHW_d_monthly"] = q_dhw_monthly
        cdec["selqDHW_p_monthly"] = [q / rper["eta_dhw_p"] for q in q_dhw_monthly]
        cdec["selqDHW_f_monthly"] = [q / rper["eta_dhw_f"] for q in q_dhw_monthly]
        cdec["selqDHW_e_monthly"] = [q / rper["eta_dhw_e"] for q in q_dhw_monthly]
        cdec["selqDHW_s_monthly"] = [q / rper["eta_dhw_s"] for q in q_dhw_monthly]

        # Floor area (unchanged)
        cdec["s_floor_area"] = dhr["s_floor_area"]

    return calc_dispersed_eff



def consumi_heat_params(case, constants, tmp_dh_variables, tmp_vc_variables, total_sel_variables, total_vc_variables,
                        year, noisematrix):
    calc_dispersed_eff = heating_efficiency(case, constants, noisematrix, year)
    vc_e, vc_f, vc_separated = {}, {}, {}
    for params_type in ["current_params", "planned_params"]:
        vc_separated[params_type] = {}
        params = case[params_type]


        tmp_dh_variables[params_type] = calculate(params, case, constants, noisematrix, params_type, year)
        tmp_dh_variables[params_type].update(calc_dispersed_eff[params_type])

        tmp_total_sel = total_sel_variables[params_type]
        for tmp in tmp_dh_variables[params_type]:
            tmp_total_sel[tmp] = tmp_total_sel[tmp] + tmp_dh_variables[params_type][tmp]

        selected_variable_costs(calc_dispersed_eff, case, year, noisematrix, params_type, vc_e, vc_f, vc_separated)
        tmp_vc_variables[params_type] = vc_separated[params_type]

        tmp_total_vc = total_vc_variables[params_type]
        for tmp in tmp_vc_variables[params_type]:
            tmp_total_vc[tmp] = tmp_total_vc[tmp] + tmp_vc_variables[params_type][tmp]
    return calc_dispersed_eff, vc_e, vc_f

def consumi_dispersed(case, constants, dispersed_heat_values, total_sel_variables,
                      total_vc_variables, vc_variables, year, noisematrix):

    # if monte carlo=1 removed here
    dispersed_heat_values #[case.id] = {}
    tmp_dh_variables = dispersed_heat_values#[case.id]
    vc_variables#[case.id] = {}
    tmp_vc_variables = vc_variables#[case.id]
    calc_dispersed_eff, vc_e, vc_f = consumi_heat_params(case, constants, tmp_dh_variables, tmp_vc_variables,
                                                         total_sel_variables, total_vc_variables, year, noisematrix)
    return calc_dispersed_eff, vc_e, vc_f