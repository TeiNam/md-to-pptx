"""공통 테스트 픽스처(fixture) 및 설정."""

import tempfile
from pathlib import Path

import pytest
from pptx import Presentation


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """임시 디렉토리를 제공하는 픽스처."""
    return tmp_path


@pytest.fixture
def sample_pptx(tmp_path: Path) -> Path:
    """기본 플레이스홀더가 포함된 샘플 PPTX 템플릿 파일을 생성하는 픽스처."""
    pptx_path = tmp_path / "sample_template.pptx"
    prs = Presentation()
    prs.save(str(pptx_path))
    return pptx_path


@pytest.fixture
def sample_markdown() -> str:
    """샘플 마크다운 텍스트를 제공하는 픽스처."""
    return (
        "# 테스트 문서\n\n"
        "## 섹션 1\n\n"
        "본문 텍스트입니다.\n\n"
        "- 항목 1\n"
        "- 항목 2\n"
        "  - 하위 항목\n\n"
        "```python\nprint('hello')\n```\n"
    )
