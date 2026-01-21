# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

네이버 증권 종목 리포트 뷰어 애플리케이션입니다. 모듈화된 Python 패키지 구조를 사용합니다.

## Project Structure

```
analyst_hub/
├── main.py                     # 앱 진입점
├── requirements.txt            # 의존성 목록
├── src/
│   ├── __init__.py
│   ├── config.py               # 설정값 (URL, 색상, 상수)
│   ├── models.py               # 데이터 모델 (ReportData, Annotation)
│   ├── scraper.py              # 웹 크롤링 로직
│   ├── pdf_handler.py          # PDF 처리 (렌더링, 어노테이션)
│   └── ui/
│       ├── __init__.py
│       ├── styles.py           # ttk 스타일 설정
│       ├── widgets.py          # 커스텀 위젯
│       └── app.py              # 메인 앱 클래스
├── data/
│   └── capture/                # 캡처 이미지 저장 폴더
└── CLAUDE.md                   # 이 파일
```

## Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install requests beautifulsoup4 lxml pymupdf pillow
```

## Run

```bash
python main.py
```

## Module Descriptions

### src/config.py
- `COLORS`: 다크 테마 색상 팔레트
- `NAVER_BASE_URL`, `RESEARCH_URL`: 네이버 금융 URL
- `PDF_RENDER_SCALE`, `ZOOM_MIN`, `ZOOM_MAX`: PDF 설정
- `HIGHLIGHT_COLORS`, `LINE_COLORS`: 어노테이션 색상

### src/models.py
- `ReportData`: 리포트 정보 dataclass
- `Annotation`: 어노테이션 정보 dataclass

### src/scraper.py
- `NaverReportScraper`: 리포트 스크래핑 클래스
  - `fetch_reports()`: 리포트 목록 가져오기
  - `fetch_report_meta()`: 상세 정보 가져오기

### src/pdf_handler.py
- `PDFHandler`: PDF 처리 클래스
  - `load_pdf()`: PDF 로드
  - `render_page()`: 페이지 렌더링
  - `apply_annotations()`: 어노테이션 합성
  - `add_highlight()`, `add_line()`: 어노테이션 추가

### src/ui/styles.py
- `setup_styles()`: ttk 스타일 초기화
- `STYLES`: 스타일 이름 상수

### src/ui/widgets.py
- `ReportListWidget`: 리포트 목록 위젯
- `PDFViewerWidget`: PDF 뷰어 위젯
- `AnnotationToolbar`: 어노테이션 도구 모음

### src/ui/app.py
- `NaverReportViewerApp`: 메인 앱 클래스

## Other Files

### ai-quiz-game.html
A standalone HTML/CSS/JavaScript O/X quiz game about artificial intelligence. Open directly in a browser—no build step required.

## Language Note

Most UI text and comments are in Korean (한국어).
