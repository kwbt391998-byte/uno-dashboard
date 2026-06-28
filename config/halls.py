"""
config/halls.py — ホール設定（新ホール追加はここだけ）
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class HallConfig:
    name: str
    short_name: str
    x_username: Optional[str]
    anaslo_url: Optional[str]
    data_dir: str
    hi_set_min_games: int = 5000
    hi_set_min_diff: int = 1000
    hi_set_min_conditions: int = 2
    juggler_reg_threshold: float = 250.0
    event_days: list = field(default_factory=list)
    event_label: str = ""
    juggler_keywords: list = field(default_factory=lambda: [
        "マイジャグ","アイムジャグ","ファンキー","ゴーゴー","ジャグラー"
    ])

HALLS = {
    "有楽町UNO": HallConfig(
        name="有楽町UNO",
        short_name="yuurakucho_uno",
        x_username="sl_u_yuurakucho",
        anaslo_url="https://ana-slo.com/ホールデータ/東京都/有楽町uno-データ一覧/",
        data_dir="yuurakucho_uno",
        event_days=[1,11,21],
        event_label="1の付く日",
    ),
}
DEFAULT_HALL = "有楽町UNO"
