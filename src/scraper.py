"""
웹 크롤링 모듈
- NaverReportScraper: 네이버 금융 리포트 스크래핑
"""

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Callable

from .config import (
    RESEARCH_URL, HTTP_HEADERS, PARSER,
    MAX_PAGES_TO_FETCH, REQUEST_TIMEOUT,
    ALLOWED_PDF_DOMAINS
)
from .models import ReportData

# 로거 설정
logger = logging.getLogger(__name__)


class NaverReportScraper:
    """네이버 금융 종목 리포트 스크래퍼"""

    def __init__(self) -> None:
        self.headers = HTTP_HEADERS
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        logger.debug("NaverReportScraper 초기화됨")

    def fetch_reports(self, date: Optional[str] = None,
                      progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ReportData]:
        """
        리포트 목록 가져오기

        Args:
            date: 필터링할 날짜 (yy.mm.dd 형식), None이면 오늘
            progress_callback: 진행 상황 콜백 (current_page, total_pages)

        Returns:
            ReportData 리스트

        Raises:
            requests.RequestException: 네트워크 오류 발생 시
        """
        if date is None:
            date = datetime.now().strftime("%y.%m.%d")

        logger.info(f"리포트 목록 가져오기 시작: 날짜={date}")
        reports: List[ReportData] = []
        consecutive_errors = 0
        max_consecutive_errors = 3

        for page in range(1, MAX_PAGES_TO_FETCH + 1):
            if progress_callback:
                progress_callback(page, MAX_PAGES_TO_FETCH)

            url = f"{RESEARCH_URL}company_list.naver?&page={page}"
            logger.debug(f"페이지 {page} 요청: {url}")

            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()  # HTTP 에러 체크

                # 인코딩 자동 감지 시도
                if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                    response.encoding = 'euc-kr'

                soup = BeautifulSoup(response.text, PARSER)
                table = soup.find('table', class_='type_1')

                if not table:
                    logger.warning(f"페이지 {page}: 테이블을 찾을 수 없음")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("연속 오류 한계 도달, 스크래핑 중단")
                        break
                    continue

                # 오류 카운터 리셋
                consecutive_errors = 0

                rows = table.find_all('tr')
                found_old_date = False
                page_reports = 0

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue

                    report = self._parse_report_row(cols)
                    if report is None:
                        continue

                    if report.date == date:
                        reports.append(report)
                        page_reports += 1
                    elif reports and report.date != date:
                        found_old_date = True
                        break

                logger.debug(f"페이지 {page}: {page_reports}개 리포트 수집")

                if found_old_date:
                    logger.debug(f"이전 날짜 리포트 발견, 스크래핑 종료")
                    break

                # 마지막 행의 날짜 확인
                if reports and rows:
                    last_row = rows[-1] if rows else None
                    if last_row:
                        cols = last_row.find_all('td')
                        if len(cols) >= 5:
                            last_date = cols[4].get_text(strip=True)
                            if last_date != date:
                                logger.debug(f"마지막 행 날짜가 다름 ({last_date}), 스크래핑 종료")
                                break

            except requests.Timeout:
                logger.warning(f"페이지 {page} 요청 타임아웃")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("연속 타임아웃 한계 도달, 스크래핑 중단")
                    break
                continue

            except requests.HTTPError as e:
                logger.warning(f"페이지 {page} HTTP 오류: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("연속 HTTP 오류 한계 도달, 스크래핑 중단")
                    break
                continue

            except requests.RequestException as e:
                logger.error(f"페이지 {page} 네트워크 오류: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("연속 네트워크 오류 한계 도달, 스크래핑 중단")
                    break
                continue

            except Exception as e:
                logger.error(f"페이지 {page} 예기치 않은 오류: {e}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
                continue

        logger.info(f"리포트 목록 가져오기 완료: 총 {len(reports)}개")
        return reports

    def _parse_report_row(self, cols) -> Optional[ReportData]:
        """
        테이블 행에서 리포트 정보 파싱

        Args:
            cols: BeautifulSoup td 요소 리스트

        Returns:
            ReportData 또는 None
        """
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
                raw_pdf_link = pdf_link_tag.get('href', '')
                pdf_link = self._validate_pdf_url(raw_pdf_link)

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

        except (IndexError, AttributeError) as e:
            logger.debug(f"행 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.warning(f"행 파싱 중 예기치 않은 오류: {e}")
            return None

    @staticmethod
    def _validate_pdf_url(url: str) -> str:
        """
        PDF URL 유효성 검사

        Args:
            url: 검증할 URL

        Returns:
            유효한 URL 또는 빈 문자열
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)

            # HTTPS 프로토콜 강제
            if parsed.scheme not in ('https', 'http'):
                logger.warning(f"허용되지 않은 프로토콜: {parsed.scheme} ({url})")
                return ""

            # HTTP를 HTTPS로 업그레이드
            if parsed.scheme == 'http':
                url = 'https' + url[4:]
                parsed = urlparse(url)
                logger.debug(f"HTTP → HTTPS 업그레이드: {url}")

            # 허용된 도메인 확인
            domain = parsed.hostname or ''
            if not any(domain == allowed or domain.endswith('.' + allowed)
                       for allowed in ALLOWED_PDF_DOMAINS):
                logger.warning(f"허용되지 않은 PDF 도메인: {domain} ({url})")
                return ""

            return url

        except Exception as e:
            logger.warning(f"PDF URL 검증 실패: {url}, 오류: {e}")
            return ""

    def fetch_report_meta(self, report: ReportData) -> ReportData:
        """
        리포트 상세 정보 가져오기 (투자의견, 목표가)

        Args:
            report: ReportData 객체

        Returns:
            업데이트된 ReportData 객체
        """
        logger.debug(f"메타 정보 가져오기: {report.stock} - {report.title}")

        try:
            response = self.session.get(report.link, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # 인코딩 자동 감지
            if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
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
                            logger.debug(f"투자의견: {value}")
                        elif '목표주가' in label or '목표가' in label:
                            report.target = value
                            logger.debug(f"목표가: {value}")

        except requests.Timeout:
            logger.warning(f"메타 정보 요청 타임아웃: {report.link}")
        except requests.HTTPError as e:
            logger.warning(f"메타 정보 HTTP 오류: {e}")
        except requests.RequestException as e:
            logger.warning(f"메타 정보 네트워크 오류: {e}")
        except Exception as e:
            logger.error(f"메타 정보 파싱 오류: {e}", exc_info=True)

        return report

    def close(self) -> None:
        """세션 종료"""
        try:
            self.session.close()
            logger.debug("스크래퍼 세션 종료됨")
        except Exception as e:
            logger.warning(f"세션 종료 중 오류: {e}")

    def __enter__(self) -> 'NaverReportScraper':
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료"""
        self.close()
