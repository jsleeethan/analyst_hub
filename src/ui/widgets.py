"""
커스텀 위젯 모듈
- ReportListWidget: 리포트 목록 (Treeview)
- PDFViewerWidget: PDF 뷰어 (Canvas + 컨트롤)
- AnnotationToolbar: 어노테이션 도구 모음
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional

from ..config import (
    COLORS, HIGHLIGHT_COLORS, LINE_COLORS,
    DEFAULT_HIGHLIGHT_COLOR, DEFAULT_LINE_COLOR,
    TRANSPARENCY_OPTIONS, DEFAULT_ALPHA,
    LINE_WIDTH_OPTIONS, DEFAULT_LINE_WIDTH
)
from ..models import ReportData

# PDF 지원 여부 확인
try:
    from PIL import ImageTk
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    ImageTk = None


class ReportListWidget(ttk.Frame):
    """리포트 목록 위젯"""

    def __init__(self, parent, colors: dict = None,
                 on_select: Callable[[int], None] = None,
                 on_double_click: Callable[[int], None] = None):
        super().__init__(parent, style='Card.TFrame')

        self.colors = colors or COLORS
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.reports: List[ReportData] = []

        self._create_ui()

    def _create_ui(self):
        """UI 생성"""
        # 내부 패딩
        inner_frame = ttk.Frame(self, style='Card.TFrame')
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # 헤더 영역
        header_frame = ttk.Frame(inner_frame, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 16))

        list_header = ttk.Label(header_frame,
                                text="📋  오늘의 리포트",
                                style='CardTitle.TLabel')
        list_header.pack(side=tk.LEFT)

        # 검색 영역
        search_frame = ttk.Frame(inner_frame, style='Card.TFrame')
        search_frame.pack(fill=tk.X, pady=(0, 12))

        search_container = tk.Frame(search_frame, bg=self.colors['bg_elevated'],
                                    highlightbackground=self.colors['border'],
                                    highlightthickness=1)
        search_container.pack(fill=tk.X)

        search_icon = tk.Label(search_container, text="🔍",
                               bg=self.colors['bg_elevated'],
                               fg=self.colors['text_muted'],
                               font=('Segoe UI', 10))
        search_icon.pack(side=tk.LEFT, padx=(10, 5), pady=8)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = tk.Entry(search_container,
                                textvariable=self.search_var,
                                bg=self.colors['bg_elevated'],
                                fg=self.colors['text_primary'],
                                insertbackground=self.colors['text_primary'],
                                font=('Segoe UI', 10),
                                bd=0,
                                highlightthickness=0)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=8)

        # Treeview 컨테이너
        tree_container = tk.Frame(inner_frame, bg=self.colors['border'])
        tree_container.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(tree_container, style='Card.TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 컬럼
        columns = ('no', 'stock', 'title', 'firm')
        self.tree = ttk.Treeview(tree_frame,
                                 columns=columns,
                                 show='headings',
                                 style='Report.Treeview',
                                 selectmode='browse')

        # 컬럼 설정
        self.tree.heading('no', text='No.')
        self.tree.heading('stock', text='종목명')
        self.tree.heading('title', text='리포트 제목')
        self.tree.heading('firm', text='증권사')

        self.tree.column('no', width=45, minwidth=40, anchor='center')
        self.tree.column('stock', width=85, minwidth=70, anchor='w')
        self.tree.column('title', width=230, minwidth=150, anchor='w')
        self.tree.column('firm', width=85, minwidth=70, anchor='w')

        # 스크롤바
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 이벤트
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)

    def _on_search(self, *args):
        """검색어 변경 시"""
        self._update_list()

    def _on_select(self, event):
        """항목 선택 시"""
        selection = self.tree.selection()
        if selection and self.on_select:
            try:
                idx = int(selection[0])
            except (ValueError, IndexError):
                return
            self.on_select(idx)

    def _on_double_click(self, event):
        """더블클릭 시"""
        selection = self.tree.selection()
        if selection and self.on_double_click:
            try:
                idx = int(selection[0])
            except (ValueError, IndexError):
                return
            self.on_double_click(idx)

    def set_reports(self, reports: List[ReportData]):
        """리포트 목록 설정"""
        self.reports = reports
        self._update_list()

    def _update_list(self):
        """리스트 업데이트"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_term = self.search_var.get().lower()

        # 필터링
        filtered = []
        for i, report in enumerate(self.reports):
            if not search_term or report.matches_search(search_term):
                filtered.append((i, report))

        # 내림차순 번호
        total = len(filtered)
        for idx, (i, report) in enumerate(filtered):
            no = total - idx
            self.tree.insert('', 'end', iid=str(i), values=(
                no,
                report.stock,
                report.title,
                report.firm
            ))

    def get_report_count(self) -> int:
        """리포트 개수 반환"""
        return len(self.reports)


class PDFViewerWidget(ttk.Frame):
    """PDF 뷰어 위젯"""

    def __init__(self, parent, colors: dict = None):
        super().__init__(parent, style='Card.TFrame')

        self.colors = colors or COLORS
        self._current_photo = None
        self.image_offset_x = 0
        self.image_offset_y = 0

        # 콜백
        self.on_prev_page: Optional[Callable] = None
        self.on_next_page: Optional[Callable] = None
        self.on_zoom_in: Optional[Callable] = None
        self.on_zoom_out: Optional[Callable] = None
        self.on_open_link: Optional[Callable] = None
        self.on_download: Optional[Callable] = None
        self.on_mouse_press: Optional[Callable] = None
        self.on_mouse_drag: Optional[Callable] = None
        self.on_mouse_release: Optional[Callable] = None

        self._create_ui()

    def _create_ui(self):
        """UI 생성"""
        inner_frame = ttk.Frame(self, style='Card.TFrame')
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # 상단 정보 영역
        info_frame = ttk.Frame(inner_frame, style='Card.TFrame')
        info_frame.pack(fill=tk.X, pady=(0, 12))

        self.stock_label = tk.Label(info_frame,
                                    text="리포트를 선택하세요",
                                    font=('Segoe UI', 18, 'bold'),
                                    bg=self.colors['bg_card'],
                                    fg=self.colors['text_primary'])
        self.stock_label.pack(anchor=tk.W)

        self.title_label = tk.Label(info_frame,
                                    text="",
                                    font=('Segoe UI', 11),
                                    bg=self.colors['bg_card'],
                                    fg=self.colors['text_secondary'],
                                    wraplength=800,
                                    justify='left')
        self.title_label.pack(anchor=tk.W, pady=(4, 0))

        # 메타 정보 카드
        meta_container = tk.Frame(inner_frame, bg=self.colors['bg_elevated'])
        meta_container.pack(fill=tk.X, pady=(8, 12))

        meta_inner = tk.Frame(meta_container, bg=self.colors['bg_elevated'])
        meta_inner.pack(fill=tk.X, padx=16, pady=12)

        self.meta_labels = {}
        meta_items = [('firm', '증권사'), ('date', '작성일'),
                      ('opinion', '투자의견'), ('target', '목표가')]

        for i, (key, label) in enumerate(meta_items):
            item_frame = tk.Frame(meta_inner, bg=self.colors['bg_elevated'])
            item_frame.pack(side=tk.LEFT, padx=(0, 32) if i < len(meta_items) - 1 else 0)

            tk.Label(item_frame, text=label,
                     bg=self.colors['bg_elevated'],
                     fg=self.colors['text_muted'],
                     font=('Segoe UI', 9)).pack(anchor=tk.W)

            self.meta_labels[key] = tk.Label(item_frame, text="-",
                                             bg=self.colors['bg_elevated'],
                                             fg=self.colors['accent'],
                                             font=('Segoe UI', 13, 'bold'))
            self.meta_labels[key].pack(anchor=tk.W, pady=(2, 0))

        # PDF 컨트롤 바
        control_frame = ttk.Frame(inner_frame, style='Card.TFrame')
        control_frame.pack(fill=tk.X, pady=(0, 8))

        # 좌측: 페이지 네비게이션
        nav_frame = ttk.Frame(control_frame, style='Card.TFrame')
        nav_frame.pack(side=tk.LEFT)

        self.prev_btn = ttk.Button(nav_frame, text="◀", style='Icon.TButton',
                                   command=self._on_prev_page, state='disabled', width=3)
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 4))

        page_container = tk.Frame(nav_frame, bg=self.colors['bg_elevated'],
                                  padx=12, pady=6)
        page_container.pack(side=tk.LEFT, padx=4)

        self.page_label = tk.Label(page_container, text="0 / 0",
                                   bg=self.colors['bg_elevated'],
                                   fg=self.colors['text_primary'],
                                   font=('Segoe UI', 10))
        self.page_label.pack()

        self.next_btn = ttk.Button(nav_frame, text="▶", style='Icon.TButton',
                                   command=self._on_next_page, state='disabled', width=3)
        self.next_btn.pack(side=tk.LEFT, padx=(4, 0))

        # 중앙: 줌 컨트롤
        zoom_frame = ttk.Frame(control_frame, style='Card.TFrame')
        zoom_frame.pack(side=tk.LEFT, padx=(24, 0))

        self.zoom_out_btn = ttk.Button(zoom_frame, text="−", style='Icon.TButton',
                                       command=self._on_zoom_out, width=3, state='disabled')
        self.zoom_out_btn.pack(side=tk.LEFT, padx=(0, 4))

        zoom_container = tk.Frame(zoom_frame, bg=self.colors['bg_elevated'],
                                  padx=10, pady=6)
        zoom_container.pack(side=tk.LEFT, padx=4)

        self.zoom_label = tk.Label(zoom_container, text="100%",
                                   bg=self.colors['bg_elevated'],
                                   fg=self.colors['text_primary'],
                                   font=('Segoe UI', 10),
                                   width=5)
        self.zoom_label.pack()

        self.zoom_in_btn = ttk.Button(zoom_frame, text="+", style='Icon.TButton',
                                      command=self._on_zoom_in, width=3, state='disabled')
        self.zoom_in_btn.pack(side=tk.LEFT, padx=(4, 0))

        # 우측: 외부 링크 버튼
        link_frame = ttk.Frame(control_frame, style='Card.TFrame')
        link_frame.pack(side=tk.RIGHT)

        self.link_btn = ttk.Button(link_frame, text="🔗 원본 보기", style='Nav.TButton',
                                   command=self._on_open_link, state='disabled')
        self.link_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.pdf_btn = ttk.Button(link_frame, text="📥 다운로드", style='Nav.TButton',
                                  command=self._on_download, state='disabled')
        self.pdf_btn.pack(side=tk.LEFT)

        # 어노테이션 툴바를 위한 프레임 (외부에서 추가)
        self.toolbar_frame = ttk.Frame(inner_frame, style='Card.TFrame')
        self.toolbar_frame.pack(fill=tk.X)

        # PDF 캔버스 영역
        canvas_container = tk.Frame(inner_frame, bg=self.colors['border'])
        canvas_container.pack(fill=tk.BOTH, expand=True)

        canvas_frame = tk.Frame(canvas_container, bg=self.colors['bg_elevated'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_elevated'],
                                highlightthickness=0, cursor='arrow')

        self.v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                         command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                                         command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set,
                              xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 마우스 이벤트
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)
        self.canvas.bind('<Button-5>', self._on_mousewheel)
        self.canvas.bind('<ButtonPress-1>', self._handle_mouse_press)
        self.canvas.bind('<B1-Motion>', self._handle_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._handle_mouse_release)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        # 초기 메시지
        self.show_placeholder()

    def _on_prev_page(self):
        if self.on_prev_page:
            self.on_prev_page()

    def _on_next_page(self):
        if self.on_next_page:
            self.on_next_page()

    def _on_zoom_in(self):
        if self.on_zoom_in:
            self.on_zoom_in()

    def _on_zoom_out(self):
        if self.on_zoom_out:
            self.on_zoom_out()

    def _on_open_link(self):
        if self.on_open_link:
            self.on_open_link()

    def _on_download(self):
        if self.on_download:
            self.on_download()

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, 'units')
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, 'units')

    def _handle_mouse_press(self, event):
        if self.on_mouse_press:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.on_mouse_press(x, y)

    def _handle_mouse_drag(self, event):
        if self.on_mouse_drag:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.on_mouse_drag(x, y)

    def _handle_mouse_release(self, event):
        if self.on_mouse_release:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.on_mouse_release(x, y)

    def _on_canvas_resize(self, event):
        # 콜백은 app에서 처리
        pass

    def show_placeholder(self):
        """플레이스홀더 표시"""
        self.canvas.delete('all')
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_text(
            cx, cy,
            text="📄\n\n리포트를 선택하면\nPDF 내용이 여기에 표시됩니다.",
            fill=self.colors['text_muted'],
            font=('Segoe UI', 13),
            justify='center'
        )

    def show_loading(self):
        """로딩 표시"""
        self.canvas.delete('all')
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_text(
            cx, cy,
            text="⏳\n\nPDF를 불러오는 중...",
            fill=self.colors['text_secondary'],
            font=('Segoe UI', 12),
            justify='center'
        )

    def show_no_pdf(self):
        """PDF 없음 표시"""
        self.canvas.delete('all')
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_text(
            cx, cy,
            text="📄\n\nPDF가 제공되지 않는 리포트입니다.\n\n'원본 보기' 버튼을 클릭하여\n웹페이지에서 확인하세요.",
            fill=self.colors['text_muted'],
            font=('Segoe UI', 12),
            justify='center'
        )
        self.disable_controls()

    def show_error(self, error_msg: str):
        """에러 표시"""
        self.canvas.delete('all')
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_text(
            cx, cy,
            text=f"⚠️\n\nPDF를 불러올 수 없습니다.\n\n{error_msg}\n\n'다운로드' 버튼으로 직접 다운로드하세요.",
            fill=self.colors['danger'],
            font=('Segoe UI', 11),
            justify='center'
        )
        self.disable_controls()

    def show_no_support(self):
        """PDF 미지원 표시"""
        self.canvas.delete('all')
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_text(
            cx, cy,
            text="⚠️\n\nPDF 뷰어를 사용하려면\n라이브러리를 설치하세요.\n\npip install pymupdf pillow",
            fill=self.colors['danger'],
            font=('Segoe UI', 12),
            justify='center'
        )

    def display_image(self, img, current_page: int, total_pages: int, zoom_level: float):
        """이미지 표시"""
        if not PDF_SUPPORT:
            return

        self.canvas.delete('all')
        self.canvas.update_idletasks()

        photo = ImageTk.PhotoImage(img)
        self._current_photo = photo

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        img_width, img_height = img.size

        if img_width < canvas_width:
            img_x = (canvas_width - img_width) // 2
        else:
            img_x = 10

        if img_height < canvas_height:
            img_y = (canvas_height - img_height) // 2
        else:
            img_y = 10

        self.image_offset_x = img_x
        self.image_offset_y = img_y

        self.canvas.create_image(img_x, img_y, anchor='nw', image=photo, tags='pdf_image')

        scroll_width = max(img_width + 20, canvas_width)
        scroll_height = max(img_height + 20, canvas_height)
        self.canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))

        self.update_controls(current_page, total_pages, zoom_level)

    def update_controls(self, current_page: int, total_pages: int, zoom_level: float):
        """컨트롤 업데이트"""
        self.page_label.configure(text=f"{current_page + 1} / {total_pages}")
        self.zoom_label.configure(text=f"{int(zoom_level * 100)}%")

        self.prev_btn.configure(state='normal' if current_page > 0 else 'disabled')
        self.next_btn.configure(state='normal' if current_page < total_pages - 1 else 'disabled')
        self.zoom_in_btn.configure(state='normal' if zoom_level < 2.0 else 'disabled')
        self.zoom_out_btn.configure(state='normal' if zoom_level > 0.5 else 'disabled')

    def disable_controls(self):
        """컨트롤 비활성화"""
        self.prev_btn.configure(state='disabled')
        self.next_btn.configure(state='disabled')
        self.zoom_in_btn.configure(state='disabled')
        self.zoom_out_btn.configure(state='disabled')
        self.page_label.configure(text="0 / 0")

    def update_report_info(self, report: Optional[ReportData]):
        """리포트 정보 업데이트"""
        if report:
            self.stock_label.configure(text=report.stock)
            self.title_label.configure(text=report.title)
            self.meta_labels['firm'].configure(text=report.firm)
            self.meta_labels['date'].configure(text=report.date)
            self.meta_labels['opinion'].configure(text=report.opinion)
            self.meta_labels['target'].configure(text=report.target)
            self.link_btn.configure(state='normal')
            self.pdf_btn.configure(state='normal' if report.pdf_link else 'disabled')
        else:
            self.stock_label.configure(text="리포트를 선택하세요")
            self.title_label.configure(text="")
            for key in self.meta_labels:
                self.meta_labels[key].configure(text="-")
            self.link_btn.configure(state='disabled')
            self.pdf_btn.configure(state='disabled')

    def set_cursor(self, cursor: str):
        """캔버스 커서 설정"""
        self.canvas.configure(cursor=cursor)

    def scroll_to_top(self):
        """스크롤을 맨 위로"""
        self.canvas.yview_moveto(0)


class AnnotationToolbar(tk.Frame):
    """어노테이션 도구 모음"""

    def __init__(self, parent, colors: dict = None):
        super().__init__(parent, bg=colors['bg_elevated'] if colors else COLORS['bg_elevated'])

        self.colors = colors or COLORS
        self.current_tool = None  # None, 'highlighter', 'line', 'eraser'

        # 현재 설정
        self.current_highlight_color = DEFAULT_HIGHLIGHT_COLOR
        self.current_line_color = DEFAULT_LINE_COLOR
        self.current_alpha = DEFAULT_ALPHA
        self.current_line_width = DEFAULT_LINE_WIDTH

        # 콜백
        self.on_tool_change: Optional[Callable[[str], None]] = None
        self.on_undo: Optional[Callable] = None
        self.on_clear: Optional[Callable] = None
        self.on_capture: Optional[Callable] = None
        self.on_auto_highlight_rules: Optional[Callable] = None
        self.on_auto_highlight_llm: Optional[Callable] = None

        self._create_ui()

    def _create_ui(self):
        """UI 생성"""
        # 첫 번째 줄: 형광펜, 라인 도구
        toolbar_frame1 = tk.Frame(self, bg=self.colors['bg_elevated'])
        toolbar_frame1.pack(fill=tk.X, pady=(0, 4))

        toolbar_inner1 = tk.Frame(toolbar_frame1, bg=self.colors['bg_elevated'])
        toolbar_inner1.pack(fill=tk.X, padx=12, pady=8)

        # 형광펜 섹션
        tk.Label(toolbar_inner1, text="🖍️ 형광펜:",
                 bg=self.colors['bg_elevated'],
                 fg=self.colors['text_secondary'],
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 8))

        self.highlighter_btn = ttk.Button(toolbar_inner1, text="선택",
                                          style='Tool.TButton',
                                          command=self._toggle_highlighter)
        self.highlighter_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 형광펜 색상 선택
        self.color_buttons = []
        color_frame = tk.Frame(toolbar_inner1, bg=self.colors['bg_elevated'])
        color_frame.pack(side=tk.LEFT, padx=(4, 8))

        for color in HIGHLIGHT_COLORS:
            btn = tk.Button(color_frame, bg=color, width=2, height=1,
                            relief='flat', bd=0,
                            command=lambda c=color: self._select_highlight_color(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.color_buttons.append(btn)

        self._update_color_selection()

        # 투명도 조절
        tk.Label(toolbar_inner1, text="투명도:",
                 bg=self.colors['bg_elevated'],
                 fg=self.colors['text_secondary'],
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(8, 6))

        self.transparency_buttons = []
        trans_frame = tk.Frame(toolbar_inner1, bg=self.colors['bg_elevated'])
        trans_frame.pack(side=tk.LEFT, padx=(0, 8))

        for label, alpha in TRANSPARENCY_OPTIONS:
            btn = tk.Button(trans_frame, text=label, width=4,
                            bg=self.colors['bg_elevated'],
                            fg=self.colors['text_primary'],
                            font=('Segoe UI', 8),
                            relief='flat', bd=1,
                            activebackground=self.colors['border'],
                            command=lambda a=alpha: self._select_transparency(a))
            btn.pack(side=tk.LEFT, padx=1)
            self.transparency_buttons.append((btn, alpha))

        self._update_transparency_selection()

        # 구분선
        tk.Frame(toolbar_inner1, bg=self.colors['border'], width=1, height=24).pack(side=tk.LEFT, padx=12)

        # 라인 섹션
        tk.Label(toolbar_inner1, text="✏️ 라인:",
                 bg=self.colors['bg_elevated'],
                 fg=self.colors['text_secondary'],
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 8))

        self.line_btn = ttk.Button(toolbar_inner1, text="선택",
                                   style='Tool.TButton',
                                   command=self._toggle_line)
        self.line_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 라인 색상 선택
        self.line_color_buttons = []
        line_color_frame = tk.Frame(toolbar_inner1, bg=self.colors['bg_elevated'])
        line_color_frame.pack(side=tk.LEFT, padx=(4, 8))

        for color in LINE_COLORS:
            btn = tk.Button(line_color_frame, bg=color, width=2, height=1,
                            relief='flat', bd=0,
                            command=lambda c=color: self._select_line_color(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.line_color_buttons.append(btn)

        self._update_line_color_selection()

        # 라인 굵기
        tk.Label(toolbar_inner1, text="굵기:",
                 bg=self.colors['bg_elevated'],
                 fg=self.colors['text_secondary'],
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(8, 6))

        self.line_width_buttons = []
        width_frame = tk.Frame(toolbar_inner1, bg=self.colors['bg_elevated'])
        width_frame.pack(side=tk.LEFT, padx=(0, 8))

        for width in LINE_WIDTH_OPTIONS:
            btn = tk.Button(width_frame, text=str(width), width=2,
                            bg=self.colors['bg_elevated'],
                            fg=self.colors['text_primary'],
                            font=('Segoe UI', 8),
                            relief='flat', bd=1,
                            command=lambda w=width: self._select_line_width(w))
            btn.pack(side=tk.LEFT, padx=1)
            self.line_width_buttons.append((btn, width))

        self._update_line_width_selection()

        # 두 번째 줄
        toolbar_frame2 = tk.Frame(self, bg=self.colors['bg_elevated'])
        toolbar_frame2.pack(fill=tk.X, pady=(0, 8))

        toolbar_inner2 = tk.Frame(toolbar_frame2, bg=self.colors['bg_elevated'])
        toolbar_inner2.pack(fill=tk.X, padx=12, pady=8)

        # 지우개 버튼
        self.eraser_btn = ttk.Button(toolbar_inner2, text="🧹 지우개",
                                     style='Tool.TButton',
                                     command=self._toggle_eraser)
        self.eraser_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 구분선
        tk.Frame(toolbar_inner2, bg=self.colors['border'], width=1, height=24).pack(side=tk.LEFT, padx=8)

        # 되돌리기 버튼
        self.undo_btn = ttk.Button(toolbar_inner2, text="↩️ 되돌리기",
                                   style='Tool.TButton',
                                   command=self._on_undo,
                                   state='disabled')
        self.undo_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 전체 삭제 버튼
        self.clear_btn = ttk.Button(toolbar_inner2, text="🗑️ 전체 삭제",
                                    style='Tool.TButton',
                                    command=self._on_clear)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 구분선
        tk.Frame(toolbar_inner2, bg=self.colors['border'], width=1, height=24).pack(side=tk.LEFT, padx=12)

        # 캡쳐 버튼
        self.capture_btn = ttk.Button(toolbar_inner2, text="📷 캡쳐",
                                      style='Accent.TButton',
                                      command=self._on_capture)
        self.capture_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 구분선
        tk.Frame(toolbar_inner2, bg=self.colors['border'], width=1, height=24).pack(side=tk.LEFT, padx=12)

        # 자동 하이라이트 버튼 (룰 기반, 항상 활성)
        self.auto_highlight_btn = ttk.Button(toolbar_inner2, text="🤖 자동 하이라이트",
                                              style='Accent.TButton',
                                              command=self._on_auto_highlight_rules)
        self.auto_highlight_btn.pack(side=tk.LEFT, padx=(0, 4))

        # AI 정밀 분석 버튼 (LLM, API 키 있을 때만 활성 - app.py에서 제어)
        self.ai_highlight_btn = ttk.Button(toolbar_inner2, text="🧠 AI 정밀 분석",
                                            style='Accent.TButton',
                                            command=self._on_auto_highlight_llm,
                                            state='disabled')
        self.ai_highlight_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 현재 도구 상태 표시
        self.tool_status = tk.Label(toolbar_inner2, text="",
                                    bg=self.colors['bg_elevated'],
                                    fg=self.colors['warning'],
                                    font=('Segoe UI', 9, 'bold'))
        self.tool_status.pack(side=tk.RIGHT)

    def _deactivate_all_tools(self):
        """모든 도구 버튼 비활성화 스타일로"""
        self.highlighter_btn.configure(style='Tool.TButton')
        self.line_btn.configure(style='Tool.TButton')
        self.eraser_btn.configure(style='Tool.TButton')

    def _toggle_highlighter(self):
        if self.current_tool == 'highlighter':
            self.current_tool = None
            self._deactivate_all_tools()
            self.tool_status.configure(text="")
        else:
            self.current_tool = 'highlighter'
            self._deactivate_all_tools()
            self.highlighter_btn.configure(style='ToolActive.TButton')
            self.tool_status.configure(text="🖍️ 형광펜 모드 - 드래그하여 영역 선택")

        if self.on_tool_change:
            self.on_tool_change(self.current_tool)

    def _toggle_line(self):
        if self.current_tool == 'line':
            self.current_tool = None
            self._deactivate_all_tools()
            self.tool_status.configure(text="")
        else:
            self.current_tool = 'line'
            self._deactivate_all_tools()
            self.line_btn.configure(style='ToolActive.TButton')
            self.tool_status.configure(text="✏️ 라인 모드 - 드래그하여 선 그리기")

        if self.on_tool_change:
            self.on_tool_change(self.current_tool)

    def _toggle_eraser(self):
        if self.current_tool == 'eraser':
            self.current_tool = None
            self._deactivate_all_tools()
            self.tool_status.configure(text="")
        else:
            self.current_tool = 'eraser'
            self._deactivate_all_tools()
            self.eraser_btn.configure(style='ToolActive.TButton')
            self.tool_status.configure(text="🧹 지우개 모드 - 어노테이션 클릭하여 삭제")

        if self.on_tool_change:
            self.on_tool_change(self.current_tool)

    def _update_color_selection(self):
        for btn in self.color_buttons:
            if btn.cget('bg') == self.current_highlight_color:
                btn.configure(relief='solid', bd=2)
            else:
                btn.configure(relief='flat', bd=0)

    def _select_highlight_color(self, color):
        self.current_highlight_color = color
        self._update_color_selection()
        if self.current_tool != 'highlighter':
            self._toggle_highlighter()

    def _update_transparency_selection(self):
        for btn, alpha in self.transparency_buttons:
            if alpha == self.current_alpha:
                btn.configure(relief='solid', bd=2, bg=self.colors['accent'], fg='white')
            else:
                btn.configure(relief='flat', bd=1, bg=self.colors['bg_elevated'],
                              fg=self.colors['text_primary'])

    def _select_transparency(self, alpha):
        self.current_alpha = alpha
        self._update_transparency_selection()
        if self.current_tool != 'highlighter':
            self._toggle_highlighter()

    def _update_line_color_selection(self):
        for btn in self.line_color_buttons:
            if btn.cget('bg') == self.current_line_color:
                btn.configure(relief='solid', bd=2)
            else:
                btn.configure(relief='flat', bd=0)

    def _select_line_color(self, color):
        self.current_line_color = color
        self._update_line_color_selection()
        if self.current_tool != 'line':
            self._toggle_line()

    def _update_line_width_selection(self):
        for btn, width in self.line_width_buttons:
            if width == self.current_line_width:
                btn.configure(relief='solid', bd=2, bg=self.colors['accent'], fg='white')
            else:
                btn.configure(relief='flat', bd=1, bg=self.colors['bg_elevated'],
                              fg=self.colors['text_primary'])

    def _select_line_width(self, width):
        self.current_line_width = width
        self._update_line_width_selection()
        if self.current_tool != 'line':
            self._toggle_line()

    def _on_undo(self):
        if self.on_undo:
            self.on_undo()

    def _on_clear(self):
        if self.on_clear:
            self.on_clear()

    def _on_capture(self):
        if self.on_capture:
            self.on_capture()

    def _on_auto_highlight_rules(self):
        if self.on_auto_highlight_rules:
            self.on_auto_highlight_rules()

    def _on_auto_highlight_llm(self):
        if self.on_auto_highlight_llm:
            self.on_auto_highlight_llm()

    def set_undo_enabled(self, enabled: bool):
        """되돌리기 버튼 활성화/비활성화"""
        self.undo_btn.configure(state='normal' if enabled else 'disabled')

    def set_ai_highlight_enabled(self, enabled: bool):
        """AI 정밀 분석 버튼 활성화/비활성화"""
        self.ai_highlight_btn.configure(state='normal' if enabled else 'disabled')

    def set_auto_highlight_enabled(self, enabled: bool):
        """자동 하이라이트 버튼 활성화/비활성화 (분석 중 중복 클릭 방지용)"""
        self.auto_highlight_btn.configure(state='normal' if enabled else 'disabled')

    def reset_tool(self):
        """도구 초기화"""
        self.current_tool = None
        self._deactivate_all_tools()
        self.tool_status.configure(text="")
