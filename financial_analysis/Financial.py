from support_functions.help_functions import is_number, \
    get_fixed_cost_from_sheet_by_key, get_noise_value, get_fixed_cost_from_sheet_by_key_noise, \
    get_fixed_cost_by_key_from_sheet_noise, get_noise_value_fixed_cost_by_name, \
    get_coefficients, get_value_from_sheet_multi, get_hdd_rad, get_hhours, lateral

from energy_analysis.heating_systems import get_effitiency_coefs

noise = 0


def calculate_costs(current_params, planned_params, common_params, constants, e_disp, report, case, noisematrix, year):

    hdd_rad_params = get_hdd_rad(common_params, constants, noisematrix, case, year)
    coefficients = get_coefficients(constants, "none", noisematrix, case)
    efficiency_coefficients = get_effitiency_coefs(constants, "planned_params", noisematrix, case)
    position = common_params["storey_position"]
    ndw = common_params["dwelling_count"]
    s_floor = common_params["floor_area"] + get_noise_value(noisematrix, case, "common", "floor_area")
    buildtype = common_params["building_type"]
    nfloor = common_params["floor_count"]
    s_v = common_params["total_surface_area_to_volume_ratio"] + \
          get_noise_value(noisematrix, case, "common", "total_surface_area_to_volume_ratio")
    h = common_params["wall_height"] + get_noise_value(noisematrix, case, "common", "wall_height")
    curr_win_sur_rat = current_params["window_to_surface_area_ratio"] + \
                       get_noise_value(noisematrix, case, "current", "window_to_surface_area_ratio")
    plan_win_sur_rat = planned_params["window_to_surface_area_ratio"] + \
                       get_noise_value(noisematrix, case, "planned", "window_to_surface_area_ratio")
    s_winratio = plan_win_sur_rat
    dhw_vol = s_floor * nfloor * coefficients["dhw_load"] * 0.04
    mh2o = 12 / 60

    wall_cond = planned_params["wall_envelope_thermal_conductivity"] + \
                get_noise_value(noisematrix, case, "planned", "wall_envelope_thermal_conductivity")
    wall_thick = planned_params["wall_thickness"] + \
                 get_noise_value(noisematrix, case, "planned", "wall_thickness")
    roof_cond = planned_params["roof_envelope_thermal_conductivity"] + \
                get_noise_value(noisematrix, case, "planned", "roof_envelope_thermal_conductivity")
    roof_thick = planned_params["roof_thickness"] + \
                 get_noise_value(noisematrix, case, "planned", "roof_thickness")
    floor_cond = planned_params["floor_envelope_thermal_conductivity"] + \
                 get_noise_value(noisematrix, case, "planned", "floor_envelope_thermal_conductivity")
    floor_thick = planned_params["floor_thickness"] + \
                  get_noise_value(noisematrix, case, "planned", "floor_thickness")
    uisolw = wall_cond / wall_thick
    uisolr = roof_cond / roof_thick
    uisolf = floor_cond / floor_thick
    hdd = hdd_rad_params["hdd"]
    t_base = efficiency_coefficients["t_base"]
    t_min = t_base - 2 * hdd / hdd_rad_params["tday"]
    t_med = t_base - hdd / hdd_rad_params["tday"]
    t_base_t_min = (t_base - t_min) / hdd / 1000
    pgen_ = e_disp / ndw * 1000000 / 3600 / get_hhours(hdd) * t_base_t_min
    pgen = int(pgen_ / 5 + 0.5) * 5
    pgen_hp_ = e_disp / ndw * 1000000 / 3600 / 18 * t_base_t_min
    pgen_hp = int(pgen_hp_ / 5 + 1) * 5
    ssun = e_disp / ndw / hdd_rad_params["rad"] / 0.4

    pgen_dhw = mh2o * coefficients["cp_water"] * (45 - 15) / 1000
    e_dhw = ndw * dhw_vol * coefficients["cp_water"] * (45 - 15) * 365 * 0.000001
    s_sun_dhw = e_dhw / ndw / hdd_rad_params["rad"] / 0.4  # hdd_rad_params["rad_total"]

    sr_ = s_floor
    sf_ = s_floor
    vol_ = h * s_floor * nfloor
    s_tot_ = s_v * vol_
    lateral_params = lateral(common_params, s_tot_, case, noisematrix)
    s_lat = lateral_params["lateral_area"]
    swin_ = min(s_floor * s_winratio * nfloor, s_lat)
    sw_ = s_lat

    cost, cost1, cost2, cost3, cost4, cost5, cost6, cost7, cost8 = 0, 0, 0, 0, 0, 0, 0, 0, 0

    if current_params["heating_type"] != planned_params["heating_type"] or \
            current_params["burner_type"] != planned_params["burner_type"]:
        if planned_params["heating_type"] == 1:
            burner_type = planned_params["burner_type"]
            cost = get_fixed_cost_from_sheet_by_key_noise(constants.heating_dhw["table1"], burner_type,
                                                          noisematrix, "burner_type") * max(15, pgen)
        elif planned_params["heating_type"] == 2:
            cost = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table1"], "heating", "pellet stove",
                                                          noisematrix) * max(10, pgen)
        elif planned_params["heating_type"] == 3:
            cost = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table1"], "heating", "heat pump",
                                                          noisematrix) * max(10, pgen_hp)

    if current_params["emitter_type"] != planned_params["emitter_type"]:
        if planned_params["emitter_type"] == 2 and current_params["emitter_type"] == 1:
            cost1 = (get_fixed_cost_from_sheet_by_key_noise(constants.heating_dhw["table3"],
                                                            planned_params["emitter_type"], noisematrix, "emitter_type")
                     - get_fixed_cost_from_sheet_by_key(constants.heating_dhw["table3"],
                                                        current_params["emitter_type"])) \
                    * pgen
        else:
            cost1 = get_fixed_cost_from_sheet_by_key_noise(
                constants.heating_dhw["table3"], planned_params["emitter_type"], noisematrix, "emitter_type") * pgen

    solar_perc = current_params["solar_perc"]
    if not is_number(solar_perc):
        solar_perc = 0

    if bool(planned_params["solar_check"]):
        cost2 = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table1"], "heating", "solar_heating",
                                                       noisematrix) * ssun * \
                max(0, (planned_params["solar_perc"] - solar_perc))

    if current_params["DHW_type"] != planned_params["DHW_type"] or \
            current_params["DHW_burner_type"] != planned_params["DHW_burner_type"]:
        if planned_params["DHW_type"] == 1:
            cost3 = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table2"], "plant_type",
                                                           "electric_boiler", noisematrix) * max(50, dhw_vol)
        elif planned_params["DHW_type"] == 2:
            cost3 = get_fixed_cost_from_sheet_by_key_noise(
                constants.heating_dhw["table2"], planned_params["DHW_burner_type"] + 1, noisematrix, "DHW_burner_type") \
                    * max(19, pgen_dhw)
        elif planned_params["DHW_type"] == 3:
            cost3 = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table2"], "plant_type", "heat_pump",
                                                           noisematrix) * max(50, dhw_vol)

    dhw_solar_perc = current_params["DHW_solar_perc"]
    if not is_number(dhw_solar_perc):
        dhw_solar_perc = 0
    if bool(planned_params["DHW_solar_check"]):
        cost4 = get_fixed_cost_by_key_from_sheet_noise(constants.heating_dhw["table2"], "plant_type", "solar_heater",
                                                       noisematrix) * s_sun_dhw * \
                max(0, (planned_params["DHW_solar_perc"] - dhw_solar_perc))

    if current_params["wall_insulation_check"] != planned_params["wall_insulation_check"]:
        wall_mat_cost = constants.envelope_windows["table1"][1 - 1]["material_cost"]
        wall_ins_cost = constants.envelope_windows["table1"][1 - 1]["installation_cost"]
        cost5 = ((wall_mat_cost * (wall_thick / wall_cond * 0.03 / 0.1) + wall_ins_cost) +
                 get_noise_value_fixed_cost_by_name(noisematrix, "wall_insulation")) * sw_

    if current_params["roof_insulation_check"] != planned_params["roof_insulation_check"]:
        roof_mat_cost = constants.envelope_windows["table1"][2 - 1]["material_cost"]
        roof_ins_cost = constants.envelope_windows["table1"][2 - 1]["installation_cost"]
        cost6 = ((roof_mat_cost * (roof_thick / roof_cond * 0.03 / 0.1) +
                  get_noise_value_fixed_cost_by_name(noisematrix, "roof_insulation")) + roof_ins_cost) * sr_

    if current_params["floor_insulation_check"] != planned_params["floor_insulation_check"]:
        floor_mat_cost = constants.envelope_windows["table1"][3 - 1]["material_cost"]
        floor_ins_cost = constants.envelope_windows["table1"][3 - 1]["installation_cost"]
        cost7 = ((floor_mat_cost * (floor_thick / floor_cond * 0.03 / 0.1) +
                  get_noise_value_fixed_cost_by_name(noisematrix, "floor_insulation")) + floor_ins_cost) * sf_

    curr_win = current_params["window_transmittance_value"] + \
               get_noise_value(noisematrix, case, "current", "window_transmittance_value")
    plan_win = planned_params["window_transmittance_value"] + \
               get_noise_value(noisematrix, case, "planned", "window_transmittance_value")
    if curr_win != plan_win or \
            curr_win_sur_rat != plan_win_sur_rat:
        if plan_win >= 4:  # single glazed
            cost8 = (constants.envelope_windows["table2"][1 - 1]["value"] +
                     get_noise_value_fixed_cost_by_name(noisematrix, "single_glazed_cost")) * swin_
        if plan_win < 4:  # double glazed
            cost8 = (constants.envelope_windows["table2"][2 - 1]["value"] +
                     get_noise_value_fixed_cost_by_name(noisematrix, "single_glazed_cost")) * swin_

    invest_heating = (cost + cost1 + cost2 + cost5 + cost6 + cost7 + cost8) * ndw
    invest_dhw = (cost3 + cost4) * ndw


    report["individual_costs"] = {
        "heating_generator_cost": cost * ndw,
        "heating_emitter_cost": cost1 * ndw,
        "heating_solar_cost": cost2 * ndw,
        "dhw_generator_cost": cost3 * ndw,
        "dhw_solar_cost": cost4 * ndw,
        "window_cost": cost8 * ndw,
        "wall_envelope_cost": cost5 * ndw,
        "roof_envelope_cost": cost6 * ndw,
        "floor_envelope_cost": cost7 * ndw,
        "total_cost": invest_heating + invest_dhw
    }

    return {
        "heating_cost": invest_heating,
        "dhw_cost": invest_dhw,
        "t_min": t_min,
        "t_med": t_med,
    }


def get_fuel_cost(sheet, country, year, memo, noisematrix=None):
    """
    Returns gas cost in €/kWh for a given year and country.
    Assumes base prices are in €/smc and converts using 10.35 kWh/smc.
    """
    # Future: enable noise injection if needed
    # noise = get_vc_noise_value(noisematrix, year, "fuel_costs")
    noise = 0  # set to 0 unless used

    if year == 0:
        year = 1

    price_eur_per_smc = get_value_from_sheet_multi(
        sheet,
        "variable_costs",
        (("country", country), ("source", "methane_gas")),
        "p" + str(year),
        memo
    )

    kWh_per_smc = 10.35  # standard LHV of natural gas in Ireland
    price_eur_per_kWh = price_eur_per_smc / kWh_per_smc + noise

    return round(price_eur_per_kWh, 4)



def get_electric_cost(sheet, country, year, memo, noisematrix=None):
    #noise = get_vc_noise_value(noisematrix, year, "electric_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "electric_energy")), "p" + str(year), memo
    ) + noise


def get_pellet_cost(sheet, country, year, memo, noisematrix=None):
    #noise = get_vc_noise_value(noisematrix, year, "pellet_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "pellet")), "p" + str(year), memo
    ) / 19000 * 1000 + noise

def get_oil_cost(sheet, country, year, memo, noisematrix=None):
    # noise = get_vc_noise_value(noisematrix, year, "oil_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs",
        (("country", country), ("source", "heating_oil")),
        "p" + str(year),
        memo + noise
    )

def get_discount_rate(sheet, country, memo):
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "discount rate")), "variation_rate_per_year", memo
    )

def get_maintenance_cost(case, params_type, constants):
    """
    Returns the annual maintenance cost (€) for the given scenario,
    based on heating_type and corresponding heating system name.
    """
    params = case[params_type]
    heating_type = params.get("heating_type")

    # Map heating_type to matching string in constants
    heating_name_map = {
        1: "1-Type B open chamber",
        2: "pellet stove",
        3: "heat pump"
    }

    heating_name = heating_name_map.get(heating_type)
    if heating_name is None:
        raise ValueError(f"Unsupported or unknown heating_type: {heating_type}")

    # Look up in table1
    for row in constants.heating_dhw["table1"]:
        if row.get("heating") == heating_name:
            return row["maintenance_cost"]

    raise ValueError(f"No matching maintenance cost found for heating system: '{heating_name}'")


def estimate_annual_energy_bills(case, params_type, heating_loads, elec_kwh, year, constants, memo, noisematrix):
    """
    Estimate total annual energy bill (fuel + electricity + appliances) in euros.
    Accounts for PV self-consumption and grid export where applicable.
    """
    sheet = constants.variable_costs
    params = case[params_type]
    country = case["common_params"]["country"]
    fuel_type = params.get("fuel_type")

    # === Fuel demand (space heating + DHW)
    selq_f = heating_loads[params_type].get("selq_f", 0)
    selqDHW_f = heating_loads[params_type].get("selqDHW_f", 0)
    total_fuel_demand = selq_f + selqDHW_f  # [kWh]

    # === Prices
    if fuel_type == 1:
        fuel_price = get_fuel_cost(sheet, country, year, memo, noisematrix)
    elif fuel_type == 2:
        fuel_price = get_oil_cost(sheet, country, year, memo, noisematrix)
    elif fuel_type == 3:
        fuel_price = get_pellet_cost(sheet, country, year, memo, noisematrix)
    else:
        fuel_price = 0

    electric_price = get_electric_cost(sheet, country, year, memo, noisematrix)


    # === Electricity bill (includes PV export logic)
    export_rate = 0.18  # €/kWh paid for exported electricity
    monthly_bills = []

    if isinstance(elec_kwh, list):
        # Handle monthly input
        electric_bill = 0

        for month_val in elec_kwh:
            if month_val >= 0:
                monthly_bills.append(month_val * electric_price)
            else:
                monthly_bills.append(month_val * export_rate)

        electric_bill = sum(monthly_bills)

    else:
        # Keep legacy behavior if scalar value is passed
        if elec_kwh >= 0:
            electric_bill = elec_kwh * electric_price
        else:
            exported_kwh = -elec_kwh
            export_credit = exported_kwh * export_rate
            electric_bill = -export_credit  # user earns from export

    # === Final bill
    fuel_bill = total_fuel_demand * fuel_price
    total_bill = round(fuel_bill + electric_bill, 2)

    return fuel_bill, electric_bill, total_bill, monthly_bills


def calculate_npv(case, vita, curr_annual_costs, plan_annual_costs, total_investment):
    """
    Calculate the NPV and (discounted and undiscounted) cash flows over time.

    Parameters:
    - case: contains 'discount_rate' under 'common_params' (in percent)
    - vita: lifetime (years)
    - curr_annual_costs: € value of current annual energy + maintenance
    - plan_annual_costs: € value of planned annual energy + maintenance (+ control)
    - total_investment: upfront retrofit investment

    Returns:
    - npv: Net Present Value (€, rounded to 2 decimals)
    - cash_flow: list of annual savings (no discounting)
    - discounted_cash_flow: list of discounted savings
    - cumulative_cash_flow: list of cumulative (undiscounted) savings
    - cumulative_discounted_cash_flow: list of cumulative discounted savings
    """
    discount_rate = case["common_params"]["discount_rate"] / 100  # convert from %
    inflation_rate = 0.02  # assumed 2% escalation per year

    cash_flow = []
    discounted_cash_flow = []
    cumulative_cash_flow = []
    cumulative_discounted_cash_flow = []

    cumulative_simple = -total_investment
    cumulative_discounted = -total_investment

    for t in range(vita):
        # Apply inflation to both current and planned costs
        escalated_curr = curr_annual_costs * ((1 + inflation_rate) ** t)
        escalated_plan = plan_annual_costs * ((1 + inflation_rate) ** t)

        # Net saving and discount
        annual_saving = escalated_curr - escalated_plan
        discounted_saving = annual_saving / ((1 + discount_rate) ** t)

        # Round & store
        cash_flow.append(round(annual_saving, 2))
        discounted_cash_flow.append(round(discounted_saving, 2))

        # Cumulative tracking
        cumulative_simple += annual_saving
        cumulative_discounted += discounted_saving
        cumulative_cash_flow.append(round(cumulative_simple, 2))
        cumulative_discounted_cash_flow.append(round(cumulative_discounted, 2))

    # Final NPV is total discounted savings minus investment
    npv = round(cumulative_discounted, 2)

    return (
        npv,
        cash_flow,
        discounted_cash_flow,
        cumulative_cash_flow,
        cumulative_discounted_cash_flow
    )


def calculate_payback_periods(investment, cash_flow, discounted_cash_flow):
    """
    Compute the simple and discounted payback periods.

    Parameters:
        investment (float): upfront investment in euros
        cash_flow (list of float): yearly undiscounted net savings
        discounted_cash_flow (list of float): yearly discounted net savings

    Returns:
        tuple: (simple_payback, discounted_payback), rounded to 2 decimals
    """
    # --- Simple Payback ---
    cumulative_simple = 0
    simple_pp = None
    for i, val in enumerate(cash_flow):
        cumulative_simple += val
        if cumulative_simple >= investment:
            overshoot = cumulative_simple - investment
            fraction = 1 - (overshoot / val)
            simple_pp = i + fraction
            break

    # --- Discounted Payback ---
    cumulative_discounted = 0
    discounted_pp = None
    for i, val in enumerate(discounted_cash_flow):
        cumulative_discounted += val
        if cumulative_discounted >= investment:
            overshoot = cumulative_discounted - investment
            fraction = 1 - (overshoot / val)
            discounted_pp = i + fraction
            break

    return (
        round(simple_pp, 2) if simple_pp is not None else None,
        round(discounted_pp, 2) if discounted_pp is not None else None
    )


def calculate_irr(cash_flows, investment, precision=1e-6, max_iterations=1000):
    """
    Compute the Internal Rate of Return (IRR) using a bisection method.

    Parameters:
    - cash_flows: list of annual cash flows (yearly savings), years 1 to N
    - investment: initial investment (positive number)
    - precision: convergence threshold
    - max_iterations: maximum number of iterations

    Returns:
    - IRR as a percentage (rounded to 2 decimals), or "Negative IRR"
    """
    flows = [-investment] + list(cash_flows)  # add negative investment at year 0

    def npv(rate):
        return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(flows))

    # Ensure IRR exists
    if all(f >= 0 for f in flows) or all(f <= 0 for f in flows):
        return "Negative IRR"

    low, high = -0.9999, 1.0  # avoid div by zero

    for _ in range(max_iterations):
        mid = (low + high) / 2
        val = npv(mid)

        if abs(val) < precision:
            return round(mid * 100, 2)

        if val > 0:
            low = mid
        else:
            high = mid

    return "Negative IRR"





def calculate_profitability_index(discounted_cash_flows, investment):
    """
    Calculate the Profitability Index (PI) for a retrofit project.

    Parameters:
    - discounted_cash_flows: list of discounted cash flows (starting from year 1)
    - investment: initial investment (upfront cost at year 0)

    Returns:
    - Profitability Index (rounded to 2 decimals), or "Not profitable" if PI < 1
    """
    if investment == 0:
        return "Undefined (zero investment)"

    total_present_value = sum(discounted_cash_flows)
    pi = total_present_value / investment

    return round(pi, 2)

