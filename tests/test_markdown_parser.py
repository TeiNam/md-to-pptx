"""
Markdown_Parser 테스트 모듈.

속성 기반 테스트(hypothesis)와 단위 테스트(pytest)를 포함한다.
- Property 2: 마크다운 파싱 라운드트립 (요구사항 2.5)
- Property 3: 마크다운 파싱 구조 보존 (요구사항 2.1, 2.2, 2.3)
- 단위 테스트: EmptyDocumentError 발생 (요구사항 2.4)
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from md_to_pptx.exceptions import EmptyDocumentError
from md_to_pptx.markdown_parser import MarkdownParser
from md_to_pptx.models import NodeType


# === Hypothesis 전략 ===

# 안전한 텍스트 (마크다운 특수문자 제외)
_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        whitelist_characters=",.",
    ),
    min_size=1,
    max_size=30,
).map(lambda t: t.strip()).filter(lambda t: len(t) > 0)

# 제목 레벨 (1~6)
_heading_level = st.integers(min_value=1, max_value=6)


def _heading_fragment(level: int, text: str) -> str:
    """제목 마크다운 조각을 생성한다."""
    return f"{'#' * level} {text}"


def _paragraph_fragment(text: str) -> str:
    """본문 마크다운 조각을 생성한다."""
    return text


def _unordered_list_fragment(items: list[str]) -> str:
    """비순서 목록 마크다운 조각을 생성한다."""
    return "\n".join(f"- {item}" for item in items)


def _ordered_list_fragment(items: list[str]) -> str:
    """순서 목록 마크다운 조각을 생성한다."""
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


def _code_block_fragment(code: str, lang: str = "") -> str:
    """코드 블록 마크다운 조각을 생성한다."""
    return f"```{lang}\n{code}\n```"


# 구조화된 마크다운 문서 생성 전략
# 미리 정의된 마크다운 조각을 조합하여 안정적인 마크다운을 생성한다
_markdown_fragments = st.sampled_from([
    "# 보고서 제목\n\n본문 텍스트입니다.\n",
    "# 프로젝트 개요\n\n## 배경\n\n프로젝트 배경 설명입니다.\n",
    "# 제목\n\n- 항목 1\n- 항목 2\n- 항목 3\n",
    "# 제목\n\n1. 첫 번째\n2. 두 번째\n3. 세 번째\n",
    "# 제목\n\n```python\nprint('hello')\n```\n",
    "# 제목\n\n## 섹션 1\n\n본문입니다.\n\n## 섹션 2\n\n다른 본문입니다.\n",
    "# 제목\n\n**굵은 텍스트**와 *기울임 텍스트*가 있습니다.\n",
    "# 제목\n\n`인라인 코드`가 포함된 문장입니다.\n",
    "# 제목\n\n- 항목 1\n  - 하위 항목 1\n  - 하위 항목 2\n- 항목 2\n",
    "# 분석 보고서\n\n## 요약\n\n핵심 내용입니다.\n\n## 상세\n\n- 포인트 1\n- 포인트 2\n\n```bash\necho test\n```\n",
    "# 제목\n\n| 이름 | 값 |\n| --- | --- |\n| A | 1 |\n| B | 2 |\n",
])



# === Property 2: 마크다운 파싱 라운드트립 ===


class TestProperty2MarkdownParsingRoundtrip:
    """
    Property 2: 마크다운 파싱 라운드트립

    parse → to_markdown → parse 결과가 원본과 의미적으로 동등한지 검증한다.

    Feature: md-to-pptx-report-generator, Property 2: 마크다운 파싱 라운드트립
    Validates: Requirements 2.5
    """

    @given(markdown_text=_markdown_fragments)
    @settings(max_examples=100)
    def test_roundtrip_section_count_preserved(self, markdown_text):
        """parse → to_markdown → parse 후 섹션 수가 일치해야 한다."""
        parser = MarkdownParser()

        # 1차 파싱
        doc1 = parser.parse(markdown_text)
        # 마크다운으로 변환
        regenerated = parser.to_markdown(doc1)
        # 2차 파싱
        doc2 = parser.parse(regenerated)

        assert len(doc1.sections) == len(doc2.sections), (
            f"섹션 수 불일치: 원본 {len(doc1.sections)}개, "
            f"라운드트립 {len(doc2.sections)}개"
        )

    @given(markdown_text=_markdown_fragments)
    @settings(max_examples=100)
    def test_roundtrip_section_titles_preserved(self, markdown_text):
        """parse → to_markdown → parse 후 섹션 제목이 일치해야 한다."""
        parser = MarkdownParser()

        doc1 = parser.parse(markdown_text)
        regenerated = parser.to_markdown(doc1)
        doc2 = parser.parse(regenerated)

        for i, (s1, s2) in enumerate(zip(doc1.sections, doc2.sections)):
            assert s1.title == s2.title, (
                f"섹션 [{i}] 제목 불일치: '{s1.title}' vs '{s2.title}'"
            )

    @given(markdown_text=_markdown_fragments)
    @settings(max_examples=100)
    def test_roundtrip_node_types_preserved(self, markdown_text):
        """parse → to_markdown → parse 후 각 섹션의 노드 타입 목록이 일치해야 한다."""
        parser = MarkdownParser()

        doc1 = parser.parse(markdown_text)
        regenerated = parser.to_markdown(doc1)
        doc2 = parser.parse(regenerated)

        for i, (s1, s2) in enumerate(zip(doc1.sections, doc2.sections)):
            types1 = [n.type for n in s1.nodes]
            types2 = [n.type for n in s2.nodes]
            assert types1 == types2, (
                f"섹션 [{i}] '{s1.title}' 노드 타입 불일치: "
                f"{types1} vs {types2}"
            )

    @given(markdown_text=_markdown_fragments)
    @settings(max_examples=100)
    def test_roundtrip_document_title_preserved(self, markdown_text):
        """parse → to_markdown → parse 후 문서 제목이 일치해야 한다."""
        parser = MarkdownParser()

        doc1 = parser.parse(markdown_text)
        regenerated = parser.to_markdown(doc1)
        doc2 = parser.parse(regenerated)

        assert doc1.title == doc2.title, (
            f"문서 제목 불일치: '{doc1.title}' vs '{doc2.title}'"
        )


# === Property 3: 마크다운 파싱 구조 보존 ===


class TestProperty3MarkdownParsingStructurePreservation:
    """
    Property 3: 마크다운 파싱 구조 보존

    각 요소의 NodeType 분류, 중첩 목록 깊이, 인라인 서식 보존을 검증한다.

    Feature: md-to-pptx-report-generator, Property 3: 마크다운 파싱 구조 보존
    Validates: Requirements 2.1, 2.2, 2.3
    """

    def test_heading_classified_as_heading_type(self):
        """제목이 HEADING 타입의 섹션으로 분류되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = "# 제목 1\n\n본문\n\n## 제목 2\n\n본문 2\n"
        doc = parser.parse(md)

        # 섹션 레벨이 올바르게 설정되었는지 확인
        assert doc.sections[0].level == 1
        assert doc.sections[0].title == "제목 1"
        assert doc.sections[1].level == 2
        assert doc.sections[1].title == "제목 2"

    @given(level=_heading_level, title=_safe_text)
    @settings(max_examples=100)
    def test_heading_level_preserved(self, level, title):
        """임의의 제목 레벨(1~6)이 올바르게 보존되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = f"{'#' * level} {title}\n\n본문 텍스트\n"
        doc = parser.parse(md)

        assert len(doc.sections) >= 1
        assert doc.sections[0].level == level
        assert doc.sections[0].title == title

    def test_unordered_list_classified_correctly(self):
        """비순서 목록이 UNORDERED_LIST로 분류되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = "# 제목\n\n- 항목 1\n- 항목 2\n- 항목 3\n"
        doc = parser.parse(md)

        list_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.UNORDERED_LIST
        ]
        assert len(list_nodes) == 1
        assert list_nodes[0].type == NodeType.UNORDERED_LIST

    def test_ordered_list_classified_correctly(self):
        """순서 목록이 ORDERED_LIST로 분류되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = "# 제목\n\n1. 첫 번째\n2. 두 번째\n3. 세 번째\n"
        doc = parser.parse(md)

        list_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.ORDERED_LIST
        ]
        assert len(list_nodes) == 1
        assert list_nodes[0].type == NodeType.ORDERED_LIST

    def test_code_block_classified_correctly(self):
        """코드 블록이 CODE_BLOCK으로 분류되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = "# 제목\n\n```python\nprint('hello')\n```\n"
        doc = parser.parse(md)

        code_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.CODE_BLOCK
        ]
        assert len(code_nodes) == 1
        assert code_nodes[0].type == NodeType.CODE_BLOCK
        assert code_nodes[0].language == "python"
        assert "print" in code_nodes[0].content

    def test_table_classified_correctly(self):
        """표가 TABLE로 분류되어야 한다 (요구사항 2.1)."""
        parser = MarkdownParser()
        md = "# 제목\n\n| 이름 | 값 |\n| --- | --- |\n| A | 1 |\n"
        doc = parser.parse(md)

        table_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.TABLE
        ]
        assert len(table_nodes) == 1
        assert table_nodes[0].type == NodeType.TABLE

    def test_nested_list_depth_preserved(self):
        """중첩 목록의 깊이가 보존되어야 한다 (요구사항 2.2)."""
        parser = MarkdownParser()
        md = "# 제목\n\n- 항목 1\n  - 하위 항목 1\n    - 깊은 항목\n  - 하위 항목 2\n- 항목 2\n"
        doc = parser.parse(md)

        list_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.UNORDERED_LIST
        ]
        assert len(list_nodes) == 1

        # 최상위 목록의 깊이는 0
        top_list = list_nodes[0]
        assert top_list.level == 0

        # 하위 목록이 존재하고 깊이가 증가하는지 확인
        first_item = top_list.children[0]
        nested_lists = [
            c for c in first_item.children
            if c.type == NodeType.UNORDERED_LIST
        ]
        assert len(nested_lists) >= 1
        assert nested_lists[0].level == 1

    def test_bold_inline_format_preserved(self):
        """굵게(bold) 인라인 서식이 BOLD로 보존되어야 한다 (요구사항 2.3)."""
        parser = MarkdownParser()
        md = "# 제목\n\n**굵은 텍스트**가 있습니다.\n"
        doc = parser.parse(md)

        # 본문 노드에서 BOLD 자식 확인
        para_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.PARAGRAPH
        ]
        assert len(para_nodes) >= 1

        bold_found = False
        for para in para_nodes:
            for child in para.children:
                if child.type == NodeType.BOLD:
                    assert child.content == "굵은 텍스트"
                    bold_found = True
        assert bold_found, "BOLD 노드가 발견되어야 합니다"

    def test_italic_inline_format_preserved(self):
        """기울임(italic) 인라인 서식이 ITALIC으로 보존되어야 한다 (요구사항 2.3)."""
        parser = MarkdownParser()
        md = "# 제목\n\n*기울임 텍스트*가 있습니다.\n"
        doc = parser.parse(md)

        para_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.PARAGRAPH
        ]
        assert len(para_nodes) >= 1

        italic_found = False
        for para in para_nodes:
            for child in para.children:
                if child.type == NodeType.ITALIC:
                    assert child.content == "기울임 텍스트"
                    italic_found = True
        assert italic_found, "ITALIC 노드가 발견되어야 합니다"

    def test_inline_code_format_preserved(self):
        """인라인 코드 서식이 INLINE_CODE로 보존되어야 한다 (요구사항 2.3)."""
        parser = MarkdownParser()
        md = "# 제목\n\n`인라인 코드`가 포함된 문장입니다.\n"
        doc = parser.parse(md)

        para_nodes = [
            n for n in doc.sections[0].nodes
            if n.type == NodeType.PARAGRAPH
        ]
        assert len(para_nodes) >= 1

        code_found = False
        for para in para_nodes:
            for child in para.children:
                if child.type == NodeType.INLINE_CODE:
                    assert child.content == "인라인 코드"
                    code_found = True
        assert code_found, "INLINE_CODE 노드가 발견되어야 합니다"

    @given(
        element_type=st.sampled_from([
            ("unordered_list", "- 항목 A\n- 항목 B\n", NodeType.UNORDERED_LIST),
            ("ordered_list", "1. 첫째\n2. 둘째\n", NodeType.ORDERED_LIST),
            ("code_block", "```\ncode\n```\n", NodeType.CODE_BLOCK),
            ("paragraph", "일반 본문 텍스트입니다.\n", NodeType.PARAGRAPH),
        ])
    )
    @settings(max_examples=100)
    def test_element_type_classification(self, element_type):
        """각 마크다운 요소가 올바른 NodeType으로 분류되어야 한다 (요구사항 2.1)."""
        name, fragment, expected_type = element_type
        parser = MarkdownParser()
        md = f"# 테스트 제목\n\n{fragment}"
        doc = parser.parse(md)

        node_types = [n.type for n in doc.sections[0].nodes]
        assert expected_type in node_types, (
            f"'{name}' 요소가 {expected_type}으로 분류되어야 하지만, "
            f"실제 타입: {node_types}"
        )


# === 단위 테스트: EmptyDocumentError 발생 (요구사항 2.4) ===


class TestEmptyDocumentError:
    """
    빈 마크다운 파일에 대한 EmptyDocumentError 발생 확인.

    요구사항 2.4: 빈 마크다운 파일이 제공되면
    "마크다운 파일에 내용이 없습니다" 오류 메시지를 반환한다.
    """

    def test_empty_string_raises_error(self):
        """빈 문자열에 대해 EmptyDocumentError가 발생해야 한다."""
        parser = MarkdownParser()
        with pytest.raises(EmptyDocumentError):
            parser.parse("")

    def test_whitespace_only_raises_error(self):
        """공백만 있는 문자열에 대해 EmptyDocumentError가 발생해야 한다."""
        parser = MarkdownParser()
        with pytest.raises(EmptyDocumentError):
            parser.parse("   \n\n  \t  \n  ")
