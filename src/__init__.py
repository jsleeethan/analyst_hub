"""
네이버 증권 종목 리포트 뷰어 패키지
"""

from .config import COLORS, NAVER_BASE_URL, RESEARCH_URL, PDF_RENDER_SCALE, ZOOM_MIN, ZOOM_MAX
from .models import ReportData, Annotation
from .scraper import NaverReportScraper
from .pdf_handler import PDFHandler

__all__ = [
    'COLORS',
    'NAVER_BASE_URL',
    'RESEARCH_URL',
    'PDF_RENDER_SCALE',
    'ZOOM_MIN',
    'ZOOM_MAX',
    'ReportData',
    'Annotation',
    'NaverReportScraper',
    'PDFHandler',
]
