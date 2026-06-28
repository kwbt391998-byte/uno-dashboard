import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
PUBLIC_DIR = Path("dashboard/public")
RESULT_PATH = Path("logs/analysis_result.json")

def stars_html(s):
    return '<span style="color:#f59e0b">'+"★"*s.count("★")+'</span><span style="color:#374151">'+"☆"*s.count("☆")+'</span>'

def score_color(score):
    if score>=60: return "#e74c3c"
    if score>=40: return "#e67e22"
    if score>=20: return "#f39c12"
    return "#95a5a6"

def generate_html(r):
    hall=r.get("hall","有楽町UNO")
    generated=r.get("generated_at","")[:16].replace("T"," ")
    targets=r.get("today_targets",[])
    store=r.get("store",{})
    models=r.get("models",[])
    model_wins=r.get("model_wins",[])
    machines=r.get("machines",[])
    suffixes=r.get("suffixes",[])
    weekdays=r.get("weekdays",[])
    clusters=r.get("clusters",{})
    kw_acc=r.get("keyword_accuracy",[])

    target_cards=""
    for i,t in enumerate(targets[:10],1):
        score=t.get("スコア_推定",0)
        color=score_color(float(score))
        star=stars_html(t.get("期待度","★☆☆☆☆"))
        target_cards+=(
            '<div class="card" onclick="toggle(\'td' + str(i) + '\')">'
            '<div class="rank">#' + str(i) + '</div>'
            '<div class="card-main">'
            '<div class="card-header">'
            '<span class="mname">' + str(t.get("機種名","")) + '</span>'
            '<span>' + star + '</span>'
            '</div>'
            '<div class="badges">'
            '<span class="badge blue">台番号 ' + str(t.get("台番号","")) + '</span>'
            '<span class="badge green">末尾' + str(t.get("末尾","")) + '</span>'
            '<span class="badge" style="background:' + color + ';color:#fff">スコア ' + str(score) + '</span>'
            '</div>'
            '<div class="sub">勝率 ' + str(t.get("勝率_推定","")) + ' ／ 高設定候補 ' + str(t.get("高設定候補回数","")) + '回/' + str(t.get("稼働日数","")) + '日</div>'
            '</div>'
            '<div class="chev">›</div>'
            '</div>'
            '<div class="detail" id="td' + str(i) + '">'
            '<div class="reason-label">🔍 根拠</div>'
            '<div class="reason">' + str(t.get("根拠","")) + '</div>'
            '</div>'
        )

    store_rows="".join('<tr><td class="k">'+k+'</td><td class="v">'+str(v)+'</td></tr>' for k,v in store.items() if k!="免責")
    model_rows="".join("<tr><td>"+m.get("機種名","")+"</td><td>"+m.get("高設定候補率_推定","")+"</td><td>"+m.get("期待度","")+"</td><td>"+m.get("勝率_推定","")+"</td></tr>" for m in models[:10])
    machine_rows="".join("<tr><td>"+m.get("台番号","")+"</td><td>"+m.get("機種名","")+"</td><td>"+str(m.get("高設定候補回数",""))+"</td><td>"+m.get("期待度","")+"</td></tr>" for m in machines[:15])
    suffix_rows="".join("<tr><td>末尾"+s.get("末尾","")+"</td><td>"+s.get("高設定候補率_推定","")+"</td><td>"+s.get("期待度","")+"</td></tr>" for s in suffixes)
    weekday_rows="".join("<tr><td>"+w.get("曜日","")+"曜</td><td>"+w.get("高設定候補率_推定","")+"</td><td>"+w.get("期待度","")+"</td></tr>" for w in weekdays)
    cluster_items=""
    for kind,items in clusters.items():
        for c in items[:3]:
            cluster_items+='<div class="ci"><span class="badge purple">'+kind+'</span> '+c.get("日付","")+" "+c.get("機種名","")+" "+c.get("台番号","")+"</div>"
    acc_rows="".join("<tr><td>"+a.get("キーワード","")+"</td><td>"+a.get("的中率_推定","")+"</td><td>"+str(a.get("合計",""))+"回</td><td>"+a.get("信頼度","")+"</td></tr>" for a in kw_acc[:10])
    model_win_rows="".join(
        "<tr><td>"+m.get("機種名","")+"</td><td>"+str(m.get("設置台数",""))+"</td><td>"+m.get("勝率_推定","")+"</td><td>"+str(m.get("プラス台数",""))+"</td><td>"+str(m.get("マイナス台数",""))+"</td><td>"+str(m.get("総差枚",""))+"</td><td>"+str(m.get("平均差枚",""))+"</td><td>"+str(m.get("平均G数",""))+"</td><td>"+m.get("期待度","")+"</td></tr>"
        for m in model_wins)

    disclaimer=r.get("disclaimer","")

    css = '''*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,sans-serif;background:#0f0f1a;color:#e8e8f0;padding-bottom:80px}
.header{background:linear-gradient(135deg,#1a1a3e,#2d1b69);padding:20px 16px 16px;position:sticky;top:0;z-index:100;border-bottom:2px solid #7c3aed}
.header h1{font-size:1.3rem;font-weight:800;color:#fff}
.header p{font-size:0.75rem;color:#a78bfa;margin-top:2px}
.header small{font-size:0.7rem;color:#6b7280}
.nav{display:flex;overflow-x:auto;gap:8px;padding:12px 16px;background:#141428;border-bottom:1px solid #1e1e3a;position:sticky;top:88px;z-index:99;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}
.nav a{flex-shrink:0;background:#1e1e3a;border:1px solid #2d2d5a;color:#a78bfa;padding:8px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;text-decoration:none;white-space:nowrap}
.nav a.active{background:#7c3aed;color:#fff;border-color:#7c3aed}
.sec{padding:16px}
.sec-title{font-size:1.1rem;font-weight:800;color:#a78bfa;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #2d2d5a}
.card{background:#1a1a3a;border:1px solid #2d2d5a;border-radius:16px;padding:14px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;cursor:pointer}
.card:active{background:#221a4a}
.rank{font-size:1.4rem;font-weight:900;color:#7c3aed;min-width:36px}
.card-main{flex:1;min-width:0}
.card-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;margin-bottom:6px}
.mname{font-size:1rem;font-weight:800;color:#fff}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
.badge{font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:10px}
.blue{background:#1e3a5f;color:#60a5fa}
.green{background:#1a3a2a;color:#34d399}
.purple{background:#3b1a6e;color:#c4b5fd}
.sub{font-size:0.78rem;color:#9ca3af}
.chev{font-size:1.4rem;color:#4b5563;align-self:center;transition:transform 0.2s}
.detail{display:none;background:#111130;border:1px solid #2d2d5a;border-top:none;border-radius:0 0 16px 16px;padding:12px 14px;margin-top:-10px;margin-bottom:10px}
.detail.open{display:block}
.reason-label{font-size:0.75rem;color:#6b7280;margin-bottom:4px}
.reason{font-size:0.85rem;color:#d1d5db;line-height:1.5}
.tbl{width:100%;border-collapse:collapse;font-size:0.85rem}
.tbl th{background:#1e1e3a;color:#a78bfa;padding:10px 8px;text-align:left;font-size:0.78rem;font-weight:700;border-bottom:2px solid #2d2d5a;white-space:nowrap}
.tbl td{padding:10px 8px;border-bottom:1px solid #1e1e3a;color:#e8e8f0}
.tbl .k{color:#9ca3af;font-size:0.8rem} .tbl .v{font-weight:600;color:#fff}
.ci{background:#1a1a3a;border-radius:10px;padding:10px 12px;margin-bottom:8px;font-size:0.85rem;color:#d1d5db}
.empty{text-align:center;padding:32px;color:#4b5563;font-size:0.9rem}
.disc{background:#1a1a2e;border:1px solid #2d2d5a;border-radius:12px;padding:12px;font-size:0.72rem;color:#6b7280;margin:16px;line-height:1.6}'''

    js = '''function toggle(id){
  var el=document.getElementById(id);
  el.classList.toggle('open');
  var chev=el.previousElementSibling.querySelector('.chev');
  if(chev) chev.style.transform=el.classList.contains('open')?'rotate(90deg)':'';
}
var secs=document.querySelectorAll('section[id]');
secs.forEach(function(s){
  new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(e.isIntersecting){
        document.querySelectorAll('.nav a').forEach(function(b){b.classList.remove('active');});
        var t=document.querySelector('.nav a[href="#'+e.target.id+'"]');
        if(t) t.classList.add('active');
      }
    });
  },{rootMargin:'-40% 0px -55% 0px'}).observe(s);
});'''

    no_data_4 = '<tr><td colspan=4 class="empty">データなし</td></tr>'
    no_data_3 = '<tr><td colspan=3 class="empty">データなし</td></tr>'
    no_target = '<div class="empty">CSVをアップロードするとここに表示されます</div>'
    no_cluster = '<div class="empty">並びパターンなし</div>'
    no_acc = '<tr><td colspan=4 class="empty">照合データ蓄積中</td></tr>'

    return (
        '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<title>🎰 ' + hall + '</title>\n'
        '<style>\n' + css + '\n</style>\n'
        '</head>\n<body>\n'
        '<div class="header">\n'
        '  <h1>🎰 ' + hall + '</h1>\n'
        '  <p>AIホール分析システム</p>\n'
        '  <small>更新: ' + generated + '</small>\n'
        '</div>\n'
        '<nav class="nav">\n'
        '  <a href="#today" class="active">⭐ 今日の狙い</a>\n'
        '  <a href="#store">🏪 店舗全体</a>\n'
        '  <a href="#model">🎰 機種別</a>\n'
        '  <a href="#model_win">🏆 機種別勝率</a>\n'
        '  <a href="#machine">🔢 台番号</a>\n'
        '  <a href="#suffix">🔢 末尾</a>\n'
        '  <a href="#cluster">🔗 並び</a>\n'
        '  <a href="#weekday">📅 曜日</a>\n'
        '  <a href="#accuracy">📈 的中率</a>\n'
        '</nav>\n'
        '<section class="sec" id="today">\n'
        '  <div class="sec-title">⭐ 今日の狙い台 <span style="font-size:0.75rem;color:#6b7280;font-weight:400">（AI推定）</span></div>\n'
        '  ' + (target_cards if target_cards else no_target) + '\n'
        '</section>\n'
        '<section class="sec" id="store">\n'
        '  <div class="sec-title">🏪 店舗全体集計</div>\n'
        '  <table class="tbl"><tbody>' + store_rows + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="model">\n'
        '  <div class="sec-title">🎰 機種別ランキング</div>\n'
        '  <table class="tbl"><thead><tr><th>機種名</th><th>高設定候補率</th><th>期待度</th><th>勝率</th></tr></thead>\n'
        '  <tbody>' + (model_rows or no_data_4) + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="model_win">\n'
        '  <div class="sec-title">🏆 機種別勝率 <span style="font-size:0.75rem;color:#6b7280;font-weight:400">（累計差枚ベース）</span></div>\n'
        '  <table class="tbl"><thead><tr><th>機種名</th><th>設置台数</th><th>勝率</th><th>+台数</th><th>-台数</th><th>総差枚</th><th>平均差枚</th><th>平均G数</th><th>期待度</th></tr></thead>\n'
        '  <tbody>' + (model_win_rows or '<tr><td colspan=9 class="empty">データなし</td></tr>') + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="machine">\n'
        '  <div class="sec-title">🔢 台番号別ランキング</div>\n'
        '  <table class="tbl"><thead><tr><th>台番号</th><th>機種名</th><th>高設定候補回数</th><th>期待度</th></tr></thead>\n'
        '  <tbody>' + (machine_rows or no_data_4) + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="suffix">\n'
        '  <div class="sec-title">🔢 末尾別分析</div>\n'
        '  <table class="tbl"><thead><tr><th>末尾</th><th>高設定候補率</th><th>期待度</th></tr></thead>\n'
        '  <tbody>' + (suffix_rows or no_data_3) + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="cluster">\n'
        '  <div class="sec-title">🔗 並び分析</div>\n'
        '  ' + (cluster_items or no_cluster) + '\n'
        '</section>\n'
        '<section class="sec" id="weekday">\n'
        '  <div class="sec-title">📅 曜日別分析</div>\n'
        '  <table class="tbl"><thead><tr><th>曜日</th><th>高設定候補率</th><th>期待度</th></tr></thead>\n'
        '  <tbody>' + (weekday_rows or no_data_3) + '</tbody></table>\n'
        '</section>\n'
        '<section class="sec" id="accuracy">\n'
        '  <div class="sec-title">📈 示唆キーワード的中率</div>\n'
        '  <table class="tbl"><thead><tr><th>キーワード</th><th>的中率</th><th>回数</th><th>信頼度</th></tr></thead>\n'
        '  <tbody>' + (acc_rows or no_acc) + '</tbody></table>\n'
        '</section>\n'
        '<div class="disc">⚠️ ' + disclaimer + '</div>\n'
        '<script>\n' + js + '\n</script>\n'
        '</body></html>'
    )

def main():
    PUBLIC_DIR.mkdir(parents=True,exist_ok=True)
    r=json.loads(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else {"hall":"有楽町UNO","generated_at":datetime.now().isoformat()}
    html=generate_html(r)
    out=PUBLIC_DIR/"index.html"
    out.write_text(html,encoding="utf-8")
    print(f"✅ ダッシュボード生成: {out}")

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    main()
