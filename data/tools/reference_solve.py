import highspy, json, os, sys, time, hashlib, glob
import numpy as np
def run(path, tl):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", tl)
    h.setOptionValue("threads", 1)
    h.setOptionValue("mip_rel_gap", 0.0)
    h.setOptionValue("mip_abs_gap", 1e-9)
    st = h.readModel(path)
    lp = h.getLp()
    nint = sum(1 for t in lp.integrality_ if t != highspy.HighsVarType.kContinuous)
    nnz = lp.a_matrix_.start_[lp.num_col_]
    hess = h.getHessian().dim_ if hasattr(h,'getHessian') else 0
    t0=time.time(); h.run(); dt=time.time()-t0
    ms = h.modelStatusToString(h.getModelStatus())
    info = h.getInfo()
    sense = "min" if lp.sense_==highspy.ObjSense.kMinimize else "max"
    return dict(rows=int(lp.num_row_), cols=int(lp.num_col_), nnz=int(nnz), integers=int(nint),
        q_dim=int(hess), status=ms, objective=float(info.objective_function_value), sense=sense,
        highs_time_s=round(dt,3), nodes=int(info.mip_node_count) if nint else None,
        mip_gap=float(info.mip_gap) if nint else None, dual_bound=float(info.mip_dual_bound) if nint else None,
        iters=int(info.simplex_iteration_count))
out={}
for grp,tl in (("netlib",60),("milp",90),("qp",60)):
    for p in sorted(glob.glob(f"{grp}/*.mps")):
        name=os.path.basename(p)[:-4]
        try:
            r=run(p,tl)
        except Exception as e:
            r=dict(error=str(e))
        r["group"]=grp; r["file"]=p
        r["sha256"]=hashlib.sha256(open(p,'rb').read()).hexdigest()
        out[name]=r
        print(name, grp, r.get("rows"), r.get("cols"), r.get("nnz"), r.get("integers"), r.get("status"), r.get("objective"), r.get("highs_time_s"), flush=True)
json.dump(out, open("/home/claude/ref_raw.json","w"), indent=1)
