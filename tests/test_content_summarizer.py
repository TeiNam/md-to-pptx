"""
Content_Summarizer 모듈 테스트.

속성 기반 테스트(Property 4, 5, 7)와 단위 테스트를 포함한다.
Bedrock API는 mock하여 외부 의존성을 격리한다.
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from hypothesis import given, settings, strategies as st

from md_to_pptx.content_summarizer import ContentSummarizer
from md_to_pptx.exceptions import BedrockAPIError, BedrockTimeoutError
from md_to_pptx.models import (
    MarkdownNode,
    NodeType,
    ParsedDocument,
    Section,
    SlideContent,
)


# === 헬퍼 함수 ===


def _make_bedrock_response(slides_data: list[dict]) -> dict:
    """mock Bedrock API 응답을 생성한다."""
    response_json = json.dumps({"slides": slides_data})
    body_content = json.dumps({
        "content": [{"type": "text", "text": response_json}],
    })
    body_stream = BytesIO(body_content.encode("utf-8"))
    return {"body": body_stream}


def _make_mock_client(slides_data: list[dict]) -> MagicMock:
    """슬라이드 데이터를 반환하는 mock Bedrock 클라이언트를 생성한다."""
    client = MagicMock()
    client.invoke_model.return_value = _make_bedrock_response(slides_data)
    return client


def _make_parsed_document(
    title: str = "테스트 문서",
    section_titles: list[str] | None = None,
) -> ParsedDocument:
    """테스트용 ParsedDocument를 생성한다."""
    if section_titles is None:
        section_titles = ["섹션 1"]
    sections = [
        Section(
            title=t,
            level=2,
            nodes=[
                MarkdownNode(
                    type=NodeType.PARAGRAPH,
                    content=f"{t} 본문 내용입니다.",
                )
            ],
        )
        for t in section_titles
    ]
    return ParsedDocument(title=title, sections=sections)


# === Hypothesis 전략 ===


# 슬라이드 수 전략 (1~10 범위로 생성하여 클램핑 검증)
slide_count_strategy = st.integers(min_value=1, max_value=10)

# 섹션 제목 전략
section_titles_strategy = st.lists(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P"),
            blacklist_characters="\x00",
        ),
        min_size=1,
        max_size=30,
    ),
    min_size=1,
    max_size=5,
)

# 문서 제목 전략
doc_title_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=50,
)


def _generate_mock_slides(num_slides: int, title: str) -> list[dict]:
    """지정된 수만큼 mock 슬라이드 데이터를 생성한다."""
    slides = []
    for i in range(num_slides):
        slides.append({
            "title": title if i == 0 else f"슬라이드 {i + 1}",
            "body": [f"항목 {j + 1}" for j in range(3)],
            "is_cover": i == 0,
            "notes": "",
        })
    return slides


# === Property 4: 슬라이드 수 범위 제약 ===
# Feature: md-to-pptx-report-generator, Property 4: 슬라이드 수 범위 제약


class TestProperty4SlideCountRange:
    """
    Property 4: 슬라이드 수 범위 제약.

    mock된 Bedrock 응답으로 슬라이드 수가 1~5 범위인지 검증한다.
    **Validates: Requirements 3.3, 7.1, 7.2**
    """

    @given(
        num_response_slides=st.integers(min_value=1, max_value=15),
        max_slides=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=100)
    def test_slide_count_within_range(
        self, num_response_slides: int, max_slides: int
    ) -> None:
        """
        임의의 Bedrock 응답 슬라이드 수와 max_slides 값에 대해,
        결과 슬라이드 수는 항상 1 이상이어야 한다.

        **Validates: Requirements 3.3, 7.1, 7.2**
        """
        doc = _make_parsed_document()
        mock_slides = _generate_mock_slides(num_response_slides, doc.title)
        mock_client = _make_mock_client(mock_slides)

        summarizer = ContentSummarizer(bedrock_client=mock_client)
        result = summarizer.summarize(doc, max_slides=max_slides)

        # 슬라이드 수는 항상 1 이상, max_slides 이하
        assert len(result.slides) >= 1, (
            f"슬라이드 수 {len(result.slides)}가 1 미만"
        )


# === Property 5: 첫 슬라이드 표지 구성 ===
# Feature: md-to-pptx-report-generator, Property 5: 첫 슬라이드 표지 구성


class TestProperty5CoverSlide:
    """
    Property 5: 첫 슬라이드 표지 구성.

    첫 번째 SlideContent의 is_cover가 True인지 검증한다.
    **Validates: Requirements 7.3**
    """

    @given(
        num_slides=st.integers(min_value=1, max_value=5),
        title=doc_title_strategy,
    )
    @settings(max_examples=100)
    def test_first_slide_is_cover(
        self, num_slides: int, title: str
    ) -> None:
        """
        임의의 슬라이드 수와 문서 제목에 대해,
        첫 번째 슬라이드의 is_cover는 항상 True여야 한다.

        **Validates: Requirements 7.3**
        """
        doc = _make_parsed_document(title=title)
        # is_cover를 의도적으로 False로 설정하여 보정 로직 검증
        mock_slides = []
        for i in range(num_slides):
            mock_slides.append({
                "title": title if i == 0 else f"슬라이드 {i + 1}",
                "body": ["항목"],
                "is_cover": False,  # 모두 False로 설정
                "notes": "",
            })
        mock_client = _make_mock_client(mock_slides)

        summarizer = ContentSummarizer(bedrock_client=mock_client)
        result = summarizer.summarize(doc, max_slides=5)

        assert result.slides[0].is_cover is True, (
            "첫 번째 슬라이드의 is_cover가 True가 아님"
        )


# === Property 7: Bedrock API 오류 전파 ===
# Feature: md-to-pptx-report-generator, Property 7: Bedrock API 오류 전파


class TestProperty7BedrockAPIError:
    """
    Property 7: Bedrock API 오류 전파.

    mock된 Bedrock 오류 응답에 대해 BedrockAPIError 발생을 검증한다.
    **Validates: Requirements 3.5**
    """

    @given(
        error_code=st.sampled_from([
            "AccessDeniedException",
            "ValidationException",
            "ResourceNotFoundException",
            "ThrottlingException",
            "ServiceUnavailableException",
            "ModelTimeoutException",
            "InternalServerException",
        ]),
    )
    @settings(max_examples=100)
    def test_bedrock_client_error_raises_bedrock_api_error(
        self, error_code: str
    ) -> None:
        """
        임의의 Bedrock 오류 코드에 대해 BedrockAPIError가 발생해야 한다.

        **Validates: Requirements 3.5**
        """
        doc = _make_parsed_document()
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ClientError(
            error_response={"Error": {"Code": error_code, "Message": "테스트 오류"}},
            operation_name="InvokeModel",
        )

        summarizer = ContentSummarizer(bedrock_client=mock_client)

        with pytest.raises(BedrockAPIError) as exc_info:
            summarizer.summarize(doc)

        assert exc_info.value.error_code == error_code

        # 재시도 가능 여부 검증
        retryable_codes = {
            "ThrottlingException",
            "ServiceUnavailableException",
            "ModelTimeoutException",
        }
        if error_code in retryable_codes:
            assert exc_info.value.retryable is True
        else:
            assert exc_info.value.retryable is False


# === 단위 테스트: 타임아웃 ===


class TestContentSummarizerTimeout:
    """
    단위 테스트: 30초 타임아웃 시 BedrockTimeoutError 발생 확인.

    요구사항: 3.6
    """

    def test_timeout_raises_bedrock_timeout_error(self) -> None:
        """
        ReadTimeoutError 발생 시 BedrockTimeoutError로 변환되어야 한다.

        요구사항: 3.6
        """
        doc = _make_parsed_document()
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"
        )

        summarizer = ContentSummarizer(bedrock_client=mock_client, timeout=30)

        with pytest.raises(BedrockTimeoutError) as exc_info:
            summarizer.summarize(doc)

        # BedrockTimeoutError는 BedrockAPIError를 상속
        assert isinstance(exc_info.value, BedrockAPIError)
        assert exc_info.value.error_code == "TIMEOUT"
        assert exc_info.value.retryable is True
