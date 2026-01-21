# Analyst Hub

네이버 증권에서 오늘 날짜의 종목 리포트를 수집하고, PDF 리포트를 직접 뷰어에서 확인할 수 있는 Python 데스크톱 애플리케이션입니다.


## 주요 기능

- 📊 **리포트 자동 수집**: 네이버 증권에서 오늘 날짜의 종목 리포트를 자동으로 수집합니다
- 📄 **PDF 뷰어**: PDF 리포트를 애플리케이션 내에서 직접 확인할 수 있습니다
- ✏️ **PDF 어노테이션 도구**:
  - 형광펜: 다양한 색상의 형광펜으로 텍스트 강조 (투명도 조절 가능)
  - 선 그리기: 다양한 색상과 굵기로 선 그리기
  - 지우개: 어노테이션 삭제
  - 되돌리기: 작업 취소
- 🔍 **검색 및 필터링**: 종목명, 증권사, 투자의견 등으로 리포트 검색 및 필터링
- 📸 **PDF 캡처**: 현재 보고 있는 PDF 페이지를 이미지로 저장
- 🔎 **줌 기능**: PDF 확대/축소 기능
- 🎨 **모던 다크 테마**: 눈의 피로를 줄이는 다크 테마 UI

## 시스템 요구사항

- Python 3.10 이상
- Windows, macOS, Linux (Tkinter 지원 환경)

## 설치 방법

### 1. 저장소 클론 또는 다운로드

```bash
git clone <repository-url>
cd analyst_hub
```

또는 프로젝트 폴더로 이동합니다.

### 2. 가상환경 생성 및 활성화 (권장)

**Windows:**
```bash
python -m venv venv_analyst_hub
venv_analyst_hub\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv_analyst_hub
source venv_analyst_hub/bin/activate
```

### 3. 필요한 라이브러리 설치

```bash
pip install -r requirements.txt
```

또는:

```bash
pip install requests beautifulsoup4 lxml pymupdf pillow
```

## 사용 방법

### 애플리케이션 실행

```bash
python main.py
```

### 기본 사용법

1. **리포트 로드**: 애플리케이션 실행 시 자동으로 오늘 날짜의 리포트를 수집합니다
2. **리포트 선택**: 왼쪽 목록에서 보고 싶은 리포트를 클릭합니다
3. **PDF 보기**: 선택한 리포트의 PDF가 오른쪽 뷰어에 표시됩니다
4. **페이지 이동**: ◀ ▶ 버튼으로 페이지를 이동할 수 있습니다
5. **줌 조절**: + / − 버튼으로 확대/축소할 수 있습니다

### 어노테이션 도구 사용

1. **형광펜**: 형광펜 버튼을 클릭한 후, PDF에서 드래그하여 텍스트를 강조합니다
   - 색상 선택: 형광펜 색상 버튼을 클릭하여 색상을 변경할 수 있습니다
   - 투명도 조절: 투명도 드롭다운에서 원하는 투명도를 선택합니다

2. **선 그리기**: 선 그리기 버튼을 클릭한 후, PDF에서 드래그하여 선을 그립니다
   - 색상 선택: 선 색상 버튼을 클릭하여 색상을 변경할 수 있습니다
   - 굵기 조절: 굵기 드롭다운에서 원하는 굵기를 선택합니다

3. **지우개**: 지우개 버튼을 클릭한 후, 삭제하고 싶은 어노테이션을 클릭합니다

4. **되돌리기**: 되돌리기 버튼을 클릭하여 마지막 작업을 취소합니다

### 리포트 검색

- 상단 검색창에 종목명, 증권사명, 리포트 제목 등을 입력하여 리포트를 필터링할 수 있습니다

### PDF 캡처

- 캡처 버튼을 클릭하면 현재 보고 있는 PDF 페이지가 `data/capture/` 폴더에 이미지로 저장됩니다
- 파일명 형식: `{종목명}_{날짜}_{시간}_page{페이지번호}.png`

## 프로젝트 구조

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
│       ├── widgets.py          # 커스텀 위젯 (리포트 목록, PDF 뷰어)
│       └── app.py              # 메인 앱 클래스
├── data/
│   └── capture/                # 캡처 이미지 저장 폴더
├── README.md                   # 이 파일
└── CLAUDE.md                   # 개발 가이드
```

## 모듈 설명

### src/config.py
- 색상 팔레트 (`COLORS`)
- URL 상수 (`NAVER_BASE_URL`, `RESEARCH_URL`)
- PDF 렌더링 설정 (`PDF_RENDER_SCALE`, `ZOOM_MIN`, `ZOOM_MAX`)
- 어노테이션 설정 (형광펜/라인 색상, 투명도, 굵기)

### src/models.py
- `ReportData`: 리포트 정보 저장 dataclass
- `Annotation`: 어노테이션 정보 저장 dataclass

### src/scraper.py
- `NaverReportScraper`: 네이버 금융 리포트 스크래핑 클래스
  - `fetch_reports()`: 리포트 목록 가져오기
  - `fetch_report_meta()`: 상세 정보 가져오기

### src/pdf_handler.py
- `PDFHandler`: PDF 처리 클래스
  - `load_pdf()`: PDF 다운로드 및 로드
  - `render_page()`: 페이지 렌더링
  - `apply_annotations()`: 어노테이션 합성

### src/ui/styles.py
- `setup_styles()`: ttk 스타일 초기화
- 스타일 이름 상수 (`STYLES`)

### src/ui/widgets.py
- `ReportListWidget`: 리포트 목록 (Treeview)
- `PDFViewerWidget`: PDF 뷰어 (Canvas + 컨트롤)
- `AnnotationToolbar`: 어노테이션 도구 모음

### src/ui/app.py
- `NaverReportViewerApp`: 메인 앱 클래스
  - 위젯 조합 및 이벤트 연결

## 주요 의존성

- **requests**: HTTP 요청을 위한 라이브러리
- **beautifulsoup4**: HTML 파싱을 위한 라이브러리
- **lxml**: BeautifulSoup의 빠른 파서 (선택사항, 없으면 html.parser 사용)
- **pymupdf**: PDF 렌더링 및 조작을 위한 라이브러리
- **pillow (PIL)**: 이미지 처리 및 Tkinter 이미지 표시를 위한 라이브러리
- **tkinter**: GUI 프레임워크 (Python 기본 포함)

## 버전 정보

- **v2.0**: 프로젝트 구조 모듈화 (src/ 패키지 구조)
- **v1.0**: PDF 어노테이션 기능 추가 (형광펜, 선 그리기, 지우개, 되돌리기)
- **v0.9**: 기본 리포트 뷰어 기능

## 문제 해결

### PDF가 표시되지 않는 경우

다음 명령어로 필요한 라이브러리가 설치되어 있는지 확인하세요:

```bash
pip install pymupdf pillow
```

### 리포트가 로드되지 않는 경우

- 인터넷 연결을 확인하세요
- 네이버 증권 사이트의 구조가 변경되었을 수 있습니다

### 어노테이션이 저장되지 않는 경우

- 어노테이션은 현재 세션 동안만 유지됩니다
- PDF 파일 자체는 수정되지 않으며, 뷰어에만 표시됩니다

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 작성자

Analyst Hub 개발팀

---

**참고**: 이 애플리케이션은 네이버 증권의 공개된 정보를 수집하여 표시합니다. 사용 시 네이버의 이용약관을 준수해주세요.
