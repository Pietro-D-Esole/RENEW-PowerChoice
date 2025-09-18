# Simplified and complete input module that uses minimal user inputs
# and populates full `case` dictionary from datasets

from support_functions import constants

def choose_option(prompt, options):
    """Display numbered options and return the chosen one."""
    options = list(options)
    print(prompt)
    for i, opt in enumerate(options, start=1):
        print(f"{i}. {opt}")
    while True:
        choice = input("Enter number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Invalid choice, try again.")


def get_available_cities(constants, country=None):
    if country:
        return sorted({row["city"] for row in constants.city_climate if row["country"] == country})
    return sorted({row["city"] for row in constants.city_climate})


def get_valid_input():
    """Interactive CLI input with numbered menus. Returns: case, mc_params."""

    # Allowed options from dataset
    allowed_countries = sorted({entry["country"] for entry in constants.thermal_data})
    allowed_building_years = [
        "<1900", "1901-1920", "1921-1945",
        "1946-1960", "1961-1975", "1976-1990",
        "1991-2005", ">2005"
    ]
    allowed_building_types = sorted({entry["building_type"] for entry in constants.thermal_data})

    # 1️⃣ Country & City
    country = choose_option("Select country:", allowed_countries)
    city = choose_option("Select city:", get_available_cities(constants, country))

    # 2️⃣ Building info
    building_year = choose_option("Select building year:", allowed_building_years)
    building_type = choose_option("Select building type:", allowed_building_types)

    n_dwellings = int(input("Enter dwelling count: "))
    n_floor = int(input("Enter floor count: "))
    s_floor = int(input("Enter floor area (m²): "))

    # 3️⃣ Heating/DHW systems
    print("Heating type options: 1 = gas/diesel burner, 2 = pellet stove, 3 = heat-pump")
    current_heating_type = int(choose_option("Select current heating type:", [1, 2, 3]))
    print("Heating type options: 1 = gas/diesel burner, 2 = pellet stove, 3 = heat-pump")
    planned_heating_type = int(choose_option("Select planned heating type:", [1, 2, 3]))

    emitter_map = {1: 1, 2: 2, 3: 1}
    current_emitter_type = emitter_map.get(current_heating_type, 6)
    planned_emitter_type = emitter_map.get(planned_heating_type, 6)

    print("DHW type options: 1 = electric boiler, 2 = gas burner DHW, 3 = DHW heat-pump")
    current_dhw_type = int(choose_option("Select current DHW type:", [1, 2, 3]))
    print("DHW type options: 1 = electric boiler, 2 = gas burner DHW, 3 = DHW heat-pump")
    planned_dhw_type = int(choose_option("Select planned DHW type:", [1, 2, 3]))

    current_pv_panel = choose_option("Do you have PV panels now?", ["yes", "no"]).lower()
    planned_pv_panels = choose_option("Do you want to install PV panels?", ["yes", "no"]).lower()

    # 4️⃣ Common parameters
    common_params = {
        "mode": 0,
        "dwelling_count": n_dwellings,
        "floor_count": n_floor,
        "n_occupants": 2,
        "country": country,
        "city": city,
        "building_type": building_type,
        "building_year": building_year,
        "floor_area": s_floor,
        "storey_position": "mid",
        "wall_thermal_transmittance": 0,
        "roof_thermal_transmittance": 0,
        "floor_thermal_transmittance": 0,
        "total_surface_area_to_volume_ratio": 0,
        "wall_height": 0,
        "discount_rate": 8,
        "churn_rate": 0,
        "churn_rate_95": 0,
        "default_churn_rate": 0,
        "default_churn_rate_95": 0
    }

    # 5️⃣ Current parameters
    current_params = {
        "heating_type": current_heating_type,
        "burner_type": current_emitter_type,
        "emitter_type": 1,
        "fuel_type": 1,
        "solar_check": 0,
        "solar_perc": 0,
        "DHW_type": current_dhw_type,
        "DHW_burner_type": 1,
        "DHW_solar_check": 0,
        "DHW_solar_perc": 0,
        "wall_insulation_check": 0,
        "roof_insulation_check": 0,
        "floor_insulation_check": 0,
        "wall_envelope_thermal_conductivity": 0.05,
        "wall_thickness": 0.1,
        "roof_envelope_thermal_conductivity": 0.08,
        "roof_thickness": 0.1,
        "floor_envelope_thermal_conductivity": 0.04,
        "floor_thickness": 0.1,
        "window_flag": "",
        "window_transmittance_value": 0,
        "window_to_surface_area_ratio": 0,
        "cooling_system_type": 3,
        "panel_type": 0 if current_pv_panel == "no" else 3,
        "target_pv_fraction": 1,
        "pv_roof_utilization_ratio": 0.7
    }

    # 6️⃣ Planned parameters
    planned_params = {
        "heating_type": planned_heating_type,
        "burner_type": planned_emitter_type,
        "emitter_type": 1,
        "fuel_type": 4,
        "solar_check": 0,
        "solar_perc": 0,
        "DHW_type": planned_dhw_type,
        "DHW_burner_type": 3,
        "DHW_solar_check": 0,
        "DHW_solar_perc": 0,
        "wall_insulation_check": 0,
        "roof_insulation_check": 0,
        "floor_insulation_check": 0,
        "wall_envelope_thermal_conductivity": 0.03,
        "wall_thickness": 0.1,
        "roof_envelope_thermal_conductivity": 0.03,
        "roof_thickness": 0.1,
        "floor_envelope_thermal_conductivity": 0.03,
        "floor_thickness": 0.1,
        "window_flag": "",
        "window_transmittance_value": 0,
        "window_to_surface_area_ratio": 0,
        "cooling_system_type": 3,
        "panel_type": 3 if planned_pv_panels == "yes" else 0,
        "target_pv_fraction": 1,
        "pv_roof_utilization_ratio": 0.7
    }

    # Fill thermal data
    for entry in constants.thermal_data:
        if (entry["country"] == country and
                entry["building_year"] == building_year and
                entry["building_type"] == building_type):
            common_params["wall_height"] = entry.get("height", 0)
            common_params["roof_thermal_transmittance"] = entry.get("roof_trans", 0)
            common_params["wall_thermal_transmittance"] = entry.get("wall_trans", 0)
            common_params["floor_thermal_transmittance"] = entry.get("floor_trans", 0)
            common_params["total_surface_area_to_volume_ratio"] = entry.get("disp_v_ratio", 0)
            current_params["window_transmittance_value"] = entry.get("windows_trans", 0)
            current_params["window_to_surface_area_ratio"] = entry.get("win_floor_ratio", 0)
            planned_params["window_transmittance_value"] = entry.get("windows_trans", 0)
            planned_params["window_to_surface_area_ratio"] = entry.get("win_floor_ratio", 0)
            break

    case = {
        "common_params": common_params,
        "current_params": current_params,
        "planned_params": planned_params
    }

    mc_params = {"uncertainty_advanced_flag": -1, "confidence_level": 95,
                 # ["uncertainty_advanced_flag": -1] used in get_noise is used in an "if" function. The value "-1" makes the "else" blok run, computing the noisematrix
                 "noise_flag": 2, "geometry_noise_check": 1,
                 "pv_panel_noise_check": 1, "pv_panel_confidence": 10,
                 "geometry_confidence": 10, "number_of_monte_carlo_runs": 1500,
                 "thermal_prop_noise_check": 1, "thermal_prop_confidence": 10,
                 "efficiencies_noise_check": 1,
                 "efficiencies_confidence": 5,
                 "simplified_DHW_load_noise_check": 1,
                 "simplified_DHW_load_confidence": 10,
                 "environment_noise_check": 1, "environment_confidence": 20,
                 "investment_noise_check": 1, "investment_confidence": 10,
                 "energy_cost_noise_check": 1, "energy_cost_confidence_today": 1, "energy_cost_confidence_final": 10,
                 "Uwall_noise_check": 1, "Uwall_confidence": 15,
                 "Uroof_noise_check": 1, "Uroof_confidence": 17,
                 "Ufloor_noise_check": 1, "Ufloor_confidence": 18,
                 "Sfloor_noise_check": 1, "Sfloor_confidence": 12,
                 "sd_vol_ratio_noise_check": 1, "sd_vol_ratio_confidence": 7,
                 "wall_height_noise_check": 1, "wall_height_confidence": 5,
                 "Uwindows_noise_check": 1, "Uwindows_confidence": 22,
                 "window_floor_ratio_noise_check": 1,
                 "window_floor_ratio_confidence": 6,
                 "wall_thermal_conductivity_noise_check": 1,
                 "wall_thermal_conductivity_confidence": 7,
                 "wall_thickness_noise_check": 1,
                 "wall_thickness_confidence": 4,
                 "roof_thermal_conductivity_noise_check": 1,
                 "roof_thermal_conductivity_confidence": 3,
                 "roof_thickness_noise_check": 1,
                 "roof_thickness_confidence": 5,
                 "floor_thermal_conductivity_noise_check": 1,
                 "floor_thermal_conductivity_confidence": 8,
                 "floor_thickness_noise_check": 1,
                 "floor_thickness_confidence": 2,
                 "he_conv_noise_check": 1, "he_conv_confidence": 8,
                 "shadow_noise_check": 1, "shadow_confidence": 35,
                 "sun_factor_noise_check": 1, "sun_factor_confidence": 15,
                 "alfa_plaster_noise_check": 1,
                 "alfa_plaster_confidence": 7,
                 "air_change_noise_check": 1, "air_change_confidence": 30,
                 "advanced_DHW_load_noise_check": 1,
                 "advanced_DHW_load_confidence": 7,
                 "regulation_eff_noise_check": 1,
                 "regulation_eff_confidence": 4,
                 "distribution_eff_noise_check": 1,
                 "distribution_eff_confidence": 4,
                 "emission_eff_noise_check": 1,
                 "emission_eff_confidence": 9,
                 "heating_solar_fraction_noise_check": 1,
                 "heating_solar_fraction_confidence": 22,
                 "heating_burner_eff_noise_check": 1,
                 "heating_burner_eff_confidence": 6,
                 "heating_pellet_eff_noise_check": 1,
                 "heating_pellet_eff_confidence": 5,
                 "heating_heat_pump_COP_noise_check": 1,
                 "heating_heat_pump_COP_confidence": 19,
                 "DHW_solar_fraction_noise_check": 1,
                 "DHW_solar_fraction_confidence": 11,
                 "DHW_burner_eff_noise_check": 1,
                 "DHW_burner_eff_confidence": 7,
                 "DHW_electric_boiler_eff_noise_check": 1,
                 "DHW_electric_boiler_eff_confidence": 14,
                 "DHW_heat_pump_COP_noise_check": 1,
                 "DHW_heat_pump_COP_confidence": 12,
                 "HDD_noise_check": 1, "HDD_confidence": 22,
                 "solar_RAD_noise_check": 1, "solar_RAD_confidence": 18,
                 "heating_days_noise_check": 1,
                 "heating_days_confidence": 14,
                 "discount_rate_noise_check": 1,
                 "discount_rate_confidence": 7,
                 "fixed_costs_noise_check": 1, "fixed_costs_confidence": 15,
                 "fuel_cost_noise_check": 1, "fuel_cost_confidence_today": 1, "fuel_cost_confidence_final": 3,
                 "electric_cost_noise_check": 1,
                 "electric_cost_confidence_today": 1, "electric_cost_confidence_final": 6,
                 "pellet_cost_noise_check": 1, "pellet_cost_confidence_today": 1,
                 "pellet_cost_confidence_final": 11,
                 "incentives_check": -1, "incentives_amount_%": 60,
                 "incentives_refund_years": 15,
                 "loan_check": -1, "loan_amount_%": 85,
                 "loan_refund_years": 20, "loan_rate": 5,
                 "time_horizon_years": 25, "min_Epsav": "", "min_Esav": 10,
                 "min_NPV": 1000, "min_IRR": 3, "min_Dpayback": 30,
                 "min_loss_risk": 15,
                 "min_churn_rate": 20, "min_default_rate": 3, "max_Epsav": "",
                 "max_Esav": 75,
                 "max_NPV": 15000, "max_IRR": 17, "max_Dpayback": 11,
                 "max_loss_risk": 5,
                 "max_churn_rate": 5, "max_default_rate": 1, "weight_Epsav": "",
                 "weight_Esav": 2, "weight_NPV": 5, "weight_IRR": 1,
                 "weight_Dpayback": 7, "weight_loss_risk": 3,
                 "weight_churn_rate": 1, "weight_default_rate": 4, "unit_option": "optionkwh"}

    return case, mc_params



