
def generate_summary(final_results):
    import numpy as np

    def summarize_stat(series):
        arr = np.array(series)
        return {
            "mean": round(np.mean(arr), 2),
            "p5": round(np.percentile(arr, 5), 2),
            "p95": round(np.percentile(arr, 95), 2)
        }

    summary = {}
    for key, vals in final_results.items():
        # Filter out None (e.g., failed IRRs or Paybacks)
        filtered = [x for x in vals if isinstance(x, (int, float, np.floating))]

        if len(filtered) == 0:
            summary[key] = {"mean": None, "p5": None, "p95": None}
            #print(f"[WARN] No valid numerical data for key: {key}")
        else:
            if len(filtered) < len(vals):
                print(f"[INFO] Skipped {len(vals) - len(filtered)} non-numeric entries for: {key}")
            summary[key] = summarize_stat(filtered)

    return summary



def print_energy_summary_with_bounds(summary):
    print("\n================ FINAL ENERGY SUMMARY (MC Stats) ================\n")
    print(f"{'Metric':<35}{'Current (Mean [P5–P95])':>30}{'Planned (Mean [P5–P95])':>30}")
    print("-" * 95)

    def fmt(key):
        if key not in summary:
            return "-"
        s = summary[key]
        return f"{s['mean']:>8.0f} [{s['p5']:>5.0f}–{s['p95']:>5.0f}]"

    print(f"{'Heating losses (selq_d)':<35}{fmt('curr_heat_loss'):>30}{fmt('plan_heat_loss'):>30}")
    print(f"{'Total fuel demand':<35}{fmt('curr_fuel_demand'):>30}{fmt('plan_fuel_demand'):>30}")
    print(f"{'Total electricity demand':<35}{fmt('curr_electricity_demand'):>30}{fmt('plan_electricity_demand'):>30}")
    print(f"{'Total energy demand':<35}{fmt('curr_total_demand'):>30}{fmt('plan_total_demand'):>30}")
    print(f"{'PV annual production':<35}{'-':>30}{fmt('plan_pv_production'):>30}")
    print(f"{'Net electricity after PV':<35}{'-':>30}{fmt('plan_NET_electricity_load'):>30}")
    print(f"{'Emissions (kg CO2eq)':<35}{fmt('curr_emissions'):>30}{fmt('plan_emissions'):>30}")
    print("=" * 95)


def print_cost_summary_with_bounds(summary):
    print("\n================= SCENARIO ENERGY COST SUMMARY =================\n")
    print(f"{'Scenario':<20}{'Fuel Bill (€)':>20}{'Electric Bill (€)':>25}{'Total Expenses (€)':>30}")
    print("-" * 95)

    def fmt(k): s = summary.get(k, None); return f"{s['mean']:>8.0f} [{s['p5']:>5.0f}–{s['p95']:>5.0f}]" if s else "-"

    print(f"{'Current':<20}{fmt('curr_fuel_bills'):>20}{fmt('curr_electricity_bills'):>25}{fmt('curr_expenses'):>30}")
    print(f"{'Planned':<20}{fmt('plan_fuel_bills'):>20}{fmt('plan_electricity_bills'):>25}{fmt('plan_expenses'):>30}")
    print("=" * 95)


def print_financial_summary_with_bounds(summary):
    print("\n================== FINANCIAL SUMMARY ==================\n")

    def fmt(key, suffix=""):
        s = summary.get(key)
        if not s or s["mean"] is None or s["p5"] is None or s["p95"] is None:
            return "-"
        return f"{s['mean']:,.2f} [{s['p5']:,.2f}–{s['p95']:,.2f}]{suffix}"

    print(f"{'Investment:':35} €{fmt('investment')}")
    print(f"{'Net Present Value (NPV):':35} €{fmt('npv')}")
    print(f"{'Internal Rate of Return (IRR):':35} {fmt('irr', '%')}")
    print(f"{'Simple Payback Period:':35} {fmt('simple_pp', ' years')}")
    print(f"{'Discounted Payback Period:':35} {fmt('discounted_pp', ' years')}")
    print("=" * 60)


# Helper to get the highest density interval (hdi)
def hdi_range(data, cred_mass=0.95):
    """Return the shortest interval containing cred_mass of the data."""
    import numpy as np
    sorted_data = np.sort(data)
    n_data = len(sorted_data)
    interval_idx_inc = int(np.floor(cred_mass * n_data))
    n_intervals = n_data - interval_idx_inc
    interval_width = sorted_data[interval_idx_inc:] - sorted_data[:n_intervals]
    min_idx = np.argmin(interval_width)
    return sorted_data[min_idx], sorted_data[min_idx + interval_idx_inc]


def plot_discounted_cash_flow(summary, final_results, vita=20):
    import numpy as np
    import matplotlib.pyplot as plt

    flows = final_results.get("discounted_cash_flow", [])
    if not flows:
        print("No discounted cash flow data available.")
        return

    flows_array = np.array(flows)  # Shape: (n_runs, vita)
    mean_cf = np.mean(flows_array, axis=0)

    # Compute HDI for each year
    hdi_low, hdi_high = [], []
    for i in range(flows_array.shape[1]):
        low, high = hdi_range(flows_array[:, i], 0.95)
        hdi_low.append(low)
        hdi_high.append(high)

    years = np.arange(1, vita + 1)

    plt.figure(figsize=(10, 6))
    plt.plot(years, mean_cf, label="Expected Value", color="blue", linewidth=2)
    plt.fill_between(years, hdi_low, hdi_high, color="blue", alpha=0.2, label="95% HDI Range")
    plt.axhline(0, color="black", linewidth=1, linestyle="--")
    plt.title("Discounted Cash Flow Over Time (Monte Carlo Summary)")
    plt.xlabel("Year")
    plt.ylabel("Discounted Cash Flow (€)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_discounted_cumulative_cash_flow(summary, final_results, vita):
    import numpy as np
    import matplotlib.pyplot as plt

    flows = final_results.get("cumulative_discounted_cash_flow", [])
    if not flows:
        print("No cumulative discounted cash flow data available.")
        return

    flows_array = np.array(flows)  # Shape: (n_runs, vita)
    mean_cf = np.mean(flows_array, axis=0)

    # Compute HDI for each year
    hdi_low, hdi_high = [], []
    for i in range(flows_array.shape[1]):
        low, high = hdi_range(flows_array[:, i], 0.95)
        hdi_low.append(low)
        hdi_high.append(high)

    years = np.arange(1, vita + 1)

    plt.figure(figsize=(10, 6))
    plt.plot(years, mean_cf, label="Expected Cumulative Value", color="green", linewidth=2)
    plt.fill_between(years, hdi_low, hdi_high, color="green", alpha=0.2, label="95% HDI Range")
    plt.axhline(0, color="black", linewidth=1, linestyle="--")
    plt.title("Cumulative Discounted Cash Flow Over Time (Monte Carlo Summary)")
    plt.xlabel("Year")
    plt.ylabel("Cumulative Discounted Cash Flow (€)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()





def plot_monthly_energy_vs_pv(final_results):
    import matplotlib.pyplot as plt
    import numpy as np

    # === Extract and average Monte Carlo results ===
    fuel_arr = np.array(final_results["plan_monthly_fuel_demand"])        # shape (n_runs, 12)
    elec_arr = np.array(final_results["plan_monthly_electricity_demand"]) # shape (n_runs, 12)
    pv_arr   = np.array(final_results["plan_monthly_pv_production"])      # shape (n_runs, 12)

    fuel_avg = np.mean(fuel_arr, axis=0)
    elec_avg = np.mean(elec_arr, axis=0)
    pv_avg   = np.mean(pv_arr, axis=0)

    months = np.arange(12)
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    bar_width = 0.6

    fig, ax = plt.subplots(figsize=(12, 7))

    # === Upper bars: energy demand (stacked) ===
    bar1 = ax.bar(months, fuel_avg, bar_width, label="Fuel Demand", color="#D95F02")
    bar2 = ax.bar(months, elec_avg, bar_width, bottom=fuel_avg, label="Electricity Demand", color="#1B9E77")

    # === Lower bars: PV production (mirrored) ===
    ax.bar(months, -pv_avg, bar_width, label="PV Production", color="#7570B3", alpha=0.75)

    # === Formatting ===
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(months)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Energy (kWh)")
    ax.set_title("Monthly Energy Consumption vs. PV Production (Avg over MC Runs)")

    # Add legend above
    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.12))

    # Add gridlines
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.show()


