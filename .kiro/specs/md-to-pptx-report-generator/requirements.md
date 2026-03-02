# 요구사항 문서

## 소개

마크다운(Markdown) 파일의 내용을 분석하고 요약하여, 사용자가 제공한 PPT 템플릿 양식에 맞게 자동으로 보고서용 PPTX 파일을 생성하는 Python 도구이다. Amazon Bedrock을 활용하여 콘텐츠를 요약하며, 한국어 폰트 지원과 높은 가독성을 갖춘 프레젠테이션을 출력한다.

## 용어 사전

- **Report_Generator**: 마크다운 파일과 PPT 템플릿을 입력받아 보고서용 PPTX 파일을 생성하는 전체 시스템
- **Template_Analyzer**: PPT 템플릿 파일의 슬라이드 레이아웃, 텍스트 박스, 제목 박스, 플레이스홀더(placeholder) 등 구조를 분석하는 모듈
- **Content_Summarizer**: Amazon Bedrock API를 호출하여 마크다운 콘텐츠를 보고서에 적합한 분량으로 요약하는 모듈
- **Slide_Composer**: 요약된 콘텐츠를 템플릿 레이아웃에 맞게 슬라이드에 배치하고 서식을 적용하는 모듈
- **Markdown_Parser**: 마크다운 파일을 파싱하여 제목, 본문, 목록, 코드 블록 등 구조화된 데이터로 변환하는 모듈
- **Font_Manager**: 한국어 폰트 설정 및 폰트 적용을 관리하는 모듈
- **플레이스홀더(Placeholder)**: PPT 템플릿 내에서 콘텐츠가 삽입될 위치를 나타내는 영역
- **슬라이드 레이아웃(Slide Layout)**: PPT 템플릿에 정의된 슬라이드의 구조적 배치 형태

## 요구사항

### 요구사항 1: PPT 템플릿 분석

**사용자 스토리:** 개발자로서, PPT 템플릿 파일을 입력하면 레이아웃 구조가 자동으로 분석되기를 원한다. 이를 통해 콘텐츠를 올바른 위치에 배치할 수 있다.

#### 인수 조건

1. WHEN 유효한 PPTX 템플릿 파일이 제공되면, THE Template_Analyzer SHALL 각 슬라이드 레이아웃에 포함된 플레이스홀더의 유형(제목, 부제목, 본문, 이미지 등)과 위치 정보를 추출한다
2. WHEN 템플릿 파일에 여러 슬라이드 레이아웃이 존재하면, THE Template_Analyzer SHALL 각 레이아웃의 이름, 플레이스홀더 개수, 플레이스홀더 유형 목록을 구조화된 데이터로 반환한다
3. IF 유효하지 않은 파일 형식이 제공되면, THEN THE Template_Analyzer SHALL "지원하지 않는 파일 형식입니다" 메시지와 함께 오류를 반환한다
4. IF 템플릿 파일에 플레이스홀더가 하나도 없으면, THEN THE Template_Analyzer SHALL "템플릿에 사용 가능한 플레이스홀더가 없습니다" 경고 메시지를 반환한다

### 요구사항 2: 마크다운 파일 파싱

**사용자 스토리:** 개발자로서, 마크다운 파일의 구조를 정확히 파싱하여 제목 계층, 본문, 목록, 코드 블록 등을 구분하고 싶다. 이를 통해 PPT 슬라이드에 적절히 매핑할 수 있다.

#### 인수 조건

1. WHEN 마크다운 파일이 제공되면, THE Markdown_Parser SHALL 제목(h1~h6), 본문 텍스트, 순서 있는 목록, 순서 없는 목록, 코드 블록, 표(table)를 구분하여 구조화된 데이터로 변환한다
2. WHEN 마크다운 파일에 중첩된 목록이 포함되면, THE Markdown_Parser SHALL 중첩 깊이를 보존하여 파싱한다
3. THE Markdown_Parser SHALL 마크다운 내 인라인 서식(굵게, 기울임, 코드)을 인식하고 해당 서식 정보를 보존한다
4. IF 빈 마크다운 파일이 제공되면, THEN THE Markdown_Parser SHALL "마크다운 파일에 내용이 없습니다" 오류 메시지를 반환한다
5. FOR ALL 유효한 마크다운 파일에 대해, 파싱 후 다시 마크다운 텍스트로 변환하면 원본과 의미적으로 동등한 결과를 생성한다 (라운드트립 속성)

### 요구사항 3: Amazon Bedrock 기반 콘텐츠 요약

**사용자 스토리:** 개발자로서, 마크다운 파일의 내용을 Amazon Bedrock을 통해 보고서에 적합한 분량으로 요약하고 싶다. 보고서 용도이므로 핵심 정보가 누락되지 않아야 한다.

#### 인수 조건

1. WHEN 파싱된 마크다운 콘텐츠가 제공되면, THE Content_Summarizer SHALL Amazon Bedrock API를 호출하여 보고서에 적합한 분량으로 요약된 텍스트를 반환한다
2. THE Content_Summarizer SHALL 요약 시 원본 마크다운의 제목 계층 구조를 유지한다
3. THE Content_Summarizer SHALL 요약 결과를 슬라이드 단위로 구분하여 반환하며, 마크다운 파일 하나당 최대 5개 슬라이드 분량으로 제한한다
4. WHILE 요약을 수행하는 동안, THE Content_Summarizer SHALL 핵심 데이터(수치, 날짜, 고유명사)를 보존한다
5. IF Amazon Bedrock API 호출이 실패하면, THEN THE Content_Summarizer SHALL 오류 코드와 "Bedrock API 호출에 실패했습니다" 메시지를 반환하고, 재시도 가능 여부를 안내한다
6. IF Amazon Bedrock API 응답 시간이 30초를 초과하면, THEN THE Content_Summarizer SHALL 타임아웃 오류를 반환한다


### 요구사항 4: 슬라이드 콘텐츠 배치 및 서식 적용

**사용자 스토리:** 개발자로서, 요약된 콘텐츠가 템플릿의 레이아웃에 맞게 자동 배치되고, 줄간격·들여쓰기·불릿포인트 등 서식이 적용되기를 원한다. 이를 통해 가독성 높은 보고서를 생성할 수 있다.

#### 인수 조건

1. WHEN 요약된 콘텐츠와 템플릿 레이아웃 정보가 제공되면, THE Slide_Composer SHALL 각 슬라이드의 플레이스홀더에 콘텐츠를 자동 배치한다
2. THE Slide_Composer SHALL 본문 텍스트에 1.2~1.5배 줄간격(line spacing)을 적용한다
3. THE Slide_Composer SHALL 목록 항목에 불릿포인트(bullet point)를 적용하고, 중첩 목록의 경우 깊이에 따라 들여쓰기를 적용한다
4. THE Slide_Composer SHALL 제목 텍스트와 본문 텍스트에 서로 다른 폰트 크기를 적용하여 시각적 계층 구조를 표현한다
5. WHEN 콘텐츠가 플레이스홀더의 영역을 초과하면, THE Slide_Composer SHALL 폰트 크기를 단계적으로 축소하여 영역 내에 맞춘다
6. IF 폰트 크기를 최소 크기(10pt)까지 축소해도 영역을 초과하면, THEN THE Slide_Composer SHALL 해당 슬라이드에 대해 "콘텐츠가 플레이스홀더 영역을 초과합니다" 경고를 기록한다
7. THE Slide_Composer SHALL 마크다운의 굵게(bold) 서식을 PPT의 굵게 서식으로, 기울임(italic) 서식을 PPT의 기울임 서식으로 변환한다

### 요구사항 5: 한국어 폰트 지원

**사용자 스토리:** 개발자로서, 생성된 PPT에 한국어 폰트가 올바르게 적용되기를 원한다. 한국어 텍스트가 깨지거나 대체 폰트로 표시되지 않아야 한다.

#### 인수 조건

1. THE Font_Manager SHALL 기본 한국어 폰트로 "맑은 고딕(Malgun Gothic)"을 사용한다
2. WHERE 사용자가 한국어 폰트를 지정하면, THE Font_Manager SHALL 지정된 폰트를 우선 적용한다
3. IF 지정된 한국어 폰트가 시스템에 설치되어 있지 않으면, THEN THE Font_Manager SHALL "지정된 폰트를 찾을 수 없습니다. 기본 폰트(맑은 고딕)를 사용합니다" 경고 메시지를 출력하고 기본 폰트로 대체한다
4. THE Font_Manager SHALL 영문 텍스트와 한국어 텍스트가 혼합된 경우에도 폰트가 일관되게 적용되도록 한다
5. THE Font_Manager SHALL PPT 파일 내에 폰트 정보를 임베딩하여 다른 시스템에서 열어도 동일하게 표시되도록 한다

### 요구사항 6: PPTX 파일 생성 및 출력

**사용자 스토리:** 개발자로서, 최종 결과물이 유효한 PPTX 파일로 저장되기를 원한다. 파일이 정상적으로 열리고 편집 가능해야 한다.

#### 인수 조건

1. WHEN 모든 슬라이드 구성이 완료되면, THE Report_Generator SHALL 유효한 PPTX 파일을 지정된 출력 경로에 저장한다
2. THE Report_Generator SHALL 생성된 PPTX 파일이 Microsoft PowerPoint 및 LibreOffice Impress에서 정상적으로 열리는 형식을 준수한다
3. WHEN 출력 파일명이 지정되지 않으면, THE Report_Generator SHALL 입력 마크다운 파일명을 기반으로 "{마크다운파일명}_report.pptx" 형식의 파일명을 자동 생성한다
4. IF 출력 경로에 동일한 이름의 파일이 이미 존재하면, THEN THE Report_Generator SHALL 기존 파일을 덮어쓰기 전에 사용자에게 확인을 요청한다
5. WHEN PPTX 파일 생성이 완료되면, THE Report_Generator SHALL 생성된 파일 경로, 슬라이드 수, 처리 소요 시간을 포함한 결과 요약을 출력한다

### 요구사항 7: 슬라이드 수 제한 및 콘텐츠 분배

**사용자 스토리:** 개발자로서, 마크다운 파일 하나의 내용이 PPT 5장을 넘지 않도록 제한하고 싶다. 보고서 용도이므로 적절한 분량을 유지해야 한다.

#### 인수 조건

1. THE Content_Summarizer SHALL 마크다운 파일 하나당 생성되는 슬라이드 수를 최대 5장으로 제한한다
2. WHEN 마크다운 콘텐츠의 분량이 적어 5장을 채울 필요가 없으면, THE Content_Summarizer SHALL 콘텐츠 분량에 맞게 슬라이드 수를 자동 조절한다 (최소 1장)
3. THE Content_Summarizer SHALL 첫 번째 슬라이드를 표지(제목 슬라이드)로 구성하고, 나머지 슬라이드에 본문 콘텐츠를 분배한다
4. THE Content_Summarizer SHALL 논리적 섹션(마크다운 제목 기준) 단위로 콘텐츠를 슬라이드에 분배하여 하나의 주제가 여러 슬라이드에 분산되지 않도록 한다

### 요구사항 8: CLI 인터페이스

**사용자 스토리:** 개발자로서, 명령줄에서 간편하게 도구를 실행하고 싶다. 템플릿 파일, 마크다운 파일, 출력 경로 등을 인자로 전달할 수 있어야 한다.

#### 인수 조건

1. THE Report_Generator SHALL 명령줄 인터페이스(CLI)를 통해 실행 가능하다
2. THE Report_Generator SHALL 다음 CLI 인자를 지원한다: 템플릿 파일 경로(필수), 마크다운 파일 경로(필수), 출력 파일 경로(선택), 한국어 폰트명(선택)
3. IF 필수 인자가 누락되면, THEN THE Report_Generator SHALL 사용법(usage) 안내 메시지를 출력한다
4. IF 지정된 입력 파일이 존재하지 않으면, THEN THE Report_Generator SHALL "파일을 찾을 수 없습니다: {파일경로}" 오류 메시지를 반환한다
5. WHEN 실행이 시작되면, THE Report_Generator SHALL 진행 상태(템플릿 분석 중, 콘텐츠 요약 중, 슬라이드 생성 중 등)를 콘솔에 출력한다

### 요구사항 9: PPT 품질 향상

**사용자 스토리:** 개발자로서, 생성된 PPT의 시각적 품질이 높기를 원한다. 전문적인 보고서로 사용할 수 있는 수준이어야 한다.

#### 인수 조건

1. THE Slide_Composer SHALL 텍스트 정렬(좌측 정렬 기본, 제목은 중앙 정렬)을 일관되게 적용한다
2. THE Slide_Composer SHALL 슬라이드 간 여백(margin)을 일관되게 유지한다
3. THE Slide_Composer SHALL 코드 블록을 고정폭 폰트(monospace font)와 배경색을 적용하여 시각적으로 구분한다
4. THE Slide_Composer SHALL 표(table) 데이터를 PPT 표 객체로 변환하며, 헤더 행에 배경색을 적용하여 구분한다
5. THE Slide_Composer SHALL 슬라이드 하단에 페이지 번호를 자동 삽입한다
6. WHILE 콘텐츠를 배치하는 동안, THE Slide_Composer SHALL 텍스트 박스 간 최소 간격을 유지하여 요소가 겹치지 않도록 한다
