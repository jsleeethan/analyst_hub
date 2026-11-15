"""
웹 크롤링 모듈
- NaverReportScraper: 네이버 금융 리포트 스크래핑 (신규 JSON API 기반)
"""

import requests
from datetime import datetime
from typing import List, Optional, Callable

from .config import HTTP_HEADERS, REQUEST_TIMEOUT
from .models import ReportData


API_BASE = "https://stock.naver.com"
LIST_ENDPOINT = "/api/stockSecurity/researches/v2/company"
DETAIL_ENDPOINT = "/api/stockSecurity/researches/v2/company/{nid}/detail-page"
REPORT_PAGE_URL = "https://stock.naver.com/research/company/{nid}"


class NaverReportScraper:
    """네이버 금융 종목 리포트 스크래퍼 (stock.naver.com JSON API)"""

    def __init__(self):
        self.session = requests.Session()
        headers = dict(HTTP_HEADERS)
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['Referer'] = 'https://stock.naver.com/research/company'
        self.session.headers.update(headers)

    def fetch_reports(self, date: Optional[str] = None,
                      progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ReportData]:
        """
        리포트 목록 가져오기

        Args:
            date: 필터링할 날짜 (yyyy-mm-dd 또는 yy.mm.dd 형식). None이면 오늘
            progress_callback: 진행 상황 콜백 (current, total)

        Returns:
            ReportData 리스트
        """
        today = datetime.now()
        if date is None:
            start_date = today.strftime("%Y-%m-%d")
        else:
            start_date = self._normalize_date(date)

        reports: List[ReportData] = []
        index = 0
        page_size = 50

        while True:
            params = {
                'size': page_size,
                'index': index,
                'startDate': start_date,
                'endDate': start_date,
            }

            if progress_callback:
                progress_callback(index + 1, index + 1)

            try:
                resp = self.session.get(
                    API_BASE + LIST_ENDPOINT,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError):
                break

            items = data.get('items', []) or []
            for item in items:
                report = self._parse_item(item)
                if report is not None:
                    reports.append(report)

            if not data.get('hasNext'):
                break
            index += len(items) or page_size

        return reports

    @staticmethod
    def _normalize_date(date: str) -> str:
        """다양한 날짜 포맷을 yyyy-mm-dd 로 정규화"""
        date = date.strip()
        for fmt in ("%Y-%m-%d", "%y.%m.%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(date, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date

    @staticmethod
    def _display_date(iso_date: str) -> str:
        """yyyy-mm-dd → yy.mm.dd"""
        try:
            return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%y.%m.%d")
        except (ValueError, TypeError):
            return iso_date or ""

    @staticmethod
    def _format_price(value) -> str:
        """목표가 포맷팅 (천 단위 콤마)"""
        if not value:
            return "-"
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)

    def _parse_item(self, item: dict) -> Optional[ReportData]:
        """API 응답의 리포트 항목 파싱"""
        try:
            nid = item.get('nid')
            if not nid:
                return None

            return ReportData(
                stock=item.get('itemName', ''),
                title=item.get('title', ''),
                firm=item.get('brokerName', ''),
                date=self._display_date(item.get('writeDate', '')),
                link=REPORT_PAGE_URL.format(nid=nid),
                pdf_link="",  # 상세 조회 시 채워짐
                views=str(item.get('readCount', '0')),
                opinion=item.get('opinionText') or "-",
                target=self._format_price(item.get('goalPrice')),
            )
        except Exception:
            return None

    def fetch_report_meta(self, report: ReportData) -> ReportData:
        """
        리포트 상세 정보 가져오기 (PDF 링크, 투자의견, 목표가)

        Args:
            report: ReportData 객체

        Returns:
            업데이트된 ReportData 객체
        """
        nid = self._extract_nid(report.link)
        if not nid:
            return report

        try:
            resp = self.session.get(
                API_BASE + DETAIL_ENDPOINT.format(nid=nid),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return report

        content = data.get('researchContent') or {}

        attach_url = content.get('attachUrl')
        if attach_url:
            report.pdf_link = attach_url

        opinion = content.get('opinionText')
        if opinion:
            report.opinion = opinion

        goal = content.get('goalPrice')
        if goal:
            report.target = self._format_price(goal)

        return report

    @staticmethod
    def _extract_nid(link: str) -> str:
        """리포트 상세 페이지 URL에서 nid 추출"""
        if not link:
            return ""
        return link.rstrip('/').rsplit('/', 1)[-1]

    def close(self):
        """세션 종료"""
        self.session.close()
