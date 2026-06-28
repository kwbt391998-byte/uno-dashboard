
import logging, time
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
DISCLAIMER = "⚠️ このシートの数値はすべてAIによる推定値です。実際の設定を断定するものではありません。"
SHEETS = {
    "today":"⭐ 今日の狙い","store":"🏪 店舗全体","model":"🎰 機種別",
    "machine":"🔢 台番号別","suffix":"🔢 末尾別","cluster":"🔗 並び分析",
    "weekday":"📅 曜日別","event":"🎉 イベント日","new":"🆕 新台",
    "model_win":"🏆 機種別勝率",
    "x_kw":"🐦 X示唆KW","matches":"🎯 示唆照合","accuracy":"📈 的中率",
    "log":"📝 実行ログ","guide":"📖 使い方",
}

def _client(sa_file):
    creds=Credentials.from_service_account_file(sa_file,scopes=SCOPES)
    return gspread.authorize(creds)

def _ensure(ss):
    existing={ws.title:ws for ws in ss.worksheets()}
    sheets={}
    for key,name in SHEETS.items():
        if name not in existing:
            ws=ss.add_worksheet(title=name,rows=3000,cols=25); time.sleep(0.4)
        else: ws=existing[name]
        sheets[key]=ws
    return sheets

def _write(ws, rows):
    ws.clear(); time.sleep(0.3)
    if rows: ws.update("A1",rows); time.sleep(0.5)

def _dict_rows(records):
    if not records: return [["データなし"]]
    headers=list(records[0].keys())
    return [headers]+[[str(r.get(h,"")) for h in headers] for r in records]

def _write_today(ws, targets, hall):
    tomorrow=(datetime.now()+timedelta(days=1)).strftime("%Y/%m/%d")
    rows=[[f"⭐ {hall} — 明日の狙い台 AI推定 ({tomorrow})"],[DISCLAIMER],
          ["更新",datetime.now().strftime("%Y/%m/%d %H:%M")],[""],
          ["順位","台番号","機種名","末尾","スコア","高設定候補回数","稼働日数","勝率_推定","期待度","根拠"]]
    for i,t in enumerate(targets,1):
        rows.append([i,t["台番号"],t["機種名"],t["末尾"],t["スコア_推定"],
                     t["高設定候補回数"],t["稼働日数"],t["勝率_推定"],t["期待度"],t["根拠"]])
    _write(ws,rows)

def _write_guide(ws, hall):
    rows=[[f"📖 {hall} AIホール分析システム — 使い方"],[""],
          ["⚠️ 免責事項"],[DISCLAIMER],[""],
          ["シート","内容"],
          ["⭐ 今日の狙い","明日の推奨台・機種（AI推定スコア順）"],
          ["🏪 店舗全体","集計台数・勝率・高設定候補率"],
          ["🎰 機種別","機種ごとの期待度ランキング"],
          ["🔢 台番号別","台番号ごとの高設定候補回数"],
          ["🔢 末尾別","末尾数字ごとの傾向"],
          ["🔗 並び分析","2台・3台・島の並びパターン"],
          ["📅 曜日別","曜日ごとの傾向"],
          ["🎉 イベント日","イベント日 vs 通常日の比較"],
          ["🆕 新台","最近登場した機種の分析"],
          ["🐦 X示唆KW","Xから抽出したキーワード"],
          ["🎯 示唆照合","X示唆 × 翌日結果の照合"],
          ["📈 的中率","キーワード別の過去的中率（AI学習）"],
          ["📝 実行ログ","毎日の実行履歴"],[""],
          ["📥 データ入力方法"],
          ["アナスロデータ","手動でCSVをdata/yuurakucho_uno/に配置"],
          ["X投稿","X APIまたはdata/yuurakucho_uno/x_posts/に手動CSV"]]
    _write(ws,rows)

def push(spreadsheet_id, analysis, x_posts, sa_file="service_account.json"):
    logger.info("スプレッドシート書き込み開始...")
    client=_client(sa_file)
    ss=client.open_by_key(spreadsheet_id)
    ws=_ensure(ss)
    hall=analysis.get("hall","")
    _write_guide(ws["guide"],hall)
    _write_today(ws["today"],analysis.get("today_targets",[]),hall)
    store=analysis.get("store",{})
    _write(ws["store"],[["項目","値"]]+[[k,str(v)] for k,v in store.items()])
    _write(ws["model"],_dict_rows(analysis.get("models",[])))
    _write(ws["model_win"],_dict_rows(analysis.get("model_wins",[])))
    _write(ws["machine"],_dict_rows(analysis.get("machines",[])))
    _write(ws["suffix"],_dict_rows(analysis.get("suffixes",[])))
    _write(ws["weekday"],_dict_rows(analysis.get("weekdays",[])))
    ev=analysis.get("events",{})
    _write(ws["event"],[["項目","値"]]+[[k,str(v)] for k,v in ev.items()])
    _write(ws["new"],_dict_rows(analysis.get("new_machines",[])))
    clusters=analysis.get("clusters",{})
    cluster_rows=[["種類","日付","機種名","台番号","台数"]]
    for kind,items in clusters.items():
        for c in items:
            cluster_rows.append([kind,c["日付"],c["機種名"],c["台番号"],c["台数"]])
    _write(ws["cluster"],cluster_rows)
    x_rows=[["投稿日時","投稿URL","示唆KW","OCR_KW","AI推定示唆"]]
    for p in x_posts:
        x_rows.append([p.get("投稿日時",""),p.get("投稿URL",""),
            p.get("示唆キーワード",""),p.get("OCRキーワード",""),p.get("AI推定示唆","")])
    _write(ws["x_kw"],x_rows)
    _write(ws["matches"],_dict_rows(analysis.get("x_suggestion_matches",[])))
    _write(ws["accuracy"],_dict_rows(analysis.get("keyword_accuracy",[])))
    try:
        existing=ws["log"].get_all_values() or [["日時","ステータス","メッセージ"]]
        existing.append([datetime.now().strftime("%Y/%m/%d %H:%M:%S"),"OK",
            f"{hall}: データ{analysis.get('record_count',0)}件"])
        _write(ws["log"],existing[-300:])
    except Exception as e: logger.error(f"ログ書き込みエラー: {e}")
    logger.info(f"✅ スプレッドシート更新完了")
    logger.info(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
