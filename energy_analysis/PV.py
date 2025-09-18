
from energy_analysis.heating_systems import heating_efficiency
from support_functions.help_functions import get_solar_climate
from models import estimate_appliance_load
import support_functions.constants


def calculate_monthly_pv_output(ghi, monthly_temp, panel_params):
    area = panel_params["area_m2"]
    eta = panel_params["efficiency"]
    pr = panel_params["performance_ratio"] #+get_noise_value
    gamma = panel_params["power_temp_coeff"]

    monthly_output_kWh = []
    for i in range(len(monthly_temp)):
        temp_effect = 1 + gamma * (monthly_temp[i] - 25)
        output = ghi[i] * area * eta * pr * temp_effect
        monthly_output_kWh.append(output)

    return monthly_output_kWh




def get_panel(panel_type, constants):
    """
    Return the panel dictionary based on the panel_type index.
    If panel_type == 0 or out of range, return None to indicate no panel installed.
    """
    try:
        if panel_type == 0:
            return None  # No PV installed
        panels = constants.heating_dhw["table_5"]
        return panels[panel_type - 1]  # panel_type is 1-based index
    except (IndexError, AttributeError, TypeError):
        print(f"Invalid panel_type: {panel_type}. Returning no panel.")
        return None



def size_pv_system(case, constants, params_type, dispersed_heat_values, total_sel_variables,
                   total_vc_variables, vc_variables, year, noisematrix):
    panel_type = case[params_type].get("panel_type", 0)
    panel_params = get_panel(panel_type, constants)
    dwelling_count = case["common_params"]["dwelling_count"]
    target_fraction = case[params_type]["target_pv_fraction"]
    roof_utilization_ratio = case[params_type]["pv_roof_utilization_ratio"]

    if panel_params is None or target_fraction == 0:
        return {
            "n_panels": 0,
            "monthly_production_kWh": [0] * 12,
            "total_annual_production_kWh": 0,
            "total_cost_eur": 0,
            "annual_maintenance_cost_eur": 0,
            "total_panel_area_m2": 0,
            "peak_price_per_wp": 0
        }


    # Constants

    # Select planned or current electricity consumption
    l = heating_efficiency(case, constants, noisematrix, year)
    h = l[params_type]
    appliance_load = estimate_appliance_load(case, params_type)
    elec_demand = round(h["selq_e"] + h["selqDHW_e"] + appliance_load, 2)

    # Panel and building data
    floor_area = case["common_params"]['floor_area'] * dwelling_count
    usable_roof_area = floor_area * roof_utilization_ratio

    # Monthly irradiance & temp

    monthly_ghi, monthly_temp = get_solar_climate(case, constants)
    # Apply tilt gain (25% more for 35° tilt)
    tilt_gain = 1.25
    monthly_ghi = [g * tilt_gain for g in monthly_ghi]

    # Ensure it's a list
    monthly_ghi = list(monthly_ghi)
    monthly_temp = list(monthly_temp)

    # PV output per panel
    monthly_output_per_panel = calculate_monthly_pv_output(monthly_ghi, monthly_temp, panel_params)
    yearly_output_per_panel = sum(monthly_output_per_panel)

    # Target energy and required panels
    target_annual_energy = elec_demand * target_fraction

    # Manual ceil (without math.ceil)
    n_panels = int(target_annual_energy // yearly_output_per_panel)
    if target_annual_energy % yearly_output_per_panel > 0:
        n_panels += 1

    # Panel area check
    total_panel_area = n_panels * panel_params['area_m2']
    max_panels = int(usable_roof_area // panel_params['area_m2'])

    if total_panel_area > usable_roof_area:
        # Adjust number of panels to fit the available roof area
        n_panels = max_panels
        total_panel_area = n_panels * panel_params['area_m2']

    # Max panels that can fit on roof

    if n_panels > max_panels:
        n_panels = max_panels  # Adjust down if roof can't fit them

    # Multiply each month by number of panels
    total_annual_production = [val * n_panels for val in monthly_output_per_panel]

    # Costs
    total_cost = n_panels * (panel_params['cost'] + panel_params['installation_cost'])
    annual_maintenance_cost = n_panels * panel_params['maintenance_cost']

    total_wp = n_panels * panel_params["wp_rating"]
    peak_price_per_wp = total_cost / total_wp  # €/Wp

    return {
        "n_panels": n_panels,
        "monthly_production_kWh": total_annual_production,
        "total_annual_production_kWh": sum(total_annual_production),
        "total_cost_eur": total_cost,
        "annual_maintenance_cost_eur": annual_maintenance_cost,
        "total_panel_area_m2": total_panel_area,
        "peak_price_per_wp": peak_price_per_wp
    }



