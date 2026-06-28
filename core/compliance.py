"""
core/compliance.py — コンプライアンスチェック
"""
import logging
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class AccessStatus(Enum):
    ALLOWED  = "allowed"
    BLOCKED  = "blocked"
    API_ONLY = "api_only"
    MANUAL   = "manual_only"

@dataclass
class ComplianceResult:
    url: str
    status: AccessStatus
    reason: str
    alternative: str
    checked_at: str = ""
    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now().isoformat()
    def is_allowed(self):
        return self.status == AccessStatus.ALLOWED
    def to_dict(self):
        return {"url":self.url,"status":self.status.value,
                "reason":self.reason,"alternative":self.alternative}

KNOWN_POLICIES = {
    "ana-slo.com": ComplianceResult(
        url="https://ana-slo.com/",
        status=AccessStatus.MANUAL,
        reason="bot検出(Cloudflare)を実装。自動アクセスをブロックしている。",
        alternative="手動でCSVをdata/yuurakucho_uno/に配置してください",
    ),
    "x.com": ComplianceResult(
        url="https://x.com/",
        status=AccessStatus.API_ONLY,
        reason="X利用規約 Section 2.5 でスクレイピング明示禁止",
        alternative="X API v2(無料枠あり)またはdata/yuurakucho_uno/x_posts/に手動CSV",
    ),
}

def check(url):
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.replace("www.","")
    for known, result in KNOWN_POLICIES.items():
        if known in domain:
            emoji = "✅" if result.is_allowed() else "🚫"
            logger.warning(f"[COMPLIANCE] {emoji} {domain}: {result.status.value}")
            return result
    rp = urllib.robotparser.RobotFileParser()
    robots_url = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}/robots.txt"
    rp.set_url(robots_url)
    try:
        rp.read()
        allowed = rp.can_fetch("*", url)
        return ComplianceResult(url=url,
            status=AccessStatus.ALLOWED if allowed else AccessStatus.BLOCKED,
            reason=f"robots.txt: {'許可' if allowed else '禁止'}",
            alternative="" if allowed else "このURLへの自動アクセスは禁止されています")
    except Exception as e:
        return ComplianceResult(url=url, status=AccessStatus.ALLOWED,
            reason=f"robots.txt取得不可({e})", alternative="")
