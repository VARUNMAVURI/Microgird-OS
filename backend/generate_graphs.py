import matplotlib.pyplot as plt
import numpy as np
import os

# Set output directory to frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'frontend')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ------------------------------------------------------------------
# 1. Bar Chart: Performance Comparison
# ------------------------------------------------------------------
labels = ['Optimization Accuracy', 'Algorithmic Interpretability', 'Grid Integration', 'System Automation', 'User Interface', 'Decision Support']
base_paper = [80, 40, 30, 35, 20, 25]
microgrid = [93, 88, 91, 85, 95, 90]

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
rects1 = ax.bar(x - width/2, base_paper, width, label='Base Paper')
rects2 = ax.bar(x + width/2, microgrid, width, label='Microgrid OS Project')

ax.set_ylabel('Performance Score (0-100)')
ax.set_title('Performance Comparison: Base Paper vs Microgrid OS System')
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=15)
ax.legend()
fig.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig11_10_performance_bar.png'), dpi=300)
plt.close()

# ------------------------------------------------------------------
# 2. Pie Chart: Distribution of Actions
# ------------------------------------------------------------------
labels = ['Charging Battery', 'Discharging Battery', 'Grid Import', 'Grid Export', 'Strategic Hold']
sizes = [40, 20, 15, 10, 15]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

fig, ax = plt.subplots(figsize=(8, 6))
ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors)
ax.axis('equal')
ax.set_title('Distribution of AI-Executed Grid Scheduling Actions')
plt.savefig(os.path.join(OUTPUT_DIR, 'fig11_11_actions_pie.png'), dpi=300)
plt.close()

# ------------------------------------------------------------------
# 3. Line Chart: Accuracy/Efficiency Comparison
# ------------------------------------------------------------------
iterations = [1, 2, 3, 4]
heuristic = [80, 82, 84, 85]
drl = [84, 88, 91, 93]

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(iterations, heuristic, marker='o', label='Heuristic Model')
ax.plot(iterations, drl, marker='o', label='DRL Agent (DQN/PPO)')

ax.set_xlabel('Training Iterations')
ax.set_ylabel('Optimization Efficiency (%)')
ax.set_title('Efficiency Comparison Between Heuristic Algorithm and DRL')
ax.set_xticks(iterations)
ax.grid(True)
ax.legend()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig11_12_efficiency_line.png'), dpi=300)
plt.close()

print("Microgrid OS graphs successfully generated!")
