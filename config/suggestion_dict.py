"""
config/suggestion_dict.py — 示唆キーワード辞書（自動追加対応）
"""
import json
from pathlib import Path

SUGGESTION_DICT = {
    "設定6":    ["設定6","6確","最高設定","MAX設定"],
    "設定456":  ["456","上位設定","高設定"],
    "ドラゴン": ["ドラゴン","龍","竜","dragon"],
    "虎":       ["虎","トラ","タイガー","tiger"],
    "猫":       ["猫","ネコ","cat"],
    "赤":       ["赤","レッド","red","紅"],
    "青":       ["青","ブルー","blue","蒼"],
    "金":       ["金","ゴールド","gold","黄金"],
    "虹":       ["虹","レインボー","rainbow"],
    "桜":       ["桜","さくら","cherry","花見"],
    "星":       ["星","star","★","☆"],
    "数字7":    ["⑦","7番","末尾7","ラッキー7"],
    "全台":     ["全台","全○","全◯","全丸"],
    "角台":     ["角台","角"],
    "据え置き": ["据え","据置","継続"],
    "イベント": ["イベント","感謝祭","周年","特日"],
    "ジャグラー系": ["ジャグラー","マイジャグ","アイム","ファンキー","ゴーゴー"],
    "末尾1": ["末尾1","尾数1"],
    "末尾3": ["末尾3","尾数3"],
    "末尾5": ["末尾5","尾数5"],
    "末尾7": ["末尾7","尾数7"],
    "リセット": ["リセット","全台変更","据えなし"],
}

DICT_FILE = Path("data/suggestion_dict_learned.json")

def load_dict():
    if DICT_FILE.exists():
        try:
            learned = json.loads(DICT_FILE.read_text(encoding="utf-8"))
            merged = dict(SUGGESTION_DICT)
            merged.update(learned)
            return merged
        except Exception:
            pass
    return dict(SUGGESTION_DICT)

def add_new_keyword(category, keyword):
    current = load_dict()
    if category not in current:
        current[category] = []
    if keyword not in current[category]:
        current[category].append(keyword)
        DICT_FILE.parent.mkdir(parents=True, exist_ok=True)
        DICT_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

def extract_keywords(text):
    if not text:
        return []
    found = []
    for category, keywords in load_dict().items():
        for kw in keywords:
            if kw in text:
                found.append((category, kw))
    return found
