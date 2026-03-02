"""
CLI 엔트리포인트 모듈.

argparse 기반 CLI로 마크다운 → PPTX 보고서 생성을 실행한다.
"""

import argparse
import logging
import os
import sys

from md_to_pptx.exceptions import ReportGeneratorError
from md_to_pptx.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        prog="md-to-pptx",
        description="마크다운 파일을 분석·요약하여 PPT 보고서를 자동 생성합니다.",
    )
    parser.add_argument(
        "template",
        help="PPT 템플릿 파일 경로 (.pptx)",
    )
    parser.add_argument(
        "markdown",
        help="마크다운 파일 경로 (.md)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="출력 파일 경로 (미지정 시 자동 생성)",
    )
    parser.add_argument(
        "-f", "--font",
        default=None,
        help="한국어 폰트명 (미지정 시 기본 폰트 사용)",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="출력 파일 중복 시 확인 없이 덮어쓰기",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 메인 함수."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = create_parser()
    args = parser.parse_args(argv)

    # 출력 파일 중복 확인
    output_path = args.output
    confirm_overwrite = args.yes

    if output_path and os.path.exists(output_path) and not confirm_overwrite:
        # 비대화형 환경(파이프라인, CI 등)에서는 자동 취소
        if not sys.stdin.isatty():
            print(
                f"❌ 출력 파일이 이미 존재합니다: {output_path}\n"
                "   비대화형 환경에서는 -y 옵션을 사용하세요.",
                file=sys.stderr,
            )
            return 1
        answer = input(f"파일이 이미 존재합니다: {output_path}\n덮어쓰시겠습니까? (y/N): ")
        if answer.lower() != "y":
            print("취소되었습니다.")
            return 1
        confirm_overwrite = True

    try:
        print(f"📄 템플릿 분석 중: {args.template}")
        print(f"📝 마크다운 파싱 중: {args.markdown}")

        generator = ReportGenerator()
        result = generator.generate(
            template_path=args.template,
            markdown_path=args.markdown,
            output_path=output_path,
            font_name=args.font,
            confirm_overwrite=confirm_overwrite,
        )

        print(f"✅ 보고서 생성 완료: {result.output_path}")
        print(f"   슬라이드 수: {result.slide_count}")
        print(f"   소요 시간: {result.elapsed_seconds:.2f}초")

        if result.warnings:
            print(f"   ⚠️  경고 {len(result.warnings)}건:")
            for w in result.warnings:
                print(f"      - {w}")

        return 0

    except ReportGeneratorError as e:
        print(f"❌ 오류: {e}", file=sys.stderr)
        return 1
    except FileExistsError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("예상치 못한 오류 발생")
        print(f"❌ 예상치 못한 오류: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
