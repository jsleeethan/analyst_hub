"""
PDF 처리 모듈
- PDFHandler: PDF 다운로드, 렌더링, 어노테이션 합성
"""

import logging
import requests
from io import BytesIO
from urllib.parse import urlparse
from typing import List, Optional, Dict, Tuple, Any

from .config import (
    HTTP_HEADERS, PDF_RENDER_SCALE, PDF_DOWNLOAD_TIMEOUT,
    ALLOWED_PDF_DOMAINS
)

# 로거 설정
logger = logging.getLogger(__name__)

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
    logger.warning("PDF 지원 라이브러리가 설치되지 않았습니다. pip install pymupdf pillow")


def parse_hex_color(color: str) -> Tuple[int, int, int]:
    """
    16진수 색상 문자열을 RGB 튜플로 변환

    Args:
        color: '#RRGGBB' 형식의 색상 문자열

    Returns:
        (R, G, B) 튜플

    Raises:
        ValueError: 잘못된 색상 형식
    """
    if not color or len(color) != 7 or color[0] != '#':
        logger.warning(f"잘못된 색상 형식: {color}, 기본값 사용")
        return (255, 255, 0)  # 기본 노란색

    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return (r, g, b)
    except ValueError as e:
        logger.warning(f"색상 파싱 실패: {color}, 오류: {e}")
        return (255, 255, 0)  # 기본 노란색


class PDFHandler:
    """PDF 처리 클래스 (지연 로딩 지원)"""

    def __init__(self) -> None:
        self._pdf_doc: Optional[Any] = None  # fitz.Document
        self._pdf_data: Optional[BytesIO] = None
        self._page_cache: Dict[int, Any] = {}  # 페이지 이미지 캐시
        self._max_cache_size: int = 5  # 최대 캐시 페이지 수

        self.total_pages: int = 0
        self.current_page: int = 0
        self.zoom_level: float = 1.0
        self.annotations: Dict[int, List[dict]] = {}

        logger.debug("PDFHandler 초기화됨")

    @staticmethod
    def is_supported() -> bool:
        """PDF 지원 여부 확인"""
        return PDF_SUPPORT

    def load_pdf(self, pdf_url: str) -> bool:
        """
        PDF 다운로드 및 로드 (지연 로딩)

        Args:
            pdf_url: PDF URL

        Returns:
            성공 여부
        """
        if not PDF_SUPPORT:
            logger.error("PDF 지원 라이브러리가 설치되지 않음")
            return False

        # URL 유효성 검사
        try:
            parsed = urlparse(pdf_url)
            if parsed.scheme not in ('https', 'http'):
                raise ValueError(f"허용되지 않은 프로토콜: {parsed.scheme}")
            domain = parsed.hostname or ''
            if not any(domain == allowed or domain.endswith('.' + allowed)
                       for allowed in ALLOWED_PDF_DOMAINS):
                raise ValueError(f"허용되지 않은 PDF 도메인: {domain}")
        except ValueError as e:
            logger.error(f"PDF URL 검증 실패: {e}")
            raise Exception(f"PDF URL 검증 실패: {e}")

        try:
            logger.info(f"PDF 다운로드 시작: {pdf_url}")
            response = requests.get(
                pdf_url,
                headers=HTTP_HEADERS,
                timeout=PDF_DOWNLOAD_TIMEOUT
            )

            if response.status_code != 200:
                logger.error(f"PDF 다운로드 실패: HTTP {response.status_code}")
                raise Exception(f"PDF 다운로드 실패: {response.status_code}")

            # 기존 문서 정리
            self._cleanup()

            # PDF 데이터 저장 (지연 로딩을 위해)
            self._pdf_data = BytesIO(response.content)
            self._pdf_doc = fitz.open(stream=self._pdf_data, filetype="pdf")

            self.total_pages = len(self._pdf_doc)
            self.current_page = 0
            self.zoom_level = 1.0
            self.annotations = {}
            self._page_cache = {}

            logger.info(f"PDF 로드 완료: {self.total_pages}페이지")
            return True

        except requests.RequestException as e:
            logger.error(f"PDF 다운로드 네트워크 오류: {e}")
            raise Exception(f"PDF 다운로드 실패: {e}")
        except Exception as e:
            logger.error(f"PDF 로드 오류: {e}")
            raise

    def _get_page_image(self, page_num: int) -> Optional[Any]:
        """
        페이지 이미지 가져오기 (캐시 사용)

        Args:
            page_num: 페이지 번호

        Returns:
            PIL Image 또는 None
        """
        if not self._pdf_doc or page_num < 0 or page_num >= self.total_pages:
            return None

        # 캐시 확인
        if page_num in self._page_cache:
            logger.debug(f"페이지 {page_num} 캐시에서 로드")
            return self._page_cache[page_num]

        # 페이지 렌더링
        try:
            page = self._pdf_doc[page_num]
            mat = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 캐시에 추가 (최대 크기 관리)
            if len(self._page_cache) >= self._max_cache_size:
                # 현재 페이지와 가장 먼 페이지 제거
                pages_to_remove = sorted(
                    self._page_cache.keys(),
                    key=lambda p: abs(p - page_num),
                    reverse=True
                )
                if pages_to_remove:
                    removed = pages_to_remove[0]
                    del self._page_cache[removed]
                    logger.debug(f"캐시에서 페이지 {removed} 제거")

            self._page_cache[page_num] = img
            logger.debug(f"페이지 {page_num} 렌더링 및 캐시")
            return img

        except Exception as e:
            logger.error(f"페이지 {page_num} 렌더링 실패: {e}")
            return None

    @property
    def images(self) -> List:
        """하위 호환성을 위한 images 속성 (권장하지 않음)"""
        logger.warning("images 속성은 deprecated됨. _get_page_image() 사용 권장")
        return []

    def render_page(self, page_num: Optional[int] = None,
                    zoom: Optional[float] = None,
                    apply_annotations: bool = True) -> Optional[Any]:
        """
        페이지 렌더링

        Args:
            page_num: 페이지 번호 (None이면 현재 페이지)
            zoom: 줌 레벨 (None이면 현재 줌)
            apply_annotations: 어노테이션 적용 여부

        Returns:
            렌더링된 PIL Image
        """
        if not self._pdf_doc:
            logger.warning("PDF가 로드되지 않음")
            return None

        if page_num is None:
            page_num = self.current_page

        if zoom is None:
            zoom = self.zoom_level

        if page_num < 0 or page_num >= self.total_pages:
            logger.warning(f"잘못된 페이지 번호: {page_num}")
            return None

        img = self._get_page_image(page_num)
        if img is None:
            return None

        img = img.copy()

        # 줌 적용
        new_width = int(img.width * zoom)
        new_height = int(img.height * zoom)
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 어노테이션 합성
        if apply_annotations:
            resized = self.apply_annotations(resized, page_num, zoom)

        return resized

    def apply_annotations(self, img: Any, page_num: int, zoom: float) -> Any:
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
            try:
                # 줌 레벨 보정
                scale = zoom / ann.get('zoom', 1.0)

                if ann['type'] == 'highlight':
                    x1, y1, x2, y2 = ann['coords']
                    x1, y1, x2, y2 = int(x1 * scale), int(y1 * scale), int(x2 * scale), int(y2 * scale)

                    # 색상을 RGBA로 변환 (안전한 파싱)
                    r, g, b = parse_hex_color(ann.get('color', '#FFFF00'))
                    alpha = ann.get('alpha', 77)

                    draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, alpha))

                elif ann['type'] == 'line':
                    x1, y1, x2, y2 = ann['coords']
                    x1, y1, x2, y2 = int(x1 * scale), int(y1 * scale), int(x2 * scale), int(y2 * scale)

                    r, g, b = parse_hex_color(ann.get('color', '#FF0000'))
                    width = int(ann.get('width', 3) * scale)

                    draw.line([x1, y1, x2, y2], fill=(r, g, b, 255), width=max(1, width))

            except Exception as e:
                logger.error(f"어노테이션 렌더링 실패: {e}")
                continue

        # 합성
        result = Image.alpha_composite(img, overlay)
        return result.convert('RGB')

    def search_text(self, query: str, page_num: Optional[int] = None) -> List[Dict]:
        """
        PDF에서 텍스트 검색

        Args:
            query: 검색할 텍스트
            page_num: 특정 페이지만 검색 (None이면 전체 검색)

        Returns:
            검색 결과 리스트 [{'page': int, 'rects': [(x1,y1,x2,y2), ...], 'text': str}, ...]
        """
        if not self._pdf_doc or not query:
            return []

        results = []
        pages_to_search = [page_num] if page_num is not None else range(self.total_pages)

        for pn in pages_to_search:
            if pn < 0 or pn >= self.total_pages:
                continue

            try:
                page = self._pdf_doc[pn]
                text_instances = page.search_for(query)

                if text_instances:
                    # fitz.Rect를 튜플로 변환하고 PDF_RENDER_SCALE 적용
                    rects = [
                        (
                            int(rect.x0 * PDF_RENDER_SCALE),
                            int(rect.y0 * PDF_RENDER_SCALE),
                            int(rect.x1 * PDF_RENDER_SCALE),
                            int(rect.y1 * PDF_RENDER_SCALE)
                        )
                        for rect in text_instances
                    ]
                    results.append({
                        'page': pn,
                        'rects': rects,
                        'text': query,
                        'count': len(rects)
                    })
                    logger.debug(f"페이지 {pn}에서 '{query}' {len(rects)}개 발견")

            except Exception as e:
                logger.error(f"페이지 {pn} 텍스트 검색 실패: {e}")
                continue

        logger.info(f"'{query}' 검색 완료: {sum(r['count'] for r in results)}개 발견")
        return results

    def get_page_text(self, page_num: int) -> str:
        """
        페이지의 전체 텍스트 추출

        Args:
            page_num: 페이지 번호

        Returns:
            페이지 텍스트
        """
        if not self._pdf_doc or page_num < 0 or page_num >= self.total_pages:
            return ""

        try:
            page = self._pdf_doc[page_num]
            return page.get_text()
        except Exception as e:
            logger.error(f"페이지 {page_num} 텍스트 추출 실패: {e}")
            return ""

    def get_page_blocks(self, page_num: int) -> List[str]:
        """
        페이지의 텍스트 블록(단락) 단위로 추출.
        자동 하이라이트가 단락 내 모든 라인에 적용되도록 그룹핑하는 데 사용.

        Args:
            page_num: 페이지 번호

        Returns:
            블록(단락) 텍스트 리스트. 각 블록 내부에는 줄바꿈(\n)이 보존됨.
        """
        if not self._pdf_doc or page_num < 0 or page_num >= self.total_pages:
            return []

        try:
            page = self._pdf_doc[page_num]
            # blocks: [(x0, y0, x1, y1, text, block_no, block_type), ...]
            # block_type == 0 은 텍스트 블록, 1은 이미지
            blocks_raw = page.get_text("blocks")
            return [b[4] for b in blocks_raw if len(b) >= 7 and b[6] == 0 and b[4].strip()]
        except Exception as e:
            logger.error(f"페이지 {page_num} 블록 추출 실패: {e}")
            return []

    def add_auto_highlights(self, page_num: int, spans: List[Any],
                              zoom: float) -> List[dict]:
        """
        자동 하이라이트: HighlightSpan 리스트를 받아 search_for로 좌표 변환 후
        add_highlight 반복 호출.

        Args:
            page_num: 페이지 번호
            spans: HighlightSpan 리스트 (auto_highlighter.HighlightSpan)
            zoom: 현재 줌 레벨

        Returns:
            추가된 어노테이션 dict 리스트 (undo 등록용)
        """
        if not self._pdf_doc or page_num < 0 or page_num >= self.total_pages:
            return []

        added: List[dict] = []
        try:
            page = self._pdf_doc[page_num]
        except Exception as e:
            logger.error(f"페이지 {page_num} 접근 실패: {e}")
            return []

        for span in spans:
            try:
                rects = page.search_for(span.snippet)
            except Exception as e:
                logger.debug(f"search_for 실패 ('{span.snippet[:30]}...'): {e}")
                continue

            for rect in rects:
                coords = (
                    rect.x0 * PDF_RENDER_SCALE,
                    rect.y0 * PDF_RENDER_SCALE,
                    rect.x1 * PDF_RENDER_SCALE,
                    rect.y1 * PDF_RENDER_SCALE,
                )
                annotation = self.add_highlight(page_num, coords, span.color, span.alpha, zoom)
                added.append(annotation)

        logger.info(f"자동 하이라이트 페이지 {page_num}: {len(spans)}개 스팬 → {len(added)}개 어노테이션 추가")
        return added

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
        logger.debug(f"형광펜 추가: 페이지 {page_num}, 좌표 {coords}")
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
        logger.debug(f"라인 추가: 페이지 {page_num}, 좌표 {coords}")
        return annotation

    def add_search_highlight(self, page_num: int, rect: Tuple[int, int, int, int],
                             color: str = '#FFFF00', alpha: int = 100) -> dict:
        """검색 결과 하이라이트 추가"""
        return self.add_highlight(page_num, rect, color, alpha, 1.0)

    def clear_search_highlights(self, page_num: Optional[int] = None) -> None:
        """검색 하이라이트 제거"""
        pages = [page_num] if page_num is not None else list(self.annotations.keys())

        for pn in pages:
            if pn in self.annotations:
                # alpha가 100인 것은 검색 하이라이트로 간주
                self.annotations[pn] = [
                    ann for ann in self.annotations[pn]
                    if not (ann.get('type') == 'highlight' and ann.get('alpha') == 100)
                ]

    def remove_annotation(self, page_num: int, annotation: dict) -> bool:
        """어노테이션 제거"""
        if page_num in self.annotations and annotation in self.annotations[page_num]:
            self.annotations[page_num].remove(annotation)
            logger.debug(f"어노테이션 제거: 페이지 {page_num}")
            return True
        return False

    def clear_annotations(self, page_num: int) -> List[dict]:
        """페이지의 모든 어노테이션 삭제 (삭제된 어노테이션 반환)"""
        if page_num in self.annotations:
            cleared = self.annotations[page_num].copy()
            self.annotations[page_num] = []
            logger.debug(f"페이지 {page_num} 어노테이션 전체 삭제: {len(cleared)}개")
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
                logger.info(f"페이지 이미지 저장: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"이미지 저장 실패: {e}")
            return False

    def _cleanup(self) -> None:
        """리소스 정리"""
        if self._pdf_doc:
            try:
                self._pdf_doc.close()
            except Exception:
                pass
            self._pdf_doc = None

        if self._pdf_data:
            try:
                self._pdf_data.close()
            except Exception:
                pass
            self._pdf_data = None

        self._page_cache = {}
        logger.debug("PDF 리소스 정리됨")

    def reset(self) -> None:
        """상태 초기화"""
        self._cleanup()
        self.total_pages = 0
        self.current_page = 0
        self.zoom_level = 1.0
        self.annotations = {}
        logger.debug("PDFHandler 상태 초기화됨")

    def __del__(self):
        """소멸자 - 리소스 정리"""
        self._cleanup()
