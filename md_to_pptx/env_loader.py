"""
환경 변수 로드 공통 모듈.

프로젝트 루트의 .env 파일을 한 번만 로드하여
중복 로드를 방지한다.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_loaded = False


def load_env() -> None:
    """프로젝트 루트의 .env 파일을 로드한다. 이미 로드된 경우 건너뛴다."""
    global _loaded
    if _loaded:
        return

    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(".env 파일에서 환경 변수 로드 완료: %s", env_path)
    except ImportError:
        # python-dotenv 미설치 시 boto3 기본 체인 사용
        pass

    _loaded = True
