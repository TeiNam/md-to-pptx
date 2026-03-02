"""
FontManager 모듈 테스트.

속성 기반 테스트(Property-Based Test)와 단위 테스트를 포함한다.
- Property 16: 사용자 지정 폰트 우선 적용
- Property 17: 미설치 폰트 기본값 대체
- 단위 테스트: 기본 폰트가 "나눔고딕"인지 확인
"""

import warnings
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from md_to_pptx.exceptions import FontNotFoundWarning
from md_to_pptx.font_manager import FontManager


# === Hypothesis 전략 ===

# 유효한 폰트명 생성 전략 (빈 문자열 제외, 합리적인 길이)
valid_font_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"),
                           whitelist_characters="-_"),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip())


# === Property 16: 사용자 지정 폰트 우선 적용 ===


class TestProperty16UserFontPriority:
    """
    Property 16: 사용자 지정 폰트 우선 적용.

    유효한 폰트명 지정 시 FontConfig에 반영되는지 검증한다.
    is_font_available을 mock하여 True를 반환하도록 설정한다.

    Feature: md-to-pptx-report-generator, Property 16: 사용자 지정 폰트 우선 적용
    **Validates: Requirements 5.2**
    """

    @given(font_name=valid_font_names)
    @settings(max_examples=100)
    def test_user_font_reflected_in_config(self, font_name: str) -> None:
        """유효한 폰트명 지정 시 FontConfig.korean_font에 해당 폰트가 반영된다."""
        with patch.object(FontManager, "is_font_available", return_value=True):
            manager = FontManager(font_name=font_name)
            config = manager.get_font_config()

            # 사용자 지정 폰트가 FontConfig에 반영되어야 한다
            assert config.korean_font == font_name


# === Property 17: 미설치 폰트 기본값 대체 ===


class TestProperty17FallbackToDefault:
    """
    Property 17: 미설치 폰트 기본값 대체.

    미설치 폰트명에 대해 경고 발생 및 기본 폰트 대체를 검증한다.
    is_font_available을 mock하여 False를 반환하도록 설정한다.

    Feature: md-to-pptx-report-generator, Property 17: 미설치 폰트 기본값 대체
    **Validates: Requirements 5.3**
    """

    @given(font_name=valid_font_names)
    @settings(max_examples=100)
    def test_unavailable_font_falls_back_to_default(self, font_name: str) -> None:
        """미설치 폰트 지정 시 기본 폰트로 대체되고 FontNotFoundWarning이 발생한다."""
        with patch.object(FontManager, "is_font_available", return_value=False):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                manager = FontManager(font_name=font_name)
                config = manager.get_font_config()

                # 기본 폰트로 대체되어야 한다
                assert config.korean_font == FontManager.DEFAULT_FONT

                # FontNotFoundWarning이 발생해야 한다
                font_warnings = [
                    w for w in caught
                    if issubclass(w.category, FontNotFoundWarning)
                ]
                assert len(font_warnings) >= 1


# === 단위 테스트: 기본 폰트 확인 (요구사항 5.1) ===


class TestFontManagerDefaults:
    """FontManager 기본 설정 단위 테스트."""

    def test_default_font_is_malgun_gothic(self) -> None:
        """폰트명 미지정 시 기본 폰트가 '나눔고딕'이어야 한다."""
        # 환경 변수 격리: DEFAULT_FONT가 설정되어 있어도 기본값 테스트
        with patch.dict("os.environ", {}, clear=False):
            # DEFAULT_FONT 환경 변수 제거하여 기본값 사용
            import os
            env_backup = os.environ.pop("DEFAULT_FONT", None)
            try:
                # 클래스 속성 재설정
                from md_to_pptx.font_manager import _get_default_font
                original_default = FontManager.DEFAULT_FONT
                FontManager.DEFAULT_FONT = _get_default_font()
                manager = FontManager()
                config = manager.get_font_config()
                assert config.korean_font == "나눔고딕"
                FontManager.DEFAULT_FONT = original_default
            finally:
                if env_backup is not None:
                    os.environ["DEFAULT_FONT"] = env_backup

    def test_default_mono_font_is_d2coding(self) -> None:
        """기본 고정폭 폰트가 'D2Coding'이어야 한다."""
        import os
        env_backup = os.environ.pop("DEFAULT_MONO_FONT", None)
        try:
            from md_to_pptx.font_manager import _get_default_mono_font
            original_default = FontManager.DEFAULT_MONO_FONT
            FontManager.DEFAULT_MONO_FONT = _get_default_mono_font()
            manager = FontManager()
            config = manager.get_font_config()
            assert config.mono_font == "D2Coding"
            FontManager.DEFAULT_MONO_FONT = original_default
        finally:
            if env_backup is not None:
                os.environ["DEFAULT_MONO_FONT"] = env_backup

    def test_font_config_has_correct_default_sizes(self) -> None:
        """FontConfig의 기본 폰트 크기가 설계 문서와 일치해야 한다."""
        manager = FontManager()
        config = manager.get_font_config()

        assert config.title_size_pt == 28
        assert config.body_size_pt == 16
        assert config.code_size_pt == 12
        assert config.min_size_pt == 10
