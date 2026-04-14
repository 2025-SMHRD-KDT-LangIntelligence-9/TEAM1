from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from database import SessionLocal
from models import Correction
import logging

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30  # 기본 보존 기간 (7 / 30 / 90 선택 가능 - SFR-006)

def delete_expired_corrections():
    """보존 기간이 지난 교정 기록 자동 삭제 (매일 새벽 2시 실행)"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=DEFAULT_RETENTION_DAYS)
        deleted = db.query(Correction).filter(
            Correction.created_at < cutoff
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"[스케줄러] 만료 교정 기록 {deleted}건 삭제 완료 (기준: {cutoff.strftime('%Y-%m-%d')} 이전)")
    except Exception as e:
        db.rollback()
        logger.error(f"[스케줄러] 자동 삭제 중 오류 발생: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler(timezone="Asia/Seoul")

def start_scheduler():
    scheduler.add_job(
        delete_expired_corrections,
        trigger=CronTrigger(hour=2, minute=0),
        id="auto_delete_expired",
        replace_existing=True
    )
    scheduler.start()
    logger.info("[스케줄러] 자동 삭제 스케줄러 시작 (매일 02:00 KST)")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[스케줄러] 스케줄러 종료")
