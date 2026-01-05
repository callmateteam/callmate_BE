# 프롬프트 관리 가이드

## 개요

이 디렉토리는 LLM에 전달되는 프롬프트를 마크다운 파일로 관리합니다.

### 왜 마크다운으로 관리하는가?

✅ **유지보수성**: 코드 수정 없이 프롬프트만 변경 가능
✅ **버전 관리**: Git으로 프롬프트 변경 이력 추적
✅ **협업**: 개발자가 아니어도 프롬프트 수정 가능
✅ **테스트**: 여러 버전의 프롬프트를 쉽게 A/B 테스트
✅ **가독성**: 마크다운 문법으로 구조화된 프롬프트 작성

---

## 디렉토리 구조

```
prompts/
├── common/
│   └── system.md              # 공통 시스템 프롬프트
├── call_analysis/
│   ├── summarize.md           # 통화 요약 프롬프트
│   └── recommend_replies.md   # 추천 멘트 생성 프롬프트
└── README.md
```

---

## 프롬프트 파일 형식

### 변수 사용
프롬프트에서 동적 값은 `{{variable_name}}` 형식으로 작성합니다.

```markdown
통화 내용: {{transcript}}
영업 유형: {{sales_type}}
```

### 구조 권장사항
```markdown
# 프롬프트 제목

## 역할
AI의 역할 정의

## 입력 정보
- 변수1: {{variable1}}
- 변수2: {{variable2}}

## 분석/작업 목표
무엇을 해야 하는지 상세히 설명

## 출력 형식
원하는 출력 형식 예시

## 주의사항
지켜야 할 규칙
```

---

## 코드에서 사용하기

### 1. 기본 사용법

```python
from app.core.prompt_manager import get_prompt

# 변수 없이 로드
prompt = get_prompt("common/system.md")

# 변수와 함께 렌더링
prompt = get_prompt(
    "call_analysis/summarize.md",
    {
        "transcript": "안녕하세요...",
        "sales_type": "insurance",
        "conversation_goal": "follow_up"
    }
)
```

### 2. 서비스에서 사용

```python
from app.core.prompt_manager import get_prompt
import openai

# 프롬프트 로드
system_prompt = get_prompt("common/system.md")
user_prompt = get_prompt(
    "call_analysis/summarize.md",
    {"transcript": transcript, "sales_type": "insurance"}
)

# OpenAI 호출
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)
```

---

## 프롬프트 작성 가이드라인

### 1. 명확한 역할 정의
```markdown
## 역할
당신은 영업 통화 전문 분석가입니다.
```

### 2. 구체적인 지시사항
❌ 나쁜 예:
```markdown
통화를 분석하세요.
```

✅ 좋은 예:
```markdown
통화 내용을 분석하여:
1. 고객의 핵심 니즈를 한 문장으로 추출
2. 반대 의견을 배열로 나열
3. 결정 단계를 4가지 중 선택
```

### 3. 명확한 출력 형식
```markdown
## 출력 형식
JSON 형식으로 출력하세요:

\`\`\`json
{
  "customer_needs": "...",
  "objections": ["..."]
}
\`\`\`
```

### 4. 예시 제공
```markdown
## 좋은 응답 예시
- "고객은 가족 건강 보장에 관심이 있습니다."

## 나쁜 응답 예시
- "고객이 보험에 관심 있어 보입니다." (너무 모호함)
```

### 5. 금지 사항 명시
```markdown
## 주의사항
- 통화 내용에 없는 정보를 추측하지 마세요
- 과장된 표현을 사용하지 마세요
```

---

## 프롬프트 수정 워크플로우

### 1. 개발 중 수정
```bash
# 1. 프롬프트 파일 수정
vim prompts/call_analysis/summarize.md

# 2. 서버 재시작 불필요 (자동 리로드)
# 단, 캐시 사용 시 Python 코드에서 reload 필요
```

### 2. 캐시 클리어
```python
from app.core.prompt_manager import prompt_manager

# 모든 캐시 클리어
prompt_manager.clear_cache()

# 특정 프롬프트만 리로드
prompt_manager.reload_prompt("call_analysis/summarize.md")
```

### 3. A/B 테스트
```bash
# 버전별 프롬프트 관리
prompts/call_analysis/
├── summarize.md           # 현재 버전
├── summarize_v2.md        # 테스트 버전
└── summarize_old.md       # 이전 버전 (백업)
```

---

## 변수 네이밍 규칙

### 표준 변수명
- `transcript`: 통화 전사 텍스트
- `sales_type`: 영업 유형 (insurance, real_estate, b2b)
- `conversation_goal`: 대화 목표 (follow_up, objection_handling, close)
- `tone`: 톤 (friendly, professional, persuasive)
- `customer_needs`: 고객 니즈
- `objections`: 반대 의견
- `decision_stage`: 결정 단계

### 신규 변수 추가 시
1. 소문자 + 언더스코어 형식 사용 (`new_variable`)
2. 의미가 명확한 이름 사용
3. 프롬프트 파일의 "입력 정보" 섹션에 문서화

---

## 버전 관리

### Git 커밋 메시지 규칙
```bash
# 프롬프트 신규 추가
git commit -m "prompt: add call coaching prompt"

# 프롬프트 수정
git commit -m "prompt: improve summarize accuracy by adding examples"

# 프롬프트 삭제
git commit -m "prompt: remove deprecated objection handling prompt"
```

### 변경 이력 추적
```bash
# 특정 프롬프트의 변경 이력 확인
git log -- prompts/call_analysis/summarize.md

# 프롬프트 변경 내용 확인
git diff HEAD~1 prompts/call_analysis/summarize.md
```

---

## 성능 최적화

### 1. 프롬프트 길이
- 너무 긴 프롬프트는 토큰 비용 증가
- 핵심만 간결하게 작성
- 불필요한 예시는 제거

### 2. 캐싱
```python
# 캐싱 활성화 (기본값)
prompt = get_prompt("common/system.md")  # 캐시 사용

# 캐싱 비활성화 (개발 중)
prompt = prompt_manager.load_prompt("common/system.md", use_cache=False)
```

### 3. 토큰 계산
```python
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4")
tokens = encoding.encode(prompt)
print(f"Token count: {len(tokens)}")
```

---

## 문제 해결

### Q: 프롬프트 변경이 반영되지 않아요
A: 캐시를 클리어하세요
```python
from app.core.prompt_manager import prompt_manager
prompt_manager.clear_cache()
```

### Q: 변수가 치환되지 않아요
A: 변수 이름과 중괄호 형식을 확인하세요
```markdown
올바름: {{transcript}}
틀림: {transcript}, {{ transcript }}, {{Transcript}}
```

### Q: JSON 파싱 에러가 발생해요
A: 프롬프트에서 JSON 형식을 명확히 요구하고, 예시를 제공하세요
```markdown
반드시 JSON 형식만 출력하세요 (설명 제외)
```

---

## 참고 자료

- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/claude/docs/prompt-engineering)
