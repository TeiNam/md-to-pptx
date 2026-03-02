# 구현 계획: md-to-pptx-report-generator

## 개요

마크다운 파일을 분석·요약하여 PPT 템플릿 기반 보고서 PPTX를 자동 생성하는 Python CLI 도구를 구현한다. 모듈별 단일 책임 원칙에 따라 순차적으로 구현하며, 각 모듈은 dataclass 기반 데이터 모델을 통해 연결된다. Python 베스트 프랙티스(타입 힌트, logging, 적절한 예외 처리, snake_case/PascalCase 네이밍, 모듈화, dataclass)를 엄격히 준수한다.

## 태스크

- [x] 1. 프로젝트 구조 및 데이터 모델 설정
  - [x] 1.1 프로젝트 디렉토리 구조 및 의존성 설정
    - `md_to_pptx/` 패키지 디렉토리 생성 (`__init__.py` 포함)
    - `tests/` 디렉토리 생성 (`conftest.py`, `__init__.py` 포함)
    - `pyproject.toml` 생성: Python 3.10+, 의존성(python-pptx, mistune, boto3, pytest, hypothesis)
    - `requirements.txt` 생성
    - _요구사항: 전체_

  - [x] 1.2 데이터 모델 정의 (`md_to_pptx/models.py`)
    - 설계 문서의 모든 dataclass 구현: `PlaceholderType`, `PlaceholderInfo`, `LayoutInfo`, `TemplateInfo`, `NodeType`, `MarkdownNode`, `Section`, `ParsedDocument`, `SlideContent`, `SummarizedContent`, `FontConfig`, `GenerationResult`
    - 모든 필드에 타입 힌트 적용, frozen 속성 설정
    - _요구사항: 전체 데이터 모델_

  - [x] 1.3 커스텀 예외 클래스 정의 (`md_to_pptx/exceptions.py`)
    - 설계 문서의 모든 예외/경고 클래스 구현: `ReportGeneratorError`, `InvalidFileFormatError`, `FileNotFoundError`, `EmptyDocumentError`, `NoPlaceholderWarning`, `BedrockAPIError`, `BedrockTimeoutError`, `ContentOverflowWarning`, `FontNotFoundWarning`
    - 각 예외에 적절한 한국어 오류 메시지 포함
    - _요구사항: 1.3, 1.4, 2.4, 3.5, 3.6, 4.6, 5.3, 8.4_

- [x] 2. Template_Analyzer 구현
  - [x] 2.1 Template_Analyzer 모듈 구현 (`md_to_pptx/template_analyzer.py`)
    - `TemplateAnalyzer` 클래스 구현: `analyze(template_path: str) -> TemplateInfo`
    - python-pptx를 사용하여 PPTX 템플릿의 슬라이드 레이아웃, 플레이스홀더 유형/위치 추출
    - 유효하지 않은 파일 형식 시 `InvalidFileFormatError` 발생
    - 플레이스홀더 없는 경우 `NoPlaceholderWarning` 경고 발행 (`warnings` 모듈 사용)
    - logging 모듈로 분석 진행 상태 로깅
    - mcpydoc으로 python-pptx API 확인 후 사용
    - _요구사항: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.2 Template_Analyzer 속성 테스트 작성 (`tests/test_template_analyzer.py`)
    - **Property 1: 템플릿 분석 정확성** - 유효한 PPTX 템플릿에 대해 레이아웃 수와 플레이스홀더 수/유형이 원본과 일치하는지 검증
    - **검증 대상: 요구사항 1.1, 1.2**

  - [x] 2.3 Template_Analyzer 오류 처리 속성 테스트 작성 (`tests/test_template_analyzer.py`)
    - **Property 6: 잘못된 입력 파일 오류 처리** - 비-PPTX 파일 또는 존재하지 않는 경로에 대해 적절한 예외 발생 검증
    - **검증 대상: 요구사항 1.3, 8.4**

  - [x] 2.4 Template_Analyzer 단위 테스트 작성 (`tests/test_template_analyzer.py`)
    - 플레이스홀더 없는 템플릿에 대한 `NoPlaceholderWarning` 경고 발생 확인
    - _요구사항: 1.4_

- [x] 3. Markdown_Parser 구현
  - [x] 3.1 Markdown_Parser 모듈 구현 (`md_to_pptx/markdown_parser.py`)
    - `MarkdownParser` 클래스 구현: `parse(markdown_text: str) -> ParsedDocument`, `to_markdown(document: ParsedDocument) -> str`
    - mistune 3.x AST 모드를 활용하여 제목(h1~h6), 본문, 순서/비순서 목록, 코드 블록, 표, 인라인 서식(bold, italic, code) 파싱
    - 중첩 목록 깊이 보존
    - 빈 마크다운 파일 시 `EmptyDocumentError` 발생
    - 라운드트립 변환 지원 (`to_markdown` 메서드)
    - logging 모듈로 파싱 진행 상태 로깅
    - mcpydoc으로 mistune 3.x API 확인 후 사용
    - _요구사항: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Markdown_Parser 라운드트립 속성 테스트 작성 (`tests/test_markdown_parser.py`)
    - **Property 2: 마크다운 파싱 라운드트립** - parse → to_markdown → parse 결과가 원본과 의미적으로 동등한지 검증
    - **검증 대상: 요구사항 2.5**

  - [x] 3.3 Markdown_Parser 구조 보존 속성 테스트 작성 (`tests/test_markdown_parser.py`)
    - **Property 3: 마크다운 파싱 구조 보존** - 각 요소의 NodeType 분류, 중첩 목록 깊이, 인라인 서식 보존 검증
    - **검증 대상: 요구사항 2.1, 2.2, 2.3**

  - [x] 3.4 Markdown_Parser 단위 테스트 작성 (`tests/test_markdown_parser.py`)
    - 빈 마크다운 파일에 대한 `EmptyDocumentError` 발생 확인
    - _요구사항: 2.4_

- [x] 4. 체크포인트 - 기반 모듈 검증
  - 모든 테스트가 통과하는지 확인하고, 사용자에게 질문이 있으면 문의한다.

- [x] 5. Font_Manager 구현
  - [x] 5.1 Font_Manager 모듈 구현 (`md_to_pptx/font_manager.py`)
    - `FontManager` 클래스 구현: `get_font_config() -> FontConfig`, `is_font_available(font_name: str) -> bool`
    - 기본 한국어 폰트 "맑은 고딕(Malgun Gothic)" 설정
    - 사용자 지정 폰트 우선 적용, 미설치 시 `FontNotFoundWarning` 경고 + 기본 폰트 대체
    - 영문/한국어 혼합 텍스트 폰트 일관성 보장
    - logging 모듈로 폰트 설정 상태 로깅
    - _요구사항: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.2 Font_Manager 속성 테스트 작성 (`tests/test_font_manager.py`)
    - **Property 16: 사용자 지정 폰트 우선 적용** - 유효한 폰트명 지정 시 FontConfig에 반영되는지 검증
    - **검증 대상: 요구사항 5.2**

  - [x] 5.3 Font_Manager 기본 폰트 대체 속성 테스트 작성 (`tests/test_font_manager.py`)
    - **Property 17: 미설치 폰트 기본값 대체** - 미설치 폰트명에 대해 경고 발생 및 기본 폰트 대체 검증
    - **검증 대상: 요구사항 5.3**

  - [x] 5.4 Font_Manager 단위 테스트 작성 (`tests/test_font_manager.py`)
    - 기본 폰트가 "맑은 고딕"인지 확인
    - _요구사항: 5.1_

- [x] 6. Content_Summarizer 구현
  - [x] 6.1 Content_Summarizer 모듈 구현 (`md_to_pptx/content_summarizer.py`)
    - `ContentSummarizer` 클래스 구현: `summarize(document: ParsedDocument, max_slides: int = 5) -> SummarizedContent`
    - boto3를 사용하여 Amazon Bedrock API 호출 (bedrock_client 주입 가능)
    - 요약 시 제목 계층 구조 유지, 핵심 데이터(수치, 날짜, 고유명사) 보존
    - 슬라이드 수 1~5장 범위 제한, 첫 슬라이드는 표지(is_cover=True)
    - 논리적 섹션 단위로 콘텐츠 분배 (하나의 주제가 여러 슬라이드에 분산되지 않도록)
    - 콘텐츠 분량에 따라 슬라이드 수 자동 조절
    - API 실패 시 `BedrockAPIError`, 30초 타임아웃 시 `BedrockTimeoutError` 발생
    - logging 모듈로 요약 진행 상태 로깅
    - mcpydoc으로 boto3 Bedrock API 확인 후 사용
    - _요구사항: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.1, 7.2, 7.3, 7.4_

  - [x] 6.2 Content_Summarizer 슬라이드 수 속성 테스트 작성 (`tests/test_content_summarizer.py`)
    - **Property 4: 슬라이드 수 범위 제약** - mock된 Bedrock 응답으로 슬라이드 수가 1~5 범위인지 검증
    - **검증 대상: 요구사항 3.3, 7.1, 7.2**

  - [x] 6.3 Content_Summarizer 표지 슬라이드 속성 테스트 작성 (`tests/test_content_summarizer.py`)
    - **Property 5: 첫 슬라이드 표지 구성** - 첫 번째 SlideContent의 is_cover가 True인지 검증
    - **검증 대상: 요구사항 7.3**

  - [x] 6.4 Content_Summarizer 오류 처리 속성 테스트 작성 (`tests/test_content_summarizer.py`)
    - **Property 7: Bedrock API 오류 전파** - mock된 Bedrock 오류 응답에 대해 BedrockAPIError 발생 검증
    - **검증 대상: 요구사항 3.5**

  - [x] 6.5 Content_Summarizer 단위 테스트 작성 (`tests/test_content_summarizer.py`)
    - 30초 타임아웃 시 `BedrockTimeoutError` 발생 확인
    - _요구사항: 3.6_

- [x] 7. 체크포인트 - 핵심 모듈 검증
  - 모든 테스트가 통과하는지 확인하고, 사용자에게 질문이 있으면 문의한다.

- [x] 8. Slide_Composer 구현
  - [x] 8.1 Slide_Composer 모듈 구현 (`md_to_pptx/slide_composer.py`)
    - `SlideComposer` 클래스 구현: `compose(template_info: TemplateInfo, summarized_content: SummarizedContent, template_path: str) -> Presentation`
    - FontManager를 생성자에서 주입받아 사용
    - 플레이스홀더에 콘텐츠 자동 배치 (제목/본문 구분)
    - 본문 줄간격 1.2~1.5배 적용
    - 목록 항목 불릿포인트 및 중첩 깊이별 들여쓰기 적용
    - 제목/본문 폰트 크기 차등 적용 (시각적 계층 구조)
    - 콘텐츠 영역 초과 시 폰트 크기 단계적 축소, 최소 10pt까지 축소 후에도 초과 시 `ContentOverflowWarning` 경고 기록
    - bold/italic 인라인 서식 → PPT bold/italic 변환
    - 제목 중앙 정렬, 본문 좌측 정렬
    - 슬라이드 간 여백 일관성 유지
    - 코드 블록: 고정폭 폰트 + 배경색 적용
    - 표 데이터: PPT 표 객체 변환, 헤더 행 배경색 적용
    - 슬라이드 하단 페이지 번호 자동 삽입
    - 텍스트 박스 간 최소 간격 유지 (겹침 방지)
    - logging 모듈로 슬라이드 생성 진행 상태 로깅
    - mcpydoc으로 python-pptx API 확인 후 사용
    - _요구사항: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 8.2 Slide_Composer 콘텐츠 배치 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 8: 슬라이드 콘텐츠 배치 완전성** - 슬라이드 수가 SummarizedContent와 일치하고 플레이스홀더에 콘텐츠가 배치되는지 검증
    - **검증 대상: 요구사항 4.1**

  - [x] 8.3 Slide_Composer 서식 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 9: 슬라이드 서식 속성 일관성** - 줄간격(1.2~1.5), 폰트 크기 계층, 텍스트 정렬 검증
    - **검증 대상: 요구사항 4.2, 4.4, 9.1**

  - [x] 8.4 Slide_Composer 인라인 서식 변환 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 10: 인라인 서식 변환** - bold/italic 서식이 PPT run에 올바르게 반영되는지 검증
    - **검증 대상: 요구사항 4.7**

  - [x] 8.5 Slide_Composer 목록 들여쓰기 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 11: 목록 들여쓰기 깊이 보존** - 중첩 목록의 들여쓰기 레벨이 원본과 일치하는지 검증
    - **검증 대상: 요구사항 4.3**

  - [x] 8.6 Slide_Composer 코드 블록 폰트 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 12: 코드 블록 고정폭 폰트 적용** - 코드 블록에 고정폭 폰트가 적용되는지 검증
    - **검증 대상: 요구사항 9.3**

  - [x] 8.7 Slide_Composer 표 변환 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 13: 표 데이터 변환** - 표가 PPT 표 객체로 변환되고 헤더 행에 배경색이 적용되는지 검증
    - **검증 대상: 요구사항 9.4**

  - [x] 8.8 Slide_Composer 페이지 번호 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 14: 페이지 번호 삽입** - 모든 슬라이드 하단에 페이지 번호가 존재하는지 검증
    - **검증 대상: 요구사항 9.5**

  - [x] 8.9 Slide_Composer 텍스트 박스 비겹침 속성 테스트 작성 (`tests/test_slide_composer.py`)
    - **Property 15: 텍스트 박스 비겹침** - 슬라이드 내 텍스트 박스 영역이 서로 겹치지 않는지 검증
    - **검증 대상: 요구사항 9.6**

  - [x] 8.10 Slide_Composer 단위 테스트 작성 (`tests/test_slide_composer.py`)
    - 최소 폰트 크기(10pt)까지 축소 후에도 초과 시 `ContentOverflowWarning` 경고 기록 확인
    - _요구사항: 4.6_

- [x] 9. 체크포인트 - Slide_Composer 검증
  - 모든 테스트가 통과하는지 확인하고, 사용자에게 질문이 있으면 문의한다.

- [x] 10. Report_Generator 및 CLI 통합
  - [x] 10.1 Report_Generator 모듈 구현 (`md_to_pptx/report_generator.py`)
    - `ReportGenerator` 클래스 구현: `generate(template_path, markdown_path, output_path, font_name) -> GenerationResult`
    - 전체 파이프라인 조율: Template_Analyzer → Markdown_Parser → Content_Summarizer → Slide_Composer
    - 입력 파일 존재 여부 검증, 미존재 시 `FileNotFoundError` 발생
    - 출력 파일명 자동 생성: `{마크다운파일명}_report.pptx`
    - 출력 파일 중복 시 사용자 확인 요청 (CLI 프롬프트)
    - 생성 완료 후 `GenerationResult` 반환 (파일 경로, 슬라이드 수, 소요 시간, 경고 목록)
    - logging 모듈로 전체 파이프라인 진행 상태 로깅
    - _요구사항: 6.1, 6.2, 6.3, 6.4, 6.5, 8.5_

  - [x] 10.2 CLI 엔트리포인트 구현 (`md_to_pptx/main.py`)
    - argparse 기반 CLI 구현: 템플릿 경로(필수), 마크다운 경로(필수), 출력 경로(선택), 폰트명(선택)
    - 필수 인자 누락 시 사용법(usage) 안내 메시지 출력
    - 진행 상태(템플릿 분석 중, 콘텐츠 요약 중, 슬라이드 생성 중 등) 콘솔 출력
    - `if __name__ == "__main__"` 블록으로 직접 실행 가능
    - _요구사항: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 10.3 Report_Generator PPTX 유효성 속성 테스트 작성 (`tests/test_report_generator.py`)
    - **Property 18: PPTX 파일 유효성 라운드트립** - 생성된 PPTX를 python-pptx로 재로드 시 오류 없이 열리고 슬라이드 수 일치 검증
    - **검증 대상: 요구사항 6.1**

  - [x] 10.4 Report_Generator 출력 파일명 속성 테스트 작성 (`tests/test_report_generator.py`)
    - **Property 19: 출력 파일명 자동 생성 규칙** - 출력 경로 미지정 시 `{마크다운파일명}_report.pptx` 형식 검증
    - **검증 대상: 요구사항 6.3**

  - [x] 10.5 Report_Generator 결과 완전성 속성 테스트 작성 (`tests/test_report_generator.py`)
    - **Property 20: 생성 결과 완전성** - GenerationResult의 output_path(비어있지 않음), slide_count(1 이상), elapsed_seconds(0 이상) 검증
    - **검증 대상: 요구사항 6.5**

  - [x] 10.6 CLI 인자 파싱 속성 테스트 작성 (`tests/test_report_generator.py`)
    - **Property 21: CLI 인자 파싱 정확성** - 유효한 CLI 인자 조합에 대해 Namespace 객체 필드가 입력과 일치하는지 검증
    - **검증 대상: 요구사항 8.2**

  - [x] 10.7 Report_Generator 및 CLI 단위 테스트 작성 (`tests/test_report_generator.py`)
    - CLI 실행 가능 여부 확인 (요구사항 8.1)
    - 필수 인자 누락 시 사용법 출력 확인 (요구사항 8.3)
    - 출력 파일 중복 시 확인 요청 확인 (요구사항 6.4)
    - _요구사항: 6.4, 8.1, 8.3_

- [x] 11. 최종 체크포인트 - 전체 통합 검증
  - 모든 테스트가 통과하는지 확인하고, 사용자에게 질문이 있으면 문의한다.

## 참고 사항

- `*` 표시된 태스크는 선택 사항이며, 빠른 MVP를 위해 건너뛸 수 있다
- 각 태스크는 특정 요구사항을 참조하여 추적 가능성을 보장한다
- 체크포인트에서 점진적 검증을 수행한다
- 속성 테스트는 범용 정확성 속성을 검증하고, 단위 테스트는 구체적 예제와 엣지 케이스를 검증한다
- 모든 모듈에서 `print` 대신 `logging` 모듈을 사용한다
- 모든 함수/메서드에 타입 힌트를 적용한다
- `try-except-pass` 패턴을 사용하지 않고, 구체적인 예외를 처리한다
- 파일당 300줄 미만을 권장하며, 초과 시 모듈을 분리한다
- mcpydoc으로 python-pptx, mistune, boto3 등 라이브러리 API를 확인한 후 사용한다
