noisematrix = None

def validate_case_parameters(params):
    # todo:
    # if global variable irun is 0 reset all arrays related to monte carlo
    # sensitivity is nonsense and can be ignored
    # If sensitivity <> 1 And irun = 0 Then
    # here we need to reset variables related to MC based on irun, which we need to pass as argument if
    # we don't resolve this better by isolating monte carlo from this code
    abs_min = 0.000001
    abs_max = 1000000
    if not bool(params["wall_insulation_check"]):
        params["wall_envelope_thermal_conductivity"] = abs_max
        params["wall_thickness"] = abs_min
    if not bool(params["roof_insulation_check"]):
        params["roof_envelope_thermal_conductivity"] = abs_max
        params["roof_thickness"] = abs_min
    if not bool(params["floor_insulation_check"]):
        params["floor_envelope_thermal_conductivity"] = abs_max
        params["floor_thickness"] = abs_min
    if bool(params["solar_check"]):
        params["solar_frac"] = max(min(params["solar_perc"], 1 - abs_min), abs_min)
    else:
        params["solar_frac"] = abs_min
    if bool(params["DHW_solar_check"]):
        params["DHW_solar_frac"] = max(min(params["DHW_solar_perc"], 1 - abs_min), abs_min)
    else:
        params["DHW_solar_frac"] = abs_min
    windows_transmittance_value = params["window_transmittance_value"]
    params["sun_factor"] = (windows_transmittance_value ** 3.5 + 10) / (windows_transmittance_value ** 3.5 + 25)

def get_transmittance(params, common_params, case, noisematrix, params_type):
    import numpy as np

    tmp = get_noise_type(params_type)

    # --- Apply noise ---
    uw = common_params["wall_thermal_transmittance"] + get_noise_value(noisematrix, case, "common", "wall_thermal_transmittance")
    wall_cond = params["wall_envelope_thermal_conductivity"] + get_noise_value(noisematrix, case, tmp, "wall_envelope_thermal_conductivity")
    wall_thick = params["wall_thickness"] + get_noise_value(noisematrix, case, tmp, "wall_thickness")

    ur = common_params["roof_thermal_transmittance"] + get_noise_value(noisematrix, case, "common", "roof_thermal_transmittance")
    roof_cond = params["roof_envelope_thermal_conductivity"] + get_noise_value(noisematrix, case, tmp, "roof_envelope_thermal_conductivity")
    roof_thick = params["roof_thickness"] + get_noise_value(noisematrix, case, tmp, "roof_thickness")

    uf = common_params["floor_thermal_transmittance"] + get_noise_value(noisematrix, case, "common", "floor_thermal_transmittance")
    floor_cond = params["floor_envelope_thermal_conductivity"] + get_noise_value(noisematrix, case, tmp, "floor_envelope_thermal_conductivity")
    floor_thick = params["floor_thickness"] + get_noise_value(noisematrix, case, tmp, "floor_thickness")

    # --- Physical bounds ---
    min_cond, max_cond = 0.02, 5.0     # W/m·K
    min_thick, max_thick = 0.01, 1.0   # m

    wall_cond = np.clip(wall_cond, min_cond, max_cond)
    roof_cond = np.clip(roof_cond, min_cond, max_cond)
    floor_cond = np.clip(floor_cond, min_cond, max_cond)

    wall_thick = np.clip(wall_thick, min_thick, max_thick)
    roof_thick = np.clip(roof_thick, min_thick, max_thick)
    floor_thick = np.clip(floor_thick, min_thick, max_thick)

    # --- Final U-values ---
    p = {
        "uwall": 1 / (1 / max(uw, 0.001) + wall_thick / wall_cond),
        "uroof": 1 / (1 / max(ur, 0.001) + roof_thick / roof_cond),
        "ufloor": 1 / (1 / max(uf, 0.001) + floor_thick / floor_cond)
    }

    # --- Optional debug output ---
    for label, u in [("wall", p["uwall"]), ("roof", p["uroof"]), ("floor", p["ufloor"])]:
        if not (0.1 <= u <= 5.0):
            print(f"[Warning] Unrealistic U-value for {label}: {u:.3f}")

    return p


def lateral(common_params, s_tot, case, noisematrix):
    floor_area = common_params["floor_area"] + get_noise_value(noisematrix, case, "common", "floor_area")
    building_type = common_params["building_type"]
    storey_pos = common_params.get("storey_position", "").lower()

    dispersed_lateral = {}
    if building_type in ["multistorey", "detached house"]:
        lateral_area = s_tot - 2 * floor_area
    elif building_type == "semi_detached house":
        # Assume only 3 walls exposed → 3/4 of the normal lateral area
        lateral_area = (s_tot - 2 * floor_area) * 0.75
    elif building_type == "end_terrace_house":
        # Assume 2 walls exposed → 1/2 of normal lateral area
        lateral_area = (s_tot - 2 * floor_area) * 0.5
    elif building_type == "mid_terrace_house":
        # Only front/back walls exposed → ~1/4 to 1/2
        lateral_area = (s_tot - 2 * floor_area) * 0.4  # you can tune this
    elif building_type == "apartment":
        if storey_pos in ["top", "ground"]:
            lateral_area = s_tot - floor_area
        elif storey_pos == "mid":
            lateral_area = s_tot
        else:
            # If position unknown, fallback conservatively
            lateral_area = s_tot - floor_area
    else:
        # Default fallback
        lateral_area = s_tot - 2 * floor_area

    dispersed_lateral["lateral_area"] = lateral_area
    return dispersed_lateral


def calculate_rad(city_climate_sheet, memo):
    if "data" in memo:
        return memo["data"]
    rad_values = []
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for row in city_climate_sheet:
        rad_monthly = [row['january'], row['february'], row['march'], row['april'], row['may'], row['june'],
                       row['july'], row['august'], row['september'], row['october'], row['november'], row['december']]
        rad_days = get_rad_days(row, days)
        rad_tmp = sum(round(rad_days[i] * rad_monthly[i], 4) for i in range(12))
        rad_tmp_total = sum(round(days[i] * rad_monthly[i], 4) for i in range(12))
        rad_values.append({
            "country": row["country"],
            "city": row["city"],
            "rad": rad_tmp,
            "rad_total": rad_tmp_total,
            "rad_days": rad_days
        })
    memo["data"] = rad_values
    return rad_values




def get_hdd_rad(common_params, constants, noisematrix, case, year):
    p = {}
    country = common_params["country"]
    city = common_params["city"]
    rads = calculate_rad(constants.city_climate, constants.rad_memo)
    hdd_val = get_by_city_country(constants.city_climate, "city_climate", country, city, "hdd",
                                  constants.sheet_multi_memo)

    if hdd_val is None:
        print(f"[ERROR] HDD not found for ({country}, {city}) — setting HDD = 0 as fallback")
        hdd_val = 0

    p["hdd"] = hdd_val + get_noise_value(noisematrix, case, "hdd", year)
    p["tday"] = sum(
        get_by_city_country(rads, "rads", country, city, "rad_days", constants.sheet_multi_memo)) + get_noise_value(
        noisematrix, case, "tday", year)
    p["rad"] = get_by_city_country(rads, "rads", country, city, "rad", constants.sheet_multi_memo) + get_noise_value(
        noisematrix, case, "rad", year)
    p["rad_total"] = get_by_city_country(rads, "rads", country, city, "rad_total", constants.sheet_multi_memo)
    return p


def get_hhours(hdd):
    if hdd < 600:
        return 6
    elif 600 <= hdd <= 900:
        return 8
    elif 900.1 <= hdd <= 1400:
        return 10
    elif 1400.1 <= hdd <= 2100:
        return 12
    elif 2100.1 <= hdd <= 3000:
        return 14
    else:
        return 18

def get_by_city_country(sheet, key, country, city, field, memo):
    return get_value_from_sheet_multi(
        sheet,
        key,
        (("country", country), ("city", city)),
        field,
        memo
    )

def get_value_from_sheet_multi(sheet, key, search_columns, find_column, memo):
    key_tuple_hash = hash((key, search_columns, find_column))
    if key_tuple_hash in memo:
        return memo[key_tuple_hash]
    #print(f"\nDEBUG: Sheet sample = {sheet[:2]}")  # show first two rows
    for row in sheet:
        matches = 0
        for search_column in search_columns:
            row_val = row[search_column[0]]
            search_column_val = search_column[1]
            if isinstance(row_val, str) and isinstance(search_column_val, str):
                row_val = row_val.lower().strip()
                search_column_val = search_column_val.lower().strip()
            if row_val == search_column_val:
                matches += 1
        if matches == len(search_columns):
            memo[key_tuple_hash] = row[find_column]
            return row[find_column]

    # Not found, print a helpful warning
    print(f"[WARN] No match found for {search_columns} in '{key}', looking for field '{find_column}'")

    # Suggest close matches by city or country
    possible_matches = []
    for row in sheet:
        for col, val in search_columns:
            if isinstance(row[col], str) and val.lower().strip() in row[col].lower():
                possible_matches.append((row["country"], row["city"]))
                break
    if possible_matches:
        print(f"       Did you mean one of these? {possible_matches[:5]}")
    else:
        print("       No similar entries found in the data.")

    memo[key_tuple_hash] = None
    return None


def get_rad_days(row, days): #row, days
    rad_days = [0] * 12
    tmp = row['heatingonoff']

    stmp = tmp.split("/")[0].split(".")
    etmp = tmp.split("/")[1].split(".")

    start_day = int(stmp[0])
    start_month = int(stmp[1])
    end_day = int(etmp[0])
    end_month = int(etmp[1])

    for i in range(start_month, len(days) + 1):
        if i == start_month:
            rad_days[i - 1] = days[i - 1] - start_day + 1
        else:
            rad_days[i - 1] = days[i - 1]

    for i in range(1, end_month + 1):
        if i == end_month:
            rad_days[i - 1] = end_day
        else:
            rad_days[i - 1] = days[i - 1]

    return rad_days


def get_solar_climate(case, constants):
    country = case["common_params"]["country"]

    # Extract the dictionary from the list
    data_dict = constants.solar_climate_data[0]

    # Default to Ireland if country not found
    if country not in data_dict:
        country = "Ireland"

    data = data_dict[country]
    return data["monthly_ghi"], data["monthly_temp"]


def get_value_from_sheet(sheet, search_name, search_value, find_name):
    for row in sheet:
        if row[search_name] == search_value:
            return row[find_name]
    return None

def get_value_from_sheet_no_header(sheet, search_name):
    for row in sheet:
        if row[search_name]:
            return row[search_name]
    return None

def get_coefficients(constants, param_type, noisematrix, case):
    #hash_key = hash((param_type, case.id, "empty" if noisematrix is None else "matrix"))
    #if hash_key in constants.coefficients_memo:
        #return constants.coefficients_memo[hash_key]
    noise_type = get_noise_type(param_type)
    alfa = get_value_from_sheet(constants.other_thermal_data, 'description', 'alfa (plaster)', 'value') + get_noise_value_constants(noisematrix, "alfa")
    shadow = get_value_from_sheet(constants.other_thermal_data, 'description', 'shadow', 'value') + get_noise_value_constants(noisematrix, "shadow")
    dhw_load = get_value_from_sheet(constants.other_thermal_data, 'description','DHWload  [kg/person /day]   1 person=25 m2', 'value') + get_noise_value_constants(noisematrix, "dhw_load")
    sun_factor = get_value_from_sheet(constants.other_thermal_data, 'description','sun factor (glass transmission coeff.)', 'value')
    airchangecoeff = get_value_from_sheet(constants.other_thermal_data, 'description','Airchangecoeff   [1/h]','value') + get_noise_value(noisematrix, case, noise_type, "airchangecoeff")
    he = 23 + get_noise_value_constants(noisematrix, "he")
    eta_conv = 0.5 + get_noise_value_constants(noisematrix, "eta_conv")
    fixed_constants = {
        "rho_air": 1.188,
        "cp_air": 1007,
        "he": he,
        "dhw_load": dhw_load,
        "cp_water": 4182,
        "eta_conv": eta_conv,
        "alfa": alfa,
        "shadow": shadow,
        "sun_factor": sun_factor,
        "airchangecoeff": airchangecoeff
    }  # todo: add fixed constants to Constants table and use that JSON param here
    #constants.coefficients_memo[hash_key] = fixed_constants
    return fixed_constants

def get_noise_value(noisematrix, case, param_type, key):
    if noisematrix is None:
        return 0
    return noisematrix[id(case)][param_type].get(key, 0)



def get_vc_noise_value(noisematrix, year, key):
    if noisematrix is None:
        return 0
    return noisematrix["costs"][key][year]


def get_noise_value_constants(noisematrix, key):
    if noisematrix is None:
        return 0
    return noisematrix["constants"][key]


def get_noise_type(params_type):
    if params_type == "current_params":
        return "current"
    else:
        return "planned"


def get_noise_value_fixed_cost_by_name(noisematrix, name):
    if noisematrix is None:
        return 0
    return noisematrix["costs"]["fixed_costs"][name]

def selected_variable_costs(calc_dispersed_eff, case, vcs, year, noisematrix, params_type, vc_e, vc_f, vc_separated,memo):
    calc_vc = {}

    params = case[params_type]
    calc_vc[params_type] = {}
    calc_vc_cur = calc_vc[params_type]
    heating_flag = params["heating_type"]
    heating_dhw_flag = params["DHW_type"]
    pellet = 0
    if heating_flag == 2:
        pellet = 1
    country = country = case["common_params"]["country"]
    c_disp_eff_curr = calc_dispersed_eff[params_type]
    tmp = 0.076 #price of fuel considered, previously was "get_fuel_costs"
    calc_vc_cur["selVC_f"] = c_disp_eff_curr["selq_f"] * tmp
    if pellet == 1:
        calc_vc_cur["selVC_f"] = c_disp_eff_curr["selq_f"] * get_pellet_cost(vcs, country, year, memo, noisematrix)
    calc_vc_cur["selVC_e"] = c_disp_eff_curr["selq_e"] * get_electric_cost(vcs, country, year, memo, noisematrix)
    calc_vc_cur["selVCDHW_f"] = c_disp_eff_curr["selqDHW_f"] * get_fuel_cost(vcs, country, year, memo, noisematrix)
    if pellet == 1 and heating_dhw_flag == 0:
        calc_vc_cur["selVCDHW_f"] = c_disp_eff_curr["selqDHW_f"] * get_pellet_cost(vcs, country, year, memo,noisematrix)
    calc_vc_cur["selVCDHW_e"] = c_disp_eff_curr["selqDHW_e"] * get_electric_cost(vcs, country, year, memo, noisematrix)
    vc_separated[params_type] = calc_vc_cur

    vc_f[params_type] = calc_vc[params_type]["selVC_f"] + calc_vc[params_type]["selVCDHW_f"]
    vc_e[params_type] = calc_vc[params_type]["selVC_e"] + calc_vc[params_type]["selVCDHW_e"]


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

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

def get_fixed_cost_by_key_from_sheet(sheet, search_name, search_value):
    cost1 = get_value_from_sheet(sheet, search_name, search_value, 'cost')
    cost2 = get_value_from_sheet(sheet, search_name, search_value, 'installation_cost')
    if cost2 == "":
        cost2 = 0
    return cost1 + cost2


def get_fixed_cost_by_key_from_sheet_noise(sheet, search_name, search_value, noisematrix):
    org_val = get_fixed_cost_by_key_from_sheet(sheet, search_name, search_value)
    if noisematrix is None:
        return org_val

    if search_name == "heating":
        search_value = search_value.replace(" ", "_")
    elif search_name == "plant_type" and search_value != "electric_boiler":
        search_value = "dhw_" + search_value
    return org_val + noisematrix["costs"]["fixed_costs"][search_value]


def get_electric_cost(sheet, country, year, memo, noisematrix=None):
    noise = get_vc_noise_value(noisematrix, year, "electric_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "electric_energy")), "p" + str(year), memo
    ) / 3.6 + noise

def get_fuel_cost(sheet, country, year, memo, noisematrix=None):
    noise = get_vc_noise_value(noisematrix, year, "fuel_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "methane_gas")), "p" + str(year), memo
    ) / 0.656 / 55500 * 1000 + noise

def get_pellet_cost(sheet, country, year, memo, noisematrix=None):
    noise = get_vc_noise_value(noisematrix, year, "pellet_costs")
    if year == 0:
        year = 1
    return get_value_from_sheet_multi(
        sheet, "variable_costs", (("country", country), ("source", "pellet")), "p" + str(year), memo
    ) / 19000 * 1000 + noise

def get_fixed_cost_from_sheet_by_key(sheet, row):
    cost1 = sheet[row-1]["cost"]
    cost2 = sheet[row-1]["installation_cost"]
    if not is_number(cost2):
        cost2 = 0
    return cost1 + cost2

def get_fixed_cost_from_sheet_by_key_noise(sheet, row, noisematrix, value_type):
    org_val = get_fixed_cost_from_sheet_by_key(sheet, row)
    if noisematrix is None:
        return org_val
    burner_switcher = {
        1: "1-Type B open chamber",
        2: "2-Type C sealed chamber",
        3: "3- Gas/diesel modulating",
        4: "4- Condensing",
        5: "5- Gas/diesel on-off",
        6: "6- Air cooled"
    }
    emitter_switcher = {
        1: "1- Radiators",
        2: "2- Radiators with Valve",
        3: "3- Fan coil",
        4: "4- Floor panels",
        5: "5- Ceiling and wall panels",
        6: "6- Other types"
    }
    dhw_burner_switcher = {
        1: "1- Open chamber centralized",
        2: "2- Sealed chamber autonomous"
    }
    if value_type == "burner_type":
        return  org_val + noisematrix["costs"]["fixed_costs"][burner_switcher[row]]
    elif value_type == "emitter_type":
        return org_val + noisematrix["costs"]["fixed_costs"][emitter_switcher[row]]
    elif value_type == "DHW_burner_type":
        return org_val + noisematrix["costs"]["fixed_costs"][dhw_burner_switcher[row - 1]]

def init_consumi_variables():
    dispersed_heat_values = {}
    dispersed_heat_keys = [
        "q_win", "qsg", "q_floor", "q_roof", "q_v", "q_w", "q_is", "q_dhw", "s_floor_area", "selq_d", "selq_p",
        "selq_f", "selq_e", "selq_s", "selqDHW_d", "selqDHW_p", "selqDHW_f", "selqDHW_e", "selqDHW_s"
    ]
    total_sel_variables = {
        "current_params": dict.fromkeys(dispersed_heat_keys, 0),
        "planned_params": dict.fromkeys(dispersed_heat_keys, 0)
    }
    vc_variables = {}
    vc_keys = ["selVC_f", "selVC_e", "selVCDHW_f", "selVCDHW_e"]
    total_vc_variables = {
        "current_params": dict.fromkeys(vc_keys, 0),
        "planned_params": dict.fromkeys(vc_keys, 0)
    }
    total_costs = {"total_heating_cost": 0, "total_dhw_cost": 0, "cases": []}
    billnew, schurn, sdefau, schurn95, sdefau95 = 0, 0, 0, 0, 0
    # todo: confirm this is correct, put on this scope as it seems this is global in consumi
    fixed_costs = {"heating_cost": 0, "dhw_cost": 0, "t_min": -1000000, "t_med": -1000000}
    return dispersed_heat_values, fixed_costs, schurn, schurn95, sdefau, sdefau95, total_costs, total_sel_variables, total_vc_variables, vc_variables


def get_vals(params_type, heating_loads, appliance_load, pv_result):
    h = heating_loads[params_type]

    # Original outputs (unchanged)
    heating_losses = round(h["selq_d"], 2)
    fuel_demand = round(h["selq_f"] + h["selqDHW_f"], 2)
    elec_demand = round(h["selq_e"] + h["selqDHW_e"] + appliance_load, 2)
    total_demand = round(fuel_demand + elec_demand, 2)

    # New: derive monthly values only if pv_result is provided
    if pv_result is not None and "monthly_production_kWh" in pv_result:
        # Equal monthly split of appliance load
        appliance_monthly = [appliance_load / 12.0] * 12

        # Monthly electric load = heating + DHW + appliance
        monthly_electric_demand = [
            h["selq_e_monthly"][i] +
            h["selqDHW_e_monthly"][i] +
            appliance_monthly[i]
            for i in range(12)
        ]

        # PV monthly production
        pv_monthly = pv_result["monthly_production_kWh"]

        # Net grid electricity per month
        net_grid = [
            monthly_electric_demand[i] - pv_monthly[i]
            for i in range(12)
        ]

        # Bundle monthly results
        elec_monthly = {
            "electric_demand": [round(val, 2) for val in monthly_electric_demand],
            "pv_production": [round(val, 2) for val in pv_monthly],
            "net_grid_electricity": [round(val, 2) for val in net_grid]
        }
    else:
        elec_monthly = None

    # Return original values plus new monthly dictionary
    return heating_losses, fuel_demand, elec_demand, total_demand, elec_monthly



def get_heating_types_helper(heating_and_dhw):
    table1 = heating_and_dhw['table1']
    table3 = heating_and_dhw['table3']
    table1 = table1[slice(len(table1) - 3)]
    burner_types = map(lambda h: h['heating'], table1)
    emitter_types = map(lambda h: h['heatingemittertype'], table3)
    result = {"burner_types": {}, "emitter_types": {}}
    for i, v in enumerate(burner_types):
        result["burner_types"][i + 1] = ' '.join(v.split())
    for i, v in enumerate(emitter_types):
        result["emitter_types"][i + 1] = ' '.join(v.split())
    return result



def get_plant_types_helper1(heating_and_dhw):
    table2 = heating_and_dhw['table2']
    table2 = table2[slice(1, len(table2) - 2)]
    plant_typs = map(lambda h: h['plant_type'], table2)
    result = {}
    for i, v in enumerate(plant_typs):
        result[i + 1] = v
    return result

def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)
