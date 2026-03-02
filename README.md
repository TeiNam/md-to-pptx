# md-to-pptx-report-generator

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![python-pptx](https://img.shields.io/badge/python--pptx-0.6.23+-009688.svg)
![mistune](https://img.shields.io/badge/mistune-3.x-orange.svg)
![boto3](https://img.shields.io/badge/boto3-Bedrock-FF9900.svg)
![pytest](https://img.shields.io/badge/pytest-9.0-0A9EDC.svg)
![hypothesis](https://img.shields.io/badge/hypothesis-PBT-purple.svg)

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://qr.kakaopay.com/Ej74xpc815dc06149)

## 개요

마크다운(`.md`) 파일을 분석·요약하여 PPT 템플릿 기반 보고서 PPTX를 자동 생성하는 Python CLI 도구입니다.

Amazon Bedrock(Claude)을 활용해 문서를 슬라이드 단위로 요약하고, 기존 PPTX 템플릿의 레이아웃과 플레이스홀더를 분석하여 콘텐츠를 자동 배치합니다.

## 주요 기능

- 마크다운 파싱: 제목(h1~h6), 본문, 순서/비순서 목록, 코드 블록, 표, 인라인 서식(bold, italic, code) 지원
- AI 요약: Amazon Bedrock Claude를 통한 문서 자동 요약 및 슬라이드 분배
- 템플릿 기반: 기존 PPTX 템플릿의 레이아웃/플레이스홀더를 분석하여 콘텐츠 배치
- 한국어 폰트: 기본 "나눔고딕" 지원, .env 또는 CLI로 사용자 지정 폰트 우선 적용
- 서식 변환: bold/italic → PPT 서식, 코드 블록 → 고정폭 폰트, 표 → PPT 표 객체
- 자동 조절: 콘텐츠 초과 시 폰트 크기 단계적 축소, 슬라이드 수 자동 조절(1~5장)

## 아키텍처

```
┌─────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌────────────────┐
│  Template    │    │  Markdown    │    │  Content          │    │  Slide         │
│  Analyzer    │───▶│  Parser      │───▶│  Summarizer       │───▶│  Composer      │
│              │    │              │    │  (Bedrock Claude)  │    │                │
└─────────────┘    └──────────────┘    └───────────────────┘    └────────────────┘
       │                                                                │
       │                    ┌──────────────┐                           │
       └───────────────────▶│  Report      │◀──────────────────────────┘
                            │  Generator   │
                            └──────┬───────┘
                                   │
                                   ▼
                              output.pptx
```

| 모듈 | 역할 |
|------|------|
| `template_analyzer.py` | PPTX 템플릿의 레이아웃, 플레이스홀더 유형/위치 추출 |
| `markdown_parser.py` | mistune 3.x AST 모드로 마크다운 파싱, 라운드트립 변환 지원 |
| `content_summarizer.py` | Amazon Bedrock API로 문서를 슬라이드 단위 요약 |
| `slide_composer.py` | 요약 콘텐츠를 PPT 슬라이드로 구성 (서식, 레이아웃 적용) |
| `font_manager.py` | 한국어 폰트 설정 및 시스템 폰트 검증 |
| `report_generator.py` | 전체 파이프라인 조율 |
| `main.py` | CLI 엔트리포인트 |


## 설치

### 요구사항

- Python 3.10 이상
- AWS 계정 및 Bedrock 접근 권한 (Claude 모델)

### 설치 방법

```bash
# 저장소 클론
git clone <repository-url>
cd md_to_pptx

# 가상환경 생성 (pyenv 사용 시)
pyenv virtualenv 3.12.12 md-to-pptx-env
pyenv local md-to-pptx-env

# 의존성 설치
pip install -r requirements.txt
```

### AWS 설정

Amazon Bedrock Claude 모델을 사용하므로 AWS 자격 증명이 필요합니다.

자격 증명은 다음 우선순위로 적용됩니다:

1. `.env` 파일 (프로젝트 루트)
2. boto3 기본 체인 (`~/.aws/credentials`, AWS SSO, IAM 역할, 환경 변수 등)

#### 방법 1: .env 파일 사용

```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# .env 파일 편집
vi .env
```

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

#### 방법 2: AWS SSO 사용

```bash
# SSO 프로필 설정
aws configure sso

# SSO 로그인
aws sso login --profile your-profile
export AWS_PROFILE=your-profile
```

Bedrock 콘솔에서 사용할 모델의 접근을 활성화해야 합니다.

#### 모델 설정

`.env`의 `BEDROCK_MODEL_ID`로 모델을 지정할 수 있습니다. 미설정 시 다음 순서로 fallback합니다:

1. `global.anthropic.claude-opus-4-6-v1` (기본)
2. `global.anthropic.claude-opus-4-5-20251101-v1:0` (fallback)

```env
# 특정 모델 지정 시
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-6-v1
```

#### 폰트 설정

`.env`의 `DEFAULT_FONT`로 기본 한국어 폰트를 지정할 수 있습니다. 미설정 시 "나눔고딕"을 사용합니다.

```env
DEFAULT_FONT=나눔고딕
DEFAULT_MONO_FONT=D2Coding
```

CLI의 `-f` 옵션으로 지정한 폰트가 `.env` 설정보다 우선합니다.

## 사용법

### CLI 기본 사용

```bash
# 패키지 설치 (CLI 명령어 등록)
pip install -e .

# 기본 사용 (출력 파일명 자동 생성)
md-to-pptx template.pptx document.md

# 출력 경로 지정
md-to-pptx template.pptx document.md -o report.pptx

# 폰트 지정
md-to-pptx template.pptx document.md -f "나눔바른고딕"

# 기존 파일 덮어쓰기 허용
md-to-pptx template.pptx document.md -o report.pptx -y
```

### CLI 인자

| 인자 | 필수 | 설명 |
|------|------|------|
| `template` | O | PPT 템플릿 파일 경로 (`.pptx`) |
| `markdown` | O | 마크다운 파일 경로 (`.md`) |
| `-o`, `--output` | X | 출력 파일 경로 (미지정 시 `{마크다운파일명}_report.pptx`) |
| `-f`, `--font` | X | 한국어 폰트명 (미지정 시 .env `DEFAULT_FONT` 또는 "나눔고딕") |
| `-y`, `--yes` | X | 출력 파일 중복 시 확인 없이 덮어쓰기 |

### 실행 예시

```bash
$ md-to-pptx template.pptx 분석보고서.md

📄 템플릿 분석 중: template.pptx
📝 마크다운 파싱 중: 분석보고서.md
✅ 보고서 생성 완료: ./분석보고서_report.pptx
   슬라이드 수: 4
   소요 시간: 3.21초
```

### Python API 사용

```python
from md_to_pptx.report_generator import ReportGenerator

generator = ReportGenerator()
result = generator.generate(
    template_path="template.pptx",
    markdown_path="document.md",
    output_path="output.pptx",
    font_name="나눔고딕",
)

print(f"생성 완료: {result.output_path}")
print(f"슬라이드 수: {result.slide_count}")
print(f"소요 시간: {result.elapsed_seconds:.2f}초")
```

## 지원하는 마크다운 요소

| 요소 | 마크다운 문법 | PPT 변환 결과 |
|------|-------------|--------------|
| 제목 (h1~h6) | `# 제목` ~ `###### 제목` | 슬라이드 제목 / 섹션 구분 |
| 본문 | 일반 텍스트 | 본문 텍스트 |
| 비순서 목록 | `- 항목` | 불릿포인트 목록 |
| 순서 목록 | `1. 항목` | 번호 목록 |
| 중첩 목록 | 들여쓰기 | 깊이별 들여쓰기 적용 |
| 코드 블록 | ` ```python ``` ` | 고정폭 폰트 + 배경색 |
| 표 | `\| A \| B \|` | PPT 표 객체 (헤더 배경색) |
| 굵게 | `**텍스트**` | PPT bold 서식 |
| 기울임 | `*텍스트*` | PPT italic 서식 |
| 인라인 코드 | `` `코드` `` | 고정폭 폰트 |

## 테스트

속성 기반 테스트(hypothesis)와 단위 테스트(pytest)로 구성되어 있습니다.

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 특정 모듈 테스트
python -m pytest tests/test_markdown_parser.py -v
python -m pytest tests/test_template_analyzer.py -v
python -m pytest tests/test_slide_composer.py -v
python -m pytest tests/test_content_summarizer.py -v
python -m pytest tests/test_font_manager.py -v
python -m pytest tests/test_report_generator.py -v
```

### 테스트 구성 (66개)

| 테스트 파일 | 테스트 수 | 검증 내용 |
|------------|----------|----------|
| `test_template_analyzer.py` | 7 | 템플릿 분석 정확성, 오류 처리 |
| `test_markdown_parser.py` | 16 | 파싱 라운드트립, 구조 보존, 빈 문서 처리 |
| `test_font_manager.py` | 5 | 폰트 우선 적용, 기본값 대체 |
| `test_content_summarizer.py` | 4 | 슬라이드 수 범위, 표지 구성, API 오류 처리 |
| `test_slide_composer.py` | 16 | 콘텐츠 배치, 서식, 인라인 변환, 표, 페이지 번호 |
| `test_report_generator.py` | 16 | PPTX 유효성, 파일명 생성, CLI 파싱 |

## 프로젝트 구조

```
md_to_pptx/
├── __init__.py
├── models.py              # 데이터 모델 (dataclass)
├── exceptions.py          # 커스텀 예외/경고 클래스
├── template_analyzer.py   # PPTX 템플릿 분석
├── markdown_parser.py     # 마크다운 파싱 (mistune 3.x)
├── content_summarizer.py  # AI 요약 (Amazon Bedrock)
├── slide_composer.py      # 슬라이드 구성 (python-pptx)
├── font_manager.py        # 한국어 폰트 관리
├── report_generator.py    # 파이프라인 조율
└── main.py                # CLI 엔트리포인트
tests/
├── conftest.py            # 공통 픽스처
├── test_template_analyzer.py
├── test_markdown_parser.py
├── test_content_summarizer.py
├── test_font_manager.py
├── test_slide_composer.py
└── test_report_generator.py
```

## 라이선스

이 프로젝트는 개인 프로젝트입니다.
