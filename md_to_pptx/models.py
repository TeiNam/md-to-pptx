"""
데이터 모델 정의 모듈.

모듈 간 데이터 전달에 사용되는 핵심 데이터 클래스를 정의한다.
모든 모델은 dataclasses를 사용하며, 불변(frozen) 속성을 권장한다.
"""

from dataclasses import dataclass, field
from enum import Enum


# === 템플릿 분석 관련 ===


class PlaceholderType(Enum):
    """플레이스홀더 유형"""

    TITLE = "title"
    SUBTITLE = "subtitle"
    BODY = "body"
    IMAGE = "image"
    TABLE = "table"
    OTHER = "other"


@dataclass(frozen=True)
class PlaceholderInfo:
    """개별 플레이스홀더 정보"""

    idx: int                          # 플레이스홀더 인덱스
    type: PlaceholderType             # 유형
    name: str                         # 이름
    left: int                         # 좌측 위치 (EMU)
    top: int                          # 상단 위치 (EMU)
    width: int                        # 너비 (EMU)
    height: int                       # 높이 (EMU)


@dataclass(frozen=True)
class LayoutInfo:
    """슬라이드 레이아웃 정보"""

    name: str                         # 레이아웃 이름
    index: int                        # 레이아웃 인덱스
    placeholders: list[PlaceholderInfo] = field(default_factory=list)


@dataclass(frozen=True)
class TemplateInfo:
    """템플릿 분석 결과"""

    layouts: list[LayoutInfo]         # 레이아웃 목록
    slide_width: int                  # 슬라이드 너비 (EMU)
    slide_height: int                 # 슬라이드 높이 (EMU)


# === 마크다운 파싱 관련 ===


class NodeType(Enum):
    """마크다운 노드 유형"""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    ORDERED_LIST = "ordered_list"
    UNORDERED_LIST = "unordered_list"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    INLINE_CODE = "inline_code"
    BOLD = "bold"
    ITALIC = "italic"
    TEXT = "text"


@dataclass
class MarkdownNode:
    """마크다운 AST 노드"""

    type: NodeType
    content: str = ""
    level: int = 0                    # 제목 레벨(1~6) 또는 목록 중첩 깊이
    children: list["MarkdownNode"] = field(default_factory=list)
    language: str = ""                # 코드 블록 언어


@dataclass
class Section:
    """마크다운 섹션 (제목 + 하위 콘텐츠)"""

    title: str
    level: int                        # 제목 레벨 (1~6)
    nodes: list[MarkdownNode] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """파싱된 마크다운 문서"""

    title: str                        # 문서 제목 (첫 번째 h1)
    sections: list[Section] = field(default_factory=list)


# === 요약 관련 ===


@dataclass(frozen=True)
class SlideContent:
    """개별 슬라이드 콘텐츠"""

    title: str                        # 슬라이드 제목
    body: list[str]                   # 본문 항목 목록
    is_cover: bool = False            # 표지 슬라이드 여부
    notes: str = ""                   # 발표자 노트


@dataclass(frozen=True)
class SummarizedContent:
    """요약된 전체 콘텐츠"""

    slides: list[SlideContent]        # 슬라이드 목록 (최대 5개)
    original_title: str               # 원본 문서 제목


# === 폰트 관련 ===


@dataclass(frozen=True)
class FontConfig:
    """폰트 설정"""

    korean_font: str                  # 한국어 폰트명
    mono_font: str                    # 고정폭 폰트명
    title_size_pt: int = 28           # 제목 폰트 크기
    body_size_pt: int = 16            # 본문 폰트 크기
    code_size_pt: int = 12            # 코드 폰트 크기
    min_size_pt: int = 10             # 최소 폰트 크기


# === 결과 관련 ===


@dataclass(frozen=True)
class GenerationResult:
    """PPTX 생성 결과"""

    output_path: str                  # 출력 파일 경로
    slide_count: int                  # 생성된 슬라이드 수
    elapsed_seconds: float            # 처리 소요 시간 (초)
    warnings: list[str] = field(default_factory=list)  # 경고 메시지 목록
