
import json, logging, os, sys
from datetime import datetime
from pathlib import Path
from core.logger import setup, RunLog

log = setup("logs")
rlog = RunLog("logs")
logger = logging.getLogger("main")

HALL_NAME           = os.environ.get("HALL_NAME", "有楽町UNO")
SPREADSHEET_ID      = os.environ.get("SPREADSHEET_ID", "")
SERVICE_ACCOUNT_JSON= os.environ.get("SERVICE_ACCOUNT_JSON", "")
X_BEARER_TOKEN      = os.environ.get("X_BEARER_TOKEN", "")
USE_X_API           = os.environ.get("USE_X_API", "false").lower() == "true"
DAYS_BACK           = int(os.environ.get("DAYS_BACK", "30"))

def _setup_sa():
    path = Path("service_account.json")
    if path.exists(): return str(path)
    if SERVICE_ACCOUNT_JSON:
        path.write_text(SERVICE_ACCOUNT_JSON, encoding="utf-8")
        logger.info("service_account.json を生成")
        return str(path)
    return ""

def main():
    logger.info("="*60)
    logger.info(f"🎰 AIホール分析システム — {HALL_NAME}")
    logger.info(f"   実行日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    logger.info("="*60)

    from config.halls import HALLS
    cfg = HALLS.get(HALL_NAME)
    if not cfg:
        logger.error(f"未定義のホール: {HALL_NAME}")
        sys.exit(1)

    from core.compliance import check
    for url in ["https://ana-slo.com/", "https://x.com/"]:
        result = check(url)
        rlog.compliance("COMPLIANCE", result)
        if not result.is_allowed():
            rlog.blocked("AUTO_SCRAPING", url, result.reason, result.alternative)

    logger.info("【Step 2】アナスロデータ読み込み")
    records = []
    try:
        from importers.csv_importer import load_hall_data
        records = load_hall_data(HALL_NAME, cfg)
        rlog.info("CSV_IMPORT", f"{len(records)}件読み込み")
        if not records:
            rlog.warn("CSV_IMPORT", "データ0件",
                detail={"action": f"data/{cfg.data_dir}/ にCSVを配置してください"})
    except Exception as e:
        rlog.error("CSV_IMPORT", str(e))
        logger.error(f"CSV読込エラー: {e}", exc_info=True)

    logger.info("【Step 3】X投稿データ取得")
    x_posts = []
    if cfg.x_username:
        if USE_X_API and X_BEARER_TOKEN:
            try:
                from importers.x_importer import fetch_x_posts
                x_posts = fetch_x_posts(cfg.x_username, days=DAYS_BACK)
                rlog.info("X_API", f"{len(x_posts)}件取得")
            except Exception as e:
                rlog.error("X_API", str(e))
        else:
            try:
                from importers.x_importer import load_x_csv
                x_posts = load_x_csv(cfg.data_dir)
                rlog.info("X_CSV", f"{len(x_posts)}件読み込み")
            except Exception as e:
                rlog.error("X_CSV", str(e))

    logger.info("【Step 4】分析実行")
    analysis = {}
    if records:
        try:
            from analysis.engine import run
            analysis = run(records, x_posts, cfg)
            rlog.info("ANALYSIS", "完了", detail={
                "record_count": len(records),
                "today_targets": len(analysis.get("today_targets", [])),
            })
            Path("logs").mkdir(exist_ok=True)
            Path("logs/analysis_result.json").write_text(
                json.dumps(analysis, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")
        except Exception as e:
            rlog.error("ANALYSIS", str(e))
            logger.error(f"分析エラー: {e}", exc_info=True)
    else:
        rlog.warn("ANALYSIS", "データ0件のためスキップ")

    logger.info("【Step 5】ダッシュボード生成")
    try:
        from dashboard.generate import main as gen_dashboard
        gen_dashboard()
        rlog.info("DASHBOARD", "生成完了")
    except Exception as e:
        rlog.error("DASHBOARD", str(e))

    if SPREADSHEET_ID and analysis:
        logger.info("【Step 6】スプレッドシート更新")
        sa_file = _setup_sa()
        if sa_file:
            try:
                from sheets.writer import push
                push(SPREADSHEET_ID, analysis, x_posts, sa_file)
                rlog.info("SHEETS", "更新完了")
            except Exception as e:
                rlog.error("SHEETS", str(e))
                logger.error(f"スプレッドシートエラー: {e}", exc_info=True)
        else:
            rlog.warn("SHEETS", "SERVICE_ACCOUNT_JSON未設定")
    else:
        if not SPREADSHEET_ID:
            logger.info("SPREADSHEET_ID未設定 → スプレッドシートスキップ")

    log_path = rlog.save()
    summary = rlog.summary()
    logger.info("="*60)
    logger.info(f"実行サマリ: {summary['counts']}")
    if summary["blocked_steps"]:
        logger.warning(f"⚠️  自動取得中止ステップ: {summary['blocked_steps']}")
    logger.info(f"ログ: {log_path}")
    if summary.get("has_error"):
        sys.exit(1)

if __name__ == "__main__":
    main()
