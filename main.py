#!/usr/bin/env python3
"""
네이버 증권 종목 리포트 뷰어
- 오늘 날짜의 종목 리포트를 수집하여 보여줍니다.
- PDF 리포트를 직접 뷰어에서 확인할 수 있습니다.
- PDF 형광펜, 지우개, 되돌리기 기능 지원

필요 라이브러리 설치:
pip install -r requirements.txt
또는
pip install requests beautifulsoup4 lxml pymupdf pillow

키보드 단축키:
- Ctrl+F: PDF 텍스트 검색
- F3/Shift+F3: 다음/이전 검색 결과
- Ctrl+Z: 되돌리기
- Ctrl+S: 캡쳐
- Ctrl+R/F5: 새로고침
- Left/Right/Space: 페이지 이동
- Ctrl+/Ctrl-: 줌 인/아웃
- Home/End: 첫/마지막 페이지
"""

import logging
import sys
import tkinter as tk

from src.ui.app import NaverReportViewerApp


def setup_logging() -> None:
    """로깅 설정"""
    # 로그 포맷
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 루트 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

    # 디버그 모드 (환경변수나 인자로 제어 가능)
    if '--debug' in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("디버그 모드 활성화")


def main() -> None:
    """앱 진입점"""
    # 로깅 설정
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("네이버 증권 종목 리포트 뷰어 시작")

    # Tkinter 초기화
    root = tk.Tk()

    # 아이콘 설정 (실패해도 계속 진행)
    try:
        root.iconbitmap(default='')
    except tk.TclError:
        logger.debug("아이콘 설정 실패 (무시)")

    # 앱 실행
    try:
        app = NaverReportViewerApp(root)
        app.run()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 종료됨")
    except Exception as e:
        logger.exception(f"예기치 않은 오류: {e}")
        raise
    finally:
        logger.info("앱 종료")


if __name__ == "__main__":
    main()
