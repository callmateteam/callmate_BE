"""Company-specific prompt management service"""

from typing import Dict, List, Optional
from pathlib import Path
import json
from app.core.prompt_manager import get_prompt
from app.services.pdf_service import pdf_service
from app.services.industry_script_service import industry_script_service


class CompanyPromptService:
    """Manages company-specific prompts and scripts"""

    def __init__(self, base_path: str = "company_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache for companies and their configs
        self._companies: Dict[str, Dict] = {}
        self._scripts: Dict[str, List[Dict]] = {}  # company_id -> scripts
        self._prompt_contexts: Dict[str, str] = {}  # company_id -> generated context

    def register_company(
        self,
        company_id: str,
        name: str,
        industry: str,
        config: Optional[Dict] = None
    ) -> Dict:
        """
        Register a new company

        Args:
            company_id: Unique company identifier
            name: Company name
            industry: Industry type
            config: Additional configuration

        Returns:
            Company data
        """
        company_dir = self.base_path / company_id
        company_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (company_dir / "scripts").mkdir(exist_ok=True)
        (company_dir / "prompts").mkdir(exist_ok=True)

        company_data = {
            "id": company_id,
            "name": name,
            "industry": industry,
            "config": config or {},
            "scripts": []
        }

        # Save config
        config_path = company_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(company_data, f, ensure_ascii=False, indent=2)

        self._companies[company_id] = company_data
        self._scripts[company_id] = []

        return company_data

    def get_company(self, company_id: str) -> Optional[Dict]:
        """Get company data"""
        if company_id in self._companies:
            return self._companies[company_id]

        # Try to load from disk
        config_path = self.base_path / company_id / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                company_data = json.load(f)
            self._companies[company_id] = company_data
            return company_data

        return None

    def add_script(
        self,
        company_id: str,
        script_id: str,
        name: str,
        script_type: str,
        file_path: str,
        description: Optional[str] = None
    ) -> Dict:
        """
        Add a script PDF to company

        Args:
            company_id: Company ID
            script_id: Script unique ID
            name: Script name
            script_type: Type (sales, support, etc.)
            file_path: Path to PDF file
            description: Optional description

        Returns:
            Script data with parsed content
        """
        # Parse PDF
        parsed = pdf_service.parse_script_pdf(file_path)

        company = self.get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        script_data = {
            "id": script_id,
            "company_id": company_id,
            "name": name,
            "script_type": script_type,
            "file_path": file_path,
            "description": description,
            "key_phrases": parsed["key_phrases"],
            "sections": parsed["sections"],
            "word_count": parsed["word_count"],
            "page_count": parsed["page_count"]
        }

        # Store
        if company_id not in self._scripts:
            self._scripts[company_id] = []
        self._scripts[company_id].append(script_data)

        # Regenerate prompt context
        self._regenerate_prompt_context(company_id)

        return script_data

    def _regenerate_prompt_context(self, company_id: str):
        """Regenerate prompt context from all scripts"""
        company = self.get_company(company_id)
        if not company:
            return

        scripts = self._scripts.get(company_id, [])
        if not scripts:
            self._prompt_contexts[company_id] = ""
            return

        context_parts = [
            f"# {company['name']} 영업 스크립트 가이드",
            f"업종: {company['industry']}",
            ""
        ]

        for script in scripts:
            context_parts.append(f"## [{script['script_type']}] {script['name']}")

            if script.get("description"):
                context_parts.append(f"설명: {script['description']}")

            if script.get("key_phrases"):
                context_parts.append("\n### 권장 멘트")
                for i, phrase in enumerate(script["key_phrases"][:15], 1):
                    context_parts.append(f"{i}. \"{phrase}\"")

            if script.get("sections"):
                context_parts.append("\n### 상황별 스크립트")
                for section_name, content in script["sections"].items():
                    context_parts.append(f"\n#### {section_name}")
                    if len(content) > 300:
                        content = content[:300] + "..."
                    context_parts.append(content)

            context_parts.append("")

        self._prompt_contexts[company_id] = "\n".join(context_parts)

    def get_prompt_context(self, company_id: str) -> str:
        """
        Get the generated prompt context for a company

        Args:
            company_id: Company ID

        Returns:
            Prompt context string (empty if no scripts)
        """
        if company_id in self._prompt_contexts:
            return self._prompt_contexts[company_id]

        # Try to regenerate
        self._regenerate_prompt_context(company_id)
        return self._prompt_contexts.get(company_id, "")

    def get_analysis_prompt(
        self,
        company_id: Optional[str],
        base_prompt_path: str = "call_analysis/comprehensive_analysis.md",
        variables: Dict = None,
        industry: Optional[str] = None
    ) -> str:
        """
        Get the appropriate analysis prompt

        Args:
            company_id: Company ID (None for general/free tier)
            base_prompt_path: Base prompt template path
            variables: Variables to inject
            industry: Industry type for free tier (used when company_id is None)

        Returns:
            Final prompt string
        """
        # Get base prompt
        base_prompt = get_prompt(base_prompt_path, variables or {})

        # Case 1: SaaS customer with company_id
        if company_id:
            company = self.get_company(company_id)
            if not company:
                # Fallback to free tier with industry
                return self._add_industry_context(base_prompt, industry)

            # Get company-specific context from uploaded PDFs
            company_context = self.get_prompt_context(company_id)

            if not company_context:
                # Company exists but no scripts uploaded yet
                # Use industry-specific default script
                industry_context = industry_script_service.get_industry_context_for_prompt(
                    company["industry"]
                )
                company_section = f"""
## 회사별 맞춤 정보

이 분석은 **{company['name']}** ({company['industry']}) 고객을 위한 것입니다.

아직 회사 스크립트가 업로드되지 않아 업종별 기본 스크립트를 사용합니다:

{industry_context}

**중요**: 추천 멘트는 위 스크립트의 톤과 스타일을 참고하세요.
"""
            else:
                # Company has uploaded scripts - use those
                company_section = f"""
## 회사별 맞춤 정보

이 분석은 **{company['name']}** ({company['industry']}) 고객을 위한 것입니다.

아래 회사 스크립트를 참고하여 추천 멘트를 생성하세요:

{company_context}

**중요**: 추천 멘트는 위 스크립트의 톤과 스타일을 따라야 합니다.
회사 스크립트에 있는 문구를 우선적으로 활용하세요.
"""

            return self._inject_context(base_prompt, company_section)

        # Case 2: Free tier (no company_id)
        return self._add_industry_context(base_prompt, industry)

    def _add_industry_context(self, base_prompt: str, industry: Optional[str]) -> str:
        """Add industry-specific context for free tier users"""
        industry_context = industry_script_service.get_industry_context_for_prompt(
            industry or "other"
        )

        if not industry_context:
            return base_prompt

        industry_section = f"""
## 업종별 참고 정보

{industry_context}

**참고**: 위 업종별 스크립트를 참고하여 상황에 맞는 추천 멘트를 생성하세요.
"""
        return self._inject_context(base_prompt, industry_section)

    def _inject_context(self, base_prompt: str, context_section: str) -> str:
        """Inject context section before output format in prompt"""
        if "## 출력 형식" in base_prompt:
            parts = base_prompt.split("## 출력 형식")
            return parts[0] + context_section + "\n## 출력 형식" + parts[1]
        return base_prompt + "\n" + context_section

    def get_company_scripts(self, company_id: str) -> List[Dict]:
        """Get all scripts for a company"""
        return self._scripts.get(company_id, [])

    def delete_script(self, company_id: str, script_id: str) -> bool:
        """Delete a script"""
        if company_id not in self._scripts:
            return False

        scripts = self._scripts[company_id]
        self._scripts[company_id] = [s for s in scripts if s["id"] != script_id]

        # Regenerate context
        self._regenerate_prompt_context(company_id)

        return True


# Global instance
company_prompt_service = CompanyPromptService()
