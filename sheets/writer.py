
import logging, time
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
DISCLAIMER = "⚠️ このシートの数値はすべてAIによる推定値です。実際の設定を断定するものではありません。"

SHEETS = {
    # AI予想カテゴリ
    "today":        "【AI予想】今日の狙い（総合）",
    "today_j":      "【AI予想】ジャグラー狙い",
    "today_s":      "【AI予想】スマスロ狙い",
    "x_kw":         "【AI予想】X示唆KW",
    "matches":      "【AI予想】示唆照合",
    "accuracy":     "【AI予想】的中率",
    # ジャグラーカテゴリ
    "juggler_sum":  "【ジャグラー】総合",
    "juggler_mw":   "【ジャグラー】機種別勝率",
    "juggler_reg":  "【ジャグラー】REG分析",
    "juggler_comb": "【ジャグラー】合算分析",
    # スマスロカテゴリ
    "store":        "【スマスロ】店舗全体",
    "model":        "【スマスロ】機種別",
    "model_win":    "【スマスロ】機種別勝率",
    "machine":      "【スマスロ】台番号別",
    "suffix":       "【スマスロ】末尾別",
    "cluster":      "【スマスロ】並び分析",
    # 共通
    "weekday":      "📅 曜日別",
    "event":        "🎉 イベント日",
    "new":          "🆕 新台",
    "log":          "📝 実行ログ",
    "guide":        "📖 使い方",
}

# タブカラー設定 (RGB 0.0-1.0)
TAB_COLORS = {
    "today":       (0.6, 0.2, 1.0),
    "today_j":     (0.6, 0.2, 1.0),
    "today_s":     (0.6, 0.2, 1.0),
    "x_kw":        (0.6, 0.2, 1.0),
    "matches":     (0.6, 0.2, 1.0),
    "accuracy":    (0.6, 0.2, 1.0),
    "juggler_sum": (1.0, 0.4, 0.1),
    "juggler_mw":  (1.0, 0.4, 0.1),
    "juggler_reg": (1.0, 0.4, 0.1),
    "juggler_comb":(1.0, 0.4, 0.1),
    "store":       (0.1, 0.5, 0.9),
    "model":       (0.1, 0.5, 0.9),
    "model_win":   (0.1, 0.5, 0.9),
    "machine":     (0.1, 0.5, 0.9),
    "suffix":      (0.1, 0.5, 0.9),
    "cluster":     (0.1, 0.5, 0.9),
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

def _set_tab_colors(ss, ws_dict):
    requests=[]
    for key,(r,g,b) in TAB_COLORS.items():
        if key in ws_dict:
            requests.append({"updateSheetProperties":{
                "properties":{"sheetId":ws_dict[key].id,
                    "tabColorStyle":{"rgbColor":{"red":r,"green":g,"blue":b}}},
                "fields":"tabColorStyle"}})
    if requests:
        try: ss.batch_update({"requests":requests})
        except Exception as e: logger.warning(f"タブカラー設定スキップ: {e}")

def _write(ws, rows):
    ws.clear(); time.sleep(0.3)
    if rows: ws.update("A1",rows); time.sleep(0.5)

def _dict_rows(records):
    if not records: return [["データなし"]]
    headers=list(records[0].keys())
    return [headers]+[[str(r.get(h,"")) for h in headers] for r in records]

def _write_today(ws, targets, hall, label="総合"):
    tomorrow=(datetime.now()+timedelta(days=1)).strftime("%Y/%m/%d")
    rows=[[f"【AI予想】{hall} — {label}狙い台 ({tomorrow})"],[DISCLAIMER],
          ["更新",datetime.now().strftime("%Y/%m/%d %H:%M")],[""],
          ["順位","台番号","機種名","末尾","スコア","高設定候補回数","稼働日数","勝率_推定","累計差枚","期待度","根拠"]]
    for i,t in enumerate(targets,1):
        rows.append([i,t.get("台番号",""),t.get("機種名",""),t.get("末尾",""),t.get("スコア_推定",""),
                     t.get("高設定候補回数",""),t.get("稼働日数",""),t.get("勝率_推定",""),
                     t.get("累計差枚",""),t.get("期待度",""),t.get("根拠","")])
    _write(ws,rows)

def _write_guide(ws, hall):
    rows=[[f"📖 {hall} AIホール分析システム — 使い方"],[""],
          ["⚠️ 免責事項"],[DISCLAIMER],[""],
          ["カテゴリ","シート","内容"],
          ["【AI予想】","今日の狙い（総合）","全機種対象の推奨台（AI推定スコア順）"],
          ["【AI予想】","ジャグラー狙い","ジャグラー専用・REG/合算重視の推奨台"],
          ["【AI予想】","スマスロ狙い","スマスロ専用・差枚/G数重視の推奨台"],
          ["【AI予想】","X示唆KW","Xから抽出したキーワード一覧"],
          ["【AI予想】","示唆照合","X示唆 × 翌日結果の照合"],
          ["【AI予想】","的中率","キーワード別の過去的中率（AI学習）"],
          ["【ジャグラー】","総合","ジャグラー全体の勝率・高設定候補率"],
          ["【ジャグラー】","機種別勝率","ジャグラー機種ごとの累計差枚勝率"],
          ["【ジャグラー】","REG分析","REG確率優秀台ランキング（設定推定重視）"],
          ["【ジャグラー】","合算分析","合算確率優秀台ランキング"],
          ["【スマスロ】","店舗全体","スマスロ全体の集計"],
          ["【スマスロ】","機種別","機種ごとの高設定候補率"],
          ["【スマスロ】","機種別勝率","機種ごとの累計差枚勝率"],
          ["【スマスロ】","台番号別","台番号ごとの高設定候補回数"],
          ["【スマスロ】","末尾別","末尾数字ごとの傾向"],
          ["【スマスロ】","並び分析","2台・3台・島の並びパターン"],
          ["共通","曜日別","曜日ごとの傾向"],
          ["共通","イベント日","イベント日 vs 通常日の比較"],
          ["共通","新台","最近登場した機種の分析"],
          ["共通","実行ログ","毎日の実行履歴"],[""],
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

    # タブカラー設定
    _set_tab_colors(ss, ws)

    _write_guide(ws["guide"],hall)

    # AI予想
    _write_today(ws["today"],analysis.get("today_targets",[]),hall,"総合")
    _write_today(ws["today_j"],analysis.get("today_targets_juggler",[]),hall,"ジャグラー")
    _write_today(ws["today_s"],analysis.get("today_targets_sumasuro",[]),hall,"スマスロ")
    x_rows=[["投稿日時","投稿URL","示唆KW","OCR_KW","AI推定示唆"]]
    for p in x_posts:
        x_rows.append([p.get("投稿日時",""),p.get("投稿URL",""),
            p.get("示唆キーワード",""),p.get("OCRキーワード",""),p.get("AI推定示唆","")])
    _write(ws["x_kw"],x_rows)
    _write(ws["matches"],_dict_rows(analysis.get("x_suggestion_matches",[])))
    _write(ws["accuracy"],_dict_rows(analysis.get("keyword_accuracy",[])))

    # ジャグラー
    j_sum=analysis.get("juggler_summary",{})
    _write(ws["juggler_sum"],[["項目","値"]]+[[k,str(v)] for k,v in j_sum.items()])
    _write(ws["juggler_mw"],_dict_rows(analysis.get("juggler_model_win",[])))
    _write(ws["juggler_reg"],_dict_rows(analysis.get("juggler_reg_ranking",[])))
    _write(ws["juggler_comb"],_dict_rows(analysis.get("juggler_combined_ranking",[])))

    # スマスロ
    store=analysis.get("store",{})
    _write(ws["store"],[["項目","値"]]+[[k,str(v)] for k,v in store.items()])
    _write(ws["model"],_dict_rows(analysis.get("models",[])))
    _write(ws["model_win"],_dict_rows(analysis.get("sumasuro_model_win",[])))
    _write(ws["machine"],_dict_rows(analysis.get("machines",[])))
    _write(ws["suffix"],_dict_rows(analysis.get("suffixes",[])))
    clusters=analysis.get("clusters",{})
    cluster_rows=[["種類","日付","機種名","台番号","台数"]]
    for kind,items in clusters.items():
        for c in items:
            cluster_rows.append([kind,c["日付"],c["機種名"],c["台番号"],c["台数"]])
    _write(ws["cluster"],cluster_rows)

    # 共通
    _write(ws["weekday"],_dict_rows(analysis.get("weekdays",[])))
    ev=analysis.get("events",{})
    _write(ws["event"],[["項目","値"]]+[[k,str(v)] for k,v in ev.items()])
    _write(ws["new"],_dict_rows(analysis.get("new_machines",[])))

    try:
        existing=ws["log"].get_all_values() or [["日時","ステータス","メッセージ"]]
        existing.append([datetime.now().strftime("%Y/%m/%d %H:%M:%S"),"OK",
            f"{hall}: データ{analysis.get('record_count',0)}件"])
        _write(ws["log"],existing[-300:])
    except Exception as e: logger.error(f"ログ書き込みエラー: {e}")
    logger.info(f"✅ スプレッドシート更新完了")
    logger.info(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
