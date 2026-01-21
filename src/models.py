"""
데이터 모델 모듈
- ReportData: 리포트 정보 저장
- Annotation: 어노테이션 정보 저장
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class ReportData:
    """리포트 정보 데이터 클래스"""
    stock: str
    title: str
    firm: str
    date: str
    link: str
    pdf_link: str = ""
    views: str = "0"
    opinion: str = "-"
    target: str = "-"

    def matches_search(self, term: str) -> bool:
        """검색어와 매칭되는지 확인"""
        term_lower = term.lower()
        return (term_lower in self.stock.lower() or
                term_lower in self.title.lower() or
                term_lower in self.firm.lower())

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'stock': self.stock,
            'title': self.title,
            'firm': self.firm,
            'date': self.date,
            'link': self.link,
            'pdf_link': self.pdf_link,
            'views': self.views,
            'opinion': self.opinion,
            'target': self.target,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ReportData':
        """딕셔너리에서 생성"""
        return cls(
            stock=data.get('stock', ''),
            title=data.get('title', ''),
            firm=data.get('firm', ''),
            date=data.get('date', ''),
            link=data.get('link', ''),
            pdf_link=data.get('pdf_link', ''),
            views=data.get('views', '0'),
            opinion=data.get('opinion', '-'),
            target=data.get('target', '-'),
        )


@dataclass
class Annotation:
    """어노테이션 정보 데이터 클래스"""
    type: str  # 'highlight', 'line', 'erased'
    coords: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    color: str = '#FFFF00'
    alpha: int = 77  # 투명도 (0-255)
    width: int = 3  # 라인 굵기
    zoom: float = 1.0  # 생성 시 줌 레벨

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'type': self.type,
            'coords': self.coords,
            'color': self.color,
            'alpha': self.alpha,
            'width': self.width,
            'zoom': self.zoom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        """딕셔너리에서 생성"""
        return cls(
            type=data.get('type', 'highlight'),
            coords=tuple(data.get('coords', (0, 0, 0, 0))),
            color=data.get('color', '#FFFF00'),
            alpha=data.get('alpha', 77),
            width=data.get('width', 3),
            zoom=data.get('zoom', 1.0),
        )


@dataclass
class UndoAction:
    """되돌리기 작업 정보"""
    page: int
    annotation: Annotation
    is_erased: bool = False  # True면 삭제된 어노테이션 복원, False면 추가된 어노테이션 제거
