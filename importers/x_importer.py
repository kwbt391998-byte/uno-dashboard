
import base64, logging, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from config.suggestion_dict import extract_keywords

logger = logging.getLogger(__name__)

def _ai_suggest(text):
    if not text: return ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=100,
            system="パチスロ店の公式X投稿から設定示唆を50文字以内で要約。断定は避けて。",
            messages=[{"role":"user","content":text[:300]}])
        return msg.content[0].text if msg.content else ""
    except: return ""

def fetch_x_posts(username, days=7):
    token = os.environ.get("X_BEARER_TOKEN","")
    if not token:
        logger.warning("X_BEARER_TOKEN未設定"); return []
    try:
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {token}"
        r = s.get(f"https://api.twitter.com/2/users/by/username/{username}",timeout=10)
        if r.status_code!=200: return []
        uid = r.json()["data"]["id"]
        start=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        r2=s.get(f"https://api.twitter.com/2/users/{uid}/tweets",
            params={"max_results":50,"start_time":start,
                    "tweet.fields":"created_at,text"},timeout=15)
        if r2.status_code!=200: return []
        results=[]
        for tw in r2.json().get("data",[]):
            text=tw.get("text","")
            kws=list({k for _,k in extract_keywords(text)})
            results.append({
                "投稿日時":tw.get("created_at",""),
                "投稿URL":f"https://x.com/{username}/status/{tw['id']}",
                "本文":text,
                "示唆キーワード":",".join(kws),"OCRキーワード":"",
                "AI推定示唆":_ai_suggest(text),"全キーワード":",".join(kws),
            })
        logger.info(f"X API: {len(results)}件"); return results
    except Exception as e:
        logger.error(f"X APIエラー: {e}"); return []

def load_x_csv(hall_data_dir):
    csv_dir=Path(f"data/{hall_data_dir}/x_posts")
    csv_dir.mkdir(parents=True,exist_ok=True)
    files=list(csv_dir.glob("*.csv"))
    if not files: return []
    import pandas as pd
    records=[]
    for f in files:
        try:
            df=pd.read_csv(f,encoding="utf-8-sig")
            for _,row in df.iterrows():
                url=str(row.get("投稿URL",row.get("url",""))).strip()
                dt=str(row.get("投稿日時","")).strip()
                note=str(row.get("メモ",row.get("note",""))).strip()
                if not url: continue
                kws=list({k for _,k in extract_keywords(note)})
                records.append({
                    "投稿日時":dt,"投稿URL":url,
                    "本文":note,
                    "示唆キーワード":",".join(kws),"OCRキーワード":"",
                    "AI推定示唆":_ai_suggest(note) if note else "",
                    "全キーワード":",".join(kws),
                })
        except Exception as e: logger.error(f"X CSV読込エラー: {e}")
    logger.info(f"X手動CSV: {len(records)}件"); return records
