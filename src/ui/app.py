"""
메인 앱 클래스 모듈
- NaverReportViewerApp: 메인 앱 클래스
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import webbrowser
import os
from typing import Optional

from ..config import (
    COLORS, WINDOW_TITLE, WINDOW_GEOMETRY, WINDOW_MIN_SIZE,
    ZOOM_STEP, ZOOM_MIN, ZOOM_MAX
)
from ..models import ReportData
from ..scraper import NaverReportScraper
from ..pdf_handler import PDFHandler
from .styles import setup_styles
from .widgets import ReportListWidget, PDFViewerWidget, AnnotationToolbar


class NaverReportViewerApp:
    """네이버 종목 리포트 뷰어 메인 앱"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(*WINDOW_MIN_SIZE)

        # 스타일 설정
        self.colors = COLORS
        setup_styles(self.colors)

        # 데이터
        self.scraper = NaverReportScraper()
        self.pdf_handler = PDFHandler()
        self.reports = []
        self.current_report: Optional[ReportData] = None

        # 어노테이션 관련
        self.undo_stack = []
        self.is_drawing = False
        self.draw_start = None
        self.temp_rect = None
        self.temp_line = None

        # UI 생성
        self._create_ui()

        # 시작 시 자동으로 리포트 로드
        self.root.after(500, self.load_reports)

    def _create_ui(self):
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

    def _create_header(self, parent):
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

    def _create_report_list(self, parent):
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

    def _create_pdf_viewer(self, parent):
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

    def load_reports(self):
        """리포트 로드"""
        self.status_label.configure(text="불러오는 중...", foreground=self.colors['warning'])
        self.refresh_btn.configure(state='disabled')

        thread = threading.Thread(target=self._fetch_reports)
        thread.daemon = True
        thread.start()

    def _fetch_reports(self):
        """리포트 가져오기 (스레드)"""
        try:
            reports = self.scraper.fetch_reports()
            self.reports = reports
            self.root.after(0, self._update_report_list)
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

    def _update_report_list(self):
        """리포트 목록 업데이트"""
        report_data_list = self.reports
        self.report_list.set_reports(report_data_list)

        total = len(report_data_list)
        self.status_label.configure(text=f"✓ {total}개 로드됨",
                                    foreground=self.colors['success'])
        self.refresh_btn.configure(state='normal')

        if total == 0:
            messagebox.showinfo("알림", "오늘 날짜의 리포트가 없습니다.")

    def _show_error(self, error_msg: str):
        """에러 표시"""
        self.status_label.configure(text="✗ 로딩 실패",
                                    foreground=self.colors['danger'])
        self.refresh_btn.configure(state='normal')
        messagebox.showerror("오류", f"리포트를 불러오는데 실패했습니다.\n\n{error_msg}")

    def _on_report_select(self, idx: int):
        """리포트 선택"""
        self.current_report = self.reports[idx]

        # PDF 핸들러 초기화
        self.pdf_handler.reset()
        self.undo_stack = []
        self.annotation_toolbar.set_undo_enabled(False)
        self.annotation_toolbar.reset_tool()

        # UI 업데이트
        self.pdf_viewer.update_report_info(self.current_report)
        self.pdf_viewer.show_loading()

        # 상세 정보 로드 (PDF 링크 포함) → 완료 후 PDF 로드
        self._load_report_meta()

    def _on_report_double_click(self, idx: int):
        """리포트 더블클릭"""
        self._open_current_link()

    def _load_report_meta(self):
        """리포트 메타 정보 로드"""
        thread = threading.Thread(target=self._fetch_report_meta)
        thread.daemon = True
        thread.start()

    def _fetch_report_meta(self):
        """리포트 메타 정보 가져오기"""
        if self.current_report:
            self.scraper.fetch_report_meta(self.current_report)
            self.root.after(0, self._update_meta_labels)

    def _update_meta_labels(self):
        """메타 정보 업데이트 + PDF 로드"""
        if not self.current_report:
            return

        self.pdf_viewer.meta_labels['opinion'].configure(text=self.current_report.opinion)
        self.pdf_viewer.meta_labels['target'].configure(text=self.current_report.target)

        if self.current_report.pdf_link:
            self._load_pdf()
        else:
            self.pdf_viewer.show_no_pdf()

    def _load_pdf(self):
        """PDF 로드"""
        if not PDFHandler.is_supported():
            self.pdf_viewer.show_no_support()
            return

        self.pdf_viewer.show_loading()

        thread = threading.Thread(target=self._fetch_and_render_pdf)
        thread.daemon = True
        thread.start()

    def _fetch_and_render_pdf(self):
        """PDF 다운로드 및 렌더링"""
        try:
            self.pdf_handler.load_pdf(self.current_report.pdf_link)
            self.root.after(0, self._display_pdf_page)
        except Exception as e:
            self.root.after(0, lambda: self.pdf_viewer.show_error(str(e)))

    def _display_pdf_page(self):
        """현재 페이지 표시"""
        img = self.pdf_handler.render_page()
        if img:
            self.pdf_viewer.display_image(
                img,
                self.pdf_handler.current_page,
                self.pdf_handler.total_pages,
                self.pdf_handler.zoom_level
            )

    def _prev_page(self):
        """이전 페이지"""
        if self.pdf_handler.current_page > 0:
            self.pdf_handler.current_page -= 1
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _next_page(self):
        """다음 페이지"""
        if self.pdf_handler.current_page < self.pdf_handler.total_pages - 1:
            self.pdf_handler.current_page += 1
            self._display_pdf_page()
            self.pdf_viewer.scroll_to_top()

    def _zoom_in(self):
        """확대"""
        if self.pdf_handler.zoom_level < ZOOM_MAX:
            self.pdf_handler.zoom_level += ZOOM_STEP
            self._display_pdf_page()

    def _zoom_out(self):
        """축소"""
        if self.pdf_handler.zoom_level > ZOOM_MIN:
            self.pdf_handler.zoom_level -= ZOOM_STEP
            self._display_pdf_page()

    def _open_current_link(self):
        """원본 페이지 열기"""
        if self.current_report and self.current_report.link:
            webbrowser.open(self.current_report.link)

    def _open_pdf(self):
        """PDF 다운로드"""
        if self.current_report and self.current_report.pdf_link:
            webbrowser.open(self.current_report.pdf_link)

    def _on_tool_change(self, tool: Optional[str]):
        """도구 변경"""
        if tool is None:
            self.pdf_viewer.set_cursor('arrow')
        elif tool == 'eraser':
            self.pdf_viewer.set_cursor('X_cursor')
        else:
            self.pdf_viewer.set_cursor('crosshair')

    def _on_mouse_press(self, x: float, y: float):
        """마우스 버튼 누름"""
        if not self.pdf_handler.is_loaded:
            return

        tool = self.annotation_toolbar.current_tool

        if tool in ('highlighter', 'line'):
            self.is_drawing = True
            self.draw_start = (x, y)
        elif tool == 'eraser':
            self._erase_at_point(x, y)

    def _on_mouse_drag(self, x: float, y: float):
        """마우스 드래그"""
        if not self.is_drawing:
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

    def _on_mouse_release(self, x: float, y: float):
        """마우스 버튼 놓음"""
        if not self.is_drawing:
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

    def _add_highlight_annotation(self, coords):
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

    def _add_line_annotation(self, coords):
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

    def _erase_at_point(self, canvas_x: float, canvas_y: float):
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

    def _undo_annotation(self):
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

    def _clear_annotations(self):
        """현재 페이지의 모든 어노테이션 삭제"""
        page = self.pdf_handler.current_page
        cleared = self.pdf_handler.clear_annotations(page)

        for ann in cleared:
            self.undo_stack.append((page, ann, True))

        if cleared:
            self.annotation_toolbar.set_undo_enabled(True)
            self._display_pdf_page()

    def _capture_pdf_view(self):
        """현재 PDF 뷰어 화면 캡쳐"""
        if not self.pdf_handler.is_loaded:
            messagebox.showwarning("알림", "캡쳐할 PDF가 없습니다.")
            return

        try:
            # 캡쳐 폴더 생성
            capture_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), 'data', 'capture')
            os.makedirs(capture_dir, exist_ok=True)

            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stock_name = self.current_report.stock if self.current_report else 'unknown'
            stock_name = "".join(c for c in stock_name if c.isalnum() or c in ('_', '-'))
            filename = f"{stock_name}_{timestamp}_page{self.pdf_handler.current_page + 1}.png"
            filepath = os.path.join(capture_dir, filename)

            # 저장
            if self.pdf_handler.save_page_image(filepath):
                messagebox.showinfo("캡쳐 완료", f"이미지가 저장되었습니다.\n\n{filepath}")
            else:
                messagebox.showerror("오류", "캡쳐에 실패했습니다.")

        except Exception as e:
            messagebox.showerror("오류", f"캡쳐 중 오류가 발생했습니다.\n\n{str(e)}")

    def run(self):
        """앱 실행"""
        self.root.mainloop()

    def close(self):
        """앱 종료"""
        self.scraper.close()
        self.root.destroy()
