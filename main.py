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
"""

import tkinter as tk
from src.ui.app import NaverReportViewerApp


def main():
    """앱 진입점"""
    root = tk.Tk()

    try:
        root.iconbitmap(default='')
    except:
        pass

    app = NaverReportViewerApp(root)
    app.run()


if __name__ == "__main__":
    main()
