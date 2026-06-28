import json, logging, re
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

def _cluster_cards(clusters, cluster_freq):
    all_items=[]
    for kind,items in clusters.items():
        for c in items:
            all_items.append(c)
    if not all_items:
        return '<div class="empty">並びパターンなし（データ蓄積中）</div>'
    all_items=sorted(all_items,key=lambda x:x.get("日付",""),reverse=True)
    out=""
    for c in all_items[:15]:
        kind=c.get("種類","—"); model=c.get("機種名",""); nums=c.get("台番号","")
        date=c.get("日付",""); count=c.get("台数",0); is_ev=c.get("イベント日",False)
        freq_key=model+":::"+kind
        freq_info=cluster_freq.get(freq_key,{})
        freq_count=freq_info.get("発生回数",1)
        freq_ev=freq_info.get("うちイベント日",0)
        # 種類別推論
        if kind=="2台並び":
            reasoning="隣接する2台に同日・同時に高設定候補が集中 → 機種内の複数台へ意図的に設定を投入している可能性"
            implication="今後この機種が同条件で出た日は、連番台も合わせて追加確認を推奨"
        elif kind=="3台並び":
            reasoning="3台が連番で高設定候補 → 島の過半数に設定が入っている可能性。台を絞らず島全体を視野に入れた方が効率的"
            implication="このパターンが出た機種は「島丸ごと狙い」の戦略が有効な可能性あり"
        else:
            reasoning=f"{count}台以上がまとまって高設定候補 → 1島まるごと高設定投入の可能性（全台開放または大幅な高設定配分）"
            implication="単台狙いより島全体で複数台プレイした方が高設定に当たりやすい状況"
        freq_text=f"過去{freq_count}回発生"+(f"（うちイベント日{freq_ev}回）" if freq_ev>0 else "")
        ev_badge='<span style="font-size:0.65rem;background:#3a2000;color:#fb923c;padding:2px 6px;border-radius:8px;margin-left:6px">🎉 イベント日</span>' if is_ev else ""
        num_badges="".join('<span style="background:#1e3a5f;color:#60a5fa;padding:2px 7px;border-radius:6px;font-size:0.75rem;font-weight:700;margin-right:4px">'+n.strip()+'</span>' for n in nums.strip("[]").split(",") if n.strip())
        out+=(
            '<div style="background:#1a1a3a;border:1px solid #2d2d5a;border-radius:14px;padding:14px;margin-bottom:12px">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">'
            '<span class="badge purple">'+kind+'</span>'
            '<span style="font-size:0.78rem;color:#9ca3af">'+date+'</span>'
            +ev_badge+
            '</div>'
            '<div style="font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px">'+model+'</div>'
            '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px">'+num_badges+'</div>'
            '<div style="background:#111830;border-left:3px solid #7c3aed;padding:10px 12px;border-radius:0 10px 10px 0;margin-bottom:8px">'
            '<div style="font-size:0.7rem;color:#a78bfa;font-weight:700;margin-bottom:4px">💡 推測</div>'
            '<div style="font-size:0.8rem;color:#d1d5db;line-height:1.55">'+reasoning+'</div>'
            '</div>'
            '<div style="background:#0f1a10;border-left:3px solid #34d399;padding:8px 12px;border-radius:0 10px 10px 0;margin-bottom:8px">'
            '<div style="font-size:0.7rem;color:#34d399;font-weight:700;margin-bottom:3px">⭐ 活用方法</div>'
            '<div style="font-size:0.78rem;color:#86efac;line-height:1.5">'+implication+'</div>'
            '</div>'
            '<div style="font-size:0.7rem;color:#4b5563">📊 '+freq_text+'</div>'
            '</div>'
        )
    return out

def _kw_reasoning(kw):
    m=re.search(r"\d+",kw)
    if "末尾" in kw:
        tail=m.group() if m else "?"
        return (f"末尾{tail}の台番号（{tail}, 1{tail}, 2{tail}...）に高設定が集中している可能性",
                f"末尾{tail}の台を優先確認")
    if any(w in kw for w in ["全台","全○","全◯","全6","全5"]):
        return ("店内の複数機種・複数台で広く高設定が投入されている可能性",
                "複数機種を横断して広く確認。絞らず全体を見る")
    if any(w in kw for w in ["高設定","456","設定5","設定6","上位"]):
        return ("今日は通常より高設定の投入率が高い可能性",
                "スコア上位台を積極的に狙う戦略が有効")
    if any(w in kw for w in ["ジャグラー","マイジャグ","アイム","ファンキー","ゴーゴー"]):
        return ("ジャグラー系機種への設定集中の示唆",
                "ジャグラー系台のREG確率を重点チェック")
    if any(w in kw for w in ["イベント","感謝","周年"]):
        return ("イベントに紐づいた高設定投入が期待できる",
                "イベント関連機種・台を優先的に確認")
    if any(w in kw for w in ["据え","据置","継続"]):
        return ("前日の高設定台がそのまま据え置かれている可能性",
                "前日高設定候補だった台を継続して確認")
    return (f"「{kw}」に関連する台の傾向を確認",
            "過去の的中実績と照合して判断")

def _xkw_cards(x_posts_raw, kw_acc):
    acc_map={a["キーワード"]:a for a in kw_acc}
    posts=[p for p in (x_posts_raw or []) if p.get("本文","").strip() or p.get("全キーワード","").strip()]

    # X投稿がない場合は過去実績カードにフォールバック
    if not posts:
        if not kw_acc:
            return '<div class="empty">Xデータがありません。data/x_posts/にCSVを追加、またはX API連携を設定してください。</div>'
        out='<div style="font-size:0.73rem;color:#6b7280;margin-bottom:12px;padding:8px 12px;background:#111;border-radius:8px">📌 X投稿未取得のため、過去の示唆キーワード実績を表示しています</div>'
        for a in kw_acc[:8]:
            kw=a["キーワード"]; total=int(a.get("合計",0)); hits=int(a.get("的中回数",0))
            rate=a.get("的中率_推定","—")
            reasoning,rec=_kw_reasoning(kw)
            rate_val=hits/total if total>0 else 0
            conf_color="#e74c3c" if rate_val>=0.6 else "#e67e22" if rate_val>=0.3 else "#6b7280"
            out+=(
                '<div style="background:#1a1a3a;border:1px solid #2d2d5a;border-radius:12px;padding:12px;margin-bottom:10px">'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                '<span class="badge purple">'+kw+'</span>'
                '<span style="font-size:0.72rem;color:'+conf_color+';font-weight:700">的中率 '+rate+' ('+str(total)+'回)</span>'
                '</div>'
                '<div style="font-size:0.78rem;color:#d1d5db;margin-bottom:6px">🔍 '+reasoning+'</div>'
                '<div style="font-size:0.75rem;color:#86efac">⭐ '+rec+'</div>'
                '</div>'
            )
        return out

    # 投稿本文ベースのカード（1投稿 = 1カード）
    out=""
    for p in posts[:8]:
        text=p.get("本文","").strip()
        dt=str(p.get("投稿日時",""))[:10]
        ai_hint=p.get("AI推定示唆","").strip()
        all_kws=[k.strip() for k in p.get("全キーワード","").split(",") if k.strip()]

        # キーワードごとに推論を生成（重複タイプは1つに集約）
        reasonings=[]; recs=[]; seen_types=set()
        for kw in all_kws:
            reasoning,rec=_kw_reasoning(kw)
            # タイプ判定
            if "末尾" in kw: t="末尾"
            elif any(w in kw for w in ["全台","全○","全◯"]): t="全台"
            elif any(w in kw for w in ["高設定","456","設定5","設定6"]): t="高設定"
            elif any(w in kw for w in ["ジャグラー","マイジャグ","アイム","ファンキー"]): t="ジャグラー"
            elif any(w in kw for w in ["イベント","感謝","周年"]): t="イベント"
            elif any(w in kw for w in ["据え","据置","継続"]): t="据え置き"
            else: t=kw
            if t not in seen_types:
                reasonings.append("• "+reasoning)
                recs.append(rec)
                seen_types.add(t)

        # 最も的中率の高いキーワードの実績を表示
        best_acc={}; best_rate=0
        for kw in all_kws:
            a=acc_map.get(kw,{})
            total=int(a.get("合計",0)); hits=int(a.get("的中回数",0))
            if total>0 and hits/total>best_rate:
                best_acc=a; best_rate=hits/total

        kw_badges="".join('<span class="badge purple" style="margin-right:4px">'+kw+'</span>' for kw in all_kws)
        text_html=(
            '<div style="background:#111828;border-radius:8px;padding:10px 12px;margin-bottom:10px">'
            '<div style="font-size:0.65rem;color:#6b7280;margin-bottom:5px">🐦 X投稿内容</div>'
            '<div style="font-size:0.88rem;color:#f0f0ff;line-height:1.65;white-space:pre-wrap">'+text+'</div>'
            '</div>'
        ) if text else ""
        ai_html=(
            '<div style="background:#1a1040;border-radius:8px;padding:8px 10px;margin-bottom:8px;font-size:0.78rem;color:#c4b5fd">'
            '🤖 AI解釈: '+ai_hint+'</div>'
        ) if ai_hint else ""
        reasoning_html=(
            '<div style="background:#111830;border-left:3px solid #7c3aed;padding:10px 12px;border-radius:0 10px 10px 0;margin-bottom:8px">'
            '<div style="font-size:0.7rem;color:#a78bfa;font-weight:700;margin-bottom:6px">🔍 この投稿からわかること</div>'
            '<div style="font-size:0.8rem;color:#d1d5db;line-height:1.6">'+"<br>".join(reasonings)+'</div>'
            '</div>'
        ) if reasonings else ""
        rec_html=(
            '<div style="background:#0f1a10;border-left:3px solid #34d399;padding:8px 12px;border-radius:0 10px 10px 0;margin-bottom:8px">'
            '<div style="font-size:0.7rem;color:#34d399;font-weight:700;margin-bottom:3px">⭐ 推奨アクション</div>'
            '<div style="font-size:0.78rem;color:#86efac;line-height:1.5">'+"  /  ".join(dict.fromkeys(recs))+'</div>'
            '</div>'
        ) if recs else ""
        if best_acc:
            total=int(best_acc.get("合計",0)); hits=int(best_acc.get("的中回数",0))
            rate=best_acc.get("的中率_推定","—"); bkw=best_acc.get("キーワード","")
            rv=hits/total if total>0 else 0
            cc="#e74c3c" if rv>=0.6 else "#e67e22" if rv>=0.3 else "#6b7280"
            acc_html='<div style="font-size:0.7rem;color:'+cc+'">📊 「'+bkw+'」過去的中率: '+rate+' ('+str(total)+'回中'+str(hits)+'回的中)</div>'
        else:
            acc_html='<div style="font-size:0.7rem;color:#4b5563">📊 照合データ蓄積中</div>'

        out+=(
            '<div style="background:#1a1a3a;border:1px solid #2d2d5a;border-radius:14px;padding:14px;margin-bottom:14px">'
            '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;flex-wrap:wrap;gap:6px">'
            '<div style="display:flex;flex-wrap:wrap;gap:4px">'+kw_badges+'</div>'
            '<span style="font-size:0.68rem;color:#4b5563">📅 '+dt+'</span>'
            '</div>'
            +text_html+ai_html+reasoning_html+rec_html+acc_html+
            '</div>'
        )
    return out or '<div class="empty">Xキーワードがありません</div>'

def _target_cards(targets, prefix):
    if not targets:
        return '<div class="empty">CSVをアップロードするとここに表示されます</div>'
    out=""
    for i,t in enumerate(targets[:10],1):
        score=t.get("スコア_推定",0)
        color=score_color(float(score))
        star=stars_html(t.get("期待度","★☆☆☆☆"))
        diff=t.get("累計差枚","")
        diff_str=("+"+str(diff) if isinstance(diff,int) and diff>0 else str(diff)) if diff!="" else ""
        eid=prefix+str(i)
        out+=(
            '<div class="card" onclick="toggle(\''+eid+'\')">'
            '<div class="rank">#'+str(i)+'</div>'
            '<div class="card-main">'
            '<div class="card-header">'
            '<span class="mname">'+str(t.get("機種名",""))+'</span>'
            '<span>'+star+'</span>'
            '</div>'
            '<div class="badges">'
            '<span class="badge blue">台番号 '+str(t.get("台番号",""))+'</span>'
            '<span class="badge green">末尾'+str(t.get("末尾",""))+'</span>'
            '<span class="badge" style="background:'+color+';color:#fff">スコア '+str(score)+'</span>'
            +(('<span class="badge diff">'+diff_str+'枚</span>') if diff_str else '')
            +'</div>'
            '<div class="sub">勝率 '+str(t.get("勝率_推定",""))+' ／ 高設定候補 '+str(t.get("高設定候補回数",""))+'回/'+str(t.get("稼働日数",""))+'日</div>'
            '</div>'
            '<div class="chev">›</div>'
            '</div>'
            '<div class="detail" id="'+eid+'">'
            '<div class="reason-label">🔍 根拠</div>'
            '<div class="reason">'+str(t.get("根拠",""))+'</div>'
            '</div>'
        )
    return out

def generate_html(r):
    hall=r.get("hall","有楽町UNO")
    generated=r.get("generated_at","")[:16].replace("T"," ")
    targets=r.get("today_targets",[])
    targets_j=r.get("today_targets_juggler",[])
    targets_s=r.get("today_targets_sumasuro",[])
    store=r.get("store",{})
    models=r.get("models",[])
    model_wins=r.get("model_wins",[])
    sumasuro_mw=r.get("sumasuro_model_win",[])
    machines=r.get("machines",[])
    suffixes=r.get("suffixes",[])
    weekdays=r.get("weekdays",[])
    clusters=r.get("clusters",{})
    kw_acc=r.get("keyword_accuracy",[])
    x_posts_raw=r.get("x_posts_raw",[])
    cluster_freq=r.get("cluster_frequency",{})
    j_sum=r.get("juggler_summary",{})
    j_mw=r.get("juggler_model_win",[])
    j_reg=r.get("juggler_reg_ranking",[])
    j_comb=r.get("juggler_combined_ranking",[])
    disclaimer=r.get("disclaimer","")

    target_cards_all=_target_cards(targets,"td")
    target_cards_j=_target_cards(targets_j,"tj")
    target_cards_s=_target_cards(targets_s,"ts")

    store_rows="".join('<tr><td class="k">'+k+'</td><td class="v">'+str(v)+'</td></tr>' for k,v in store.items() if k!="免責")
    model_rows="".join("<tr><td>"+m.get("機種名","")+"</td><td>"+m.get("高設定候補率_推定","")+"</td><td>"+m.get("期待度","")+"</td><td>"+m.get("勝率_推定","")+"</td></tr>" for m in models[:12])
    smw_rows="".join("<tr><td>"+m.get("機種名","")+"</td><td>"+str(m.get("設置台数",""))+"</td><td>"+m.get("勝率_推定","")+"</td><td>"+str(m.get("プラス台数",""))+"</td><td>"+str(m.get("マイナス台数",""))+"</td><td>"+str(m.get("総差枚",""))+"</td><td>"+m.get("期待度","")+"</td></tr>" for m in sumasuro_mw[:12])
    machine_rows="".join("<tr><td>"+m.get("台番号","")+"</td><td>"+m.get("機種名","")+"</td><td>"+str(m.get("高設定候補回数",""))+"</td><td>"+m.get("期待度","")+"</td></tr>" for m in machines[:15])
    suffix_rows="".join("<tr><td>末尾"+s.get("末尾","")+"</td><td>"+s.get("高設定候補率_推定","")+"</td><td>"+s.get("期待度","")+"</td></tr>" for s in suffixes)
    weekday_rows="".join("<tr><td>"+w.get("曜日","")+"曜</td><td>"+w.get("高設定候補率_推定","")+"</td><td>"+w.get("期待度","")+"</td></tr>" for w in weekdays)
    cluster_cards=_cluster_cards(clusters, cluster_freq)
    xkw_cards=_xkw_cards(x_posts_raw, kw_acc)
    acc_rows="".join("<tr><td>"+a.get("キーワード","")+"</td><td>"+a.get("的中率_推定","")+"</td><td>"+str(a.get("合計",""))+"回</td><td>"+a.get("信頼度","")+"</td></tr>" for a in kw_acc[:10])
    j_sum_rows="".join('<tr><td class="k">'+k+'</td><td class="v">'+str(v)+'</td></tr>' for k,v in j_sum.items() if k!="免責")
    j_mw_rows="".join("<tr><td>"+m.get("機種名","")+"</td><td>"+str(m.get("設置台数",""))+"</td><td>"+m.get("勝率_推定","")+"</td><td>"+str(m.get("プラス台数",""))+"</td><td>"+str(m.get("マイナス台数",""))+"</td><td>"+str(m.get("総差枚",""))+"</td><td>"+m.get("累計REG確率","")+"</td><td>"+m.get("期待度","")+"</td></tr>" for m in j_mw[:12])
    j_reg_rows="".join("<tr><td>"+str(m.get("台番号",""))+"</td><td>"+str(m.get("機種名",""))+"</td><td>"+str(m.get("累計REG確率表示",""))+"</td><td>"+str(m.get("累計差枚",""))+"</td><td>"+str(m.get("稼働日数",""))+"日</td><td>"+str(m.get("期待度",""))+"</td></tr>" for m in j_reg[:15])
    j_comb_rows="".join("<tr><td>"+str(m.get("台番号",""))+"</td><td>"+str(m.get("機種名",""))+"</td><td>"+str(m.get("累計合算表示",""))+"</td><td>"+str(m.get("累計REG表示",""))+"</td><td>"+str(m.get("累計差枚",""))+"</td><td>"+str(m.get("期待度",""))+"</td></tr>" for m in j_comb[:15])

    no4='<tr><td colspan=4 class="empty">データなし</td></tr>'
    no3='<tr><td colspan=3 class="empty">データなし</td></tr>'
    no6='<tr><td colspan=6 class="empty">データなし</td></tr>'
    no8='<tr><td colspan=8 class="empty">データなし</td></tr>'

    css=(
        '*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}'
        'body{font-family:-apple-system,sans-serif;background:#0f0f1a;color:#e8e8f0;padding-bottom:80px}'
        '.header{background:linear-gradient(135deg,#1a1a3e,#2d1b69);padding:16px 16px 12px;position:sticky;top:0;z-index:100;border-bottom:2px solid #7c3aed}'
        '.header h1{font-size:1.2rem;font-weight:800;color:#fff}'
        '.header p{font-size:0.72rem;color:#a78bfa;margin-top:1px}'
        '.header small{font-size:0.68rem;color:#6b7280}'
        '.cat-nav{display:flex;gap:0;background:#141428;border-bottom:2px solid #1e1e3a;position:sticky;top:72px;z-index:99}'
        '.cat-btn{flex:1;padding:10px 4px;text-align:center;font-size:0.78rem;font-weight:700;color:#6b7280;cursor:pointer;border-bottom:3px solid transparent;transition:all .2s}'
        '.cat-btn.ai.active{color:#a78bfa;border-color:#7c3aed;background:#1a1a3a}'
        '.cat-btn.sm.active{color:#60a5fa;border-color:#2563eb;background:#0f1e3a}'
        '.cat-btn.jg.active{color:#fb923c;border-color:#ea580c;background:#2a1500}'
        '.subnav{display:none;overflow-x:auto;gap:8px;padding:10px 16px;background:#111120;border-bottom:1px solid #1e1e3a;scrollbar-width:none}'
        '.subnav.show{display:flex}'
        '.subnav::-webkit-scrollbar{display:none}'
        '.subnav a{flex-shrink:0;background:#1e1e3a;border:1px solid #2d2d5a;color:#9ca3af;padding:6px 12px;border-radius:20px;font-size:0.75rem;font-weight:600;text-decoration:none;white-space:nowrap}'
        '.subnav a.active{color:#fff}'
        '.subnav.ai a.active{background:#7c3aed;border-color:#7c3aed}'
        '.subnav.sm a.active{background:#2563eb;border-color:#2563eb}'
        '.subnav.jg a.active{background:#ea580c;border-color:#ea580c}'
        '.cat-section{display:none}'
        '.cat-section.show{display:block}'
        '.sec{padding:16px}'
        '.sec-title{font-size:1.05rem;font-weight:800;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #2d2d5a}'
        '.ai .sec-title{color:#a78bfa}'
        '.sm .sec-title{color:#60a5fa}'
        '.jg .sec-title{color:#fb923c}'
        '.card{background:#1a1a3a;border:1px solid #2d2d5a;border-radius:16px;padding:14px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;cursor:pointer}'
        '.card:active{background:#221a4a}'
        '.rank{font-size:1.3rem;font-weight:900;color:#7c3aed;min-width:34px}'
        '.card-main{flex:1;min-width:0}'
        '.card-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;margin-bottom:6px}'
        '.mname{font-size:0.95rem;font-weight:800;color:#fff}'
        '.badges{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}'
        '.badge{font-size:0.7rem;font-weight:700;padding:3px 7px;border-radius:10px}'
        '.blue{background:#1e3a5f;color:#60a5fa}'
        '.green{background:#1a3a2a;color:#34d399}'
        '.purple{background:#3b1a6e;color:#c4b5fd}'
        '.diff{background:#1a2a1a;color:#4ade80}'
        '.sub{font-size:0.75rem;color:#9ca3af}'
        '.chev{font-size:1.3rem;color:#4b5563;align-self:center;transition:transform .2s}'
        '.detail{display:none;background:#111130;border:1px solid #2d2d5a;border-top:none;border-radius:0 0 16px 16px;padding:12px 14px;margin-top:-10px;margin-bottom:10px}'
        '.detail.open{display:block}'
        '.reason-label{font-size:0.72rem;color:#6b7280;margin-bottom:4px}'
        '.reason{font-size:0.82rem;color:#d1d5db;line-height:1.5}'
        '.tbl{width:100%;border-collapse:collapse;font-size:0.82rem}'
        '.tbl th{background:#1e1e3a;color:#a78bfa;padding:9px 7px;text-align:left;font-size:0.75rem;font-weight:700;border-bottom:2px solid #2d2d5a;white-space:nowrap}'
        '.tbl.jg th{color:#fb923c}'
        '.tbl.sm th{color:#60a5fa}'
        '.tbl td{padding:9px 7px;border-bottom:1px solid #1e1e3a;color:#e8e8f0}'
        '.tbl .k{color:#9ca3af;font-size:0.78rem} .tbl .v{font-weight:600;color:#fff}'
        '.ci{background:#1a1a3a;border-radius:10px;padding:10px 12px;margin-bottom:8px;font-size:0.82rem;color:#d1d5db}'
        '.empty{text-align:center;padding:28px;color:#4b5563;font-size:0.88rem}'
        '.disc{background:#1a1a2e;border:1px solid #2d2d5a;border-radius:12px;padding:12px;font-size:0.7rem;color:#6b7280;margin:16px;line-height:1.6}'
        '.info-box{background:#1a2a1a;border:1px solid #2a3a2a;border-radius:12px;padding:14px;margin-bottom:12px;font-size:0.82rem;color:#86efac}'
    )

    js=(
        'function toggle(id){'
        'var el=document.getElementById(id);'
        'el.classList.toggle("open");'
        'var chev=el.previousElementSibling.querySelector(".chev");'
        'if(chev)chev.style.transform=el.classList.contains("open")?"rotate(90deg)":""}'
        'var cats=["ai","sm","jg"];'
        'function switchCat(cat){'
        'cats.forEach(function(c){'
        'document.getElementById("sec-"+c).classList.toggle("show",c===cat);'
        'document.getElementById("nav-"+c).classList.toggle("show",c===cat);'
        'document.querySelectorAll(".cat-btn").forEach(function(b){b.classList.remove("active");});'
        '});'
        'document.querySelector(".cat-btn."+cat).classList.add("active");'
        'activeSub[cat]=activeSub[cat]||firstSub[cat];'
        'switchSub(cat,activeSub[cat]);}'
        'var activeSub={};'
        'var firstSub={ai:"ai-today",sm:"sm-store",jg:"jg-sum"};'
        'function switchSub(cat,subId){'
        'activeSub[cat]=subId;'
        'document.querySelectorAll("#sec-"+cat+" .subsec").forEach(function(s){s.style.display="none";});'
        'var el=document.getElementById(subId);if(el)el.style.display="block";'
        'document.querySelectorAll("#nav-"+cat+" a").forEach(function(a){a.classList.remove("active");});'
        'document.querySelectorAll("#nav-"+cat+" a").forEach(function(a){if(a.dataset.sub===subId)a.classList.add("active");});}'
        'document.querySelectorAll(".subnav a").forEach(function(a){'
        'a.addEventListener("click",function(e){e.preventDefault();'
        'var cat=this.closest(".subnav").dataset.cat;'
        'switchSub(cat,this.dataset.sub);});});'
        'switchCat("ai");'
    )

    return (
        '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<title>🎰 '+hall+'</title>\n'
        '<style>\n'+css+'\n</style>\n'
        '</head>\n<body>\n'
        # ヘッダー
        '<div class="header">\n'
        '  <h1>🎰 '+hall+'</h1>\n'
        '  <p>AIホール分析システム</p>\n'
        '  <small>更新: '+generated+'</small>\n'
        '</div>\n'
        # カテゴリ切替
        '<div class="cat-nav">\n'
        '  <div class="cat-btn ai" onclick="switchCat(\'ai\')">🤖 AI予想</div>\n'
        '  <div class="cat-btn sm" onclick="switchCat(\'sm\')">💻 スマスロ</div>\n'
        '  <div class="cat-btn jg" onclick="switchCat(\'jg\')">🎰 ジャグラー</div>\n'
        '</div>\n'

        # AI予想サブナビ
        '<nav class="subnav ai" id="nav-ai" data-cat="ai">\n'
        '  <a href="#" data-sub="ai-today" class="active">⭐ 総合狙い</a>\n'
        '  <a href="#" data-sub="ai-jtoday">🎰 ジャグラー狙い</a>\n'
        '  <a href="#" data-sub="ai-stoday">💻 スマスロ狙い</a>\n'
        '  <a href="#" data-sub="ai-xkw">🐦 X示唆KW</a>\n'
        '  <a href="#" data-sub="ai-acc">📈 的中率</a>\n'
        '</nav>\n'
        # スマスロサブナビ
        '<nav class="subnav sm" id="nav-sm" data-cat="sm">\n'
        '  <a href="#" data-sub="sm-store">🏪 店舗全体</a>\n'
        '  <a href="#" data-sub="sm-model">🎰 機種別</a>\n'
        '  <a href="#" data-sub="sm-mwin">🏆 機種別勝率</a>\n'
        '  <a href="#" data-sub="sm-mach">🔢 台番号</a>\n'
        '  <a href="#" data-sub="sm-sfx">🔢 末尾</a>\n'
        '  <a href="#" data-sub="sm-clus">🔗 並び</a>\n'
        '  <a href="#" data-sub="sm-wd">📅 曜日</a>\n'
        '</nav>\n'
        # ジャグラーサブナビ
        '<nav class="subnav jg" id="nav-jg" data-cat="jg">\n'
        '  <a href="#" data-sub="jg-sum">📊 総合</a>\n'
        '  <a href="#" data-sub="jg-mw">🏆 機種別勝率</a>\n'
        '  <a href="#" data-sub="jg-reg">🎯 REG分析</a>\n'
        '  <a href="#" data-sub="jg-comb">🎲 合算分析</a>\n'
        '</nav>\n'

        # ====== AI予想セクション ======
        '<div class="cat-section ai" id="sec-ai">\n'

        '<div class="subsec" id="ai-today">\n'
        '<section class="sec ai">\n'
        '  <div class="sec-title">⭐ 今日の狙い台（総合）<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> AI推定</span></div>\n'
        '  '+target_cards_all+'\n'
        '</section></div>\n'

        '<div class="subsec" id="ai-jtoday" style="display:none">\n'
        '<section class="sec ai">\n'
        '  <div class="sec-title">🎰 ジャグラー狙い台<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> REG・合算重視</span></div>\n'
        '  '+target_cards_j+'\n'
        '</section></div>\n'

        '<div class="subsec" id="ai-stoday" style="display:none">\n'
        '<section class="sec ai">\n'
        '  <div class="sec-title">💻 スマスロ狙い台<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 差枚・G数重視</span></div>\n'
        '  '+target_cards_s+'\n'
        '</section></div>\n'

        '<div class="subsec" id="ai-xkw" style="display:none">\n'
        '<section class="sec ai">\n'
        '  <div class="sec-title">🐦 X示唆キーワード<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 根拠・推論付き</span></div>\n'
        '  '+xkw_cards+'\n'
        '</section></div>\n'

        '<div class="subsec" id="ai-acc" style="display:none">\n'
        '<section class="sec ai">\n'
        '  <div class="sec-title">📈 示唆キーワード的中率</div>\n'
        '  <table class="tbl"><thead><tr><th>キーワード</th><th>的中率</th><th>回数</th><th>信頼度</th></tr></thead>\n'
        '  <tbody>'+(acc_rows or '<tr><td colspan=4 class="empty">照合データ蓄積中</td></tr>')+'</tbody></table>\n'
        '</section></div>\n'

        '</div>\n'

        # ====== スマスロセクション ======
        '<div class="cat-section sm" id="sec-sm">\n'

        '<div class="subsec" id="sm-store" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🏪 スマスロ店舗全体集計</div>\n'
        '  <table class="tbl sm"><tbody>'+store_rows+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-model" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🎰 スマスロ機種別ランキング</div>\n'
        '  <table class="tbl sm"><thead><tr><th>機種名</th><th>高設定候補率</th><th>期待度</th><th>勝率</th></tr></thead>\n'
        '  <tbody>'+(model_rows or no4)+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-mwin" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🏆 スマスロ機種別勝率<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 累計差枚ベース</span></div>\n'
        '  <table class="tbl sm"><thead><tr><th>機種名</th><th>設置台数</th><th>勝率</th><th>+台数</th><th>-台数</th><th>総差枚</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(smw_rows or '<tr><td colspan=7 class="empty">データなし</td></tr>')+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-mach" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🔢 台番号別ランキング</div>\n'
        '  <table class="tbl sm"><thead><tr><th>台番号</th><th>機種名</th><th>高設定候補回数</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(machine_rows or no4)+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-sfx" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🔢 末尾別分析</div>\n'
        '  <table class="tbl sm"><thead><tr><th>末尾</th><th>高設定候補率</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(suffix_rows or no3)+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-clus" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">🔗 並び分析<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 推測・活用方法付き</span></div>\n'
        '  '+cluster_cards+'\n'
        '</section></div>\n'

        '<div class="subsec" id="sm-wd" style="display:none">\n'
        '<section class="sec sm">\n'
        '  <div class="sec-title">📅 曜日別分析</div>\n'
        '  <table class="tbl sm"><thead><tr><th>曜日</th><th>高設定候補率</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(weekday_rows or no3)+'</tbody></table>\n'
        '</section></div>\n'

        '</div>\n'

        # ====== ジャグラーセクション ======
        '<div class="cat-section jg" id="sec-jg">\n'

        '<div class="subsec" id="jg-sum" style="display:none">\n'
        '<section class="sec jg">\n'
        '  <div class="sec-title">📊 ジャグラー総合分析</div>\n'
        '  <table class="tbl jg"><tbody>'+j_sum_rows+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="jg-mw" style="display:none">\n'
        '<section class="sec jg">\n'
        '  <div class="sec-title">🏆 ジャグラー機種別勝率<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 累計差枚ベース</span></div>\n'
        '  <table class="tbl jg"><thead><tr><th>機種名</th><th>設置台数</th><th>勝率</th><th>+台数</th><th>-台数</th><th>総差枚</th><th>累計REG</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(j_mw_rows or no8)+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="jg-reg" style="display:none">\n'
        '<section class="sec jg">\n'
        '  <div class="sec-title">🎯 ジャグラーREG優秀台ランキング<span style="font-size:0.72rem;color:#6b7280;font-weight:400"> 設定推定重視</span></div>\n'
        '  <table class="tbl jg"><thead><tr><th>台番号</th><th>機種名</th><th>累計REG</th><th>累計差枚</th><th>稼働</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(j_reg_rows or no6)+'</tbody></table>\n'
        '</section></div>\n'

        '<div class="subsec" id="jg-comb" style="display:none">\n'
        '<section class="sec jg">\n'
        '  <div class="sec-title">🎲 ジャグラー合算優秀台ランキング</div>\n'
        '  <table class="tbl jg"><thead><tr><th>台番号</th><th>機種名</th><th>累計合算</th><th>累計REG</th><th>累計差枚</th><th>期待度</th></tr></thead>\n'
        '  <tbody>'+(j_comb_rows or no6)+'</tbody></table>\n'
        '</section></div>\n'

        '</div>\n'

        '<div class="disc">⚠️ '+disclaimer+'</div>\n'
        '<script>\n'+js+'\n</script>\n'
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
