"""
scraper.py 단위 테스트
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import requests

from src.scraper import NaverReportScraper
from src.models import ReportData


# 테스트용 HTML 페이지 생성
SAMPLE_HTML = """
<html>
<body>
<table class="type_1">
<tr>
    <td><a href="/item/main.naver?code=005930">삼성전자</a></td>
    <td><a href="/research/company_read.naver?nid=12345">실적 점검 리포트</a></td>
    <td>미래에셋증권</td>
    <td><a href="https://ssl.pstatic.net/imgstock/upload/research/company/1234.pdf">PDF</a></td>
    <td>26.02.02</td>
    <td>150</td>
</tr>
<tr>
    <td><a href="/item/main.naver?code=000660">SK하이닉스</a></td>
    <td><a href="/research/company_read.naver?nid=12346">반도체 전망</a></td>
    <td>KB증권</td>
    <td><a href="https://ssl.pstatic.net/imgstock/upload/research/company/1235.pdf">PDF</a></td>
    <td>26.02.02</td>
    <td>80</td>
</tr>
<tr>
    <td><a href="/item/main.naver?code=035420">NAVER</a></td>
    <td><a href="/research/company_read.naver?nid=12340">어제 리포트</a></td>
    <td>한국투자증권</td>
    <td><a href="https://ssl.pstatic.net/imgstock/upload/research/company/1230.pdf">PDF</a></td>
    <td>26.02.01</td>
    <td>200</td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_HTML_NO_TABLE = """
<html><body><div>No table here</div></body></html>
"""

SAMPLE_META_HTML = """
<html>
<body>
<table class="view_type_1">
<tr><th>투자의견</th><td>매수</td></tr>
<tr><th>목표주가</th><td>80,000</td></tr>
</table>
</body>
</html>
"""


class TestNaverReportScraperURLValidation(unittest.TestCase):
    """URL 검증 테스트"""

    def test_valid_https_url(self):
        url = "https://ssl.pstatic.net/imgstock/upload/research/company/1234.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, url)

    def test_http_upgraded_to_https(self):
        url = "http://ssl.pstatic.net/imgstock/upload/research/company/1234.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertTrue(result.startswith("https://"))

    def test_invalid_domain(self):
        url = "https://evil.com/malware.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, "")

    def test_empty_url(self):
        result = NaverReportScraper._validate_pdf_url("")
        self.assertEqual(result, "")

    def test_none_like_empty(self):
        result = NaverReportScraper._validate_pdf_url("")
        self.assertEqual(result, "")

    def test_ftp_protocol(self):
        url = "ftp://ssl.pstatic.net/file.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, "")

    def test_javascript_protocol(self):
        url = "javascript:alert(1)"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, "")

    def test_subdomain_allowed(self):
        url = "https://sub.ssl.pstatic.net/file.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, url)

    def test_finance_naver_domain(self):
        url = "https://finance.naver.com/research/something.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, url)

    def test_stock_pstatic_domain(self):
        url = "https://stock.pstatic.net/file.pdf"
        result = NaverReportScraper._validate_pdf_url(url)
        self.assertEqual(result, url)


class TestNaverReportScraperParsing(unittest.TestCase):
    """HTML 파싱 테스트 (네트워크 접근 없이)"""

    def setUp(self):
        self.scraper = NaverReportScraper()

    def tearDown(self):
        self.scraper.close()

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_success(self, mock_get):
        """정상적인 리포트 파싱"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        reports = self.scraper.fetch_reports(date="26.02.02")

        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0].stock, "삼성전자")
        self.assertEqual(reports[0].firm, "미래에셋증권")
        self.assertEqual(reports[1].stock, "SK하이닉스")

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_filters_by_date(self, mock_get):
        """날짜 필터링 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        reports = self.scraper.fetch_reports(date="26.02.01")

        # 26.02.01 날짜의 리포트만
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].stock, "NAVER")

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_no_table(self, mock_get):
        """테이블 없는 HTML"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML_NO_TABLE
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        reports = self.scraper.fetch_reports(date="26.02.02")
        self.assertEqual(len(reports), 0)

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_timeout(self, mock_get):
        """타임아웃 시 빈 리스트 반환"""
        mock_get.side_effect = requests.Timeout("timeout")

        reports = self.scraper.fetch_reports(date="26.02.02")
        self.assertEqual(len(reports), 0)

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_http_error(self, mock_get):
        """HTTP 오류 시 빈 리스트 반환"""
        mock_get.side_effect = requests.HTTPError("500 Server Error")

        reports = self.scraper.fetch_reports(date="26.02.02")
        self.assertEqual(len(reports), 0)

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_network_error(self, mock_get):
        """네트워크 오류 시 빈 리스트 반환"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        reports = self.scraper.fetch_reports(date="26.02.02")
        self.assertEqual(len(reports), 0)

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_pdf_url_validated(self, mock_get):
        """PDF URL이 검증되는지 확인"""
        html = """
        <html><body>
        <table class="type_1">
        <tr>
            <td><a href="/item/main.naver?code=005930">테스트</a></td>
            <td><a href="/research/company_read.naver?nid=1">제목</a></td>
            <td>증권사</td>
            <td><a href="https://evil.com/malware.pdf">PDF</a></td>
            <td>26.02.02</td>
            <td>10</td>
        </tr>
        </table>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        reports = self.scraper.fetch_reports(date="26.02.02")
        self.assertEqual(len(reports), 1)
        # 악성 도메인 URL은 빈 문자열로 대체되어야 함
        self.assertEqual(reports[0].pdf_link, "")

    @patch.object(requests.Session, 'get')
    def test_fetch_reports_progress_callback(self, mock_get):
        """진행 콜백 호출 확인"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        callback = MagicMock()
        self.scraper.fetch_reports(date="26.02.02", progress_callback=callback)

        self.assertTrue(callback.called)
        # 첫 번째 호출의 첫 번째 인자가 1 (첫 페이지)
        self.assertEqual(callback.call_args_list[0][0][0], 1)

    @patch.object(requests.Session, 'get')
    def test_fetch_report_meta(self, mock_get):
        """메타 정보 파싱 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_META_HTML
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        report = ReportData(
            stock="삼성전자", title="리포트", firm="증권사",
            date="26.02.02", link="https://finance.naver.com/research/company_read.naver?nid=1"
        )

        result = self.scraper.fetch_report_meta(report)
        self.assertEqual(result.opinion, "매수")
        self.assertEqual(result.target, "80,000")

    @patch.object(requests.Session, 'get')
    def test_fetch_report_meta_timeout(self, mock_get):
        """메타 정보 타임아웃 시 기본값 유지"""
        mock_get.side_effect = requests.Timeout("timeout")

        report = ReportData(
            stock="삼성전자", title="리포트", firm="증권사",
            date="26.02.02", link="https://finance.naver.com/research/company_read.naver?nid=1"
        )

        result = self.scraper.fetch_report_meta(report)
        self.assertEqual(result.opinion, "-")
        self.assertEqual(result.target, "-")


class TestNaverReportScraperContextManager(unittest.TestCase):
    """컨텍스트 매니저 테스트"""

    def test_context_manager(self):
        with NaverReportScraper() as scraper:
            self.assertIsNotNone(scraper.session)
        # 컨텍스트 종료 후 세션 닫힘 (에러 없이)

    def test_close(self):
        scraper = NaverReportScraper()
        scraper.close()  # should not raise


if __name__ == '__main__':
    unittest.main()
