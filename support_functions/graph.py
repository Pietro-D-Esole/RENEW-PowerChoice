import matplotlib.pyplot as plt
import numpy as np

# Data
interventions = ['HS', 'Envelope', 'Both']
investment = [10361.77, 20252.73, 29139.24]
npv = [12279.18, 8470.27, 6338.26]
monthly_savings = [170.24, 207.62, 259.04]
pbp = [6, 12, 15]
energy_savings = [32500.00, 27028.57, 35548.57]

# Figure and axis setup
fig, ax1 = plt.subplots(figsize=(10, 6))

# Bar chart for Investment and NPV
x = np.arange(len(interventions))  # positions for groups
bar_width = 0.35  # width of the bars
ax1.bar(x - bar_width/2, investment, bar_width, label='Investment (€)', color='blue', alpha=0.7)
ax1.bar(x + bar_width/2, npv, bar_width, label='NPV (€)', color='green', alpha=0.7)

# Labels and axis configuration
ax1.set_xlabel('Retrofit Type', fontsize=12)
ax1.set_ylabel('Cost (€)', fontsize=12)
ax1.set_xticks(x)
ax1.set_xticklabels(interventions)
ax1.legend(loc='upper left')
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Twin axis for additional data
ax2 = ax1.twinx()
ax2.plot(x, monthly_savings, label='Monthly Savings (€)', color='orange', marker='o', linestyle='--', linewidth=2)
ax2.plot(x, pbp, label='PBP (years)', color='red', marker='s', linestyle='-.', linewidth=2)
ax2.plot(x, energy_savings, label='Energy Savings (kWh)', color='purple', marker='^', linestyle='-', linewidth=2)
ax2.set_ylabel('Savings / Payback Period', fontsize=12)

# Combined legends
fig.legend(loc='upper center', ncol=5, fontsize=10, bbox_to_anchor=(0.5, 1.1))

# Title and layout adjustments
plt.title('Comparison of Retrofit Interventions', fontsize=14)
plt.tight_layout()
plt.show()
