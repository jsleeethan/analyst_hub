"""
models.py 단위 테스트
"""

import unittest
from src.models import ReportData, Annotation, UndoAction


class TestReportData(unittest.TestCase):
    """ReportData 테스트"""

    def setUp(self):
        self.report = ReportData(
            stock="삼성전자",
            title="실적 점검",
            firm="미래에셋증권",
            date="26.02.02",
            link="https://finance.naver.com/research/company_read.naver?nid=12345",
            pdf_link="https://ssl.pstatic.net/imgstock/upload/research/company/1234.pdf",
            views="100",
            opinion="매수",
            target="80,000",
        )

    def test_basic_attributes(self):
        self.assertEqual(self.report.stock, "삼성전자")
        self.assertEqual(self.report.firm, "미래에셋증권")
        self.assertEqual(self.report.opinion, "매수")

    def test_default_values(self):
        report = ReportData(
            stock="LG전자", title="리포트", firm="KB증권",
            date="26.01.01", link="https://example.com"
        )
        self.assertEqual(report.pdf_link, "")
        self.assertEqual(report.views, "0")
        self.assertEqual(report.opinion, "-")
        self.assertEqual(report.target, "-")

    def test_matches_search_stock(self):
        self.assertTrue(self.report.matches_search("삼성"))
        self.assertTrue(self.report.matches_search("삼성전자"))

    def test_matches_search_firm(self):
        self.assertTrue(self.report.matches_search("미래에셋"))

    def test_matches_search_title(self):
        self.assertTrue(self.report.matches_search("실적"))

    def test_matches_search_case_insensitive(self):
        report = ReportData(
            stock="Samsung", title="Report", firm="KB",
            date="26.01.01", link="https://example.com"
        )
        self.assertTrue(report.matches_search("samsung"))
        self.assertTrue(report.matches_search("SAMSUNG"))

    def test_matches_search_no_match(self):
        self.assertFalse(self.report.matches_search("카카오"))

    def test_to_dict(self):
        d = self.report.to_dict()
        self.assertEqual(d['stock'], "삼성전자")
        self.assertEqual(d['firm'], "미래에셋증권")
        self.assertEqual(d['opinion'], "매수")
        self.assertIn('pdf_link', d)

    def test_from_dict(self):
        d = self.report.to_dict()
        restored = ReportData.from_dict(d)
        self.assertEqual(restored.stock, self.report.stock)
        self.assertEqual(restored.title, self.report.title)
        self.assertEqual(restored.firm, self.report.firm)

    def test_from_dict_missing_keys(self):
        restored = ReportData.from_dict({'stock': 'Test'})
        self.assertEqual(restored.stock, 'Test')
        self.assertEqual(restored.title, '')
        self.assertEqual(restored.opinion, '-')

    def test_roundtrip(self):
        d = self.report.to_dict()
        restored = ReportData.from_dict(d)
        self.assertEqual(self.report.to_dict(), restored.to_dict())


class TestAnnotation(unittest.TestCase):
    """Annotation 테스트"""

    def test_default_values(self):
        ann = Annotation(type='highlight', coords=(0, 0, 100, 50))
        self.assertEqual(ann.color, '#FFFF00')
        self.assertEqual(ann.alpha, 77)
        self.assertEqual(ann.width, 3)
        self.assertEqual(ann.zoom, 1.0)

    def test_custom_values(self):
        ann = Annotation(
            type='line', coords=(10, 20, 30, 40),
            color='#FF0000', alpha=128, width=5, zoom=1.5
        )
        self.assertEqual(ann.type, 'line')
        self.assertEqual(ann.color, '#FF0000')
        self.assertEqual(ann.width, 5)

    def test_to_dict(self):
        ann = Annotation(type='highlight', coords=(1, 2, 3, 4))
        d = ann.to_dict()
        self.assertEqual(d['type'], 'highlight')
        self.assertEqual(d['coords'], (1, 2, 3, 4))

    def test_from_dict(self):
        d = {'type': 'line', 'coords': [10, 20, 30, 40], 'color': '#0000FF'}
        ann = Annotation.from_dict(d)
        self.assertEqual(ann.type, 'line')
        self.assertEqual(ann.color, '#0000FF')

    def test_from_dict_defaults(self):
        ann = Annotation.from_dict({})
        self.assertEqual(ann.type, 'highlight')
        self.assertEqual(ann.alpha, 77)

    def test_roundtrip(self):
        ann = Annotation(type='highlight', coords=(10, 20, 100, 50),
                         color='#00FF00', alpha=128)
        restored = Annotation.from_dict(ann.to_dict())
        self.assertEqual(ann.to_dict(), restored.to_dict())


class TestUndoAction(unittest.TestCase):
    """UndoAction 테스트"""

    def test_default(self):
        ann = Annotation(type='highlight', coords=(0, 0, 1, 1))
        action = UndoAction(page=0, annotation=ann)
        self.assertEqual(action.page, 0)
        self.assertFalse(action.is_erased)

    def test_erased(self):
        ann = Annotation(type='line', coords=(0, 0, 1, 1))
        action = UndoAction(page=2, annotation=ann, is_erased=True)
        self.assertTrue(action.is_erased)
        self.assertEqual(action.page, 2)


if __name__ == '__main__':
    unittest.main()
