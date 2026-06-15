#!/usr/bin/env python3
"""Publication-quality main figure. Equilibrated data only; no exponent claims."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec
from pathlib import Path
try:
    from scipy.stats import beta as beta_dist; HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

ROOT = Path(__file__).resolve().parent.parent
PROD = ROOT/"results"/"production"; FIGS = ROOT/"figures"; FIGS.mkdir(exist_ok=True)
rep  = pd.read_csv(PROD/"sweep_replicates.csv")
summ = pd.read_csv(PROD/"sweep_condition_means.csv")
noises = sorted(summ.noise.unique())

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,
    "axes.titlesize":12,"axes.titleweight":"bold","axes.labelsize":11,
    "axes.linewidth":0.9,"legend.frameon":False})
PAL = {0.3:"#1b6ca8", 0.5:"#e07b39", 0.7:"#6a4c93"}
col = lambda e: PAL.get(e,"0.3")

def boot_ci(x, n=3000, seed=0):
    rng=np.random.default_rng(seed); x=np.asarray(x)
    m=rng.choice(x,size=(n,len(x)),replace=True).mean(1); return np.percentile(m,[2.5,97.5])
ci=(rep.groupby(["noise","sigma_std"])["phi"]
      .apply(lambda s: pd.Series(dict(zip(["lo","hi"],boot_ci(s.values)))))
      .unstack().reset_index())
summ=summ.merge(ci,on=["noise","sigma_std"])

def crossing(d, level=0.90):
    d=d.sort_values("sigma_std"); x,y=d.sigma_std.values,d.phi_mean.values
    for i in range(len(y)-1):
        if y[i]>=level>=y[i+1]:
            t=(y[i]-level)/(y[i]-y[i+1]); return x[i]+t*(x[i+1]-x[i])
    return np.nan
sig_star={e:crossing(summ[summ.noise==e]) for e in noises}

fig=plt.figure(figsize=(13,8)); gs=gridspec.GridSpec(2,3,figure=fig,hspace=0.34,wspace=0.30)
tag=lambda ax,t: ax.text(-0.16,1.05,t,transform=ax.transAxes,fontsize=14,fontweight="bold",va="top")

ax=fig.add_subplot(gs[0,0])
for e in noises:
    d=summ[summ.noise==e].sort_values("sigma_std"); c=col(e)
    ax.fill_between(d.sigma_std,d.lo,d.hi,color=c,alpha=0.18,lw=0)
    ax.plot(d.sigma_std,d.phi_mean,"-o",color=c,lw=2,ms=3.5,mec="white",mew=0.5,label=f"η = {e}")
ax.axhline(0.90,ls=":",color="0.5",lw=1)
ax.set_xlabel("trait dispersion σ"); ax.set_ylabel("order parameter φ")
ax.set_title("Order erodes smoothly"); ax.legend(loc="lower left"); tag(ax,"a")

ax=fig.add_subplot(gs[0,1])
es=[e for e in noises if not np.isnan(sig_star[e])]
ax.plot(es,[sig_star[e] for e in es],"-",color="0.4",lw=1.5,zorder=1)
for e in es: ax.plot(e,sig_star[e],"o",ms=11,color=col(e),mec="white",mew=1,zorder=2)
ax.set_xlabel("noise η"); ax.set_ylabel("tolerated dispersion σ* (φ=0.90)")
ax.set_title("More noise → less tolerance"); ax.set_xlim(min(es)-0.08,max(es)+0.08); tag(ax,"b")

ax=fig.add_subplot(gs[0,2])
for e in noises:
    d=summ[summ.noise==e].sort_values("sigma_std")
    ax.plot(d.sigma_std,d.chi_seed,"-o",color=col(e),ms=3.5,mec="white",mew=0.5,label=f"η = {e}")
ax.set_xlabel("trait dispersion σ"); ax.set_ylabel("susceptibility χ = N·Var(φ)")
ax.set_title("Fluctuations peak at transition"); ax.legend(); tag(ax,"c")

ax=fig.add_subplot(gs[1,0])
for e in noises:
    d=summ[summ.noise==e].sort_values("sigma_std")
    ax.plot(d.sigma_std,d.ar1,"-o",color=col(e),ms=3.5,mec="white",mew=0.5,label=f"η = {e}")
ax.set_xlabel("trait dispersion σ"); ax.set_ylabel("lag-1 autocorrelation")
ax.set_title("Critical slowing down"); ax.legend(loc="lower right"); tag(ax,"d")

ax=fig.add_subplot(gs[1,1])
d5=summ[summ.noise==0.5].sort_values("sigma_std")
ax.plot(d5.sigma_std,100*d5.frac_lo,"-o",color="#c0392b",ms=3.5,mec="white",mew=0.5,label="weakly social (w<0.2)")
ax.plot(d5.sigma_std,100*d5.frac_hi,"-s",color="#27ae60",ms=3.5,mec="white",mew=0.5,label="strongly social (w>0.8)")
ax.set_xlabel("trait dispersion σ"); ax.set_ylabel("% of population (η=0.5)")
ax.set_title("Mechanism: the tails grow"); ax.legend(loc="upper left"); tag(ax,"e")

ax=fig.add_subplot(gs[1,2]); mu=0.7
if HAVE_SCIPY:
    xs=np.linspace(0,1,400)
    for s,cc in zip([0.10,0.30,0.45],["#86c5da","#3a86ff","#1d3557"]):
        v=min(s**2,0.999*mu*(1-mu)); k=mu*(1-mu)/v-1
        ax.plot(xs,beta_dist.pdf(xs,mu*k,(1-mu)*k),color=cc,lw=2,label=f"σ = {s}")
    ax.set_ylim(0,6); ax.set_xlabel("social weight w"); ax.set_ylabel("trait density")
    ax.set_title("Why: high σ splits population"); ax.legend()
else:
    ax.text(0.5,0.5,"(install scipy for this panel)",ha="center",va="center",transform=ax.transAxes); ax.set_axis_off()
tag(ax,"f")

fig.suptitle("Trait dispersion drives a continuous loss of collective order",fontsize=14,fontweight="bold",y=1.00)
fig.savefig(FIGS/"fig_main_v2.png",dpi=300,bbox_inches="tight")
fig.savefig(FIGS/"fig_main_v2.pdf",bbox_inches="tight")
print("  wrote figures/fig_main_v2.png + .pdf  (300 dpi)")
