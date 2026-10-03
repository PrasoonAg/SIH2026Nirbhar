import numpy as np, itertools, os, highspy, json, re, collections
rng=np.random.default_rng(26119)

def read_mps(p):
    d=dict(name="",rows=[],cols=collections.OrderedDict(),rhs={},bounds=[],ranges={},obj=None)
    sec=None
    for ln in open(p):
        if ln.startswith('*') or not ln.strip(): continue
        w=ln.split()
        if not ln[0].isspace():
            sec=w[0]
            if sec=="NAME": d["name"]=w[1] if len(w)>1 else ""
            continue
        if sec=="ROWS":
            d["rows"].append((w[0],w[1]))
            if w[0]=="N" and d["obj"] is None: d["obj"]=w[1]
        elif sec=="COLUMNS":
            col=w[0]; d["cols"].setdefault(col,[])
            for i in range(1,len(w),2): d["cols"][col].append((w[i],float(w[i+1])))
        elif sec=="RHS":
            for i in range(1,len(w),2) if len(w)%2==1 else range(0,len(w),2): d["rhs"][w[i]]=float(w[i+1])
        elif sec=="RANGES":
            for i in range(1,len(w),2): d["ranges"][w[i]]=float(w[i+1])
        elif sec=="BOUNDS":
            d["bounds"].append(w)
    return d

def write_mps(d,p,name=None):
    with open(p,'w') as f:
        f.write(f"NAME          {name or d['name']}\nROWS\n")
        for t,n in d["rows"]: f.write(f" {t}  {n}\n")
        f.write("COLUMNS\n")
        for c,ent in d["cols"].items():
            for r,v in ent: f.write(f"    {c}  {r}  {v:.12g}\n")
        f.write("RHS\n")
        for r,v in d["rhs"].items(): f.write(f"    RHS  {r}  {v:.12g}\n")
        if d["ranges"]:
            f.write("RANGES\n")
            for r,v in d["ranges"].items(): f.write(f"    RNG  {r}  {v:.12g}\n")
        if d["bounds"]:
            f.write("BOUNDS\n")
            for b in d["bounds"]:
                f.write("  "+"  ".join(b)+"\n")
        f.write("ENDATA\n")

def solve(p, tl=30):
    h=highspy.Highs(); h.setOptionValue("output_flag",False); h.setOptionValue("time_limit",tl)
    h.readModel(p); h.run()
    return h.modelStatusToString(h.getModelStatus()), h.getInfo().objective_function_value

# ---- rescaled copies (S2): row factors r_i, col factors s_j in [1e-6,1e6], objective row untouched
def rescale(src,dst,seed,lo=-6,hi=6):
    r=np.random.default_rng(seed)
    d=read_mps(src); obj=d["obj"]
    rf={n:(1.0 if n==obj else 10**r.uniform(lo,hi)) for _,n in d["rows"]}
    cf={c:10**r.uniform(lo,hi) for c in d["cols"]}
    for c,ent in list(d["cols"].items()):
        d["cols"][c]=[(rn,v*(rf[rn])*cf[c]) for rn,v in ent]
    d["rhs"]={rn:v*rf[rn] for rn,v in d["rhs"].items()}
    d["ranges"]={rn:v*rf[rn] for rn,v in d["ranges"].items()}
    nb=[]
    for b in d["bounds"]:
        t=b[0]
        if t in("FR","MI","PL","BV"): nb.append(b)
        else:
            col=b[2]; val=float(b[3])/cf[col]; nb.append([t,b[1],col,f"{val:.12g}"])
    d["bounds"]=nb
    write_mps(d,dst,name=d["name"]+"_RESC")
for nm,seed in (("afiro",1),("adlittle",2),("sc50a",3),("kb2",4)):
    for tag,(lo,hi) in (("1e3",(-3,3)),("1e6",(-6,6))):
        rescale(f"netlib/{nm}.mps",f"stress/{nm}_rescaled_{tag}.mps",seed,lo,hi)

# ---- Beale cycling LP (known optimum -1.25)
open("stress/beale_cycling.mps","w").write("""NAME          BEALE
ROWS
 N  COST
 E  R1
 E  R2
 E  R3
COLUMNS
    X1        R1        1
    X2        R2        1
    X3        R3        1
    X4        COST      -0.75
    X4        R1        0.25
    X4        R2        0.5
    X5        COST      20
    X5        R1        -8
    X5        R2        -12
    X6        COST      -0.5
    X6        R1        -1
    X6        R2        -0.5
    X6        R3        1
    X7        COST      6
    X7        R1        9
    X7        R2        3
RHS
    RHS       R3        1
ENDATA
""")
# ---- tiny infeasible and unbounded
open("infeas/tiny_infeasible.mps","w").write("""NAME          TINYINF
ROWS
 N  COST
 L  C1
 G  C2
 L  C3
COLUMNS
    X         COST      1
    X         C1        1
    X         C2        1
    X         C3        1
    Y         COST      1
    Y         C1        1
    Y         C2        1
RHS
    RHS       C1        4
    RHS       C2        7
    RHS       C3        1
ENDATA
""")
open("infeas/tiny_unbounded.mps","w").write("""NAME          TINYUNB
ROWS
 N  COST
 G  C1
COLUMNS
    X         COST      -1
    X         C1        1
    Y         COST      -1
    Y         C1        -1
RHS
    RHS       C1        1
ENDATA
""")

# ---- QPs: LP + convex Q (QUADOBJ upper triangle, objective = c'x + 1/2 x'Qx)
def make_qp(src,dst,kind,seed):
    r=np.random.default_rng(seed)
    d=read_mps(src); cols=list(d["cols"])
    n=len(cols); q=[]
    if kind=="diag":
        for j,c in enumerate(cols):
            if r.random()<0.6: q.append((c,c,float(np.round(r.uniform(0.05,2.0),4))))
    else:  # sparse PSD: Q = L L^T, L sparse n x k
        k=max(3,n//4); L=np.zeros((n,k))
        for j in range(k):
            idx=r.choice(n,size=min(4,n),replace=False); L[idx,j]=np.round(r.uniform(-1,1,len(idx)),3)
        Q=L@L.T
        for i in range(n):
            for j in range(i,n):
                if abs(Q[i,j])>1e-9: q.append((cols[i],cols[j],float(np.round(Q[i,j],6))))
    write_mps(d,dst)
    with open(dst,'r') as f: txt=f.read()
    txt=txt.replace("ENDATA\n","QUADOBJ\n"+"".join(f"    {a}  {b}  {v:.12g}\n" for a,b,v in q)+"ENDATA\n")
    open(dst,'w').write(txt)
    return len(q)
os.makedirs("qp",exist_ok=True)
nq={}
nq["afiro_qp_diag"]=make_qp("netlib/afiro.mps","qp/afiro_qp_diag.mps","diag",11)
nq["sc50a_qp_diag"]=make_qp("netlib/sc50a.mps","qp/sc50a_qp_diag.mps","diag",12)
nq["share2b_qp_diag"]=make_qp("netlib/share2b.mps","qp/share2b_qp_diag.mps","diag",13)
nq["adlittle_qp_sparse"]=make_qp("netlib/adlittle.mps","qp/adlittle_qp_sparse.mps","sparse",14)
nq["kb2_qp_sparse"]=make_qp("netlib/kb2.mps","qp/kb2_qp_sparse.mps","sparse",15)
json.dump(nq,open("/home/claude/nq.json","w"))
for f in sorted(os.listdir("stress")):
    print("stress",f,solve("stress/"+f))
for f in sorted(os.listdir("infeas")): print("infeas",f,solve("infeas/"+f))
for f in sorted(os.listdir("qp")): print("qp",f,solve("qp/"+f))
