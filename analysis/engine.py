
import json, logging, re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)
DISCLAIMER = "※ 以下はすべてAIによる推定値です。実際の設定を断定するものではありません。"
LEARN_DB_PATH = Path("data/learning_db.json")

def stars(rate):
    if rate>=80: return "★★★★★"
    elif rate>=60: return "★★★★☆"
    elif rate>=40: return "★★★☆☆"
    elif rate>=20: return "★★☆☆☆"
    else: return "★☆☆☆☆"

def _df(records):
    if not records: return pd.DataFrame()
    df=pd.DataFrame(records)
    if "日付" in df.columns: df["日付"]=pd.to_datetime(df["日付"],errors="coerce")
    for col in ["勝利フラグ","高設定候補フラグ","イベント日","ジャグラー系"]:
        if col in df.columns: df[col]=df[col].astype(bool)
    for col in ["高設定候補スコア","出玉効率","BB確率推定","RB確率推定","台番号数値"]:
        if col in df.columns: df[col]=pd.to_numeric(df[col],errors="coerce")
    return df

def store_summary(df):
    if df.empty: return {"状態":"データなし","免責":DISCLAIMER}
    hi=df["高設定候補フラグ"].mean()*100
    win=df["勝利フラグ"].mean()*100
    return {
        "集計台数":int(len(df)),"高設定候補台数":int(df["高設定候補フラグ"].sum()),
        "高設定候補率_推定":f"{hi:.1f}%","勝率_推定":f"{win:.1f}%",
        "期待度":stars(hi),
        "集計期間":f"{df['日付'].min().date()} ～ {df['日付'].max().date()}",
        "免責":DISCLAIMER,
    }

def model_analysis(df):
    if df.empty or "機種名" not in df.columns: return []
    g=df.groupby("機種名").agg(
        集計台数=("台番号","count"),勝率=("勝利フラグ","mean"),
        高設定候補率=("高設定候補フラグ","mean"),高設定候補台数=("高設定候補フラグ","sum"),
        平均出玉効率=("出玉効率","mean")).reset_index()
    g["勝率_推定"]=(g["勝率"]*100).round(1).astype(str)+"%"
    g["高設定候補率_推定"]=(g["高設定候補率"]*100).round(1).astype(str)+"%"
    g["期待度"]=(g["高設定候補率"]*100).apply(stars)
    g["高設定候補台数"]=g["高設定候補台数"].astype(int)
    return g.drop(columns=["勝率","高設定候補率"]).sort_values("高設定候補台数",ascending=False).to_dict("records")

def machine_analysis(df):
    if df.empty: return []
    g=df.groupby(["台番号","機種名"]).agg(
        勝率=("勝利フラグ","mean"),高設定候補回数=("高設定候補フラグ","sum"),
        稼働日数=("日付","nunique"),平均出玉効率=("出玉効率","mean")).reset_index()
    g["勝率_推定"]=(g["勝率"]*100).round(1).astype(str)+"%"
    g["期待度"]=(g["勝率"]*100).apply(stars)
    g["高設定候補回数"]=g["高設定候補回数"].astype(int)
    return g.drop(columns=["勝率"]).sort_values("高設定候補回数",ascending=False).to_dict("records")

def suffix_analysis(df):
    if df.empty or "末尾" not in df.columns: return []
    g=df.groupby("末尾").agg(
        台数=("台番号","count"),勝率=("勝利フラグ","mean"),
        高設定候補率=("高設定候補フラグ","mean")).reset_index()
    g["勝率_推定"]=(g["勝率"]*100).round(1).astype(str)+"%"
    g["高設定候補率_推定"]=(g["高設定候補率"]*100).round(1).astype(str)+"%"
    g["期待度"]=(g["高設定候補率"]*100).apply(stars)
    return g.drop(columns=["勝率","高設定候補率"]).sort_values("台数",ascending=False).to_dict("records")

def cluster_analysis(df):
    if df.empty: return {"2台並び":[],"3台並び":[],"島":[]}
    results={"2台並び":[],"3台並び":[],"島":[]}
    for (date,model),grp in df.groupby(["日付","機種名"]):
        hi=grp[grp["高設定候補フラグ"]].copy()
        if len(hi)<2: continue
        nums=sorted([int(n) for n in hi["台番号数値"].dropna().tolist()])
        clusters=[]; cur=[nums[0]]
        for n in nums[1:]:
            if n-cur[-1]<=2: cur.append(n)
            else:
                if len(cur)>=2: clusters.append(cur)
                cur=[n]
        if len(cur)>=2: clusters.append(cur)
        date_str=str(date.date()) if hasattr(date,"date") else str(date)
        for c in clusters:
            e={"日付":date_str,"機種名":model,"台番号":str(c),"台数":len(c),"注記":"AI推定"}
            if len(c)==2: results["2台並び"].append(e)
            elif len(c)==3: results["3台並び"].append(e)
            else: results["島"].append(e)
    return results

def weekday_analysis(df):
    if df.empty or "曜日" not in df.columns: return []
    g=df.groupby("曜日").agg(
        台数=("台番号","count"),勝率=("勝利フラグ","mean"),
        高設定候補率=("高設定候補フラグ","mean")).reset_index()
    order={"月":0,"火":1,"水":2,"木":3,"金":4,"土":5,"日":6}
    g["順序"]=g["曜日"].map(order)
    g=g.sort_values("順序").drop(columns=["順序"])
    g["勝率_推定"]=(g["勝率"]*100).round(1).astype(str)+"%"
    g["高設定候補率_推定"]=(g["高設定候補率"]*100).round(1).astype(str)+"%"
    g["期待度"]=(g["高設定候補率"]*100).apply(stars)
    return g.drop(columns=["勝率","高設定候補率"]).to_dict("records")

def event_analysis(df, cfg):
    if df.empty or "イベント日" not in df.columns: return {}
    ev=df[df["イベント日"]]; non=df[~df["イベント日"]]
    def rate(d): return round(d["高設定候補フラグ"].mean()*100,1) if not d.empty else 0
    return {
        "イベント日ラベル":cfg.event_label,
        "イベント日_高設定候補率_推定":f"{rate(ev)}%",
        "通常日_高設定候補率_推定":f"{rate(non)}%",
        "差異_推定":f"{rate(ev)-rate(non):+.1f}%",
        "期待度_イベント日":stars(rate(ev)),
    }

def new_machine_analysis(df, weeks=4):
    if df.empty or "日付" not in df.columns: return []
    cutoff=df["日付"].max()-timedelta(weeks=weeks)
    recent=df[df["日付"]>=cutoff]; older=df[df["日付"]<cutoff]
    new_models=set(recent["機種名"].unique())-set(older["機種名"].unique())
    if not new_models: return []
    new_df=recent[recent["機種名"].isin(new_models)]
    g=new_df.groupby("機種名").agg(
        集計台数=("台番号","count"),高設定候補率=("高設定候補フラグ","mean"),
        勝率=("勝利フラグ","mean"),初登場日=("日付","min")).reset_index()
    g["高設定候補率_推定"]=(g["高設定候補率"]*100).round(1).astype(str)+"%"
    g["勝率_推定"]=(g["勝率"]*100).round(1).astype(str)+"%"
    g["初登場日"]=g["初登場日"].astype(str)
    g["期待度"]=(g["高設定候補率"]*100).apply(stars)
    return g.drop(columns=["高設定候補率","勝率"]).sort_values("初登場日",ascending=False).to_dict("records")

def suggestion_match(df, x_posts):
    if df.empty or not x_posts: return []
    results=[]
    for post in x_posts:
        try:
            post_dt=pd.to_datetime(post.get("投稿日時",""),errors="coerce")
            if pd.isna(post_dt): continue
            next_day=(post_dt+timedelta(days=1)).normalize()
            day_df=df[df["日付"]==next_day]
            if day_df.empty: continue
            kws=[k for k in post.get("全キーワード","").split(",") if k]
            hi_rate=round(day_df["高設定候補フラグ"].mean()*100,1)
            for kw in kws:
                hit=False
                if "末尾" in kw:
                    m=re.search(r"\d",kw)
                    if m:
                        t=day_df[day_df["末尾"]==m.group()]
                        hit=t["高設定候補フラグ"].mean()>=0.3 if not t.empty else False
                elif any(w in kw for w in ["全台","全○","全◯"]):
                    hit=day_df["高設定候補フラグ"].mean()>=0.5
                elif any(w in kw for w in ["高設定","456"]):
                    hit=day_df["高設定候補フラグ"].sum()>=3
                results.append({
                    "投稿日時":str(post_dt.date()),"翌日":str(next_day.date()),
                    "キーワード":kw,"的中":hit,"的中表示":"〇" if hit else "×",
                    "翌日高設定候補率_推定":f"{hi_rate}%",
                    "投稿URL":post.get("投稿URL",""),
                })
        except: pass
    return results

def load_learning_db():
    if LEARN_DB_PATH.exists():
        try: return json.loads(LEARN_DB_PATH.read_text(encoding="utf-8"))
        except: pass
    return {}

def update_learning_db(matches):
    db=load_learning_db()
    for m in matches:
        kw=m["キーワード"]
        if kw not in db: db[kw]={"的中":0,"外れ":0}
        if m["的中"]: db[kw]["的中"]+=1
        else: db[kw]["外れ"]+=1
    LEARN_DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    LEARN_DB_PATH.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding="utf-8")
    return db

def keyword_accuracy(db):
    results=[]
    for kw,s in db.items():
        total=s["的中"]+s["外れ"]
        rate=round(s["的中"]/total*100,1) if total>0 else 0.0
        results.append({"キーワード":kw,"的中回数":s["的中"],"外れ回数":s["外れ"],
            "合計":total,"的中率_推定":f"{rate}%",
            "信頼度":"高(n≥10)" if total>=10 else "中(n≥5)" if total>=5 else "低(サンプル少)",
            "期待度":stars(rate)})
    return sorted(results,key=lambda x:float(x["的中率_推定"].rstrip("%")),reverse=True)

def today_targets(df, x_posts, learning_db, cfg):
    if df.empty: return []
    today=datetime.now()
    today_wd={"Monday":"月","Tuesday":"火","Wednesday":"水","Thursday":"木","Friday":"金","Saturday":"土","Sunday":"日"}.get(today.strftime("%A"),"")
    is_event=today.day in cfg.event_days
    trusted_kws={kw for kw,s in learning_db.items()
        if (s["的中"]+s["外れ"])>=3 and s["的中"]/(s["的中"]+s["外れ"])>=0.6}
    latest_kws=set()
    for p in (x_posts or [])[:5]:
        latest_kws.update(k for k in p.get("全キーワード","").split(",") if k)
    t_grp=df.groupby(["台番号","機種名","末尾"]).agg(
        hi_cnt=("高設定候補フラグ","sum"),win_rate=("勝利フラグ","mean"),
        days=("日付","nunique")).reset_index()
    target_list=[]
    for _,row in t_grp.iterrows():
        days=row["days"] or 1
        score=(row["hi_cnt"]/days)*40
        reasons=[]
        tail=str(row["末尾"])
        tail_df=df[df["末尾"]==tail]
        if not tail_df.empty and tail_df["高設定候補フラグ"].mean()>=0.3:
            score+=10; reasons.append(f"末尾{tail}傾向あり")
        for kw in latest_kws:
            if tail in kw and "末尾" in kw:
                score+=20; reasons.append(f"X示唆「{kw}」"); break
        if is_event: score+=5; reasons.append(cfg.event_label)
        wd_df=df[(df["曜日"]==today_wd)&(df["台番号"]==row["台番号"])]
        if not wd_df.empty and wd_df["高設定候補フラグ"].mean()>=0.4:
            score+=8; reasons.append(f"{today_wd}曜日傾向")
        if not reasons: reasons.append("過去データ統計")
        target_list.append({
            "台番号":str(row["台番号"]),"機種名":str(row["機種名"]),"末尾":tail,
            "スコア_推定":round(score,1),"高設定候補回数":int(row["hi_cnt"]),
            "稼働日数":int(days),"勝率_推定":f"{row['win_rate']*100:.1f}%",
            "期待度":stars(score),"根拠":" / ".join(reasons),
        })
    return sorted(target_list,key=lambda x:x["スコア_推定"],reverse=True)[:20]

def run(records, x_posts, cfg):
    logger.info("分析開始...")
    df=_df(records)
    matches=suggestion_match(df,x_posts)
    learn_db=update_learning_db(matches)
    kw_acc=keyword_accuracy(learn_db)
    targets=today_targets(df,x_posts,learn_db,cfg)
    result={
        "hall":cfg.name,"generated_at":datetime.now().isoformat(),
        "disclaimer":DISCLAIMER,
        "store":store_summary(df),"models":model_analysis(df),
        "machines":machine_analysis(df),"suffixes":suffix_analysis(df),
        "clusters":cluster_analysis(df),"weekdays":weekday_analysis(df),
        "events":event_analysis(df,cfg),"new_machines":new_machine_analysis(df),
        "x_suggestion_matches":matches,"keyword_accuracy":kw_acc,
        "today_targets":targets,
        "record_count":len(records),"x_post_count":len(x_posts),
    }
    logger.info(f"分析完了: {len(records)}件 / 狙い台: {len(targets)}件")
    return result
