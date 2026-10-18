"""Create a landscape Gantt PDF using the roster's real clock and task colors."""
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch

COLORS={'סיור':'#e6a13e','ש״ג':'#7564aa','כרמל':'#238f8b'}

def build_timeline_pdf(config,result):
    if not result or 'shifts' not in result:raise ValueError('No solved roster')
    people=[p['id'] for p in config['people']]
    hours=int(config['hours']);clock=int(result.get('start_clock_hour',(6+int(config.get('start_offset_hours',0)))%24))
    fig,ax=plt.subplots(figsize=(16,max(6,len(people)*0.32+2)))
    for index,p in enumerate(people):
        for shift in result['shifts']:
            if p not in shift['soldiers']:continue
            start=float(shift['start']);duration=float(shift['end']-shift['start'])
            ax.broken_barh([(start,duration)],(index-0.38,0.76),facecolors=COLORS[shift['task']],edgecolors='white',linewidth=0.25)
    for t in range(hours+1):
        if (clock+t)%24==0:ax.axvline(t,color='#64748b',lw=1.3,ls='--',alpha=0.7)
        if (clock+t)%24==6:ax.axvline(t,color='#cbd5e1',lw=0.7,ls=':')
    # Shade true clock-night windows, independent of start offset.
    for t in range(hours):
        if 0<=(clock+t)%24<6:ax.axvspan(t,t+1,color='#64748b',alpha=0.075,zorder=-2)
    ticks=list(range(0,hours+1,2));ax.set_xticks(ticks)
    ax.set_xticklabels([f'{(clock+t)%24:02d}:00' for t in ticks],rotation=55,ha='right',fontsize=7)
    ax.set_xlim(0,hours);ax.set_ylim(-0.7,len(people)-0.3);ax.invert_yaxis()
    ax.set_yticks(range(len(people)));ax.set_yticklabels(people,fontsize=8)
    ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
    ax.set_title('Duty Planner | Personnel activity timeline',fontsize=15,weight='bold',pad=18)
    ax.set_xlabel(f'Clock time (left to right) | {hours}-hour timeline | starts {clock:02d}:00')
    ax.legend(handles=[Patch(facecolor=v,label={'סיור':'Patrol','ש״ג':'Gate','כרמל':'Carmel'}[k]) for k,v in COLORS.items()],loc='upper center',bbox_to_anchor=(.5,1.04),ncol=3,frameon=False)
    fig.tight_layout(rect=[0,0,1,.96]);out=BytesIO()
    with PdfPages(out) as pdf:pdf.savefig(fig,bbox_inches='tight')
    plt.close(fig)
    return out.getvalue()
