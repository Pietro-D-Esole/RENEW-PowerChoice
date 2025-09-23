#from test_case import mc_params, case
from energy_analysis.models import  calculate, estimate_appliance_load
from support_functions.help_functions import init_consumi_variables, get_vals
from energy_analysis.heating_systems import heating_efficiency
from energy_analysis.PV import size_pv_system
from financial_analysis.Financial import calculate_costs,get_maintenance_cost, estimate_annual_energy_bills, calculate_npv, calculate_payback_periods, calculate_irr, calculate_profitability_index
from energy_analysis.emissions import calc_operational_emissions
from probablistic_approach.mc import generate_noise
from support_functions.print import generate_summary, print_energy_summary_with_bounds, print_cost_summary_with_bounds, print_financial_summary_with_bounds, plot_discounted_cumulative_cash_flow, plot_monthly_energy_vs_pv
from support_functions.input_module import get_valid_input
from support_functions import constants

case, mc_params = get_valid_input()
#print(case)
cases = [case]

year = 0
vita = 20
memo = {}
report = {}

final_results = {
    "curr_heat_loss": [], "plan_heat_loss": [],
    "curr_fuel_demand": [], "plan_fuel_demand": [],
    "curr_electricity_demand": [], "plan_electricity_demand": [],
    "curr_total_demand": [], "plan_total_demand": [],
    "curr_pv_production": [], "plan_pv_production": [],
    "curr_NET_electricity_load": [], "plan_NET_electricity_load": [],
    "curr_fuel_bills": [], "plan_fuel_bills": [],
    "curr_electricity_bills": [], "plan_electricity_bills": [],
    "curr_expenses": [], "plan_expenses": [],
    "investment": [],
    "npv": [],
    "irr": [],
    "simple_pp": [],
    "discounted_pp": [],
    "cash_flow": [],
    "discounted_cash_flow": [],
    "cumulative_cash_flow": [],  # list of lists (length = n_runs, each element is a list of 20 years)
    "cumulative_discounted_cash_flow": [],
    "curr_emissions": [], "plan_emissions": [],
    "plan_monthly_fuel_demand": [],           # list of 12-month lists (these three for plotting)
    "plan_monthly_electricity_demand": [],    # list of 12-month lists
    "plan_monthly_pv_production": []          # list of 12-month lists
}


n_runs = 1000

for run in range(n_runs):
    #noisematrix = None
    noisematrix = generate_noise(cases, constants, mc_params, vita, year)
    #print(noisematrix)

    #Engineering Analysis
    dispersed_heat_values, fixed_costs, schurn, schurn95, sdefau, sdefau95, total_costs, total_sel_variables, total_vc_variables, vc_variables = init_consumi_variables()

    heating_loads = heating_efficiency(case, constants, noisematrix, year)

    vc_e, vc_f, vc_separated = {}, {}, {}
    for params_type in ["current_params", "planned_params"]:
        params = case[params_type]
        # heating_loads[params_type] = {} # commented for debugging
        # # cdec = calc_dispersed_eff_current
        # cdec = heating_loads[params_type]
        # validate_case_parameters(params)  # modifies params
        # # dhr = dispersed_heat_result
        dhr = calculate(params, case, constants, noisematrix, params_type, year)
        #print(f"{params_type} heat losses: {dhr}")
        # rper = read_param_eff(params, case, constants, params_type, noisematrix, year)
        # # print(f"{params_type} param efficiencies {rper}")
        appliance_load = estimate_appliance_load(case, params_type)
        # # print(f"appliance electricity load: {appliance_load}")
        pv_result = size_pv_system(case, constants, params_type, dispersed_heat_values, total_sel_variables, total_vc_variables, vc_variables, year, noisematrix)
        #print(f"{params_type} PV results: ", pv_result)
        if params_type == "planned_params":
            pv_investment = pv_result['total_cost_eur']
        # Get heating + electricity demand values
        heat_loss, fuel_demand, elec_demand, total_demand, elec_monthly = get_vals(params_type, heating_loads, appliance_load, pv_result)
        #print(f"{params_type} net electricity results: ", elec_monthly["net_grid_electricity"])
        if params_type == "current_params":
            curr_heat_loss = heat_loss
            curr_fuel_demand = fuel_demand
            curr_elec_demand = elec_demand
            curr_total_demand = total_demand
        else:
            plan_heat_loss = heat_loss
            plan_fuel_demand = fuel_demand
            plan_elec_demand = elec_demand
            plan_total_demand = total_demand
            plan_pv = pv_result
            pv_prod = round(plan_pv.get("total_annual_production_kWh", 0), 2)
            #net_elec_after_pv = round(plan_elec_demand - pv_prod, 2)
            net_elec_after_pv = round(sum(elec_monthly["net_grid_electricity"]), 2)
            h = heating_loads["planned_params"]

            monthly_fuel = [h["selq_f_monthly"][i] + h["selqDHW_f_monthly"][i] for i in range(12)]
            monthly_elec = elec_monthly["electric_demand"]
            monthly_pv = elec_monthly["pv_production"]

            final_results["plan_monthly_fuel_demand"].append(monthly_fuel)
            final_results["plan_monthly_electricity_demand"].append(monthly_elec)
            final_results["plan_monthly_pv_production"].append(monthly_pv)

    op_emissions = calc_operational_emissions(case, curr_elec_demand, curr_fuel_demand, plan_elec_demand, net_elec_after_pv)
    curr_emissions = round(op_emissions["current_emissions"], 2)
    plan_emissions = round(op_emissions["planned_emissions"], 2)


    for params_type in ["current_params", "planned_params"]:
        # === Maintenance cost
        maintenance = get_maintenance_cost(case, params_type, constants)

        if params_type == "current_params":
            elec_kwh = curr_elec_demand
        else:
            elec_kwh = elec_monthly["net_grid_electricity"]

        # === Energy bills
        fuel_bill, electric_bill, total_bill, monthly_bills = estimate_annual_energy_bills(
            case, params_type, heating_loads, elec_kwh, year, constants, memo, noisematrix)

        #print("Monthly:", monthly_bills)
        #print("Sum of months:", sum(monthly_bills))
        #print("Reported electric bill:", electric_bill)

        # === Total expenses (maintenance + energy)
        annual_costs = maintenance + total_bill
        if params_type == "planned_params":
            annual_costs += 100  # perfect control cost

        if params_type == "current_params":
            curr_fuel_bill = fuel_bill
            curr_elec_bill = electric_bill
            curr_annual_bill = total_bill
            curr_annual_costs = annual_costs
        else:
            plan_fuel_bill = fuel_bill
            plan_elec_bill = electric_bill
            plan_annual_bill = total_bill
            plan_annual_costs = annual_costs


    #Financial Analysis
    heating_dhw_investment = calculate_costs(case["current_params"], case["planned_params"], case["common_params"],
                                             constants, plan_heat_loss, report, case, noisematrix, year)
    total_investment = heating_dhw_investment['heating_cost'] + heating_dhw_investment['dhw_cost'] + pv_investment
    #print(f"heating_cost: {heating_dhw_investment['heating_cost']:.2f}, dhw_cost: {heating_dhw_investment['dhw_cost']:.2f}, " f"pv investment: {pv_investment} total investment: {total_investment}")
    npv, cash_flow, discounted_cash_flow, cumulative_flow, cumulative_disc_flow = calculate_npv(case,vita, curr_annual_costs, plan_annual_costs, total_investment)
    simple_pp, discounted_pp = calculate_payback_periods(total_investment, cash_flow, discounted_cash_flow)
    irr_result = calculate_irr(cash_flow, total_investment)
    pi = calculate_profitability_index(discounted_cash_flow, total_investment)

    # Attach scalar results
    final_results["curr_heat_loss"].append(curr_heat_loss)
    final_results["plan_heat_loss"].append(plan_heat_loss)

    final_results["curr_fuel_demand"].append(curr_fuel_demand)
    final_results["plan_fuel_demand"].append(plan_fuel_demand)

    final_results["curr_electricity_demand"].append(curr_elec_demand)
    final_results["plan_electricity_demand"].append(plan_elec_demand)

    final_results["curr_total_demand"].append(curr_total_demand)
    final_results["plan_total_demand"].append(plan_total_demand)

    final_results["curr_pv_production"].append(0.0)  # No PV in current
    final_results["plan_pv_production"].append(pv_prod)

    final_results["curr_NET_electricity_load"].append(curr_elec_demand)
    final_results["plan_NET_electricity_load"].append(net_elec_after_pv)

    final_results["curr_fuel_bills"].append(curr_fuel_bill)
    final_results["plan_fuel_bills"].append(plan_fuel_bill)

    final_results["curr_electricity_bills"].append(curr_elec_bill)
    final_results["plan_electricity_bills"].append(plan_elec_bill)

    final_results["curr_expenses"].append(curr_annual_costs)
    final_results["plan_expenses"].append(plan_annual_costs)

    final_results["investment"].append(total_investment)
    final_results["npv"].append(npv)
    final_results["irr"].append(irr_result)
    final_results["simple_pp"].append(simple_pp)
    final_results["discounted_pp"].append(discounted_pp)

    # List of 20-year cash flows
    final_results["cash_flow"].append(cash_flow)
    final_results["discounted_cash_flow"].append(discounted_cash_flow)
    final_results["cumulative_cash_flow"].append(cumulative_flow)
    final_results["cumulative_discounted_cash_flow"].append(cumulative_disc_flow)

    # Emissions (from previously added function)
    final_results["curr_emissions"].append(curr_emissions)
    final_results["plan_emissions"].append(plan_emissions)


# === Generate statistical summary from final_results ===
summary = generate_summary(final_results)

# === Print energy-related results with confidence bounds ===
print_energy_summary_with_bounds(summary)

# === Print energy cost summary with confidence bounds ===
print_cost_summary_with_bounds(summary)

# === Print financial indicators (NPV, IRR, Payback, etc.) ===
print_financial_summary_with_bounds(summary)

plot_discounted_cumulative_cash_flow(summary, final_results, vita)

plot_monthly_energy_vs_pv(final_results)




