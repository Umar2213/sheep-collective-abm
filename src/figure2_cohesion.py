import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib as mpl
import os

mpl.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 9,
    'axes.labelsize': 10, 'axes.titlesize': 10,
    'legend.fontsize': 9, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
    'axes.spines.top': False, 'axes.spines.right': False,
})

df = pd.read_csv('/home/umar/sheep_collective/results/MASTER_all_experiments.csv', encoding='utf-8')
df.columns = ['sigma_std','phi_mean','phi_sd','n','noise','experiment']

df_05 = df[df['noise']==0.5].copy()
df_05 = df_05.sort_values(['sigma_std','n'],ascending=[True,False])
df_05 = df_05.drop_duplicates(subset='sigma_std',keep='first').sort_values('sigma_std')

df_e3 = df[df['experiment']=='exp3'].copy()
colors  = {0.3:'#1976D2', 0.5:'#F57C00', 0.7:'#C62828'}
markers = {0.3:'o',       0.5:'s',       0.7:'^'}
labels  = {0.3:'η = 0.3 (low)', 0.5:'η = 0.5 (medium)', 0.7:'η = 0.7 (high)'}

fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.4))
fig.subplots_adjust(wspace=0.42)

ax = axes[0]
ax.errorbar(df_05['sigma_std'],df_05['phi_mean'],yerr=df_05['phi_sd'],
            color='#1976D2',marker='o',markersize=5,linewidth=1.8,
            capsize=3,capthick=1.2,elinewidth=0.9,label='η = 0.5',zorder=3)
ax.axvspan(0.30,0.35,alpha=0.13,color='red',label='Critical threshold')
ax.axhline(0.9,color='grey',linewidth=0.8,linestyle=':',alpha=0.6)
ax.text(0.325,0.28,'threshold',fontsize=7,color='red',ha='center',style='italic')
ax.set_xlabel('Personality diversity (σ)')
ax.set_ylabel('Flock cohesion (φ)')
ax.set_title('A   Full diversity sweep  (η = 0.5)')
ax.set_ylim(0.25,1.05)
ax.set_xlim(-0.01,0.47)
ax.legend(loc='lower left',frameon=False)

ax = axes[1]
for eta in [0.3,0.5,0.7]:
    sub = df_e3[df_e3['noise']==eta].sort_values('sigma_std')
    ax.errorbar(sub['sigma_std'],sub['phi_mean'],yerr=sub['phi_sd'],
                color=colors[eta],marker=markers[eta],markersize=5,
                linewidth=1.8,capsize=3,capthick=1.2,elinewidth=0.9,
                label=labels[eta],zorder=3)
ax.set_xlabel('Personality diversity (σ)')
ax.set_ylabel('Flock cohesion (φ)')
ax.set_title('B   Noise × diversity interaction')
ax.set_ylim(0.25,1.05)
ax.set_xlim(-0.01,0.47)
ax.legend(loc='lower left',frameon=False)

fig.suptitle('Personality diversity and environmental noise shape flock cohesion',fontsize=10,y=1.01)
os.makedirs('/home/umar/sheep_collective/figures',exist_ok=True)
for ext in ['png','pdf']:
    path = f'/home/umar/sheep_collective/figures/figure2.{ext}'
    fig.savefig(path,bbox_inches='tight',dpi=300)
    print(f'Saved -> {path}')
print('Done.')
