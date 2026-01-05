# CallMate Backend API

> 영업 통화 내용을 분석하고, 다음 대응 멘트를 추천하는 AI 백엔드 서비스

## 프로젝트 구조

```
callmate_BE/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── calls.py          # 통화 관련 엔드포인트
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py             # 설정 관리
│   ├── models/                   # DB 모델 (추후 추가)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── call.py               # Pydantic 스키마
│   ├── services/                 # 비즈니스 로직 (추후 추가)
│   ├── __init__.py
│   └── main.py                   # FastAPI 앱 진입점
├── tests/                        # 테스트 코드
├── uploads/                      # 업로드 파일 저장 (자동 생성)
├── .env.example                  # 환경 변수 예시
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 기술 스택

- **Framework**: FastAPI 0.109.0
- **Python**: 3.11+
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **AI/ML**: OpenAI API (Whisper STT, GPT-4)
- **Server**: Uvicorn

## 설치 및 실행

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 필수 값 입력
```

필수 환경 변수:
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `OPENAI_API_KEY`: OpenAI API 키
- `SECRET_KEY`: JWT 시크릿 키 (랜덤 문자열)

### 2. 로컬 실행 (Python)

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload
```

서버 접속: http://localhost:8000

### 3. Docker 실행 (권장)

```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 중지
docker-compose down
```

## API 문서

서버 실행 후 자동 생성되는 API 문서:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 주요 엔드포인트

### 1. Health Check
```
GET /health
```

### 2. 통화 업로드
```
POST /api/v1/calls/upload
Content-Type: multipart/form-data

파일: audio file (mp3, wav, m4a)
```

### 3. 통화 분석
```
POST /api/v1/calls/analyze
{
  "call_id": "string"
}
```

응답 예시:
```json
{
  "call_id": "abc123",
  "call_summary": {
    "customer_needs": "보험 상품 비교 관심",
    "objections": ["가격 부담", "결정 보류"],
    "decision_stage": "검토 단계"
  },
  "next_action": "후속 전화 제안",
  "recommended_replies": [
    "안녕하세요, 지난번 말씀하신 보험 상품 비교 자료 준비했습니다.",
    "가격 관련해서 더 나은 옵션을 찾아봤어요."
  ]
}
```

## 개발 로드맵

### MVP 완료 항목
- [x] FastAPI 기본 구조
- [x] 통화 업로드 엔드포인트
- [x] 분석 응답 스키마
- [x] Docker 환경 구성

### 다음 단계
- [ ] STT (Speech-to-Text) 구현
- [ ] LLM 기반 요약 및 멘트 생성
- [ ] Database 모델 및 ORM
- [ ] 파일 업로드 저장 로직
- [ ] MCP 서버 구현
- [ ] 인증/권한 시스템
- [ ] CRM 연동 API

## 테스트

```bash
# 테스트 실행 (추후 구현)
pytest

# 커버리지 확인
pytest --cov=app
```

## 배포

```bash
# Docker 이미지 빌드
docker build -t callmate-api:latest .

# 프로덕션 실행
docker-compose -f docker-compose.prod.yml up -d
```

## 라이선스

MIT

## 기여

Pull Request 환영합니다!
