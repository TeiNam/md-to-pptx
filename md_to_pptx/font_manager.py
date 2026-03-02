"""
폰트 관리 모듈.

한국어 폰트 설정 및 적용을 관리한다.
기본 폰트는 .env의 DEFAULT_FONT 값을 사용하며,
미설정 시 "나눔고딕(NanumGothic)"을 기본값으로 사용한다.
사용자 지정 폰트(CLI -f 옵션)가 있으면 우선 적용하고,
미설치 시 경고와 함께 기본 폰트로 대체한다.
"""

import logging
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

from pptx.util import Pt

from md_to_pptx.env_loader import load_env

load_env()

from md_to_pptx.exceptions import FontNotFoundWarning
from md_to_pptx.models import FontConfig

logger = logging.getLogger(__name__)


def _get_default_font() -> str:
    """환경 변수에서 기본 폰트를 결정한다. 미설정 시 나눔고딕."""
    return os.environ.get("DEFAULT_FONT", "").strip() or "나눔고딕"


def _get_default_mono_font() -> str:
    """환경 변수에서 기본 고정폭 폰트를 결정한다. 미설정 시 D2Coding."""
    return os.environ.get("DEFAULT_MONO_FONT", "").strip() or "D2Coding"


class FontManager:
    """한국어 폰트 설정 및 적용을 관리하는 클래스."""

    DEFAULT_FONT = _get_default_font()
    DEFAULT_MONO_FONT = _get_default_mono_font()
    MIN_FONT_SIZE = Pt(10)

    def __init__(self, font_name: str | None = None) -> None:
        """
        FontManager를 초기화한다.

        Args:
            font_name: 사용자 지정 한국어 폰트명. None이면 기본 폰트 사용.
        """
        self._font_name = font_name
        self._resolved_font = self._resolve_font(font_name)
        logger.info("폰트 설정 완료: korean_font='%s', mono_font='%s'",
                     self._resolved_font, self.DEFAULT_MONO_FONT)

    def _resolve_font(self, font_name: str | None) -> str:
        """
        사용자 지정 폰트를 검증하고 최종 폰트명을 결정한다.

        사용자 지정 폰트가 있으면 시스템 설치 여부를 확인하고,
        미설치 시 FontNotFoundWarning 경고 후 기본 폰트로 대체한다.

        Args:
            font_name: 사용자 지정 폰트명 또는 None

        Returns:
            최종 사용할 폰트명
        """
        if font_name is None:
            logger.debug("사용자 지정 폰트 없음, 기본 폰트 '%s' 사용", self.DEFAULT_FONT)
            return self.DEFAULT_FONT

        if self.is_font_available(font_name):
            logger.info("사용자 지정 폰트 '%s' 확인됨, 우선 적용", font_name)
            return font_name

        # 미설치 폰트: 경고 발생 후 기본 폰트 대체
        logger.warning("폰트 '%s'을(를) 찾을 수 없음, 기본 폰트 '%s'(으)로 대체",
                        font_name, self.DEFAULT_FONT)
        warnings.warn(FontNotFoundWarning(font_name))
        return self.DEFAULT_FONT

    def get_font_config(self) -> FontConfig:
        """
        현재 폰트 설정을 FontConfig 객체로 반환한다.

        영문/한국어 혼합 텍스트에서도 일관된 폰트가 적용되도록
        korean_font와 mono_font를 함께 설정한다.

        Returns:
            FontConfig: 현재 폰트 설정
        """
        config = FontConfig(
            korean_font=self._resolved_font,
            mono_font=self.DEFAULT_MONO_FONT,
        )
        logger.debug("FontConfig 반환: %s", config)
        return config

    def is_font_available(self, font_name: str) -> bool:
        """
        시스템에 폰트가 설치되어 있는지 확인한다.

        플랫폼별로 다른 방법을 사용한다:
        - Linux/macOS: fc-list 명령어로 확인
        - Windows: 레지스트리 또는 폰트 디렉토리 확인
        - fc-list 미설치 시: 일반적인 폰트 디렉토리에서 파일 검색

        Args:
            font_name: 확인할 폰트명

        Returns:
            폰트 설치 여부
        """
        # fc-list 명령어로 확인 시도
        if shutil.which("fc-list"):
            return self._check_font_with_fc_list(font_name)

        # fc-list 미사용 시 폰트 디렉토리 직접 검색
        return self._check_font_in_directories(font_name)

    def _check_font_with_fc_list(self, font_name: str) -> bool:
        """fc-list 명령어로 폰트 설치 여부를 확인한다."""
        try:
            result = subprocess.run(
                ["fc-list", ":", "family"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # 폰트 패밀리 목록에서 대소문자 무시 검색
                font_families = result.stdout.lower()
                return font_name.lower() in font_families
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug("fc-list 실행 실패: %s", e)

        return False

    def _check_font_in_directories(self, font_name: str) -> bool:
        """시스템 폰트 디렉토리에서 폰트 파일을 검색한다."""
        font_dirs: list[Path] = []

        if sys.platform == "win32":
            # Windows 폰트 디렉토리
            windir = Path("C:/Windows/Fonts")
            if windir.exists():
                font_dirs.append(windir)
        elif sys.platform == "darwin":
            # macOS 폰트 디렉토리
            font_dirs.extend([
                Path("/Library/Fonts"),
                Path.home() / "Library" / "Fonts",
                Path("/System/Library/Fonts"),
            ])
        else:
            # Linux 폰트 디렉토리
            font_dirs.extend([
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".local" / "share" / "fonts",
                Path.home() / ".fonts",
            ])

        # 폰트 파일 확장자
        font_extensions = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
        font_name_lower = font_name.lower()

        for font_dir in font_dirs:
            if not font_dir.exists():
                continue
            try:
                for font_file in font_dir.rglob("*"):
                    if (font_file.suffix.lower() in font_extensions
                            and font_name_lower in font_file.stem.lower()):
                        return True
            except PermissionError:
                logger.debug("폰트 디렉토리 접근 권한 없음: %s", font_dir)

        return False
