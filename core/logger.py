"""
core/logger.py — 構造化ログ
"""
import json, logging, sys
from datetime import datetime
from pathlib import Path

def setup(log_dir="logs", level=logging.INFO):
    Path(log_dir).mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)
        fh = logging.FileHandler(
            Path(log_dir)/f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    return root

class RunLog:
    def __init__(self, log_dir="logs"):
        self._entries = []
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)
        self._logger = logging.getLogger("runlog")
    def _add(self, level, step, msg, detail=None):
        e = {"ts":datetime.now().isoformat(),"level":level,"step":step,"msg":msg}
        if detail: e["detail"] = detail
        self._entries.append(e)
    def info(self, step, msg, detail=None):
        self._logger.info(f"[{step}] {msg}"); self._add("INFO",step,msg,detail)
    def warn(self, step, msg, detail=None):
        self._logger.warning(f"[{step}] ⚠️ {msg}"); self._add("WARN",step,msg,detail)
    def error(self, step, msg, detail=None):
        self._logger.error(f"[{step}] ❌ {msg}"); self._add("ERROR",step,msg,detail)
    def blocked(self, step, url, reason, alternative):
        self._logger.error(f"[BLOCKED] {step}: {url}")
        self._add("BLOCKED",step,f"自動取得中止: {url}",{"reason":reason,"alternative":alternative})
    def compliance(self, step, result):
        emoji = "✅" if result.is_allowed() else "🚫"
        self._add("COMPLIANCE",step,f"{emoji} {result.status.value}: {result.url}",result.to_dict())
    def save(self):
        path = self._log_dir/f"structured_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(self._entries,ensure_ascii=False,indent=2))
        return path
    def summary(self):
        counts = {}
        for e in self._entries: counts[e["level"]] = counts.get(e["level"],0)+1
        blocked = [e["step"] for e in self._entries if e["level"]=="BLOCKED"]
        return {"counts":counts,"blocked_steps":blocked,"has_error":counts.get("ERROR",0)>0}
