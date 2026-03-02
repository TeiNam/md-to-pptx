"""
콘텐츠 요약 모듈.

Amazon Bedrock API를 호출하여 파싱된 마크다운 문서를
보고서용 슬라이드 단위로 요약한다.

자격 증명 우선순위:
1. .env 파일 (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
2. boto3 기본 체인 (환경 변수, ~/.aws/credentials, AWS SSO, IAM 역할 등)
"""

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError, ReadTimeoutError
from botocore.config import Config

from md_to_pptx.env_loader import load_env

load_env()

from md_to_pptx.exceptions import BedrockAPIError, BedrockTimeoutError
from md_to_pptx.models import (
    LayoutInfo,
    ParsedDocument,
    PlaceholderType,
    Section,
    MarkdownNode,
    NodeType,
    SlideContent,
    SummarizedContent,
    TemplateInfo,
)

logger = logging.getLogger(__name__)

# 슬라이드 수 제한 상수
MIN_SLIDES = 3
MAX_SLIDES_LIMIT = 12

# Bedrock 모델 ID (우선순위: .env BEDROCK_MODEL_ID → 기본값 → fallback)
PRIMARY_MODEL_ID = "global.anthropic.claude-opus-4-6-v1"
FALLBACK_MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"


def _resolve_model_id() -> str:
    """환경 변수 또는 기본값에서 Bedrock 모델 ID를 결정한다."""
    env_model = os.environ.get("BEDROCK_MODEL_ID", "").strip()
    if env_model:
        logger.info(".env에서 모델 ID 로드: %s", env_model)
        return env_model
    logger.info("기본 모델 ID 사용: %s", PRIMARY_MODEL_ID)
    return PRIMARY_MODEL_ID


class ContentSummarizer:
    """Amazon Bedrock을 활용하여 문서를 슬라이드 단위로 요약하는 클래스."""

    def __init__(
        self,
        bedrock_client: Any | None = None,
        timeout: int = 120,
    ) -> None:
        """
        ContentSummarizer 초기화.

        Args:
            bedrock_client: boto3 bedrock-runtime 클라이언트 (None이면 자동 생성)
            timeout: API 호출 타임아웃 (초, 기본 30)
        """
        self._timeout = timeout
        self._model_id = _resolve_model_id()
        if bedrock_client is not None:
            self._client = bedrock_client
        else:
            # 타임아웃 설정을 포함한 클라이언트 생성
            config = Config(
                read_timeout=timeout,
                connect_timeout=timeout,
            )
            self._client = boto3.client("bedrock-runtime", config=config)
        logger.info("ContentSummarizer 초기화 완료 (타임아웃: %d초)", timeout)

    def summarize(
        self,
        document: ParsedDocument,
        max_slides: int = 12,
        template_info: TemplateInfo | None = None,
    ) -> SummarizedContent:
        """
        파싱된 문서를 슬라이드 단위로 변환한다.
        원문을 최대한 보존하면서 슬라이드에 적합하게 분배한다.

        Args:
            document: 파싱된 마크다운 문서
            max_slides: 최대 슬라이드 수 (기본 50)
            template_info: 템플릿 분석 결과 (레이아웃 정보를 AI에 전달)

        Returns:
            SummarizedContent: 슬라이드별 콘텐츠

        Raises:
            BedrockAPIError: API 호출 실패
            BedrockTimeoutError: 타임아웃 초과
        """
        max_slides = max(MIN_SLIDES, min(max_slides, MAX_SLIDES_LIMIT))
        logger.info(
            "문서 변환 시작: '%s' (최대 %d 슬라이드)",
            document.title,
            max_slides,
        )

        # 문서를 마크다운 텍스트로 변환
        markdown_text = self._document_to_markdown(document)
        logger.debug("마크다운 텍스트 변환 완료 (%d자)", len(markdown_text))

        # 레이아웃 정보 텍스트 생성
        layout_desc = self._describe_layouts(template_info)

        # Bedrock API 호출
        prompt = self._build_prompt(
            document.title, markdown_text, max_slides, layout_desc
        )
        response_text = self._invoke_bedrock(prompt)

        # 응답 파싱
        slides = self._parse_response(response_text, document.title, max_slides)
        logger.info("문서 요약 완료: %d개 슬라이드 생성", len(slides))

        return SummarizedContent(
            slides=slides,
            original_title=document.title,
        )

    def _document_to_markdown(self, document: ParsedDocument) -> str:
        """ParsedDocument를 마크다운 텍스트로 변환한다."""
        lines: list[str] = []
        if document.title:
            lines.append(f"# {document.title}")
            lines.append("")

        for section in document.sections:
            self._section_to_markdown(section, lines)

        return "\n".join(lines)

    def _section_to_markdown(
        self, section: Section, lines: list[str]
    ) -> None:
        """섹션을 마크다운 텍스트로 변환한다."""
        prefix = "#" * section.level
        lines.append(f"{prefix} {section.title}")
        lines.append("")

        for node in section.nodes:
            self._node_to_markdown(node, lines)

    def _node_to_markdown(
        self, node: MarkdownNode, lines: list[str], indent: int = 0
    ) -> None:
        """마크다운 노드를 텍스트로 변환한다."""
        if node.type == NodeType.PARAGRAPH:
            # 인라인 서식 children이 있으면 마크다운 텍스트로 변환
            if node.children:
                text = self._inline_children_to_markdown(node.children)
                lines.append(text)
            else:
                lines.append(node.content)
            lines.append("")
        elif node.type == NodeType.CODE_BLOCK:
            lang = node.language or ""
            lines.append(f"```{lang}")
            lines.append(node.content)
            lines.append("```")
            lines.append("")
        elif node.type in (NodeType.UNORDERED_LIST, NodeType.ORDERED_LIST):
            for i, child in enumerate(node.children):
                prefix_str = "  " * indent
                if node.type == NodeType.ORDERED_LIST:
                    prefix_str += f"{i + 1}. "
                else:
                    prefix_str += "- "
                lines.append(f"{prefix_str}{child.content}")
                # 중첩 목록 처리
                for sub in child.children:
                    if sub.type in (
                        NodeType.UNORDERED_LIST,
                        NodeType.ORDERED_LIST,
                    ):
                        self._node_to_markdown(sub, lines, indent + 1)
            lines.append("")
        elif node.type == NodeType.TABLE:
            lines.append(node.content)
            lines.append("")

    @staticmethod
    def _inline_children_to_markdown(children: list[MarkdownNode]) -> str:
        """인라인 자식 노드 목록을 마크다운 텍스트로 변환한다."""
        parts: list[str] = []
        for child in children:
            parts.append(ContentSummarizer._inline_to_markdown(child))
        return "".join(parts)

    @staticmethod
    def _inline_to_markdown(node: MarkdownNode) -> str:
        """인라인 노드를 마크다운 텍스트로 변환한다."""
        if node.type == NodeType.TEXT:
            return node.content
        elif node.type == NodeType.BOLD:
            return f"**{node.content}**"
        elif node.type == NodeType.ITALIC:
            return f"*{node.content}*"
        elif node.type == NodeType.INLINE_CODE:
            return f"`{node.content}`"
        return node.content

    def _describe_layouts(
        self, template_info: TemplateInfo | None
    ) -> str:
        """템플릿 레이아웃 정보를 AI 프롬프트용 텍스트로 변환한다."""
        if template_info is None or not template_info.layouts:
            return ""

        lines: list[str] = []
        for layout in template_info.layouts:
            # 플레이스홀더 유형 요약
            ph_types = [p.type.value for p in layout.placeholders
                        if p.type not in (PlaceholderType.OTHER,)]
            if not ph_types:
                continue
            lines.append(
                f"- \"{layout.name}\": {', '.join(ph_types)}"
            )
        return "\n".join(lines)

    def _build_prompt(
        self, title: str, markdown_text: str, max_slides: int,
        layout_desc: str = "",
    ) -> str:
        """Bedrock API에 전달할 프롬프트를 생성한다."""
        layout_section = ""
        if layout_desc:
            layout_section = (
                f"\n## 사용 가능한 레이아웃\n"
                f"아래는 템플릿에 정의된 슬라이드 레이아웃 목록입니다.\n"
                f"각 슬라이드에 가장 적합한 레이아웃을 선택하여 "
                f"layout_name 필드에 정확한 이름을 지정하세요.\n"
                f"{layout_desc}\n"
            )

        return (
            f"다음 마크다운 문서를 프레젠테이션 슬라이드로 변환해주세요.\n\n"
            f"## 핵심 원칙\n"
            f"문서 내용을 최대 {max_slides}장의 슬라이드에 맞게 요약하세요.\n"
            f"핵심 데이터와 표는 반드시 보존하되, 슬라이드에 적합한 분량으로 정리하세요.\n\n"
            f"## 규칙\n"
            f"1. 첫 번째 슬라이드는 표지(cover)입니다. 문서 제목만 포함합니다.\n"
            f"2. 나머지 슬라이드에 본문을 논리적 섹션 단위로 분배하세요.\n"
            f"3. 총 슬라이드 수는 최소 3장, 최대 {max_slides}장입니다.\n"
            f"4. 수치, 날짜, 고유명사, 기술 용어를 정확히 보존하세요.\n"
            f"5. 제목 계층 구조를 유지하세요.\n"
            f"6. 하나의 주제가 여러 슬라이드에 분산되지 않도록 하세요.\n"
            f"7. **표(table)는 반드시 마크다운 표 형식(| 헤더 | ... |)으로 보존하세요.** "
            f"표를 불릿 리스트로 변환하지 마세요.\n"
            f"8. 하나의 슬라이드에 표는 최대 1개만 포함하세요.\n"
            f"9. 각 슬라이드에 적합한 레이아웃을 layout_name으로 지정하세요.\n"
            f"{layout_section}\n"
            f"## 출력 형식\n"
            f"반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.\n"
            f'{{"slides": [\n'
            f'  {{"title": "슬라이드 제목", '
            f'"body": ["항목1", "| 헤더1 | 헤더2 |", "| --- | --- |", "| 값1 | 값2 |"], '
            f'"is_cover": true/false, "notes": "발표자 노트", '
            f'"layout_name": "레이아웃 이름"}}\n'
            f"]}}\n\n"
            f"## 문서 제목\n{title}\n\n"
            f"## 문서 내용\n{markdown_text}"
        )

    def _invoke_bedrock(self, prompt: str) -> str:
        """Bedrock API를 호출하여 응답 텍스트를 반환한다. 기본 모델 실패 시 fallback 모델로 재시도한다."""
        logger.info("Bedrock API 호출 시작 (모델: %s)", self._model_id)

        # Anthropic Claude 메시지 형식
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 16384,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        })

        # 시도할 모델 목록: 현재 모델 → fallback (중복 제거)
        models_to_try = [self._model_id]
        if self._model_id != FALLBACK_MODEL_ID:
            models_to_try.append(FALLBACK_MODEL_ID)

        last_error: Exception | None = None
        for model_id in models_to_try:
            try:
                response = self._client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=request_body,
                )
                logger.info("Bedrock API 응답 수신 완료 (모델: %s)", model_id)

                # 응답 파싱
                response_body = json.loads(response["body"].read())
                stop_reason = response_body.get("stop_reason", "")
                if stop_reason == "max_tokens":
                    logger.warning(
                        "응답이 max_tokens에 의해 잘림 (모델: %s)", model_id
                    )
                content = response_body.get("content", [])
                if content and isinstance(content, list):
                    text = content[0].get("text", "")
                else:
                    text = ""
                return text

            except ReadTimeoutError:
                logger.error("Bedrock API 타임아웃 발생 (모델: %s)", model_id)
                last_error = BedrockTimeoutError()
                # fallback 모델로 재시도
                if model_id != models_to_try[-1]:
                    logger.info("fallback 모델로 재시도: %s", models_to_try[-1])
                    continue
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "UNKNOWN")
                logger.warning(
                    "Bedrock API 오류 (모델: %s): %s", model_id, error_code
                )
                retryable = error_code in (
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                )
                last_error = BedrockAPIError(
                    error_code=error_code, retryable=retryable
                )
                last_error.__cause__ = e
                # fallback 모델로 재시도
                if model_id != models_to_try[-1]:
                    logger.info("fallback 모델로 재시도: %s", models_to_try[-1])
                    continue
            except Exception as e:
                logger.error("Bedrock API 예기치 않은 오류: %s", str(e))
                last_error = BedrockAPIError(
                    error_code="UNKNOWN", retryable=False
                )
                last_error.__cause__ = e

        # 모든 모델 시도 실패
        raise last_error

    def _parse_response(
        self,
        response_text: str,
        original_title: str,
        max_slides: int,
    ) -> list[SlideContent]:
        """Bedrock 응답 텍스트를 SlideContent 리스트로 변환한다."""
        logger.debug("응답 파싱 시작")

        # JSON 블록 추출 (코드 블록 내부일 수 있음)
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 잘린 JSON 복구 시도: 마지막 완전한 슬라이드 객체까지 잘라서 파싱
            logger.warning("JSON 파싱 실패, 잘린 JSON 복구 시도")
            data = self._try_recover_truncated_json(text)
            if data is None:
                logger.warning("JSON 복구 실패, 기본 슬라이드 생성")
                return self._create_fallback_slides(original_title)

        raw_slides = data.get("slides", [])
        if not raw_slides:
            logger.warning("응답에 슬라이드 데이터 없음, 기본 슬라이드 생성")
            return self._create_fallback_slides(original_title)

        slides: list[SlideContent] = []
        for i, raw in enumerate(raw_slides):
            title = raw.get("title", "")
            body = raw.get("body", [])
            # body가 문자열인 경우 리스트로 변환
            if isinstance(body, str):
                body = [body]
            is_cover = raw.get("is_cover", False)
            notes = raw.get("notes", "")
            layout_name = raw.get("layout_name", "")
            slides.append(
                SlideContent(
                    title=title,
                    body=body,
                    is_cover=bool(is_cover),
                    notes=notes,
                    layout_name=layout_name,
                )
            )

        # 슬라이드가 없으면 기본 슬라이드 생성
        if not slides:
            return self._create_fallback_slides(original_title)

        # 첫 슬라이드는 항상 표지로 설정
        if not slides[0].is_cover:
            slides[0] = SlideContent(
                title=slides[0].title,
                body=slides[0].body,
                is_cover=True,
                notes=slides[0].notes,
            )

        logger.debug("응답 파싱 완료: %d개 슬라이드", len(slides))
        return slides

    @staticmethod
    def _try_recover_truncated_json(text: str) -> dict | None:
        """잘린 JSON에서 마지막 완전한 슬라이드 객체까지 복구를 시도한다."""
        # 마지막으로 완전한 슬라이드 객체가 끝나는 위치를 찾음
        # 패턴: }, 또는 }] 앞의 }를 찾아서 거기까지 잘라냄
        last_complete = text.rfind('"is_cover"')
        if last_complete == -1:
            return None

        # is_cover 이후 } 찾기
        brace_pos = text.find("}", last_complete)
        if brace_pos == -1:
            return None

        truncated = text[:brace_pos + 1] + "]}"
        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

        # 두 번째 시도: 마지막 완전한 }를 찾아서 배열 닫기
        for i in range(len(text) - 1, -1, -1):
            if text[i] == "}":
                candidate = text[:i + 1] + "]}"
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
        return None

    def _create_fallback_slides(
        self, original_title: str
    ) -> list[SlideContent]:
        """API 응답 파싱 실패 시 기본 슬라이드를 생성한다."""
        return [
            SlideContent(
                title=original_title,
                body=[],
                is_cover=True,
                notes="",
            )
        ]
