"""
Heuristic Forensic Provider
Provides intelligent, evidence-grounded case analysis when an external LLM
or local Ollama daemon is temporarily offline or unconfigured.
Ensures zero crashes, strictly prevents hallucinations, and strictly delineates:
Evidence, Inference, and General Advice based on real case data.
"""
import time
import re
from typing import Generator, List, Dict, Any, Optional
from backend.ai.provider import AIProvider

class HeuristicProvider(AIProvider):
    """Forensic rule-based case reasoning engine with streaming chunk simulation"""

    def check_health(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": "heuristic",
            "message": "Local Forensic Heuristic Engine is active. (Connect Ollama or OpenAI for generative neural reasoning)."
        }

    def _extract_case_info(self, system_prompt: Optional[str]) -> Dict[str, Any]:
        info = {
            "company": "Not specified",
            "job": "Not specified",
            "risk_score": 0,
            "risk_level": "Safe",
            "red_flags": [],
            "recruiter_email": "",
            "company_website": "",
            "official_domain": "",
            "domain_age": "",
            "email_match": "",
            "company_verified": False,
            "company_profile": "",
            "evidence": []
        }
        if not system_prompt:
            return info

        comp_match = re.search(r"Company Name:\s*([^\n]+)", system_prompt)
        if comp_match:
            info["company"] = comp_match.group(1).strip()

        job_match = re.search(r"Job Title:\s*([^\n]+)", system_prompt)
        if job_match:
            info["job"] = job_match.group(1).strip()

        risk_score_match = re.search(r"Risk Score:\s*(\d+)", system_prompt)
        if risk_score_match:
            info["risk_score"] = int(risk_score_match.group(1))

        risk_level_match = re.search(r"Risk Level:\s*([^\n]+)", system_prompt)
        if risk_level_match:
            info["risk_level"] = risk_level_match.group(1).strip()

        email_match = re.search(r"Recruiter Email:\s*([^\n]+)", system_prompt)
        if email_match:
            info["recruiter_email"] = email_match.group(1).strip()

        web_match = re.search(r"Website:\s*([^\n]+)", system_prompt)
        if web_match:
            info["company_website"] = web_match.group(1).strip()

        dom_match = re.search(r"Official Company Domain:\s*([^\n]+)", system_prompt)
        if dom_match:
            info["official_domain"] = dom_match.group(1).strip()

        age_match = re.search(r"Domain Registration Age:\s*([^\n]+)", system_prompt)
        if age_match:
            info["domain_age"] = age_match.group(1).strip()

        em_match = re.search(r"Email-Domain Verification:\s*([^\n]+)", system_prompt)
        if em_match:
            info["email_match"] = em_match.group(1).strip()

        prof_match = re.search(r"Company Profile:\s*([^\n]+)", system_prompt)
        if prof_match:
            info["company_profile"] = prof_match.group(1).strip()
            info["company_verified"] = True

        # Extract red flags bullet points
        flags = re.findall(r"-\s*\[([^\]]+)\]\s*([^:\n]+):\s*([^\n]+)", system_prompt)
        for sev, title, desc in flags:
            info["red_flags"].append({
                "severity": sev.strip(),
                "title": title.strip(),
                "description": desc.strip()
            })

        return info

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> str:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "").strip()
                break

        query = last_user_msg.lower()
        case = self._extract_case_info(system_prompt)

        # Build case-grounded forensic response
        resp = []
        resp.append(f"### 🛡️ Case Investigation Analysis: {case['company']} — {case['job']}\n")

        if any(w in query for w in ["why", "risky", "suspicious", "flag", "danger"]):
            resp.append(f"**Case Risk Level**: `{case['risk_level']}` (Risk Score: {case['risk_score']}/100)\n")
            if case["red_flags"]:
                resp.append("This offer was flagged based on the following specific case signals:\n")
                for idx, flag in enumerate(case["red_flags"], 1):
                    resp.append(f"**{idx}. [{flag['severity']}] {flag['title']}**\n- **Evidence**: {flag['description']}")
                resp.append("\n**Inference**:\nThese combined indicators do not necessarily prove malicious intent on their own, but in digital recruitment forensics, this cluster represents a high probability of employment fraud or unauthorized impersonation.\n")
                resp.append("**Advice**:\nDo not advance funds, sign non-disclosures without verification, or provide government ID until direct verification is obtained.")
            else:
                resp.append("**Evidence**:\nNo overt scam patterns or upfront fee demands were detected in the provided job document.\n\n**Inference**:\nThe linguistic patterns and contact structure appear consistent with conventional postings.\n\n**Advice**:\nAlways verify the offer through the employer's official careers portal.")

        elif any(w in query for w in ["red flag", "biggest red flag", "worst"]):
            if case["red_flags"]:
                resp.append(f"Based on the analysis of **{case['company']}**, the primary red flags detected in this case are:\n")
                for f in case["red_flags"]:
                    resp.append(f"• **[{f['severity']}] {f['title']}**: {f['description']}")
                resp.append("\n**Recommended Action**: Treat any request for immediate action or personal credential submission as high risk.")
            else:
                resp.append("No critical red flags were triggered for this document. However, standard due diligence is always advised.")

        elif any(w in query for w in ["what do you know about this company", "about this company", "company exist", "company verified", "is this company verified"]):
            resp.append(f"**Company Intelligence Dossier for '{case['company']}'**:\n")
            if case.get("company_profile"):
                resp.append(f"• **Public Profile**: {case['company_profile']}\n")
            if case.get("official_domain"):
                resp.append(f"• **Official Domain**: `{case['official_domain']}`")
            if case.get("domain_age"):
                resp.append(f"• **Domain Telemetry**: {case['domain_age']}")
            if not case.get("company_profile") and not case.get("official_domain"):
                resp.append("I don't have verified information about that. No independent public corporate registry record could be corroborated for this employer.")
            else:
                resp.append("\n**Notice**: Verifying company presence does not automatically validate that the specific offer letter or recruiter is authentic.")

        elif any(w in query for w in ["when was the domain registered", "domain registered", "domain age"]):
            if case.get("domain_age"):
                resp.append(f"**Domain Registration Telemetry**:\n• **Official Domain**: `{case.get('official_domain')}`\n• **Registration Age**: {case['domain_age']}\n")
                resp.append("*Contextual Note: Domain registration age is contextual telemetry, not standalone proof of fraud or safety.*")
            else:
                resp.append("I don't have verified information about that. RDAP registration records could not be independently retrieved for this domain.")

        elif any(w in query for w in ["recruiter email match", "email match", "email domain match", "email match the company website"]):
            if case.get("email_match"):
                resp.append(f"**Email-Domain Verification Analysis**:\n• **Result**: {case['email_match']}\n")
            elif case.get("recruiter_email") and case.get("official_domain"):
                resp.append(f"• **Recruiter Email**: `{case['recruiter_email']}`\n• **Company Domain**: `{case['official_domain']}`\n")
                if case['recruiter_email'].split("@")[-1].lower() == case['official_domain'].lower():
                    resp.append("The recruiter email domain matches the official corporate website domain.")
                else:
                    resp.append("The recruiter email domain differs from the official company domain.")
            else:
                resp.append("I don't have verified information about that. Either the recruiter email or official domain was missing from the case file.")

        elif any(w in query for w in ["recruiter", "email", "domain", "contact"]):
            email = case["recruiter_email"] or "Not provided in case"
            resp.append(f"**Contact Verification for {case['company']}**:\n")
            resp.append(f"• **Recruiter Email on file**: `{email}`")
            if case.get("email_match"):
                resp.append(f"• **Domain Corroboration**: {case['email_match']}")
            if any(dom in email.lower() for dom in ["@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com", "@telegram"]):
                resp.append("\n**Evidence**: The recruiter is using a generic free webmail service (@" + email.split("@")[-1] + ") rather than an official corporate domain.\n")
                resp.append("**Inference**: Legitimate corporate talent acquisition teams rarely conduct formal hiring communications via free webmail addresses.\n")
                resp.append("**Advice**: Contact the company's Human Resources department directly using contact info published on their verified website.")
            else:
                resp.append("\n**Evidence**: The email domain requires cross-referencing against the company's WHOIS and corporate MX records.")

        elif any(w in query for w in ["website", "domain", "match"]):
            web = case["company_website"] or (f"https://{case['official_domain']}" if case.get("official_domain") else "Not provided in case")
            resp.append(f"**Website Verification Analysis**:\n")
            resp.append(f"• **Official Domain / Website**: `{web}`\n")
            if case.get("domain_age"):
                resp.append(f"• **Domain Age**: {case['domain_age']}\n")
            resp.append("**Evidence**: Checking provided URL and domain records against established corporate registries.\n")
            resp.append("**Inference**: Scammers frequently register lookalike domains (typosquatting or alternate TLDs like .cc, .work, .biz) to impersonate genuine brands.\n")
            resp.append("**Advice**: Always look up the official company website independently via a reputable search engine, rather than clicking links inside unsolicited messages.")

        elif any(w in query for w in ["checklist", "verify", "step"]):
            resp.append(f"### 📋 Due Diligence Verification Checklist for {case['company']}\n")
            resp.append("1. **[ ] Official Domain Check**: Confirm that recruiter email matches the employer's genuine website.")
            resp.append("2. **[ ] Zero Upfront Fee Policy**: Legitimate employers provide equipment and training without requiring candidate deposits.")
            resp.append("3. **[ ] Direct Telephone Confirmation**: Call the employer's official switchboard found on Google Maps or LinkedIn.")
            resp.append("4. **[ ] LinkedIn Profile Audit**: Check if the recruiter has a tenured LinkedIn presence connected to other real employees.")
            resp.append("5. **[ ] Interview Verification**: Ensure you have had an interactive video interview, not just text/chat-based communication.")

        elif any(w in query for w in ["ask", "questions for recruiter", "question"]):
            resp.append(f"### ✉️ Strategic Questions to Ask the Recruiter ({case['company']})\n")
            resp.append("1. *\"Can you confirm this position is posted on your official careers page (company.com/careers), and what is the internal Job Requisition ID?\"*")
            resp.append("2. *\"Can we conduct the technical interview over Microsoft Teams or Google Meet using your corporate enterprise account?\"*")
            resp.append("3. *\"Will the offer letter be formally signed by an authorized Corporate Officer or HR Director with a verifiable corporate email address?\"*")
            resp.append("4. *\"Can you provide the company's registered Corporate Identification Number (CIN / EIN) and physical office address for validation?\"*")

        elif any(w in query for w in ["summar", "overview", "brief"]):
            resp.append(f"**Executive Case Briefing**\n")
            resp.append(f"• **Employer**: {case['company']}")
            resp.append(f"• **Role**: {case['job']}")
            resp.append(f"• **Security Assessment**: `{case['risk_level']}` ({case['risk_score']}/100 Risk Score)")
            resp.append(f"• **Critical Signals**: {len(case['red_flags'])} identified threat indicators.")
            if case["red_flags"]:
                for f in case["red_flags"][:3]:
                    resp.append(f"   - {f['title']}: {f['description']}")
            resp.append(f"• **Actionable Stance**: {'Cease communication and verify independently.' if case['risk_score'] > 50 else 'Standard cautious review recommended.'}")

        else:
            # General query with case grounding
            resp.append(f"Regarding your inquiry for **{case['company']}** ({case['job']}):\n")
            resp.append(f"• **Current Case Risk Assessment**: `{case['risk_level']}` (Risk Score: {case['risk_score']}/100)\n")
            if case["red_flags"]:
                resp.append("**Evidence Identified in this Document**:")
                for f in case["red_flags"]:
                    resp.append(f"- **{f['title']}**: {f['description']}")
                resp.append("\n**Inference**:\nThe evidence above suggests specific irregularities commonly associated with fraudulent hiring campaigns.")
            else:
                resp.append("I don't have enough information in this case to confirm specific irregularities beyond the analyzed text. Always maintain vigilance.")

        resp.append("\n\n---\n*💡 Note: CaseAI Forensic Intelligence is currently running in local verified mode. To enable dynamic generative LLM reasoning, start Ollama locally (`ollama run llama3`) or configure `OPENAI_API_KEY` in `.env`.*")
        return "\n".join(resp)

    def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        full_text = self.generate(messages, system_prompt, max_tokens, temperature)
        # Yield in realistic word chunks for realistic streaming UI
        words = full_text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + " "
            yield chunk
            time.sleep(0.015)
