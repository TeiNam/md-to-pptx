"""
CLI 엔트리포인트 모듈.

argparse 기반 CLI로 마크다운 → PPTX 보고서 생성을 실행한다.
단일 파일 또는 폴더 내 .md 파일 일괄 병렬 변환을 지원한다.
"""

import argparse
import glob
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

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
        help="마크다운 파일 경로 (.md) 또는 폴더 경로 (폴더 내 .md 일괄 변환)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="출력 파일 경로 (미지정 시 자동 생성, 폴더 모드에서는 출력 폴더)",
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
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="폴더 일괄 변환 시 병렬 워커 수 (기본: 4)",
    )
    return parser


def _convert_single(
    template_path: str,
    markdown_path: str,
    output_path: str | None,
    font_name: str | None,
    confirm_overwrite: bool,
) -> tuple[str, str | None]:
    """단일 파일 변환. (성공 메시지, 에러 메시지) 튜플 반환."""
    # 별도 프로세스에서 실행되므로 로깅 재설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        generator = ReportGenerator()
        result = generator.generate(
            template_path=template_path,
            markdown_path=markdown_path,
            output_path=output_path,
            font_name=font_name,
            confirm_overwrite=confirm_overwrite,
        )
        msg = (
            f"✅ {os.path.basename(markdown_path)} → "
            f"{os.path.basename(result.output_path)} "
            f"({result.slide_count}슬라이드, {result.elapsed_seconds:.1f}초)"
        )
        return msg, None
    except Exception as e:
        return "", f"❌ {os.path.basename(markdown_path)}: {e}"


def _run_batch(
    template_path: str,
    md_dir: str,
    output_dir: str | None,
    font_name: str | None,
    confirm_overwrite: bool,
    max_workers: int,
) -> int:
    """폴더 내 .md 파일을 병렬로 일괄 변환한다."""
    md_files = sorted(glob.glob(os.path.join(md_dir, "*.md")))
    if not md_files:
        print(f"❌ 폴더에 .md 파일이 없습니다: {md_dir}", file=sys.stderr)
        return 1

    print(f"📂 {len(md_files)}개 .md 파일 발견 (워커: {max_workers})")

    # 출력 경로 결정
    tasks: list[tuple[str, str, str | None, str | None, bool]] = []
    for md_path in md_files:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(md_path))[0]
            out = os.path.join(output_dir, f"{base}_report.pptx")
        else:
            out = None
        tasks.append((template_path, md_path, out, font_name, confirm_overwrite))

    success = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_convert_single, *task): task[1]
            for task in tasks
        }
        for future in as_completed(futures):
            msg, err = future.result()
            if err:
                print(err, file=sys.stderr)
                errors += 1
            else:
                print(msg)
                success += 1

    print(f"\n📊 완료: {success}건 성공, {errors}건 실패 / 총 {len(md_files)}건")
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI 메인 함수."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = create_parser()
    args = parser.parse_args(argv)

    # 폴더 모드: markdown 인자가 디렉토리인 경우
    if os.path.isdir(args.markdown):
        return _run_batch(
            template_path=args.template,
            md_dir=args.markdown,
            output_dir=args.output,
            font_name=args.font,
            confirm_overwrite=args.yes,
            max_workers=args.workers,
        )

    # 단일 파일 모드
    output_path = args.output
    confirm_overwrite = args.yes

    if output_path and os.path.exists(output_path) and not confirm_overwrite:
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
