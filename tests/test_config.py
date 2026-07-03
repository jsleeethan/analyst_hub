"""
config.py 단위 테스트
"""

import unittest

from src.config import (
    COLORS, NAVER_BASE_URL, RESEARCH_URL,
    HTTP_HEADERS, PDF_RENDER_SCALE, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP,
    HIGHLIGHT_COLORS, LINE_COLORS,
    DEFAULT_HIGHLIGHT_COLOR, DEFAULT_LINE_COLOR,
    TRANSPARENCY_OPTIONS, DEFAULT_ALPHA,
    LINE_WIDTH_OPTIONS, DEFAULT_LINE_WIDTH,
    WINDOW_TITLE, WINDOW_GEOMETRY, WINDOW_MIN_SIZE,
    MAX_PAGES_TO_FETCH, REQUEST_TIMEOUT, PDF_DOWNLOAD_TIMEOUT,
    ALLOWED_PDF_DOMAINS, PARSER
)


class TestColorConfig(unittest.TestCase):
    """색상 설정 테스트"""

    def test_colors_has_required_keys(self):
        required_keys = [
            'bg_dark', 'bg_card', 'bg_elevated', 'border',
            'text_primary', 'text_secondary', 'text_muted',
            'accent', 'success', 'warning', 'danger'
        ]
        for key in required_keys:
            self.assertIn(key, COLORS, f"COLORS에 '{key}' 키 없음")

    def test_colors_are_hex_format(self):
        for key, value in COLORS.items():
            self.assertTrue(
                value.startswith('#'),
                f"COLORS['{key}'] = '{value}'는 # 으로 시작해야 함"
            )

    def test_highlight_colors_valid(self):
        for color in HIGHLIGHT_COLORS:
            self.assertTrue(color.startswith('#'))
            self.assertEqual(len(color), 7)

    def test_line_colors_valid(self):
        for color in LINE_COLORS:
            self.assertTrue(color.startswith('#'))
            self.assertEqual(len(color), 7)

    def test_default_colors_in_list(self):
        self.assertIn(DEFAULT_HIGHLIGHT_COLOR, HIGHLIGHT_COLORS)
        self.assertIn(DEFAULT_LINE_COLOR, LINE_COLORS)


class TestURLConfig(unittest.TestCase):
    """URL 설정 테스트"""

    def test_urls_are_https(self):
        self.assertTrue(NAVER_BASE_URL.startswith('https://'))
        self.assertTrue(RESEARCH_URL.startswith('https://'))

    def test_research_url_is_subpath(self):
        self.assertTrue(RESEARCH_URL.startswith(NAVER_BASE_URL))

    def test_http_headers_has_user_agent(self):
        self.assertIn('User-Agent', HTTP_HEADERS)
        self.assertIn('Accept', HTTP_HEADERS)


class TestPDFConfig(unittest.TestCase):
    """PDF 설정 테스트"""

    def test_render_scale_positive(self):
        self.assertGreater(PDF_RENDER_SCALE, 0)

    def test_zoom_range_valid(self):
        self.assertLess(ZOOM_MIN, ZOOM_MAX)
        self.assertGreater(ZOOM_MIN, 0)
        self.assertGreater(ZOOM_STEP, 0)

    def test_zoom_step_fits_range(self):
        # ZOOM_STEP이 범위 내에서 의미 있는 간격인지
        self.assertLessEqual(ZOOM_STEP, ZOOM_MAX - ZOOM_MIN)


class TestAnnotationConfig(unittest.TestCase):
    """어노테이션 설정 테스트"""

    def test_transparency_options_valid(self):
        for label, alpha in TRANSPARENCY_OPTIONS:
            self.assertIsInstance(label, str)
            self.assertGreaterEqual(alpha, 0)
            self.assertLessEqual(alpha, 255)

    def test_default_alpha_valid(self):
        self.assertGreaterEqual(DEFAULT_ALPHA, 0)
        self.assertLessEqual(DEFAULT_ALPHA, 255)

    def test_line_width_options_positive(self):
        for w in LINE_WIDTH_OPTIONS:
            self.assertGreater(w, 0)

    def test_default_line_width_in_options(self):
        self.assertIn(DEFAULT_LINE_WIDTH, LINE_WIDTH_OPTIONS)


class TestWindowConfig(unittest.TestCase):
    """창 설정 테스트"""

    def test_window_title_not_empty(self):
        self.assertTrue(len(WINDOW_TITLE) > 0)

    def test_window_geometry_format(self):
        # "WIDTHxHEIGHT" 형식
        self.assertIn('x', WINDOW_GEOMETRY)
        parts = WINDOW_GEOMETRY.split('x')
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].isdigit())
        self.assertTrue(parts[1].isdigit())

    def test_window_min_size_tuple(self):
        self.assertEqual(len(WINDOW_MIN_SIZE), 2)
        self.assertGreater(WINDOW_MIN_SIZE[0], 0)
        self.assertGreater(WINDOW_MIN_SIZE[1], 0)


class TestScrapingConfig(unittest.TestCase):
    """스크래핑 설정 테스트"""

    def test_max_pages_positive(self):
        self.assertGreater(MAX_PAGES_TO_FETCH, 0)

    def test_timeouts_positive(self):
        self.assertGreater(REQUEST_TIMEOUT, 0)
        self.assertGreater(PDF_DOWNLOAD_TIMEOUT, 0)

    def test_pdf_timeout_greater_than_request(self):
        self.assertGreaterEqual(PDF_DOWNLOAD_TIMEOUT, REQUEST_TIMEOUT)


class TestSecurityConfig(unittest.TestCase):
    """보안 설정 테스트"""

    def test_allowed_pdf_domains_not_empty(self):
        self.assertGreater(len(ALLOWED_PDF_DOMAINS), 0)

    def test_allowed_domains_are_strings(self):
        for domain in ALLOWED_PDF_DOMAINS:
            self.assertIsInstance(domain, str)
            self.assertGreater(len(domain), 0)

    def test_parser_valid(self):
        self.assertIn(PARSER, ('lxml', 'html.parser'))


if __name__ == '__main__':
    unittest.main()
