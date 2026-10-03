import numpy as np, itertools, highspy, json, time, sys
def build_uc(G,T,seed):
    r=np.random.default_rng(seed)
    Pmax=np.round(r.uniform(60,150,G)); Pmin=np.round(Pmax*r.uniform(0.25,0.4,G))
    a=np.round(r.uniform(80,200,G),1); b=np.round(r.uniform(10,30,G),2); q=np.round(r.uniform(0.02,0.12,G),3)
    st=np.round(r.uniform(100,300,G),1)
    cap=Pmax.sum(); D=np.round(cap*r.uniform(0.45,0.8,T))
    return dict(G=G,T=T,Pmax=Pmax,Pmin=Pmin,a=a,b=b,q=q,st=st,D=D)
def write_uc(m,path,name):
    G,T=m["G"],m["T"]; rows=[]; cols=[]  # cols: (name,kind,lb,ub,cost,entries)
    ent={}; rhs={}; rowtype={}
    def addrow(n,t,rh=0.0): rowtype[n]=t; rhs[n]=rh
    for t in range(T): addrow(f"BAL{t}","E",m["D"][t])
    for g in range(G):
        for t in range(T):
            addrow(f"MAX{g}_{t}","L",0.0); addrow(f"MIN{g}_{t}","G",0.0); addrow(f"SU{g}_{t}","L",0.0 if t>0 else 0.0)
    colspec=[]
    def addcol(n,kind,ub,cost,e): colspec.append((n,kind,ub,cost,e))
    for g in range(G):
        for t in range(T):
            addcol(f"U{g}_{t}","I",1,m["a"][g],{f"MAX{g}_{t}":-m["Pmax"][g],f"MIN{g}_{t}":-m["Pmin"][g],f"SU{g}_{t}":-1.0, **({f"SU{g}_{t+1}":1.0} if t+1<T else {})})
    for g in range(G):
        for t in range(T):
            addcol(f"P{g}_{t}","C",m["Pmax"][g],m["b"][g],{f"BAL{t}":1.0,f"MAX{g}_{t}":1.0,f"MIN{g}_{t}":1.0})
    for g in range(G):
        for t in range(T):
            addcol(f"S{g}_{t}","C",1,m["st"][g],{f"SU{g}_{t}":-1.0})
    # startup: S[g,t] >= U[g,t]-U[g,t-1] -> U[g,t]-U[g,t-1]-S[g,t] <= 0 ; at t=0 assume units start OFF: U-S<=0
    # fix entries: U{g}_{t} appears in SU{g}_{t} with +1 and in SU{g}_{t+1} with -1 (already set -1 above wrongly signed); rebuild cleanly
    colspec=[]
    for g in range(G):
        for t in range(T):
            e={f"MAX{g}_{t}":-m["Pmax"][g],f"MIN{g}_{t}":-m["Pmin"][g],f"SU{g}_{t}":1.0}
            if t+1<T: e[f"SU{g}_{t+1}"]=-1.0
            addcol(f"U{g}_{t}","I",1,m["a"][g],e)
    for g in range(G):
        for t in range(T):
            addcol(f"P{g}_{t}","C",m["Pmax"][g],m["b"][g],{f"BAL{t}":1.0,f"MAX{g}_{t}":1.0,f"MIN{g}_{t}":1.0})
    # MAX: P - Pmax U <= 0 ; MIN: P - Pmin U >= 0 ; both set via entries above (P coeff 1, U coeff -Pmax/-Pmin)
    for g in range(G):
        for t in range(T):
            addcol(f"S{g}_{t}","C",1,m["st"][g],{f"SU{g}_{t}":-1.0})
    with open(path,"w") as f:
        f.write(f"NAME          {name}\nROWS\n N  COST\n")
        for n,t in rowtype.items(): f.write(f" {t}  {n}\n")
        f.write("COLUMNS\n"); inint=False
        for n,k,ub,cost,e in colspec:
            if k=="I" and not inint: f.write("    MARKER                 'MARKER'                 'INTORG'\n"); inint=True
            if k=="C" and inint: f.write("    MARKER                 'MARKER'                 'INTEND'\n"); inint=False
            f.write(f"    {n}  COST  {cost:.10g}\n")
            for rn,v in e.items(): f.write(f"    {n}  {rn}  {v:.10g}\n")
        if inint: f.write("    MARKER                 'MARKER'                 'INTEND'\n")
        f.write("RHS\n")
        for rn,v in rhs.items():
            if v!=0: f.write(f"    RHS  {rn}  {v:.10g}\n")
        f.write("BOUNDS\n")
        for n,k,ub,cost,e in colspec:
            f.write(f" {'BV' if k=='I' else 'UP'} BND  {n}" + ("" if k=="I" else f"  {ub:.10g}") + "\n")
        f.write("QUADOBJ\n")
        for g in range(G):
            for t in range(T): f.write(f"    P{g}_{t}  P{g}_{t}  {m['q'][g]:.10g}\n")
        f.write("ENDATA\n")
    return [c[0] for c in colspec if c[1]=="I"]

def brute(path,ints,tl=5):
    h=highspy.Highs(); h.setOptionValue("output_flag",False); h.readModel(path)
    lp=h.getLp(); name2i={lp.col_names_[i]:i for i in range(lp.num_col_)} if hasattr(lp,'col_names_') else None
    n=lp.num_col_
    # relax integrality: model has integrality flags, which MIQP in HiGHS rejects -> clear
    h.changeColsIntegrality(n,np.arange(n,dtype=np.int32),np.array([highspy.HighsVarType.kContinuous]*n))
    idx=[name2i[x] for x in ints]; best=(None,None); feas=0; t0=time.time()
    for bits in itertools.product((0.0,1.0),repeat=len(idx)):
        for i,bv in zip(idx,bits): h.changeColBounds(i,bv,bv)
        h.run()
        if h.getModelStatus()==highspy.HighsModelStatus.kOptimal:
            feas+=1; v=h.getInfo().objective_function_value
            if best[0] is None or v<best[0]-1e-12: best=(v,bits)
    return best,feas,time.time()-t0
if __name__=="__main__":
    out={}
    for nm,(G,T,seed) in {"uc_miqp_3x4":(3,4,101),"uc_miqp_4x3":(4,3,102)}.items():
        m=build_uc(G,T,seed); ints=write_uc(m,f"miqp/{nm}.mps",nm.upper())
        (v,bits),feas,dt=brute(f"miqp/{nm}.mps",ints)
        out[nm]=dict(binaries=len(ints),brute_force_objective=v,feasible_assignments=feas,assignment=[int(b) for b in bits],bf_time_s=round(dt,1))
        print(nm,out[nm],flush=True)
    json.dump(out,open("/home/claude/miqp_ref.json","w"),indent=1)
