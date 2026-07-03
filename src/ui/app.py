"""
메인 앱 클래스 모듈
- NaverReportViewerApp: 메인 앱 클래스
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import threading
import webbrowser
import os
from typing import Optional, List

from ..config import (
    COLORS, WINDOW_TITLE, WINDOW_GEOMETRY, WINDOW_MIN_SIZE,
    ZOOM_STEP, ZOOM_MIN, ZOOM_MAX
)
from ..models import ReportData
from ..scraper import NaverReportScraper
from ..pdf_handler import PDFHandler
from ..auto_highlighter import AutoHighlighter
from .styles import setup_styles
from .widgets import ReportListWidget, PDFViewerWidget, AnnotationToolbar

# 로거 설정
logger = logging.getLogger(__name__)


class NaverReportViewerApp:
    """네이버 종목 리포트 뷰어 메인 앱"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(*WINDOW_MIN_SIZE)

        # 스타일 설정
        self.colors = COLORS
        setup_styles(self.colors)

        # 스레드 동기화
        self._data_lock = threading.Lock()
        self._load_generation: int = 0  # 리포트/PDF 로드 세대 카운터
        self._is_loading_reports: bool = False  # 리포트 로딩 중복 방지

        # 데이터
        self.scraper = NaverReportScraper()
        self.pdf_handler = PDFHandler()
        self._auto_highlighter = AutoHighlighter()
        self._llm_client = None  # LLM 통합 단계에서 초기화
        self._reports: List[ReportData] = []
        self._current_report: Optional[ReportData] = None

        # 어노테이션 관련
        self.undo_stack: List[tuple] = []
        self.is_drawing: bool = False
        self.draw_start: Optional[tuple] = None
        self.temp_rect: Optional[int] = None
        self.temp_line: Optional[int] = None

        # 검색 관련
        self._search_results: List[dict] = []
        self._current_search_index: int = 0

        # UI 생성
        self._create_ui()

        # 키보드 단축키 바인딩
        self._bind_keyboard_shortcuts()

        # 시작 시 자동으로 리포트 로드
        self.root.after(500, self.load_reports)

        logger.info("NaverReportViewerApp 초기화 완료")

    @property
    def reports(self) -> List[ReportData]:
        """스레드 안전한 reports 접근"""
        with self._data_lock:
            return self._reports.copy()

    @reports.setter
    def reports(self, value: List[ReportData]) -> None:
        """스레드 안전한 reports 설정"""
        with self._data_lock:
            self._reports = value

    @property
    def current_report(self) -> Optional[ReportData]:
        """스레드 안전한 current_report 접근"""
        with self._data_lock:
            return self._current_report

    @current_report.setter
    def current_report(self, value: Optional[ReportData]) -> None:
        """스레드 안전한 current_report 설정"""
        with self._data_lock:
            self._current_report = value

    def _bind_keyboard_shortcuts(self) -> None:
        """키보드 단축키 바인딩"""
        # 페이지 이동
        self.root.bind('<Left>', lambda e: self._prev_page())
        self.root.bind('<Right>', lambda e: self._next_page())
        self.root.bind('<space>', lambda e: self._next_page())
        self.root.bind('<Shift-space>', lambda e: self._prev_page())
        self.root.bind('<Prior>', lambda e: self._prev_page())  # Page Up
        self.root.bind('<Next>', lambda e: self._next_page())   # Page Down
        self.root.bind('<Home>', lambda e: self._go_to_first_page())
        self.root.bind('<End>', lambda e: self._go_to_last_page())

        # 줌
        self.root.bind('<Control-plus>', lambda e: self._zoom_in())
        self.root.bind('<Control-equal>', lambda e: self._zoom_in())  # Ctrl+=
        self.root.bind('<Control-minus>', lambda e: self._zoom_out())
        self.root.bind('<Control-0>', lambda e: self._reset_zoom())

        # 되돌리기
        self.root.bind('<Control-z>', lambda e: self._undo_annotation())

        # 검색
        self.root.bind('<Control-f>', lambda e: self._show_search_dialog())
        self.root.bind('<F3>', lambda e: self._find_next())
        self.root.bind('<Shift-F3>', lambda e: self._find_prev())
        self.root.bind('<Escape>', lambda e: self._clear_search())

        # 새로고침
        self.root.bind('<F5>', lambda e: self.load_reports())
        self.root.bind('<Control-r>', lambda e: self.load_reports())

        # 캡쳐
        self.root.bind('<Control-s>', lambda e: self._capture_pdf_view())

        logger.debug("키보드 단축키 바인딩 완료")

    def _create_ui(self) -> None:
        """UI 생성"""
        # 메인 컨테이너
        main_container = ttk.Frame(self.root, style='Main.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        # 헤더
        self._create_header(main_container)

        # 컨텐츠 영역 (좌우 분할)
        content_frame = ttk.Frame(main_container, style='Main.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        # 좌측: 리포트 목록
        self._create_report_list(content_frame)

        # 우측: PDF 뷰어
        self._create_pdf_viewer(content_frame)

    def _create_header(self, parent) -> None:
        """헤더 생성"""
        header_frame = ttk.Frame(parent, style='Main.TFrame')
        header_frame.pack(fill=tk.X)

        # 타이틀 영역
        title_frame = ttk.Frame(header_frame, style='Main.TFrame')
        title_frame.pack(side=tk.LEFT)

        title_row = ttk.Frame(title_frame, style='Main.TFrame')
        title_row.pack(anchor=tk.W)

        icon_label = tk.Label(title_row, text="📈", font=('Segoe UI', 28),
                              bg=self.colors['bg_dark'], fg=self.colors['accent'])
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        title_text_frame = ttk.Frame(title_row, style='Main.TFrame')
        title_text_frame.pack(side=tk.LEFT)

        title_label = ttk.Label(title_text_frame,
                                text="종목 리포트 뷰어",
                                style='Title.TLabel')
        title_label.pack(anchor=tk.W)

        today = datetime.now().strftime("%Y년 %m월 %d일")
        subtitle_label = ttk.Label(title_text_frame,
                                   text=f"네이버 증권  •  {today}",
                                   style='Subtitle.TLabel')
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        # 우측 영역
        right_frame = ttk.Frame(header_frame, style='Main.TFrame')
        right_frame.pack(side=tk.RIGHT)

        self.status_label = ttk.Label(right_frame,
                                      text="",
                                      style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=(0, 16))

        self.refresh_btn = ttk.Button(right_frame,
                                      text="↻  새로고침",
                                      style='Accent.TButton',
                                      command=self.load_reports)
        self.refresh_btn.pack(side=tk.RIGHT)

    def _create_report_list(self, parent) -> None:
        """리포트 목록 생성"""
        outer_frame = tk.Frame(parent, bg=self.colors['border'])
        outer_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 12))

        self.report_list = ReportListWidget(
            outer_frame,
            colors=self.colors,
            on_select=self._on_report_select,
            on_double_click=self._on_report_double_click
        )
        self.report_list.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.report_list.configure(width=520)

    def _create_pdf_viewer(self, parent) -> None:
        """PDF 뷰어 생성"""
        outer_frame = tk.Frame(parent, bg=self.colors['border'])
        outer_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))

        self.pdf_viewer = PDFViewerWidget(outer_frame, colors=self.colors)
        self.pdf_viewer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 콜백 연결
        self.pdf_viewer.on_prev_page = self._prev_page
        self.pdf_viewer.on_next_page = self._next_page
        self.pdf_viewer.on_zoom_in = self._zoom_in
        self.pdf_viewer.on_zoom_out = self._zoom_out
        self.pdf_viewer.on_open_link = self._open_current_link
        self.pdf_viewer.on_download = self._open_pdf
        self.pdf_viewer.on_mouse_press = self._on_mouse_press
        self.pdf_viewer.on_mouse_drag = self._on_mouse_drag
        self.pdf_viewer.on_mouse_release = self._on_mouse_release

        # 어노테이션 툴바
        self.annotation_toolbar = AnnotationToolbar(
            self.pdf_viewer.toolbar_frame,
            colors=self.colors
        )
        self.annotation_toolbar.pack(fill=tk.X)

        # 툴바 콜백
        self.annotation_toolbar.on_tool_change = self._on_tool_change
        self.annotation_toolbar.on_undo = self._undo_annotation
        self.annotation_toolbar.on_clear = self._clear_annotations
        self.annotation_toolbar.on_capture = self._capture_pdf_view
        self.annotation_toolbar.on_auto_highlight_rules = self._on_auto_highlight_rules
        self.annotation_toolbar.on_auto_highlight_llm = self._on_auto_highlight_llm

    def load_reports(self) -> None:
        """리포트 로드"""
        # 중복 로딩 방지
        if self._is_loading_reports:
            logger.debug("리포트 로딩 중, 요청 무시")
            return

        self._is_loading_reports = True
        self.status_label.configure(text="불러오는 중...", foreground=self.colors['warning'])
        self.refresh_btn.configure(state='disabled')

        thread = threading.Thread(target=self._fetch_reports, daemon=True)
        thread.start()

    def _fetch_reports(self) -> None:
        """리포트 가져오기 (스레드)"""
        try:
            reports = self.scraper.fetch_reports()
            self.reports = reports
            self.root.after(0, self._update_report_list)
        except Exception as e:
            logger.error(f"리포트 로드 실패: {e}")
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self._is_loading_reports = False

    def _update_report_list(self) -> None:
        """리포트 목록 업데이트"""
        report_data_list = self.reports
        self.report_list.set_reports(report_data_list)

        total = len(report_data_list)
        self.status_label.configure(text=f"✓ {total}개 로드됨",
                                    foreground=self.colors['success'])
        self.refresh_btn.configure(state='normal')

        if total == 0:
            messagebox.showinfo("알림", "오늘 날짜의 리포트가 없습니다.")

        logger.info(f"리포트 목록 업데이트: {total}개")

    def _show_error(self, error_msg: str) -> None:
        """에러 표시"""
        self.status_label.configure(text="✗ 로딩 실패",
                                    foreground=self.colors['danger'])
        self.refresh_btn.configure(state='normal')
        messagebox.showerror("오류", f"리포트를 불러오는데 실패했습니다.\n\n{error_msg}")

    def _on_report_select(self, idx: int) -> None:
        """리포트 선택"""
        # 인덱스 범위 검사
        reports = self.reports
        if idx < 0 or idx >= len(reports):
            logger.warning(f"잘못된 리포트 인덱스: {idx}, 전체: {len(reports)}")
            return

        # 로드 세대 증가 — 이전 백그라운드 스레드의 콜백 무효화
        with self._data_lock:
            self._load_generation += 1

        self.current_report = reports[idx]
        logger.info(f"리포트 선택: {self.current_report.stock} - {self.current_report.title}")

        # PDF 핸들러 초기화
        self.pdf_handler.reset()
        self.undo_stack = []
        self._search_results = []
        self._current_search_index = 0
        self.annotation_toolbar.set_undo_enabled(False)
        self.annotation_toolbar.reset_tool()

        # UI 업데이트
        self.pdf_viewer.update_report_info(self.current_report)

        if self.current_report.pdf_link:
            self._load_pdf()
        else:
            self.pdf_viewer.show_no_pdf()

        # 상세 정보 로드
        self._load_report_meta()

    def _on_report_double_click(self, idx: int) -> None:
        """리포트 더블클릭"""
        self._open_current_link()

    def _load_report_meta(self) -> None:
        """리포트 메타 정보 로드"""
        thread = threading.Thread(target=self._fetch_report_meta, daemon=True)
        thread.start()

    def _fetch_report_meta(self) -> None:
        """리포트 메타 정보 가져오기"""
        with self._data_lock:
            gen = self._load_generation
        current = self.current_report
        if current:
            self.scraper.fetch_report_meta(current)
            # 세대가 바뀌었으면 결과를 무시 (다른 리포트가 선택됨)
            with self._data_lock:
                if gen != self._load_generation:
                    logger.debug("메타 정보 로드 완료했으나 세대 불일치, 무시")
                    return
            self.root.after(0, self._update_meta_labels)

    def _update_meta_labels(self) -> None:
        """메타 정보 업데이트"""
        current = self.current_report
        if current:
            self.pdf_viewer.meta_labels['opinion'].configure(text=current.opinion)
            self.pdf_viewer.meta_labels['target'].configure(text=current.target)

    def _load_pdf(self) -> None:
        """PDF 로드"""
        if not PDFHandler.is_supported():
            self.pdf_viewer.show_no_support()
            return

        self.pdf_viewer.show_loading()

        thread = threading.Thread(target=self._fetch_and_render_pdf, daemon=True)
        thread.start()

    def _fetch_and_render_pdf(self) -> None:
        """PDF 다운로드 및 렌더링"""
        with self._data_lock:
            gen = self._load_generation
        current = self.current_report
        if not current:
            return

        try:
            self.pdf_handler.load_pdf(current.pdf_link)
            # 세대가 바뀌었으면 결과를 무시 (다른 리포트가 선택됨)
            with self._data_lock:
                if gen != self._load_generation:
                    logger.debug("PDF 로드 완료했으나 세대 불일치, 무시")
                    return
            self.root.after(0, self._display_pdf_page)
        except Exception as e:
            logger.error(f"PDF 로드 실패: {e}")
            with self._data_lock:
                if gen != self._load_generation:
                    return
            self.root.after(0, lambda: self.pdf_viewer.show_error(str(e)))

    def _display_pdf_page(self) -> None:
        """현재 페이지 표시"""
        img = self.pdf_handler.render_page()
        if img:
            self.pdf_viewer.display_image(
                img,
                self.pdf_handler.current_page,
                self.pdf_handler.total_pages,
                self.pdf_handler.zoom_level
            )

    def _prev_page(self) -> None:
        """이전 페이지"""
        if self.pdf_handler.current_page > 0:
            self.pdf_handler.current_page -= 1
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _next_page(self) -> None:
        """다음 페이지"""
        if self.pdf_handler.current_page < self.pdf_handler.total_pages - 1:
            self.pdf_handler.current_page += 1
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _go_to_first_page(self) -> None:
        """첫 페이지로 이동"""
        if self.pdf_handler.total_pages > 0:
            self.pdf_handler.current_page = 0
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _go_to_last_page(self) -> None:
        """마지막 페이지로 이동"""
        if self.pdf_handler.total_pages > 0:
            self.pdf_handler.current_page = self.pdf_handler.total_pages - 1
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _zoom_in(self) -> None:
        """확대"""
        if self.pdf_handler.zoom_level < ZOOM_MAX:
            self.pdf_handler.zoom_level += ZOOM_STEP
            self._display_pdf_page()

    def _zoom_out(self) -> None:
        """축소"""
        if self.pdf_handler.zoom_level > ZOOM_MIN:
            self.pdf_handler.zoom_level -= ZOOM_STEP
            self._display_pdf_page()

    def _reset_zoom(self) -> None:
        """줌 초기화"""
        self.pdf_handler.zoom_level = 1.0
        self._display_pdf_page()

    def _open_current_link(self) -> None:
        """원본 페이지 열기"""
        current = self.current_report
        if current and current.link:
            webbrowser.open(current.link)

    def _open_pdf(self) -> None:
        """PDF 다운로드"""
        current = self.current_report
        if current and current.pdf_link:
            webbrowser.open(current.pdf_link)

    # === 검색 기능 ===

    def _show_search_dialog(self) -> None:
        """검색 다이얼로그 표시"""
        if self.pdf_handler.total_pages == 0:
            messagebox.showinfo("알림", "검색할 PDF가 없습니다.")
            return

        query = simpledialog.askstring(
            "PDF 텍스트 검색",
            "검색어를 입력하세요:",
            parent=self.root
        )

        if query:
            self._perform_search(query)

    def _perform_search(self, query: str) -> None:
        """검색 수행"""
        # 이전 검색 하이라이트 제거
        self.pdf_handler.clear_search_highlights()

        # 검색 실행
        results = self.pdf_handler.search_text(query)
        self._search_results = results
        self._current_search_index = 0

        if not results:
            messagebox.showinfo("검색 결과", f"'{query}'를 찾을 수 없습니다.")
            self._display_pdf_page()
            return

        # 총 검색 결과 수
        total_count = sum(r['count'] for r in results)
        logger.info(f"검색 완료: '{query}' - {total_count}개 발견")

        # 첫 번째 결과로 이동
        self._go_to_search_result(0)

        # 상태 표시
        self.status_label.configure(
            text=f"🔍 '{query}' {total_count}개 발견",
            foreground=self.colors['accent']
        )

    def _go_to_search_result(self, index: int) -> None:
        """검색 결과로 이동"""
        if not self._search_results:
            return

        if index < 0:
            index = len(self._search_results) - 1
        elif index >= len(self._search_results):
            index = 0

        self._current_search_index = index
        result = self._search_results[index]

        # 해당 페이지로 이동
        self.pdf_handler.current_page = result['page']

        # 검색 하이라이트 추가
        self.pdf_handler.clear_search_highlights()
        for rect in result['rects']:
            self.pdf_handler.add_search_highlight(result['page'], rect)

        self._display_pdf_page()
        self.pdf_viewer.scroll_to_top()

    def _find_next(self) -> None:
        """다음 검색 결과"""
        if self._search_results:
            self._go_to_search_result(self._current_search_index + 1)

    def _find_prev(self) -> None:
        """이전 검색 결과"""
        if self._search_results:
            self._go_to_search_result(self._current_search_index - 1)

    def _clear_search(self) -> None:
        """검색 결과 지우기"""
        if self._search_results:
            self._search_results = []
            self._current_search_index = 0
            self.pdf_handler.clear_search_highlights()
            self._display_pdf_page()
            self.status_label.configure(text="", foreground=self.colors['success'])

    # === 어노테이션 기능 ===

    def _on_tool_change(self, tool: Optional[str]) -> None:
        """도구 변경"""
        if tool is None:
            self.pdf_viewer.set_cursor('arrow')
        elif tool == 'eraser':
            self.pdf_viewer.set_cursor('X_cursor')
        else:
            self.pdf_viewer.set_cursor('crosshair')

    def _on_mouse_press(self, x: float, y: float) -> None:
        """마우스 버튼 누름"""
        if self.pdf_handler.total_pages == 0:
            return

        tool = self.annotation_toolbar.current_tool

        if tool in ('highlighter', 'line'):
            self.is_drawing = True
            self.draw_start = (x, y)
        elif tool == 'eraser':
            self._erase_at_point(x, y)

    def _on_mouse_drag(self, x: float, y: float) -> None:
        """마우스 드래그"""
        if not self.is_drawing or not self.draw_start:
            return

        x1, y1 = self.draw_start
        tool = self.annotation_toolbar.current_tool
        canvas = self.pdf_viewer.canvas

        if tool == 'highlighter':
            if self.temp_rect:
                canvas.delete(self.temp_rect)
            self.temp_rect = canvas.create_rectangle(
                x1, y1, x, y,
                fill=self.annotation_toolbar.current_highlight_color,
                stipple='gray50',
                outline=self.annotation_toolbar.current_highlight_color,
                width=1
            )
        elif tool == 'line':
            if self.temp_line:
                canvas.delete(self.temp_line)
            self.temp_line = canvas.create_line(
                x1, y1, x, y,
                fill=self.annotation_toolbar.current_line_color,
                width=self.annotation_toolbar.current_line_width,
                capstyle=tk.ROUND
            )

    def _on_mouse_release(self, x: float, y: float) -> None:
        """마우스 버튼 놓음"""
        if not self.is_drawing or not self.draw_start:
            return

        x1, y1 = self.draw_start
        tool = self.annotation_toolbar.current_tool
        canvas = self.pdf_viewer.canvas

        # 이미지 오프셋 적용
        offset_x = self.pdf_viewer.image_offset_x
        offset_y = self.pdf_viewer.image_offset_y

        img_x1 = x1 - offset_x
        img_y1 = y1 - offset_y
        img_x = x - offset_x
        img_y = y - offset_y

        if tool == 'highlighter':
            if self.temp_rect:
                canvas.delete(self.temp_rect)
                self.temp_rect = None

            if abs(img_x - img_x1) > 5 and abs(img_y - img_y1) > 5:
                coords = (min(img_x1, img_x), min(img_y1, img_y),
                          max(img_x1, img_x), max(img_y1, img_y))
                self._add_highlight_annotation(coords)

        elif tool == 'line':
            if self.temp_line:
                canvas.delete(self.temp_line)
                self.temp_line = None

            if abs(img_x - img_x1) > 3 or abs(img_y - img_y1) > 3:
                coords = (img_x1, img_y1, img_x, img_y)
                self._add_line_annotation(coords)

        self.is_drawing = False
        self.draw_start = None

    def _add_highlight_annotation(self, coords: tuple) -> None:
        """형광펜 어노테이션 추가"""
        page = self.pdf_handler.current_page
        annotation = self.pdf_handler.add_highlight(
            page, coords,
            self.annotation_toolbar.current_highlight_color,
            self.annotation_toolbar.current_alpha,
            self.pdf_handler.zoom_level
        )
        self.undo_stack.append((page, annotation, False))
        self.annotation_toolbar.set_undo_enabled(True)
        self._display_pdf_page()

    def _add_line_annotation(self, coords: tuple) -> None:
        """라인 어노테이션 추가"""
        page = self.pdf_handler.current_page
        annotation = self.pdf_handler.add_line(
            page, coords,
            self.annotation_toolbar.current_line_color,
            self.annotation_toolbar.current_line_width,
            self.pdf_handler.zoom_level
        )
        self.undo_stack.append((page, annotation, False))
        self.annotation_toolbar.set_undo_enabled(True)
        self._display_pdf_page()

    def _erase_at_point(self, canvas_x: float, canvas_y: float) -> None:
        """지정된 좌표의 어노테이션 삭제"""
        page = self.pdf_handler.current_page

        offset_x = self.pdf_viewer.image_offset_x
        offset_y = self.pdf_viewer.image_offset_y
        x = canvas_x - offset_x
        y = canvas_y - offset_y

        annotation = self.pdf_handler.find_annotation_at_point(
            page, x, y, self.pdf_handler.zoom_level
        )

        if annotation:
            self.pdf_handler.remove_annotation(page, annotation)
            self.undo_stack.append((page, annotation, True))
            self.annotation_toolbar.set_undo_enabled(True)
            self._display_pdf_page()

    def _undo_annotation(self) -> None:
        """마지막 어노테이션 작업 되돌리기"""
        if not self.undo_stack:
            return

        page, annotation, was_erased = self.undo_stack.pop()

        if was_erased:
            # 삭제된 어노테이션 복원
            if page not in self.pdf_handler.annotations:
                self.pdf_handler.annotations[page] = []
            self.pdf_handler.annotations[page].append(annotation)
        else:
            # 추가된 어노테이션 제거
            self.pdf_handler.remove_annotation(page, annotation)

        if not self.undo_stack:
            self.annotation_toolbar.set_undo_enabled(False)

        if page == self.pdf_handler.current_page:
            self._display_pdf_page()

    def _clear_annotations(self) -> None:
        """현재 페이지의 모든 어노테이션 삭제"""
        page = self.pdf_handler.current_page
        cleared = self.pdf_handler.clear_annotations(page)

        for ann in cleared:
            self.undo_stack.append((page, ann, True))

        if cleared:
            self.annotation_toolbar.set_undo_enabled(True)
            self._display_pdf_page()

    def _on_auto_highlight_rules(self) -> None:
        """현재 페이지에 룰 기반 자동 하이라이트 적용"""
        if self.pdf_handler.total_pages == 0:
            messagebox.showinfo("알림", "먼저 PDF 리포트를 선택하세요.")
            return

        page = self.pdf_handler.current_page
        # 블록(단락) 단위 추출 — 단락 내 모든 라인이 함께 하이라이트되도록
        blocks = self.pdf_handler.get_page_blocks(page)

        if not blocks:
            # Fallback: 블록 추출 실패 시 전체 텍스트로 (\n\n 단위로 단락 분할됨)
            page_text = self.pdf_handler.get_page_text(page)
            if not page_text.strip():
                messagebox.showinfo("알림", "이 페이지에서 텍스트를 추출할 수 없습니다.")
                return
            spans = self._auto_highlighter.analyze_with_rules(page_text)
        else:
            spans = self._auto_highlighter.analyze_with_rules(blocks)
        if not spans:
            self.status_label.configure(
                text="자동 하이라이트: 매칭 없음",
                foreground=self.colors['text_secondary']
            )
            return

        added = self.pdf_handler.add_auto_highlights(page, spans, self.pdf_handler.zoom_level)

        # undo_stack에 개별 추가 — 사용자가 한 번씩 되돌리면서 카테고리별 결과 검토 가능
        for ann in added:
            self.undo_stack.append((page, ann, False))

        if added:
            self.annotation_toolbar.set_undo_enabled(True)
            self._display_pdf_page()

        self.status_label.configure(
            text=f"🤖 자동 하이라이트 {len(added)}개 적용",
            foreground=self.colors['success']
        )
        logger.info(f"룰 기반 자동 하이라이트: {len(spans)}개 스팬 → {len(added)}개 적용")

    def _on_auto_highlight_llm(self) -> None:
        """LLM 기반 자동 하이라이트 (LLM 통합 단계에서 구현)"""
        # LLMClient/스레딩은 다음 단계에서 추가
        if self._llm_client is None or not self._llm_client.available:
            messagebox.showinfo(
                "알림",
                "AI 정밀 분석을 사용하려면 ANTHROPIC_API_KEY 환경변수와\n"
                "anthropic SDK 설치가 필요합니다."
            )
            return
        # 실제 호출 로직은 LLM 통합 단계에서 추가

    def _capture_pdf_view(self) -> None:
        """현재 PDF 뷰어 화면 캡쳐"""
        if self.pdf_handler.total_pages == 0:
            messagebox.showwarning("알림", "캡쳐할 PDF가 없습니다.")
            return

        try:
            # 캡쳐 폴더 생성
            capture_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), 'data', 'capture')
            os.makedirs(capture_dir, exist_ok=True)

            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current = self.current_report
            stock_name = current.stock if current else 'unknown'
            stock_name = "".join(c for c in stock_name if c.isalnum() or c in ('_', '-'))
            filename = f"{stock_name}_{timestamp}_page{self.pdf_handler.current_page + 1}.png"
            filepath = os.path.join(capture_dir, filename)

            # 저장
            if self.pdf_handler.save_page_image(filepath):
                messagebox.showinfo("캡쳐 완료", f"이미지가 저장되었습니다.\n\n{filepath}")
                logger.info(f"PDF 캡쳐 저장: {filepath}")
            else:
                messagebox.showerror("오류", "캡쳐에 실패했습니다.")

        except Exception as e:
            logger.error(f"캡쳐 실패: {e}")
            messagebox.showerror("오류", f"캡쳐 중 오류가 발생했습니다.\n\n{str(e)}")

    def run(self) -> None:
        """앱 실행"""
        self.root.mainloop()

    def close(self) -> None:
        """앱 종료"""
        self.scraper.close()
        self.pdf_handler.reset()
        self.root.destroy()
        logger.info("앱 종료")
