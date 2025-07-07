"""
로깅 설정
"""

import logging
import logging.config
from pathlib import Path

from app.config import settings

# 로그 디렉토리 생성
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


def get_logging_config():
    """환경에 따른 로깅 설정 반환"""
    # JSON formatter 사용 가능 여부 확인
    try:
        import pythonjsonlogger.jsonlogger  # noqa: F401

        json_formatter_available = True
    except ImportError:
        json_formatter_available = False

    formatters = {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }

    # JSON formatter가 사용 가능한 경우 추가
    if json_formatter_available:
        formatters["json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(funcName)s %(message)s",
        }

    # 핸들러 설정
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    }

    # JSON formatter가 있으면 JSON 로그 파일 핸들러 추가
    if json_formatter_available:
        handlers["json_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/app.json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        }

    app_handlers = ["console", "file", "error_file"]
    if json_formatter_available:
        app_handlers.append("json_file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": app_handlers,
                "propagate": False,
            },
            "uvicorn": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "DEBUG" if settings.debug else "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }


def setup_logging():
    """로깅 설정 초기화"""
    config = get_logging_config()
    logging.config.dictConfig(config)

    # 앱 로거 반환
    logger = logging.getLogger("app")

    # JSON formatter 사용 가능 여부 로그
    try:
        import pythonjsonlogger.jsonlogger  # noqa: F401

        logger.info("로깅 시스템이 초기화되었습니다. (JSON 포맷 지원)")
    except ImportError:
        logger.info("로깅 시스템이 초기화되었습니다. (텍스트 포맷만 지원)")

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """로거 인스턴스 반환"""
    if name:
        return logging.getLogger(f"app.{name}")
    return logging.getLogger("app")
