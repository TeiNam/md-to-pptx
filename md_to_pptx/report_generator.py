"""
보고서 생성기 모듈.

전체 파이프라인을 조율하여 마크다운 파일과 PPT 템플릿으로
보고서 PPTX를 자동 생성한다.
"""

import logging
import os
import time
import warnings

from md_to_pptx.content_summarizer import ContentSummarizer
from md_to_pptx.exceptions import InputFileNotFoundError
from md_to_pptx.font_manager import FontManager
from md_to_pptx.markdown_parser import MarkdownParser
from md_to_pptx.models import GenerationResult
from md_to_pptx.slide_composer import SlideComposer
from md_to_pptx.template_analyzer import TemplateAnalyzer

logger = logging.getLogger(__name__)


class ReportGenerator:
    """마크다운 → PPTX 보고서 생성 파이프라인을 조율하는 클래스."""

    def __init__(self, bedrock_client=None) -> None:
        """
        ReportGenerator를 초기화한다.

        Args:
            bedrock_client: Bedrock API 클라이언트 (테스트 시 mock 주입 가능)
        """
        self._bedrock_client = bedrock_client

    def generate(
        self,
        template_path: str,
        markdown_path: str,
        output_path: str | None = None,
        font_name: str | None = None,
        confirm_overwrite: bool = False,
    ) -> GenerationResult:
        """
        마크다운 파일과 PPT 템플릿으로 보고서 PPTX를 생성한다.

        Args:
            template_path: PPT 템플릿 파일 경로
            markdown_path: 마크다운 파일 경로
            output_path: 출력 파일 경로 (None이면 자동 생성)
            font_name: 한국어 폰트명 (None이면 기본 폰트)
            confirm_overwrite: 출력 파일 중복 시 덮어쓰기 허용 여부

        Returns:
            GenerationResult: 파일 경로, 슬라이드 수, 소요 시간, 경고 목록

        Raises:
            FileNotFoundError: 입력 파일이 존재하지 않을 때
        """
        start_time = time.time()
        collected_warnings: list[str] = []

        # 1. 입력 파일 존재 여부 검증
        if not os.path.isfile(template_path):
            raise InputFileNotFoundError(template_path)
        if not os.path.isfile(markdown_path):
            raise InputFileNotFoundError(markdown_path)

        # 2. 출력 경로 결정
        if output_path is None:
            output_path = self._generate_output_path(markdown_path)
        logger.info("출력 경로: %s", output_path)

        # 3. 출력 파일 중복 확인
        if os.path.exists(output_path) and not confirm_overwrite:
            raise FileExistsError(
                f"출력 파일이 이미 존재합니다: {output_path}"
            )

        # 경고 수집을 위한 컨텍스트
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # 4. 템플릿 분석
            logger.info("템플릿 분석 중: %s", template_path)
            analyzer = TemplateAnalyzer()
            template_info = analyzer.analyze(template_path)

            # 5. 마크다운 파싱
            logger.info("마크다운 파싱 중: %s", markdown_path)
            parser = MarkdownParser()
            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()
            document = parser.parse(markdown_text)

            # 6. 콘텐츠 요약
            logger.info("콘텐츠 요약 중...")
            summarizer = ContentSummarizer(
                bedrock_client=self._bedrock_client
            )
            summarized = summarizer.summarize(document)

            # 7. 슬라이드 구성
            logger.info("슬라이드 구성 중...")
            font_manager = FontManager(font_name=font_name)
            composer = SlideComposer(font_manager)
            prs = composer.compose(template_info, summarized, template_path)

            # 8. PPTX 저장
            logger.info("PPTX 저장 중: %s", output_path)
            # 출력 디렉토리가 없으면 자동 생성
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            prs.save(output_path)

            # 경고 수집
            for warning in w:
                collected_warnings.append(str(warning.message))

        elapsed = time.time() - start_time
        slide_count = len(prs.slides)

        logger.info(
            "보고서 생성 완료: %d개 슬라이드, %.2f초 소요",
            slide_count,
            elapsed,
        )

        return GenerationResult(
            output_path=output_path,
            slide_count=slide_count,
            elapsed_seconds=elapsed,
            warnings=collected_warnings,
        )

    @staticmethod
    def _generate_output_path(markdown_path: str) -> str:
        """마크다운 파일명 기반으로 출력 경로를 자동 생성한다."""
        base = os.path.splitext(os.path.basename(markdown_path))[0]
        directory = os.path.dirname(markdown_path) or "."
        return os.path.join(directory, f"{base}_report.pptx")
