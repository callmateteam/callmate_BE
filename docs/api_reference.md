# CallMate API Reference

> CallMate 백엔드 API 전체 문서
> Base URL: `http://localhost:8000/api/v1`

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [Transcripts API](#2-transcripts-api) - 음성 업로드 및 STT
3. [Analysis API](#3-analysis-api) - AI 분석
4. [Scripts API](#4-scripts-api) - 스크립트 추출
5. [Companies API](#5-companies-api) - 회사 관리
6. [에러 코드](#6-에러-코드)

---

## 1. 시스템 개요

### CallMate란?
영업 통화를 AI로 분석하여 **감정 분석**, **니즈 파악**, **추천 멘트**를 제공하는 서비스입니다.

### 핵심 기능

| 기능 | 설명 |
|-----|------|
| 음성 → 텍스트 | AssemblyAI로 화자분리 + STT |
| 감정 분석 | 고객/상담사 감정 점수화 |
| 니즈 파악 | 고객이 원하는 것 추출 |
| 대화 흐름 | 핵심 전환점 분석 |
| 추천 멘트 | 다음에 할 말 제안 |

---

## 2. Transcripts API

### 2.1 음성 파일 업로드

```
POST /transcripts/upload
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
|-----|-----|-----|------|
| file | File | ✅ | 음성 파일 (mp3, wav, m4a) |
| company_id | string | ❌ | SaaS 고객 회사 ID |
| industry | string | ❌ | 업종 (무료 사용자용) |

**지원 업종:** `insurance`, `real_estate`, `b2b`, `telecom`, `finance`, `other`

---

## 3. Analysis API

### 3.1 종합 분석

```
GET /analysis/comprehensive?transcript_id=xxx
```

| 파라미터 | 타입 | 필수 | 설명 |
|---------|-----|-----|------|
| transcript_id | string | ✅ | 전사 ID |
| company_id | string | ❌ | 회사 ID |
| industry | string | ❌ | 업종 |
| script_context | string | ❌ | 스크립트 컨텍스트 |

---

## 4. Scripts API

### 4.1 마크다운에서 추출

```
POST /scripts/extract/markdown
```

```json
{
  "markdown_text": "# 회사명\n\n## 인사말\n- \"안녕하세요\"",
  "company_name": "ABC보험"
}
```

### 4.2 PDF에서 추출

```
POST /scripts/extract/pdf
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
|-----|-----|-----|------|
| file | File | ✅ | PDF 파일 (최대 10MB) |
| company_name | string | ❌ | 회사명 |

### 4.3 마크다운 템플릿

```
GET /scripts/template/markdown
```

---

## 5. Companies API

### 5.1 회사 등록

```
POST /companies
```

```json
{
  "name": "ABC보험",
  "industry": "insurance",
  "plan": "pro"
}
```

---

## 6. 에러 코드

| 코드 | 의미 |
|-----|------|
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 422 | 유효성 검사 실패 |
| 500 | 서버 오류 |
