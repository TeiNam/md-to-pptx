"""
커스텀 예외 및 경고 클래스 정의 모듈.

보고서 생성 파이프라인에서 발생할 수 있는 오류와 경고를 정의한다.
예외(Exception)는 처리를 계속할 수 없는 치명적 오류에 사용하고,
경고(Warning)는 처리는 계속 가능하지만 사용자에게 알려야 하는 상황에 사용한다.
"""


# === 예외 클래스 ===


class ReportGeneratorError(Exception):
    """보고서 생성기 기본 예외"""

    pass


class InvalidFileFormatError(ReportGeneratorError):
    """유효하지 않은 파일 형식 (요구사항 1.3)"""

    def __init__(self, path: str):
        super().__init__(f"지원하지 않는 파일 형식입니다: {path}")


class FileNotFoundError(ReportGeneratorError):
    """파일을 찾을 수 없음 (요구사항 8.4)"""

    def __init__(self, path: str):
        super().__init__(f"파일을 찾을 수 없습니다: {path}")


class EmptyDocumentError(ReportGeneratorError):
    """빈 마크다운 파일 (요구사항 2.4)"""

    def __init__(self):
        super().__init__("마크다운 파일에 내용이 없습니다")


class BedrockAPIError(ReportGeneratorError):
    """Bedrock API 호출 실패 (요구사항 3.5)"""

    def __init__(self, error_code: str, retryable: bool = False):
        msg = f"Bedrock API 호출에 실패했습니다 (코드: {error_code})"
        if retryable:
            msg += " - 재시도 가능"
        super().__init__(msg)
        self.error_code = error_code
        self.retryable = retryable


class BedrockTimeoutError(BedrockAPIError):
    """Bedrock API 타임아웃 (요구사항 3.6)"""

    def __init__(self):
        super().__init__(error_code="TIMEOUT", retryable=True)


# === 경고 클래스 ===


class NoPlaceholderWarning(UserWarning):
    """플레이스홀더 없음 경고 (요구사항 1.4)"""

    def __init__(self):
        super().__init__("템플릿에 사용 가능한 플레이스홀더가 없습니다")


class ContentOverflowWarning(UserWarning):
    """콘텐츠 영역 초과 경고 (요구사항 4.6)"""

    def __init__(self, slide_index: int):
        super().__init__(
            f"슬라이드 {slide_index}: 콘텐츠가 플레이스홀더 영역을 초과합니다"
        )


class FontNotFoundWarning(UserWarning):
    """폰트 미설치 경고 (요구사항 5.3)"""

    def __init__(self, font_name: str):
        super().__init__(
            f"지정된 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다: {font_name}"
        )
