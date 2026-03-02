"""
마크다운 파서 모듈.

mistune 3.x AST 모드를 활용하여 마크다운 텍스트를 구조화된 문서 데이터로 변환한다.
라운드트립 변환(parse → to_markdown)을 지원한다.
"""

import logging
from typing import Any

import mistune

from md_to_pptx.exceptions import EmptyDocumentError
from md_to_pptx.models import (
    MarkdownNode,
    NodeType,
    ParsedDocument,
    Section,
)

logger = logging.getLogger(__name__)


class MarkdownParser:
    """마크다운 텍스트를 구조화된 문서 객체로 변환하는 파서."""

    def __init__(self) -> None:
        """mistune AST 파서를 초기화한다."""
        self._parser = mistune.create_markdown(
            renderer="ast",
            plugins=["table"],
        )

    def parse(self, markdown_text: str) -> ParsedDocument:
        """
        마크다운 텍스트를 구조화된 문서 객체로 변환한다.

        Args:
            markdown_text: 마크다운 원본 텍스트

        Returns:
            ParsedDocument: 섹션, 목록, 코드 블록 등 구조화된 데이터

        Raises:
            EmptyDocumentError: 빈 마크다운 파일
        """
        # 빈 문서 검사
        stripped = markdown_text.strip()
        if not stripped:
            raise EmptyDocumentError()

        logger.info("마크다운 파싱 시작 (길이: %d자)", len(markdown_text))

        # mistune AST 파싱
        tokens = self._parser(markdown_text)
        logger.debug("AST 토큰 %d개 생성됨", len(tokens))

        # AST 토큰을 섹션 구조로 변환
        title, sections = self._build_sections(tokens)

        logger.info("파싱 완료: 제목='%s', 섹션 %d개", title, len(sections))
        return ParsedDocument(title=title, sections=sections)

    def to_markdown(self, document: ParsedDocument) -> str:
        """
        ParsedDocument를 다시 마크다운 텍스트로 변환한다 (라운드트립 지원).

        Args:
            document: 파싱된 마크다운 문서

        Returns:
            마크다운 텍스트 문자열
        """
        logger.info("마크다운 변환 시작: 제목='%s'", document.title)
        lines: list[str] = []

        for section in document.sections:
            # 섹션 제목 출력
            prefix = "#" * section.level
            lines.append(f"{prefix} {section.title}")
            lines.append("")

            # 섹션 내 노드 출력
            for node in section.nodes:
                node_text = self._node_to_markdown(node)
                lines.append(node_text)
                lines.append("")

        result = "\n".join(lines).rstrip("\n") + "\n"
        logger.info("마크다운 변환 완료 (길이: %d자)", len(result))
        return result

    # === 내부 메서드: AST → ParsedDocument 변환 ===

    def _build_sections(
        self, tokens: list[dict[str, Any]]
    ) -> tuple[str, list[Section]]:
        """AST 토큰 목록을 제목과 섹션 리스트로 변환한다."""
        sections: list[Section] = []
        doc_title = ""
        current_section: Section | None = None

        for token in tokens:
            token_type = token.get("type", "")

            # 빈 줄은 건너뛴다
            if token_type == "blank_line":
                continue

            if token_type == "heading":
                level = token.get("attrs", {}).get("level", 1)
                heading_text = self._extract_inline_text(
                    token.get("children", [])
                )

                # 첫 번째 제목을 문서 제목으로 사용
                if not doc_title:
                    doc_title = heading_text

                current_section = Section(
                    title=heading_text, level=level, nodes=[]
                )
                sections.append(current_section)
            else:
                # 제목이 아닌 토큰은 현재 섹션에 추가
                node = self._token_to_node(token)
                if node is not None:
                    if current_section is None:
                        # 제목 없이 시작하는 콘텐츠는 기본 섹션에 추가
                        current_section = Section(
                            title=doc_title or "", level=1, nodes=[]
                        )
                        sections.append(current_section)
                    current_section.nodes.append(node)

        # 제목이 없는 경우 첫 번째 텍스트를 제목으로 사용
        if not doc_title and sections:
            doc_title = sections[0].title

        return doc_title, sections

    def _token_to_node(self, token: dict[str, Any]) -> MarkdownNode | None:
        """단일 AST 토큰을 MarkdownNode로 변환한다."""
        token_type = token.get("type", "")

        if token_type == "paragraph":
            return self._parse_paragraph(token)
        elif token_type == "list":
            return self._parse_list(token)
        elif token_type == "block_code":
            return self._parse_code_block(token)
        elif token_type == "table":
            return self._parse_table(token)
        elif token_type == "blank_line":
            return None
        else:
            logger.debug("알 수 없는 토큰 유형 무시: %s", token_type)
            return None

    def _parse_paragraph(self, token: dict[str, Any]) -> MarkdownNode:
        """paragraph 토큰을 MarkdownNode로 변환한다."""
        children = self._parse_inline_children(token.get("children", []))
        # 인라인 자식이 하나이고 TEXT 타입이면 content에 직접 저장
        if len(children) == 1 and children[0].type == NodeType.TEXT:
            return MarkdownNode(
                type=NodeType.PARAGRAPH, content=children[0].content
            )
        return MarkdownNode(
            type=NodeType.PARAGRAPH, children=children
        )

    def _parse_list(
        self, token: dict[str, Any], depth: int = 0
    ) -> MarkdownNode:
        """list 토큰을 MarkdownNode로 변환한다. 중첩 깊이를 보존한다."""
        attrs = token.get("attrs", {})
        is_ordered = attrs.get("ordered", False)
        list_type = (
            NodeType.ORDERED_LIST if is_ordered else NodeType.UNORDERED_LIST
        )

        items: list[MarkdownNode] = []
        for item_token in token.get("children", []):
            if item_token.get("type") == "list_item":
                item_node = self._parse_list_item(item_token, depth)
                items.append(item_node)

        return MarkdownNode(type=list_type, level=depth, children=items)

    def _parse_list_item(
        self, token: dict[str, Any], depth: int
    ) -> MarkdownNode:
        """list_item 토큰을 MarkdownNode로 변환한다."""
        children: list[MarkdownNode] = []

        for child in token.get("children", []):
            child_type = child.get("type", "")
            if child_type == "block_text":
                # block_text 내부의 인라인 요소 추출
                inline_children = self._parse_inline_children(
                    child.get("children", [])
                )
                children.extend(inline_children)
            elif child_type == "paragraph":
                inline_children = self._parse_inline_children(
                    child.get("children", [])
                )
                children.extend(inline_children)
            elif child_type == "list":
                # 중첩 목록
                nested_list = self._parse_list(child, depth + 1)
                children.append(nested_list)

        # 텍스트 자식이 하나뿐이면 content에 직접 저장
        text_children = [
            c for c in children
            if c.type not in (NodeType.ORDERED_LIST, NodeType.UNORDERED_LIST)
        ]
        nested_lists = [
            c for c in children
            if c.type in (NodeType.ORDERED_LIST, NodeType.UNORDERED_LIST)
        ]

        if (
            len(text_children) == 1
            and text_children[0].type == NodeType.TEXT
        ):
            return MarkdownNode(
                type=NodeType.LIST_ITEM,
                content=text_children[0].content,
                level=depth,
                children=nested_lists,
            )

        return MarkdownNode(
            type=NodeType.LIST_ITEM,
            level=depth,
            children=children,
        )

    def _parse_code_block(self, token: dict[str, Any]) -> MarkdownNode:
        """block_code 토큰을 MarkdownNode로 변환한다."""
        raw = token.get("raw", "")
        # 끝의 개행 제거
        content = raw.rstrip("\n")
        info = token.get("attrs", {}).get("info", "")
        language = info if info else ""

        return MarkdownNode(
            type=NodeType.CODE_BLOCK, content=content, language=language
        )

    def _parse_table(self, token: dict[str, Any]) -> MarkdownNode:
        """table 토큰을 MarkdownNode로 변환한다."""
        rows: list[MarkdownNode] = []

        for child in token.get("children", []):
            child_type = child.get("type", "")
            if child_type in ("table_head", "table_body"):
                # table_head는 직접 셀을 포함, table_body는 row를 포함
                if child_type == "table_head":
                    row_cells = self._parse_table_row_cells(
                        child.get("children", [])
                    )
                    rows.append(
                        MarkdownNode(
                            type=NodeType.LIST_ITEM,
                            content="header",
                            children=row_cells,
                        )
                    )
                else:
                    for row in child.get("children", []):
                        if row.get("type") == "table_row":
                            row_cells = self._parse_table_row_cells(
                                row.get("children", [])
                            )
                            rows.append(
                                MarkdownNode(
                                    type=NodeType.LIST_ITEM,
                                    children=row_cells,
                                )
                            )

        return MarkdownNode(type=NodeType.TABLE, children=rows)

    def _parse_table_row_cells(
        self, cells: list[dict[str, Any]]
    ) -> list[MarkdownNode]:
        """테이블 행의 셀들을 MarkdownNode 리스트로 변환한다."""
        result: list[MarkdownNode] = []
        for cell in cells:
            if cell.get("type") == "table_cell":
                text = self._extract_inline_text(cell.get("children", []))
                result.append(
                    MarkdownNode(type=NodeType.TEXT, content=text)
                )
        return result

    def _parse_inline_children(
        self, children: list[dict[str, Any]]
    ) -> list[MarkdownNode]:
        """인라인 자식 토큰 목록을 MarkdownNode 리스트로 변환한다."""
        nodes: list[MarkdownNode] = []
        for child in children:
            node = self._parse_inline(child)
            if node is not None:
                nodes.append(node)
        return nodes

    def _parse_inline(self, token: dict[str, Any]) -> MarkdownNode | None:
        """인라인 토큰을 MarkdownNode로 변환한다."""
        token_type = token.get("type", "")

        if token_type == "text":
            raw = token.get("raw", "")
            return MarkdownNode(type=NodeType.TEXT, content=raw)
        elif token_type == "strong":
            text = self._extract_inline_text(token.get("children", []))
            return MarkdownNode(type=NodeType.BOLD, content=text)
        elif token_type == "emphasis":
            text = self._extract_inline_text(token.get("children", []))
            return MarkdownNode(type=NodeType.ITALIC, content=text)
        elif token_type == "codespan":
            raw = token.get("raw", "")
            return MarkdownNode(type=NodeType.INLINE_CODE, content=raw)
        elif token_type == "softbreak":
            return MarkdownNode(type=NodeType.TEXT, content="\n")
        else:
            logger.debug("알 수 없는 인라인 토큰 무시: %s", token_type)
            return None

    def _extract_inline_text(self, children: list[dict[str, Any]]) -> str:
        """인라인 자식 토큰에서 순수 텍스트를 추출한다."""
        parts: list[str] = []
        for child in children:
            token_type = child.get("type", "")
            if token_type == "text":
                parts.append(child.get("raw", ""))
            elif token_type == "strong":
                inner = self._extract_inline_text(child.get("children", []))
                parts.append(inner)
            elif token_type == "emphasis":
                inner = self._extract_inline_text(child.get("children", []))
                parts.append(inner)
            elif token_type == "codespan":
                parts.append(child.get("raw", ""))
            elif token_type == "softbreak":
                parts.append("\n")
        return "".join(parts)

    # === 내부 메서드: ParsedDocument → 마크다운 변환 ===

    def _node_to_markdown(self, node: MarkdownNode) -> str:
        """MarkdownNode를 마크다운 텍스트로 변환한다."""
        if node.type == NodeType.PARAGRAPH:
            return self._paragraph_to_markdown(node)
        elif node.type in (NodeType.ORDERED_LIST, NodeType.UNORDERED_LIST):
            return self._list_to_markdown(node)
        elif node.type == NodeType.CODE_BLOCK:
            return self._code_block_to_markdown(node)
        elif node.type == NodeType.TABLE:
            return self._table_to_markdown(node)
        else:
            return node.content

    def _paragraph_to_markdown(self, node: MarkdownNode) -> str:
        """PARAGRAPH 노드를 마크다운 텍스트로 변환한다."""
        if node.children:
            return self._inline_children_to_markdown(node.children)
        return node.content

    def _inline_children_to_markdown(
        self, children: list[MarkdownNode]
    ) -> str:
        """인라인 자식 노드 목록을 마크다운 텍스트로 변환한다."""
        parts: list[str] = []
        for child in children:
            parts.append(self._inline_to_markdown(child))
        return "".join(parts)

    def _inline_to_markdown(self, node: MarkdownNode) -> str:
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

    def _list_to_markdown(
        self, node: MarkdownNode, indent: int = 0
    ) -> str:
        """목록 노드를 마크다운 텍스트로 변환한다."""
        lines: list[str] = []
        is_ordered = node.type == NodeType.ORDERED_LIST
        prefix_space = "  " * indent

        for idx, item in enumerate(node.children):
            if item.type == NodeType.LIST_ITEM:
                # 목록 항목 마커
                marker = f"{idx + 1}." if is_ordered else "-"

                # 항목 텍스트
                if item.content:
                    item_text = item.content
                elif item.children:
                    # 인라인 자식에서 텍스트 추출 (중첩 목록 제외)
                    inline_parts: list[str] = []
                    for child in item.children:
                        if child.type not in (
                            NodeType.ORDERED_LIST,
                            NodeType.UNORDERED_LIST,
                        ):
                            inline_parts.append(
                                self._inline_to_markdown(child)
                            )
                    item_text = "".join(inline_parts)
                else:
                    item_text = ""

                lines.append(f"{prefix_space}{marker} {item_text}")

                # 중첩 목록 처리
                for child in item.children:
                    if child.type in (
                        NodeType.ORDERED_LIST,
                        NodeType.UNORDERED_LIST,
                    ):
                        nested = self._list_to_markdown(
                            child, indent + 1
                        )
                        lines.append(nested)

        return "\n".join(lines)

    def _code_block_to_markdown(self, node: MarkdownNode) -> str:
        """코드 블록 노드를 마크다운 텍스트로 변환한다."""
        lang = node.language or ""
        return f"```{lang}\n{node.content}\n```"

    def _table_to_markdown(self, node: MarkdownNode) -> str:
        """테이블 노드를 마크다운 텍스트로 변환한다."""
        if not node.children:
            return ""

        lines: list[str] = []

        # 헤더 행
        header_row = node.children[0]
        header_cells = [c.content for c in header_row.children]
        lines.append("| " + " | ".join(header_cells) + " |")

        # 구분선
        separators = ["---"] * len(header_cells)
        lines.append("| " + " | ".join(separators) + " |")

        # 데이터 행
        for row in node.children[1:]:
            cells = [c.content for c in row.children]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)
