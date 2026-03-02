---
inclusion: always
---

# 프로젝트 환경 설정

## Python 환경
- Python 버전: 3.12.12 (pyenv)
- 가상환경: `md-to-pptx-env` (pyenv-virtualenv)
- 가상환경 활성화 명령 (bash에서 실행 시):
  ```bash
  export PATH="$HOME/.pyenv/bin:$HOME/.pyenv/shims:$PATH" && eval "$(pyenv init -)" && eval "$(pyenv virtualenv-init -)"
  ```

## 의존성
- 핵심: python-pptx, mistune 3.x, boto3
- 테스트: pytest, hypothesis
- CLI: argparse (표준 라이브러리)

## 프로젝트 구조
```
md_to_pptx/          # 메인 패키지
  __init__.py
  models.py          # 데이터 모델 (dataclass)
  exceptions.py      # 커스텀 예외
  template_analyzer.py
  markdown_parser.py
  content_summarizer.py
  slide_composer.py
  font_manager.py
  report_generator.py
  main.py            # CLI 엔트리포인트
tests/               # 테스트
  conftest.py        # 공통 픽스처
```

## 명령어
- 테스트 실행: `python -m pytest tests/ -v`
- 특정 테스트: `python -m pytest tests/test_xxx.py -v`
- 패키지 설치: `pip install -r requirements.txt`


