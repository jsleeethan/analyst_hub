"""
pdf_handler.py 단위 테스트
"""

import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

from src.pdf_handler import parse_hex_color, PDFHandler


class TestParseHexColor(unittest.TestCase):
    """parse_hex_color 함수 테스트"""

    def test_valid_color(self):
        self.assertEqual(parse_hex_color('#FF0000'), (255, 0, 0))
        self.assertEqual(parse_hex_color('#00FF00'), (0, 255, 0))
        self.assertEqual(parse_hex_color('#0000FF'), (0, 0, 255))

    def test_black_white(self):
        self.assertEqual(parse_hex_color('#000000'), (0, 0, 0))
        self.assertEqual(parse_hex_color('#FFFFFF'), (255, 255, 255))

    def test_lowercase(self):
        self.assertEqual(parse_hex_color('#ff0000'), (255, 0, 0))
        self.assertEqual(parse_hex_color('#abcdef'), (171, 205, 239))

    def test_mixed_case(self):
        self.assertEqual(parse_hex_color('#FfAa00'), (255, 170, 0))

    def test_empty_string(self):
        r, g, b = parse_hex_color('')
        self.assertEqual((r, g, b), (255, 255, 0))  # 기본 노란색

    def test_none_input(self):
        r, g, b = parse_hex_color(None)
        self.assertEqual((r, g, b), (255, 255, 0))

    def test_no_hash(self):
        r, g, b = parse_hex_color('FF0000')
        self.assertEqual((r, g, b), (255, 255, 0))

    def test_too_short(self):
        r, g, b = parse_hex_color('#FFF')
        self.assertEqual((r, g, b), (255, 255, 0))

    def test_too_long(self):
        r, g, b = parse_hex_color('#FF000000')
        self.assertEqual((r, g, b), (255, 255, 0))

    def test_invalid_hex(self):
        r, g, b = parse_hex_color('#ZZZZZZ')
        self.assertEqual((r, g, b), (255, 255, 0))


class TestPDFHandler(unittest.TestCase):
    """PDFHandler 기본 테스트"""

    def setUp(self):
        self.handler = PDFHandler()

    def test_initial_state(self):
        self.assertEqual(self.handler.total_pages, 0)
        self.assertEqual(self.handler.current_page, 0)
        self.assertEqual(self.handler.zoom_level, 1.0)
        self.assertEqual(self.handler.annotations, {})

    def test_render_page_no_pdf(self):
        result = self.handler.render_page()
        self.assertIsNone(result)

    def test_render_page_invalid_page(self):
        self.handler.total_pages = 5
        result = self.handler.render_page(page_num=-1)
        self.assertIsNone(result)

        result = self.handler.render_page(page_num=10)
        self.assertIsNone(result)

    def test_reset(self):
        self.handler.total_pages = 10
        self.handler.current_page = 5
        self.handler.zoom_level = 1.5
        self.handler.annotations = {0: [{'type': 'highlight'}]}

        self.handler.reset()

        self.assertEqual(self.handler.total_pages, 0)
        self.assertEqual(self.handler.current_page, 0)
        self.assertEqual(self.handler.zoom_level, 1.0)
        self.assertEqual(self.handler.annotations, {})

    def test_add_highlight(self):
        ann = self.handler.add_highlight(
            page_num=0, coords=(10, 20, 100, 50),
            color='#FFFF00', alpha=77, zoom=1.0
        )
        self.assertEqual(ann['type'], 'highlight')
        self.assertEqual(ann['coords'], (10, 20, 100, 50))
        self.assertEqual(ann['color'], '#FFFF00')
        self.assertIn(0, self.handler.annotations)
        self.assertEqual(len(self.handler.annotations[0]), 1)

    def test_add_line(self):
        ann = self.handler.add_line(
            page_num=1, coords=(0, 0, 100, 100),
            color='#FF0000', width=3, zoom=1.0
        )
        self.assertEqual(ann['type'], 'line')
        self.assertEqual(ann['width'], 3)
        self.assertIn(1, self.handler.annotations)

    def test_add_multiple_annotations(self):
        self.handler.add_highlight(0, (0, 0, 10, 10), '#FFFF00', 77, 1.0)
        self.handler.add_highlight(0, (20, 20, 30, 30), '#00FF00', 77, 1.0)
        self.handler.add_line(0, (0, 0, 50, 50), '#FF0000', 3, 1.0)

        self.assertEqual(len(self.handler.annotations[0]), 3)

    def test_remove_annotation(self):
        ann = self.handler.add_highlight(0, (0, 0, 10, 10), '#FFFF00', 77, 1.0)
        result = self.handler.remove_annotation(0, ann)
        self.assertTrue(result)
        self.assertEqual(len(self.handler.annotations[0]), 0)

    def test_remove_annotation_not_found(self):
        fake_ann = {'type': 'highlight', 'coords': (0, 0, 1, 1)}
        result = self.handler.remove_annotation(0, fake_ann)
        self.assertFalse(result)

    def test_remove_annotation_wrong_page(self):
        ann = self.handler.add_highlight(0, (0, 0, 10, 10), '#FFFF00', 77, 1.0)
        result = self.handler.remove_annotation(1, ann)
        self.assertFalse(result)

    def test_clear_annotations(self):
        self.handler.add_highlight(0, (0, 0, 10, 10), '#FFFF00', 77, 1.0)
        self.handler.add_line(0, (0, 0, 50, 50), '#FF0000', 3, 1.0)

        cleared = self.handler.clear_annotations(0)
        self.assertEqual(len(cleared), 2)
        self.assertEqual(len(self.handler.annotations[0]), 0)

    def test_clear_annotations_empty_page(self):
        cleared = self.handler.clear_annotations(5)
        self.assertEqual(cleared, [])

    def test_find_annotation_at_point_highlight(self):
        self.handler.add_highlight(0, (10, 10, 100, 50), '#FFFF00', 77, 1.0)
        found = self.handler.find_annotation_at_point(0, 50, 30, 1.0)
        self.assertIsNotNone(found)
        self.assertEqual(found['type'], 'highlight')

    def test_find_annotation_at_point_outside(self):
        self.handler.add_highlight(0, (10, 10, 100, 50), '#FFFF00', 77, 1.0)
        found = self.handler.find_annotation_at_point(0, 200, 200, 1.0)
        self.assertIsNone(found)

    def test_find_annotation_at_point_no_annotations(self):
        found = self.handler.find_annotation_at_point(0, 50, 50, 1.0)
        self.assertIsNone(found)

    def test_find_annotation_line_near(self):
        self.handler.add_line(0, (0, 0, 100, 100), '#FF0000', 3, 1.0)
        # 대각선 위의 점 (50, 50) 근처
        found = self.handler.find_annotation_at_point(0, 50, 52, 1.0, threshold=10)
        self.assertIsNotNone(found)

    def test_find_annotation_line_far(self):
        self.handler.add_line(0, (0, 0, 100, 100), '#FF0000', 3, 1.0)
        found = self.handler.find_annotation_at_point(0, 0, 100, 1.0, threshold=5)
        self.assertIsNone(found)

    def test_add_search_highlight(self):
        ann = self.handler.add_search_highlight(0, (10, 20, 30, 40))
        self.assertEqual(ann['alpha'], 100)
        self.assertEqual(ann['type'], 'highlight')

    def test_clear_search_highlights(self):
        # 일반 형광펜 (alpha=77)
        self.handler.add_highlight(0, (0, 0, 10, 10), '#FFFF00', 77, 1.0)
        # 검색 하이라이트 (alpha=100)
        self.handler.add_search_highlight(0, (20, 20, 30, 30))
        self.handler.add_search_highlight(0, (40, 40, 50, 50))

        self.assertEqual(len(self.handler.annotations[0]), 3)

        self.handler.clear_search_highlights()

        # 일반 형광펜만 남아야 함
        self.assertEqual(len(self.handler.annotations[0]), 1)
        self.assertEqual(self.handler.annotations[0][0]['alpha'], 77)

    def test_search_text_no_pdf(self):
        results = self.handler.search_text("test")
        self.assertEqual(results, [])

    def test_search_text_empty_query(self):
        results = self.handler.search_text("")
        self.assertEqual(results, [])

    def test_get_page_text_no_pdf(self):
        text = self.handler.get_page_text(0)
        self.assertEqual(text, "")

    def test_get_page_text_invalid_page(self):
        text = self.handler.get_page_text(-1)
        self.assertEqual(text, "")

    def test_cleanup_with_bytesio(self):
        """BytesIO가 명시적으로 닫히는지 확인"""
        mock_bytesio = MagicMock(spec=BytesIO)
        self.handler._pdf_data = mock_bytesio
        self.handler._cleanup()
        mock_bytesio.close.assert_called_once()
        self.assertIsNone(self.handler._pdf_data)

    def test_cleanup_without_bytesio(self):
        """BytesIO 없이 cleanup 호출 시 오류 없음"""
        self.handler._pdf_data = None
        self.handler._cleanup()  # should not raise

    def test_save_page_image_no_pdf(self):
        result = self.handler.save_page_image("/tmp/test.png")
        self.assertFalse(result)


class TestPDFHandlerURLValidation(unittest.TestCase):
    """PDF URL 검증 테스트"""

    def setUp(self):
        self.handler = PDFHandler()

    def test_load_pdf_invalid_protocol(self):
        with self.assertRaises(Exception) as ctx:
            self.handler.load_pdf("ftp://example.com/test.pdf")
        self.assertIn("프로토콜", str(ctx.exception))

    def test_load_pdf_invalid_domain(self):
        with self.assertRaises(Exception) as ctx:
            self.handler.load_pdf("https://evil.com/malware.pdf")
        self.assertIn("도메인", str(ctx.exception))

    def test_load_pdf_javascript_url(self):
        with self.assertRaises(Exception):
            self.handler.load_pdf("javascript:alert(1)")


if __name__ == '__main__':
    unittest.main()
