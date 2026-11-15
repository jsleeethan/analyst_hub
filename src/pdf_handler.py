"""
PDF 처리 모듈
- PDFHandler: PDF 다운로드, 렌더링, 어노테이션 합성
"""

import requests
from io import BytesIO
from typing import List, Optional, Dict, Tuple
import os

from .config import (
    HTTP_HEADERS, PDF_RENDER_SCALE, PDF_DOWNLOAD_TIMEOUT
)

# PDF 라이브러리 가용성 확인
try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageDraw, ImageTk
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    Image = None
    ImageDraw = None
    ImageTk = None
    fitz = None


class PDFHandler:
    """PDF 처리 클래스"""

    def __init__(self):
        self._doc = None  # fitz.Document (lazy rendering용)
        self._pdf_data = None  # BytesIO (doc이 참조하므로 유지)
        self.total_pages: int = 0
        self.current_page: int = 0
        self.zoom_level: float = 1.0
        self.annotations: Dict[int, List[dict]] = {}  # {page_num: [annotation_dict, ...]}

    @property
    def is_loaded(self) -> bool:
        """PDF가 로드되어 있는지 여부"""
        return self._doc is not None and self.total_pages > 0

    @staticmethod
    def is_supported() -> bool:
        """PDF 지원 여부 확인"""
        return PDF_SUPPORT

    def load_pdf(self, pdf_url: str) -> bool:
        """
        PDF 다운로드 및 로드 (lazy rendering - 페이지를 미리 렌더링하지 않음)

        Args:
            pdf_url: PDF URL

        Returns:
            성공 여부
        """
        if not PDF_SUPPORT:
            return False

        try:
            # 기존 문서 정리
            self._close_doc()

            response = requests.get(
                pdf_url,
                headers=HTTP_HEADERS,
                timeout=PDF_DOWNLOAD_TIMEOUT
            )

            if response.status_code != 200:
                raise Exception(f"PDF 다운로드 실패: {response.status_code}")

            self._pdf_data = BytesIO(response.content)
            self._doc = fitz.open(stream=self._pdf_data, filetype="pdf")

            self.total_pages = len(self._doc)
            self.current_page = 0
            self.zoom_level = 1.0
            self.annotations = {}

            return True

        except Exception as e:
            self._close_doc()
            raise e

    def _close_doc(self):
        """내부: fitz 문서 닫기"""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None
            self._pdf_data = None

    def _render_page_image(self, page_num: int) -> Optional['Image.Image']:
        """내부: 문서에서 단일 페이지를 PIL Image로 렌더링"""
        if self._doc is None or page_num < 0 or page_num >= self.total_pages:
            return None
        page = self._doc[page_num]
        mat = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def render_page(self, page_num: Optional[int] = None,
                    zoom: Optional[float] = None,
                    apply_annotations: bool = True) -> Optional['Image.Image']:
        """
        페이지 렌더링 (on-demand: 요청 시점에 해당 페이지만 렌더링)

        Args:
            page_num: 페이지 번호 (None이면 현재 페이지)
            zoom: 줌 레벨 (None이면 현재 줌)
            apply_annotations: 어노테이션 적용 여부

        Returns:
            렌더링된 PIL Image
        """
        if not self.is_loaded:
            return None

        if page_num is None:
            page_num = self.current_page

        if zoom is None:
            zoom = self.zoom_level

        img = self._render_page_image(page_num)
        if img is None:
            return None

        # 줌 적용
        new_width = int(img.width * zoom)
        new_height = int(img.height * zoom)
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 어노테이션 합성
        if apply_annotations:
            resized = self.apply_annotations(resized, page_num, zoom)

        return resized

    def apply_annotations(self, img: 'Image.Image', page_num: int,
                          zoom: float) -> 'Image.Image':
        """
        어노테이션을 이미지에 합성

        Args:
            img: PIL Image
            page_num: 페이지 번호
            zoom: 현재 줌 레벨

        Returns:
            어노테이션이 합성된 이미지
        """
        if page_num not in self.annotations or not self.annotations[page_num]:
            return img

        # RGBA 모드로 변환
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 어노테이션 레이어 생성
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for ann in self.annotations[page_num]:
            # 줌 레벨 보정
            scale = zoom / ann.get('zoom', 1.0)

            if ann['type'] == 'highlight':
                x1, y1, x2, y2 = ann['coords']
                x1, y1, x2, y2 = int(x1 * scale), int(y1 * scale), int(x2 * scale), int(y2 * scale)

                # 색상을 RGBA로 변환
                color = ann['color']
                alpha = ann.get('alpha', 77)
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)

                draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, alpha))

            elif ann['type'] == 'line':
                x1, y1, x2, y2 = ann['coords']
                x1, y1, x2, y2 = int(x1 * scale), int(y1 * scale), int(x2 * scale), int(y2 * scale)

                color = ann['color']
                width = int(ann.get('width', 3) * scale)
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)

                draw.line([x1, y1, x2, y2], fill=(r, g, b, 255), width=max(1, width))

        # 합성
        result = Image.alpha_composite(img, overlay)
        return result.convert('RGB')

    def add_highlight(self, page_num: int, coords: Tuple[float, float, float, float],
                      color: str, alpha: int, zoom: float) -> dict:
        """형광펜 어노테이션 추가"""
        if page_num not in self.annotations:
            self.annotations[page_num] = []

        annotation = {
            'type': 'highlight',
            'coords': coords,
            'color': color,
            'alpha': alpha,
            'zoom': zoom
        }

        self.annotations[page_num].append(annotation)
        return annotation

    def add_line(self, page_num: int, coords: Tuple[float, float, float, float],
                 color: str, width: int, zoom: float) -> dict:
        """라인 어노테이션 추가"""
        if page_num not in self.annotations:
            self.annotations[page_num] = []

        annotation = {
            'type': 'line',
            'coords': coords,
            'color': color,
            'width': width,
            'zoom': zoom
        }

        self.annotations[page_num].append(annotation)
        return annotation

    def remove_annotation(self, page_num: int, annotation: dict) -> bool:
        """어노테이션 제거"""
        if page_num in self.annotations and annotation in self.annotations[page_num]:
            self.annotations[page_num].remove(annotation)
            return True
        return False

    def clear_annotations(self, page_num: int) -> List[dict]:
        """페이지의 모든 어노테이션 삭제 (삭제된 어노테이션 반환)"""
        if page_num in self.annotations:
            cleared = self.annotations[page_num].copy()
            self.annotations[page_num] = []
            return cleared
        return []

    def find_annotation_at_point(self, page_num: int, x: float, y: float,
                                 zoom: float, threshold: int = 10) -> Optional[dict]:
        """지정된 좌표의 어노테이션 찾기"""
        if page_num not in self.annotations:
            return None

        for ann in self.annotations[page_num]:
            scale = zoom / ann.get('zoom', 1.0)

            if ann['type'] == 'highlight':
                ax1, ay1, ax2, ay2 = ann['coords']
                ax1, ay1, ax2, ay2 = ax1 * scale, ay1 * scale, ax2 * scale, ay2 * scale

                if ax1 <= x <= ax2 and ay1 <= y <= ay2:
                    return ann

            elif ann['type'] == 'line':
                x1, y1, x2, y2 = ann['coords']
                x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale

                # 점과 선 사이 거리 계산
                line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
                if line_len_sq == 0:
                    dist = ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
                else:
                    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_len_sq))
                    proj_x = x1 + t * (x2 - x1)
                    proj_y = y1 + t * (y2 - y1)
                    dist = ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5

                if dist <= threshold:
                    return ann

        return None

    def save_page_image(self, filepath: str, page_num: Optional[int] = None,
                        zoom: Optional[float] = None) -> bool:
        """현재 페이지를 이미지로 저장"""
        try:
            img = self.render_page(page_num, zoom, apply_annotations=True)
            if img:
                img.save(filepath, 'PNG')
                return True
            return False
        except Exception:
            return False

    def reset(self):
        """상태 초기화"""
        self._close_doc()
        self.total_pages = 0
        self.current_page = 0
        self.zoom_level = 1.0
        self.annotations = {}
