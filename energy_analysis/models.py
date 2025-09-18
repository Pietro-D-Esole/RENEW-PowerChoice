# a file to help starting calculations

from support_functions.help_functions import lateral, get_noise_type,get_transmittance, get_hdd_rad, get_coefficients, get_noise_value, get_rad_days



def get_default_energy_data():
    return {
        "total_costifissi_values": {
            "total_current_fuel_energy": 0,
            "total_planned_fuel_energy": 0,
            "total_saved_fuel_energy": 0,
            "total_current_electric_energy": 0,
            "total_planned_electric_energy": 0,
            "total_saved_electric_energy": 0,
            "total_current_fuel_bill": 0,
            "total_planned_fuel_bill": 0,
            "total_saved_fuel_bill": 0,
            "total_current_electric_bill": 0,
            "total_planned_electric_bill": 0,
            "total_saved_electric_bill": 0,
            "total_current_energy_cons": 0,
            "total_planned_energy_cons": 0,
            "total_saved_energy_cons": 0,
            "total_current_energy_bill": 0,
            "total_planned_energy_bill": 0,
            "total_saved_energy_bill": 0,
            "total_current_heating_energy_loss": 0,
            "total_planned_heating_energy_loss": 0,
            "total_saved_heating_energy_loss": 0,
            "total_current_dhw_energy_loss": 0,
            "total_planned_dhw_energy_loss": 0,
            "total_saved_dhw_energy_loss": 0,
            "total_current_energy_loss": 0,
            "total_planned_energy_loss": 0,
            "total_saved_energy_loss": 0
        },
        "monte_carlo_values": {
            "energy_saving": {
                "value": 0,
                "conf_bound": 0,
                "value_at_risk": 0,
                "cond_value_at_risk": 0
            }
        }
    }


def calculate(params, case, constants, noisematrix, param_type, year):
    """
    Revised version of `calculate()` that exactly matches `o_calculate()` for annual losses.
    Adds monthly breakdown via rad_days.
    """
    # 1. fetch common geometry & climate inputs
    tmp = get_noise_type(param_type)
    common = case["common_params"]
    nfloor = common["floor_count"]
    ndw = common["dwelling_count"]
    s_floor = common["floor_area"] + get_noise_value(noisematrix, case, "common", "floor_area")
    wh = common["wall_height"] + get_noise_value(noisematrix, case, "common", "wall_height")



    # Constants and multipliers to match o_calculate
    million = 1_000_000
    sec_in_hour = 3600
    one_over_million = 1e-6
    tf_ratio = 24 * one_over_million
    tf_ratio_hour = sec_in_hour * tf_ratio
    sec_in_day = sec_in_hour * 24
    one = million * one_over_million

    # HDD and solar inputs
    hdd_rad = get_hdd_rad(common, constants, noisematrix, case, year)
    hdd = hdd_rad["hdd"]
    tday = hdd_rad["tday"]
    rad = hdd_rad["rad"]

    # Heating days per month (for monthly breakdown)
    climate_row = next((r for r in constants.city_climate
                        if r["country"] == common["country"] and r["city"] == common["city"]), None)
    if climate_row is None:
        raise KeyError(f"No climate entry for {common['city']}, {common['country']}")
    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    rad_days = get_rad_days(climate_row, days_in_month)

    # Surface and volume terms
    s_netta = s_floor * 0.85
    v_netto = s_netta * (wh - 0.3)
    vol = s_floor * wh * nfloor
    s_tot = (common["total_surface_area_to_volume_ratio"] + get_noise_value(noisematrix, case, "common", "total_surface_area_to_volume_ratio")) * vol
    lateral_params = lateral(common, s_tot, case, noisematrix)

    trans = get_transmittance(params, common, case, noisematrix, param_type)
    fixed = get_coefficients(constants, tmp, noisematrix, case)

    u_win = params["window_transmittance_value"] + get_noise_value(noisematrix, case, tmp, "window_transmittance_value")
    win_to_sur_rat = params["window_to_surface_area_ratio"] + get_noise_value(noisematrix, case, tmp, "window_to_surface_area_ratio")

    s_win = min(win_to_sur_rat * s_floor, lateral_params["lateral_area"])

    s_wall = lateral_params["lateral_area"] - s_win * nfloor

    s_roof = s_floor
    s_floor_area = s_floor * ndw

    # Coefficients
    shadow = fixed["shadow"]
    rho_air = fixed["rho_air"]
    cp_air = fixed["cp_air"]
    alfa = fixed["alfa"]
    he = fixed["he"]
    airchangecoeff = fixed["airchangecoeff"]
    sun_factor = fixed["sun_factor"] + get_noise_value(noisematrix, case, tmp, "sun_factor")
    g_v = 0.011 * (0.04 * s_floor) * 3600
    g_v_2 = airchangecoeff * v_netto

    u_floor = trans["ufloor"]
    u_roof = trans["uroof"]
    u_w = trans["uwall"]

    # Gains/losses
    q_v_2 = nfloor * ndw * g_v * rho_air * cp_air * hdd * tf_ratio
    q_v = nfloor * ndw * g_v_2 * rho_air * cp_air * hdd * tf_ratio
    qis = ndw * min(5.294 * s_netta - 0.01557 * s_netta ** 2, 450) * tday * tf_ratio_hour
    q_win = u_win * s_win * ndw * hdd * tf_ratio_hour
    qsg = shadow * sun_factor * s_win * rad * ndw * one
    q_s = shadow * alfa * s_wall * rad * ndw * one
    q_w = u_w * s_wall * ndw * hdd * tf_ratio_hour - u_w / he * q_s


    # Adjust for building type
    q_floor = q_roof = 0
    btype = common["building_type"]
    pos = common["storey_position"]
    u_floor = trans["ufloor"]
    u_roof = trans["uroof"]

    if btype in ("multistorey", "detached house", "semi_detached house", "end_terrace_house"):
        q_floor = u_floor * s_floor * ndw * hdd * tf_ratio_hour
        qs_roof = shadow * rad * alfa * s_roof * ndw * one
        q_roof = u_roof * s_roof * ndw * hdd * tf_ratio_hour - (u_roof / he) * qs_roof
        if btype in ("semi_detached house", "end_terrace_house"):
            q_w *= 0.75
    elif btype == "terraced_house":
        q_floor = u_floor * s_floor * ndw * hdd * tf_ratio_hour
        qs_roof = shadow * rad * alfa * s_roof * ndw * one
        q_roof = u_roof * s_roof * ndw * hdd * tf_ratio_hour - (u_roof / he) * qs_roof
        q_w *= 0.5
    elif btype == "apartment":
        if pos == "top":
            qs_roof = shadow * rad * alfa * s_roof * ndw * one
            q_roof = u_roof * s_roof * ndw * hdd * tf_ratio_hour - (u_roof / he) * qs_roof
        else:  # ground
            q_floor = u_floor * s_floor * ndw * hdd * tf_ratio_hour

    # DHW load
    dhw_load = fixed["dhw_load"]
    cpw = fixed["cp_water"]
    h_w = q_w * million / (hdd * ndw * sec_in_day)
    h_win = q_win * million / (hdd * ndw * sec_in_day)
    h_v = q_v * million / (hdd * ndw * sec_in_day)
    h_v_2 = q_v_2 * million / (hdd * ndw * sec_in_day)
    q_dhw = ndw * (0.04 * s_floor) * dhw_load * cpw * (45 - 15) * 365 * one_over_million

    # Prorate to monthly
    def prorate_annual(annual):
        return [annual * (rd / tday) for rd in rad_days]

    return {
        "q_win": q_win, "q_w": q_w, "q_floor": q_floor, "q_roof": q_roof,
        "q_v": q_v, "q_is": qis, "q_dhw": q_dhw, "qsg": qsg,
        "s_floor_area": s_floor_area,

        "q_win_monthly": prorate_annual(q_win),
        "q_w_monthly": prorate_annual(q_w),
        "q_floor_monthly": prorate_annual(q_floor),
        "q_roof_monthly": prorate_annual(q_roof),
        "q_v_monthly": prorate_annual(q_v),
        "q_is_monthly": prorate_annual(qis),
        "q_dhw_monthly": prorate_annual(q_dhw),
    }



def estimate_appliance_load(case, params_type):
    import random
    params = case[params_type]
    common = case["common_params"]
    occupants = params.get("n_occupants", 1)
    dwelling_count = case["common_params"]["dwelling_count"]
    floor_count = case["common_params"]["floor_count"]
    #floor_modifier = 1 + (0.25 * (floor_count-1))

    weeks = 52 #+ get_noise_value()


    # Appliance weekly consumption (kWh)
    weekly_kwh = {}

    # Fridge (runs daily)
    weekly_kwh["fridge"] = 0.18 * 24 * 7

    # Lighting
    weekly_kwh["lighting"] = occupants * 0.06 * 3 * 7

    # TV
    weekly_kwh["tv"] = 0.10 * 2 * 7

    # Kettle (scaled by occupants)
    weekly_kwh["kettle"] = occupants * 2.5 * (0.1 * 7)

    # Kettle (scaled by occupants)
    weekly_kwh["oven"] = occupants * random.uniform(2,5) * (0.1 * 7)

    # Washing machine & dryer & dishwasher, weekly one cycle
    weekly_kwh["washing_machine"] = 2.0 * 1
    weekly_kwh["tumble_dryer"] = 2.5 * 1
    weekly_kwh["dishwasher"] = 1.8 * 1

    total_weekly = sum(weekly_kwh.values())

    annual_kwh = total_weekly * weeks * dwelling_count * floor_count
    return annual_kwh

