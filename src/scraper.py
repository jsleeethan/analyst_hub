"""
웹 크롤링 모듈
- NaverReportScraper: 네이버 금융 리포트 스크래핑
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Optional, Callable

from .config import (
    RESEARCH_URL, HTTP_HEADERS, PARSER,
    MAX_PAGES_TO_FETCH, REQUEST_TIMEOUT
)
from .models import ReportData


class NaverReportScraper:
    """네이버 금융 종목 리포트 스크래퍼"""

    def __init__(self):
        self.headers = HTTP_HEADERS
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_reports(self, date: Optional[str] = None,
                      progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ReportData]:
        """
        리포트 목록 가져오기

        Args:
            date: 필터링할 날짜 (yy.mm.dd 형식), None이면 오늘
            progress_callback: 진행 상황 콜백 (current_page, total_pages)

        Returns:
            ReportData 리스트
        """
        if date is None:
            date = datetime.now().strftime("%y.%m.%d")

        reports = []

        for page in range(1, MAX_PAGES_TO_FETCH + 1):
            if progress_callback:
                progress_callback(page, MAX_PAGES_TO_FETCH)

            url = f"{RESEARCH_URL}company_list.naver?&page={page}"

            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.encoding = 'euc-kr'

                soup = BeautifulSoup(response.text, PARSER)
                table = soup.find('table', class_='type_1')

                if not table:
                    continue

                rows = table.find_all('tr')
                found_old_date = False

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue

                    report = self._parse_report_row(cols)
                    if report is None:
                        continue

                    if report.date == date:
                        reports.append(report)
                    elif reports and report.date != date:
                        found_old_date = True
                        break

                if found_old_date:
                    break

                # 마지막 행의 날짜 확인
                if reports and rows:
                    last_row = rows[-1] if rows else None
                    if last_row:
                        cols = last_row.find_all('td')
                        if len(cols) >= 5:
                            last_date = cols[4].get_text(strip=True)
                            if last_date != date:
                                break

            except requests.RequestException:
                continue

        return reports

    def _parse_report_row(self, cols) -> Optional[ReportData]:
        """테이블 행에서 리포트 정보 파싱"""
        try:
            stock_link = cols[0].find('a')
            if not stock_link:
                return None
            stock_name = stock_link.get_text(strip=True)

            title_link = cols[1].find('a')
            if not title_link:
                return None
            title = title_link.get_text(strip=True)
            report_link = urljoin(RESEARCH_URL, title_link.get('href', ''))

            firm = cols[2].get_text(strip=True)

            pdf_link_tag = cols[3].find('a')
            pdf_link = ""
            if pdf_link_tag:
                pdf_link = pdf_link_tag.get('href', '')

            date = cols[4].get_text(strip=True)
            views = cols[5].get_text(strip=True)

            return ReportData(
                stock=stock_name,
                title=title,
                firm=firm,
                date=date,
                link=report_link,
                pdf_link=pdf_link,
                views=views,
            )

        except Exception:
            return None

    def fetch_report_meta(self, report: ReportData) -> ReportData:
        """
        리포트 상세 정보 가져오기 (투자의견, 목표가)

        Args:
            report: ReportData 객체

        Returns:
            업데이트된 ReportData 객체
        """
        try:
            response = self.session.get(report.link, timeout=REQUEST_TIMEOUT)
            response.encoding = 'euc-kr'

            soup = BeautifulSoup(response.text, PARSER)

            table = soup.find('table', class_='view_type_1')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        label = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        if '투자의견' in label:
                            report.opinion = value
                        elif '목표주가' in label or '목표가' in label:
                            report.target = value

        except requests.RequestException:
            pass

        return report

    def close(self):
        """세션 종료"""
        self.session.close()
