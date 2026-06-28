
import logging, re
from datetime import datetime
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

COL_ALIASES = {
    "日付":   ["日付","date","Date"],
    "機種名": ["機種名","機種","model"],
    "台番号": ["台番号","台番","No"],
    "差枚":   ["差枚","差玉","diff"],
    "G数":    ["G数","スタート","G"],
    "BB":     ["BB","BIG","ビッグ"],
    "RB":     ["RB","REG","バケ"],
    "合算":   ["合算","合成確率"],
}

def _find_col(df, key):
    for alias in COL_ALIASES.get(key, []):
        if alias in df.columns: return alias
    return None

def _to_int(val):
    try:
        s = re.sub(r'[^\d\-]','',str(val))
        return int(s) if s and s!='-' else None
    except: return None

def _to_float(val):
    try:
        s = re.sub(r'[^\d./]','',str(val))
        return float(s) if s else None
    except: return None

def _parse_date(val):
    for fmt in ["%Y-%m-%d","%Y/%m/%d","%m/%d/%Y","%Y%m%d"]:
        try: return datetime.strptime(str(val).strip(),fmt).strftime("%Y-%m-%d")
        except: pass
    return None

def load_csv(path, cfg):
    logger.info(f"CSV読込: {path.name}")
    try:
        if str(path).endswith(('.xlsx','.xls')): df=pd.read_excel(path)
        else: df=pd.read_csv(path,encoding='utf-8-sig')
    except Exception as e:
        logger.error(f"読込エラー: {e}"); return []
    col={k:_find_col(df,k) for k in COL_ALIASES}
    records=[]
    for _,row in df.iterrows():
        try:
            date_str=_parse_date(row[col['日付']]) if col['日付'] else None
            model=str(row[col['機種名']] if col['機種名'] else '').strip()
            mno_raw=str(row[col['台番号']] if col['台番号'] else '').strip()
            if not date_str or not model or not mno_raw: continue
            diff=_to_int(row[col['差枚']]) if col['差枚'] else None
            games=_to_int(row[col['G数']]) if col['G数'] else None
            bb=_to_int(row[col['BB']]) if col['BB'] else None
            rb=_to_int(row[col['RB']]) if col['RB'] else None
            combined=_to_float(row[col['合算']]) if col['合算'] else None
            num_m=re.search(r'\d+',mno_raw)
            mno_num=int(num_m.group()) if num_m else None
            tail=str(mno_num)[-1] if mno_num else None
            weekday_jp={"Monday":"月","Tuesday":"火","Wednesday":"水","Thursday":"木","Friday":"金","Saturday":"土","Sunday":"日"}.get(datetime.strptime(date_str,"%Y-%m-%d").strftime("%A"),"")
            day_num=int(date_str.split('-')[2])
            is_event=day_num in cfg.event_days
            is_juggler=any(k in model for k in cfg.juggler_keywords)
            efficiency=round(diff/games,4) if diff is not None and games and games>0 else None
            bb_rb_ratio=round(bb/rb,2) if bb and rb and rb>0 else None
            reg_prob=round(games/rb,1) if rb and games and rb>0 else None
            # ジャグラー専用スコアリング（REG・合算重視）
            if is_juggler:
                score=0; reasons=[]
                if games and games>=cfg.juggler_hi_min_games: score+=1; reasons.append(f"{games}G")
                if reg_prob and reg_prob<=cfg.juggler_hi_max_reg: score+=2; reasons.append(f"REG1/{reg_prob:.0f}")
                if combined and combined<=cfg.juggler_hi_max_combined: score+=1; reasons.append(f"合算1/{combined:.0f}")
                if diff and diff>0: score+=1; reasons.append(f"+{diff}枚")
                if bb_rb_ratio and bb_rb_ratio<=cfg.juggler_hi_max_bb_rb: score+=1; reasons.append(f"BB/REG={bb_rb_ratio:.1f}")
                hi_flag=score>=cfg.juggler_hi_min_score
            else:
                # スマスロ専用スコアリング（差枚・G数重視）
                score=0; reasons=[]
                if games and games>=cfg.sumasuro_hi_min_games: score+=1; reasons.append(f"{games}G")
                if diff and diff>=cfg.sumasuro_hi_min_diff: score+=2; reasons.append(f"+{diff}枚")
                if combined and combined<=130: score+=1; reasons.append(f"合算1/{combined:.0f}")
                hi_flag=score>=cfg.sumasuro_hi_min_score
            records.append({
                "日付":date_str,"曜日":weekday_jp,"イベント日":is_event,
                "機種名":model,"台番号":mno_raw,"台番号数値":mno_num,"末尾":tail,
                "ジャグラー系":is_juggler,"勝利フラグ":bool(diff and diff>0),
                "高設定候補フラグ":hi_flag,
                "高設定候補スコア":score,"高設定候補根拠":",".join(reasons),
                "差枚":diff,"G数":games,"BB":bb,"RB":rb,"合算推定":combined,
                "出玉効率":efficiency,"BB_RB比率":bb_rb_ratio,
                "BB確率推定":round(games/bb,1) if bb and games and bb>0 else None,
                "RB確率推定":reg_prob,
                "ホール":cfg.name,
            })
        except Exception as e: logger.debug(f"行スキップ: {e}")
    logger.info(f"  → {len(records)}件"); return records

def load_hall_data(hall_name, cfg):
    from pathlib import Path
    data_dir=Path(f"data/{cfg.data_dir}")
    data_dir.mkdir(parents=True,exist_ok=True)
    files=sorted(data_dir.glob("*.csv"))+sorted(data_dir.glob("*.xlsx"))
    if not files:
        logger.warning(f"[{hall_name}] CSVなし: {data_dir} に配置してください")
        return []
    all_records=[]
    for f in files:
        if f.name.startswith("sample_"): continue
        all_records.extend(load_csv(f,cfg))
    logger.info(f"[{hall_name}] 合計{len(all_records)}件")
    return all_records
