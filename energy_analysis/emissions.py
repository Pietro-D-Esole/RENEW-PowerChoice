def get_emissions_data(case) -> dict:
    # Lookup tables
    emissions_data = [
        {"note": "electricity carbon intensity"},
        {"Italy": 0.230, "Germany": 0.400, "Spain": 0.180, "Lithuania": 0.130, "Ireland": 0.310},
        {"note": "fuel carbon intensity"},
        {"gas": 0.202, "oil": 0.267, "pellet": 0.015}
    ]

    # Fuel mapping based on heating_type index from table1
    heating_type_to_fuel = {
        0: "gas",  # Type 1
        1: "gas",  # Type 2
        2: "oil",  # Type 3
        3: "gas",  # Type 4
        4: "oil",  # Type 5
        5: "gas",  # Type 6
        6: "pellet",  # Pellet stove
        7: "electricity"  # Heat pump
    }

    # Extract parameters from the case
    common = case.get("common_params", {})
    current = case.get("current_params", {})
    planned = case.get("planned_params", {})

    # Get country and electricity carbon intensity
    country = common.get("country")
    if not country:
        raise ValueError("Country must be specified in common_params.")

    electricity_CI = emissions_data[1].get(country)
    if electricity_CI is None:
        raise ValueError(f"Electricity carbon intensity not found for country: {country}")

    # Get current and planned heating types
    current_ht = current.get("heating_type")
    planned_ht = planned.get("heating_type")

    # Get fuel type based on heating_type
    current_fuel = heating_type_to_fuel.get(current_ht)
    planned_fuel = heating_type_to_fuel.get(planned_ht)

    # Get carbon intensity values
    if current_fuel == "electricity":
        current_emissions = electricity_CI
    else:
        current_emissions = emissions_data[3].get(current_fuel, 0)

    if planned_fuel == "electricity":
        planned_emissions = electricity_CI
    else:
        planned_emissions = emissions_data[3].get(planned_fuel, 0)

    return {
        "carbon_intensity": electricity_CI,
        "current_carbon_emissions": current_emissions,
        "planned_carbon_emission": planned_emissions
    }

def calc_operational_emissions(case, elec_c, fuel_c, elec_p, fuel_p) -> dict:
    """
    Calculate operational emissions based on electricity and fuel demands for current and planned scenarios.
    """
    # Get carbon intensity data
    emissions_data = get_emissions_data(case)
    elec_CI = emissions_data["carbon_intensity"]
    cur_CI = emissions_data["current_carbon_emissions"]
    plan_CI = emissions_data["planned_carbon_emission"]

    # Compute current emissions
    ce_current = (
        elec_c * elec_CI +
        fuel_c * cur_CI if cur_CI != elec_CI else elec_c * elec_CI
    )

    # Compute planned emissions
    ce_planned = (
        elec_p * elec_CI +
        fuel_p * plan_CI if plan_CI != elec_CI else elec_p * elec_CI
    )

    return {
        "current_emissions": ce_current,
        "planned_emissions": ce_planned
    }

