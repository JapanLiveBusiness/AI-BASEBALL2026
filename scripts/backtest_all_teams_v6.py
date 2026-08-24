#!/usr/bin/env python3
"""V4 all-team comparison: A pre-season, B leaky upper-bound, C rolling point-in-time."""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

BASE = ["elo_diff", "prev_win_diff", "prev_rd_diff", "rest_diff", "home_adv"]
ROLL = ["win5_diff", "win10_diff", "rd5_diff", "rd10_diff", "off10_diff", "def10_diff", "h2h_diff"]
FUTURE = ["final_win_diff", "final_rd_diff"]
CAT = ["home", "away", "venue", "month"]

def official_ranges(path):
    rows=json.loads(Path(path).read_text(encoding="utf-8")); out={}
    for y in [2024,2025,2026]:
        d=[pd.Timestamp(x["date"]) for x in rows if int(x.get("season",0))==y and x.get("game_type") in {"regular","interleague"}]
        if d: out[y]=(min(d),max(d))
    return out

def load_games(path, ranges):
    df=pd.DataFrame(json.loads(Path(path).read_text(encoding="utf-8")))
    df["date"]=pd.to_datetime(df.date); df["season"]=df.date.dt.year
    df=df[df.apply(lambda r: r.season in ranges and ranges[r.season][0] <= r.date <= ranges[r.season][1],axis=1)].copy()
    df=df.sort_values(["date","home","away"]).drop_duplicates(["date","home","away"],keep="last")
    df["margin"]=df.home_score-df.away_score
    df["target"]=np.where(df.margin>0,1,np.where(df.margin<0,0,np.nan))
    return df.dropna(subset=["target"]).reset_index(drop=True)

def mean(xs,n,default):
    xs=list(xs)[-n:]; return float(np.mean(xs)) if xs else default

def features(df):
    final={}
    for (s,t),g in pd.concat([
        df[["season","home","home_score","away_score"]].rename(columns={"home":"team","home_score":"rf","away_score":"ra"}),
        df[["season","away","away_score","home_score"]].rename(columns={"away":"team","away_score":"rf","home_score":"ra"})
    ]).groupby(["season","team"]):
        final[(s,t)]=(float((g.rf>g.ra).mean()),float((g.rf-g.ra).mean()))
    hist=defaultdict(list); elo=defaultdict(lambda:1500.0); h2h=defaultdict(list); out=[]
    for _,g in df.iterrows():
        h,a=g.home,g.away; hs=hist[(g.season,h)]; as_=hist[(g.season,a)]
        hp=final.get((g.season-1,h),(.5,0)); ap=final.get((g.season-1,a),(.5,0))
        pair=h2h[(h,a)]; hf=final[(g.season,h)]; af=final[(g.season,a)]
        last_h=hist[("all",h)][-1]["date"] if hist[("all",h)] else None
        last_a=hist[("all",a)][-1]["date"] if hist[("all",a)] else None
        rest_h=min((g.date-last_h).days,14) if last_h is not None else 4
        rest_a=min((g.date-last_a).days,14) if last_a is not None else 4
        row=g.to_dict(); row.update({
            "month":str(g.date.month),"home_adv":1.0,"elo_diff":elo[h]-elo[a],
            "prev_win_diff":hp[0]-ap[0],"prev_rd_diff":hp[1]-ap[1],"rest_diff":rest_h-rest_a,
            "win5_diff":mean([x["win"] for x in hs],5,.5)-mean([x["win"] for x in as_],5,.5),
            "win10_diff":mean([x["win"] for x in hs],10,.5)-mean([x["win"] for x in as_],10,.5),
            "rd5_diff":mean([x["rd"] for x in hs],5,0)-mean([x["rd"] for x in as_],5,0),
            "rd10_diff":mean([x["rd"] for x in hs],10,0)-mean([x["rd"] for x in as_],10,0),
            "off10_diff":mean([x["rf"] for x in hs],10,3.5)-mean([x["rf"] for x in as_],10,3.5),
            "def10_diff":mean([x["ra"] for x in as_],10,3.5)-mean([x["ra"] for x in hs],10,3.5),
            "h2h_diff":mean(pair,10,.5)-.5,"final_win_diff":hf[0]-af[0],"final_rd_diff":hf[1]-af[1]})
        out.append(row)
        win=float(g.margin>0); rec_h={"date":g.date,"win":win,"rd":g.margin,"rf":g.home_score,"ra":g.away_score}
        rec_a={"date":g.date,"win":1-win,"rd":-g.margin,"rf":g.away_score,"ra":g.home_score}
        hs.append(rec_h); as_.append(rec_a); hist[("all",h)].append(rec_h); hist[("all",a)].append(rec_a)
        # 対戦履歴は球場が逆になっても、現在のホーム球団視点で参照する。
        h2h[(h,a)].append(win); h2h[(a,h)].append(1-win)
        expected=1/(1+10**((elo[a]-elo[h]-35)/400)); change=20*(win-expected); elo[h]+=change; elo[a]-=change
    return pd.DataFrame(out)

def models(nums):
    linprep=ColumnTransformer([("n",Pipeline([("i",SimpleImputer(strategy="median")),("s",StandardScaler())]),nums),
                               ("c",Pipeline([("i",SimpleImputer(strategy="most_frequent")),("o",OneHotEncoder(handle_unknown="ignore"))]),CAT)])
    treeprep=ColumnTransformer([("n",SimpleImputer(strategy="median"),nums),
                                ("c",Pipeline([("i",SimpleImputer(strategy="most_frequent")),("o",OrdinalEncoder(handle_unknown="use_encoded_value",unknown_value=-1))]),CAT)])
    return (Pipeline([("p",linprep),("m",LogisticRegression(C=.3,max_iter=3000))]),
            Pipeline([("p",treeprep),("m",HistGradientBoostingClassifier(max_iter=180,max_leaf_nodes=15,min_samples_leaf=25,l2_regularization=2,random_state=42))]))

def logit(p):
    p=np.clip(np.asarray(p),1e-5,1-1e-5); return np.log(p/(1-p)).reshape(-1,1)

def run_variant(data,name,nums):
    tr=data[data.season==2024]; va=data[data.season==2025].copy(); te=data[data.season==2026].copy(); X=nums+CAT
    lin,tree=models(nums); lin.fit(tr[X],tr.target.astype(int)); tree.fit(tr[X],tr.target.astype(int))
    pl=lin.predict_proba(va[X])[:,1]; pt=tree.predict_proba(va[X])[:,1]
    best=min([(brier_score_loss(va.target,.05*i*pl+(1-.05*i)*pt),.05*i) for i in range(21)])
    w=best[1]; raw=w*pl+(1-w)*pt; cal=LogisticRegression(C=1e6,max_iter=2000).fit(logit(raw),va.target.astype(int))
    pv=cal.predict_proba(logit(raw))[:,1]
    threshold=max([(balanced_accuracy_score(va.target,(pv>=t).astype(int)),t) for t in np.arange(.4,.651,.005)])[1]
    conf=np.maximum(pv,1-pv); hit=((pv>=threshold).astype(int)==va.target.to_numpy())
    choices=[(hit[conf>=t].mean(),int((conf>=t).sum()),t) for t in np.arange(.6,.851,.01) if (conf>=t).sum()>=40]
    if choices:
        qualified=[x for x in choices if x[0]>=.75]
        ct=max(qualified,key=lambda x:x[1])[2] if qualified else max(choices,key=lambda x:(x[0],x[1]))[2]
    else:
        # 2025年の高信頼サンプルが40件未満なら、恣意的に80%を作らず厳選を無効化。
        ct=1.01
    lin,tree=models(nums); both=pd.concat([tr,va]); lin.fit(both[X],both.target.astype(int)); tree.fit(both[X],both.target.astype(int))
    rawt=w*lin.predict_proba(te[X])[:,1]+(1-w)*tree.predict_proba(te[X])[:,1]; p=cal.predict_proba(logit(rawt))[:,1]
    te["prob_home"]=p; te["prediction"]=(p>=threshold).astype(int); te["confidence"]=np.maximum(p,1-p); te["selected"]=te.confidence>=ct
    te["hit"]=te.prediction==te.target.astype(int); te["variant"]=name
    selected=te[te.selected]
    summary={"variant":name,"games":len(te),"accuracy":te.hit.mean()*100,"brier":brier_score_loss(te.target,p),
             "logloss":log_loss(te.target,p),"home_predictions":int(te.prediction.sum()),"away_predictions":int((1-te.prediction).sum()),
             "selected_games":len(selected),"selected_accuracy":selected.hit.mean()*100 if len(selected) else np.nan,
             "blend_linear":w,"decision_threshold":threshold,"confidence_threshold":ct}
    return te,summary

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--games",default="data/all_games_2024_2026.json")
    ap.add_argument("--hawks",default="data/hawks_games_starter_history_corrected.json"); ap.add_argument("--out",default="data")
    a=ap.parse_args(); ranges=official_ranges(a.hawks); data=features(load_games(a.games,ranges)); out=Path(a.out); out.mkdir(exist_ok=True)
    variants={"V4-A_prior":BASE,"V4-C_rolling":BASE+ROLL,"V4-B_future_leaky":BASE+ROLL+FUTURE}; summaries=[]
    for name,nums in variants.items():
        pred,s=run_variant(data,name,nums); pred.to_csv(out/f"{name}.csv",index=False,encoding="utf-8-sig"); summaries.append(s)
    report=pd.DataFrame(summaries)
    baseline=float(report.loc[report.variant=="V4-A_prior","accuracy"].iloc[0])
    report["accuracy_vs_prior"]=report.accuracy-baseline
    report["production_eligible"]=report.variant!="V4-B_future_leaky"
    eligible=report[report.production_eligible].sort_values(["accuracy","brier"],ascending=[False,True])
    recommended=eligible.iloc[0].variant
    report["recommended_from_final_test"]=report.variant==recommended
    report=report.sort_values("accuracy",ascending=False)
    report.to_csv(out/"v4_model_comparison.csv",index=False,encoding="utf-8-sig")
    print("公式戦・引分除外:",data.groupby("season").size().to_dict()); print(report.to_string(index=False))
    print(f"\n本番候補（A/Cのみ）: {recommended}")
    print("注意: V4-Bは未来情報漏洩モデルであり、差分確認専用・本番採用不可。")

if __name__=="__main__": main()
