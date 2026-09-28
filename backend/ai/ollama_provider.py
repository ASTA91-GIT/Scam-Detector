"""
Ollama Provider for Local Offline AI Inference
Primary intelligence engine for Scam Detector.
Supports local execution without external API keys, internet connection,
or cloud AI services.
"""

import os
import re
import json
import socket
import requests
from urllib.parse import urlparse
from typing import Generator, List, Dict, Any, Optional

from backend.ai.provider import AIProvider
from backend.ai.prompts import SCAM_ANALYST_SYSTEM_PROMPT, build_scam_analysis_prompt

UNAVAILABLE_MSG = "Local AI model unavailable. Start Ollama and ensure the configured model is installed."

class OllamaProvider(AIProvider):
    """Local Ollama client implementing local AI inference and structured scam analysis"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        # Preferred default is llama3.1:8b; supports llama3.2:3b or other installed models
        self.model = model or os.getenv("AI_MODEL") or "llama3.1:8b"
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    def check_health(self) -> Dict[str, Any]:
        """
        Check if local Ollama daemon is reachable and list installed models.
        Returns standardized diagnostics.
        """
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434

        # Fast socket test to prevent HTTP timeout delays
        try:
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except Exception:
            return {
                "available": False,
                "provider": "ollama",
                "model": self.model,
                "base_url": self.base_url,
                "error": UNAVAILABLE_MSG
            }

        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]

                # Match base name or exact name (e.g. llama3.1:8b or llama3.1)
                model_base = self.model.split(":")[0]
                model_present = any(self.model in m or m.startswith(model_base) for m in models)

                if model_present:
                    return {
                        "available": True,
                        "provider": "ollama",
                        "model": self.model,
                        "base_url": self.base_url,
                        "installed_models": models
                    }
                else:
                    return {
                        "available": False,
                        "provider": "ollama",
                        "model": self.model,
                        "base_url": self.base_url,
                        "installed_models": models,
                        "error": f"Model '{self.model}' is not installed in Ollama. Run 'ollama pull {self.model}' or configure an available model."
                    }

            return {
                "available": False,
                "provider": "ollama",
                "model": self.model,
                "error": f"Ollama daemon returned HTTP {res.status_code}"
            }
        except Exception as e:
            return {
                "available": False,
                "provider": "ollama",
                "model": self.model,
                "error": f"{UNAVAILABLE_MSG} ({str(e)})"
            }

    def _prepare_payload(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        stream: bool,
        response_format: Optional[str] = None
    ) -> Dict[str, Any]:
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            formatted_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if response_format:
            payload["format"] = response_format

        return payload

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        response_format: Optional[str] = None
    ) -> str:
        """Synchronous generation using Ollama"""
        payload = self._prepare_payload(
            messages,
            system_prompt,
            max_tokens,
            temperature,
            stream=False,
            response_format=response_format
        )
        try:
            res = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            res.raise_for_status()
            data = res.json()
            msg = data.get("message") or {}
            content = msg.get("content") or ""
            return content.strip()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        """Streaming generator yielding text deltas as Ollama streams them"""
        payload = self._prepare_payload(messages, system_prompt, max_tokens, temperature, stream=True)
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout
            ) as res:
                res.raise_for_status()
                for line in res.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama stream error: {str(e)}")

    def analyze_document(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Primary Scam Analysis Engine:
        1. Classifies document into functional categories (CERTIFICATE, JOB_OFFER, etc.)
        2. Executes context-aware offline LLM scam and fraud analysis.
        Strictly returns validated JSON schema adhering to forensic specifications.
        """
        health = self.check_health()
        if not health.get("available"):
            raise RuntimeError(health.get("error", UNAVAILABLE_MSG))

        # Step 1: Semantic Document Type Classification
        from backend.ai.document_classifier import classify_document_type
        doc_type, doc_type_conf, doc_type_reason = classify_document_type(
            document_text=document_text,
            metadata=metadata,
            provider=self
        )

        # Step 2: Context-Aware Scam Evaluation
        prompt = build_scam_analysis_prompt(
            document_text=document_text,
            metadata=metadata,
            document_type=doc_type,
            document_type_confidence=doc_type_conf
        )

        raw_output = self.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=SCAM_ANALYST_SYSTEM_PROMPT,
            max_tokens=2048,
            temperature=0.0,  # Deterministic forensic reasoning
            response_format="json"  # Enforces JSON output from Ollama
        )

        return self._parse_and_validate_analysis(
            raw_output=raw_output,
            classified_doc_type=doc_type,
            classified_doc_conf=doc_type_conf,
            document_text=document_text
        )

    def _parse_and_validate_analysis(
        self,
        raw_output: str,
        classified_doc_type: str = "UNKNOWN",
        classified_doc_conf: int = 80,
        document_text: str = ""
    ) -> Dict[str, Any]:
        """
        Safely extracts, parses, validates, and clamps structured output JSON.
        Prevents malformed LLM output from ever crashing the application.
        """
        from backend.ai.document_classifier import ALLOWED_DOCUMENT_TYPES

        cleaned_str = (raw_output or "").strip()

        # Remove markdown code fences if present (e.g. ```json ... ```)
        if cleaned_str.startswith("```"):
            cleaned_str = re.sub(r"^```(?:json)?\s*", "", cleaned_str)
            cleaned_str = re.sub(r"\s*```$", "", cleaned_str)

        parsed = {}
        try:
            parsed = json.loads(cleaned_str)
        except json.JSONDecodeError:
            # Fallback regex extraction of first outer JSON object
            match = re.search(r"\{.*\}", cleaned_str, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception as ex:
                    print(f"[ERROR] Failed to parse regex-extracted JSON: {ex}")
            if not parsed:
                raise ValueError(f"Model output could not be parsed as valid JSON: {cleaned_str[:200]}")

        # --- 1. Document Type & Confidence ---
        raw_type = str(parsed.get("document_type", "")).strip().upper()
        if raw_type in ALLOWED_DOCUMENT_TYPES:
            doc_type = raw_type
        else:
            doc_type = classified_doc_type if classified_doc_type in ALLOWED_DOCUMENT_TYPES else "UNKNOWN"

        raw_type_conf = parsed.get("document_type_confidence", classified_doc_conf)
        try:
            val = float(raw_type_conf)
            if val <= 1.0 and val > 0:
                val = val * 100
            doc_type_conf = max(0, min(100, int(round(val))))
        except (ValueError, TypeError):
            doc_type_conf = classified_doc_conf

        # --- 2. Clamp risk_score (0-100) ---
        raw_score = parsed.get("risk_score", 0 if doc_type == "CERTIFICATE" else 50)
        try:
            risk_score = max(0, min(100, int(round(float(raw_score)))))
        except (ValueError, TypeError):
            risk_score = 0 if doc_type == "CERTIFICATE" else 50

        # --- 3. Clamp confidence (0-100) ---
        raw_conf = parsed.get("confidence", 85)
        try:
            confidence = max(0, min(100, int(round(float(raw_conf)))))
        except (ValueError, TypeError):
            confidence = 85

        # --- 4. Validate reasoning array & prevent hallucinated evidence ---
        raw_reasoning = parsed.get("reasoning", [])
        validated_reasoning = []
        doc_lower = (document_text or "").lower()

        if isinstance(raw_reasoning, list):
            for item in raw_reasoning:
                if isinstance(item, dict):
                    sev = str(item.get("severity", "MEDIUM")).upper()
                    if sev not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                        sev = "MEDIUM"
                    try:
                        impact = max(0, min(100, int(round(float(item.get("impact_on_score", 10))))))
                    except (ValueError, TypeError):
                        impact = 10

                    finding = str(item.get("finding", "")).strip() or "Risk Pattern Detected"
                    evidence = str(item.get("evidence", "")).strip()
                    explanation = str(item.get("explanation", "")).strip() or "Identified pattern in document."

                    # Check for hallucinated evidence quote:
                    if evidence:
                        ev_clean = re.sub(r'["\']', '', evidence.lower()).strip()
                        tokens = [t for t in re.findall(r'\b\w+\b', ev_clean) if len(t) > 3]
                        if tokens and not any(t in doc_lower for t in tokens):
                            # Skip finding if evidence text does not exist in extracted document
                            continue

                    # For CERTIFICATES: discard findings that criticize lack of employment offer terms
                    if doc_type == "CERTIFICATE":
                        invalid_cert_terms = [
                            "no salary", "missing salary", "missing contract", "no job description",
                            "missing contact", "lack of contact", "job simulation title", "missing interview",
                            "lack of red flags"
                        ]
                        if any(term in finding.lower() or term in explanation.lower() for term in invalid_cert_terms):
                            continue

                    validated_reasoning.append({
                        "finding": finding,
                        "severity": sev,
                        "evidence": evidence,
                        "explanation": explanation,
                        "impact_on_score": impact
                    })

        # --- 5. Context-aware CERTIFICATE protection ---
        fee_patterns = [
            r'remit\s+.*(?:fee|deposit|\$|bitcoin|western union)',
            r'pay\s+.*(?:fee|deposit|\$|₹)',
            r'fee\s+of\s+[\$₹\d]+',
            r'payment\s+required',
            r'release\s+fee',
            r'western\s+union',
            r'bitcoin',
            r'zelle'
        ]
        has_text_payment_demand = any(re.search(p, doc_lower) for p in fee_patterns)

        if doc_type == "CERTIFICATE":
            has_explicit_fraud = any(
                r.get("severity") in ["HIGH", "CRITICAL"] and r.get("evidence")
                for r in validated_reasoning
            ) or has_text_payment_demand

            if has_text_payment_demand:
                risk_score = max(risk_score, 75)
                # Ensure a finding is recorded for the payment demand
                if not any("payment" in r.get("finding", "").lower() or "fee" in r.get("finding", "").lower() for r in validated_reasoning):
                    # Extract snippet from text
                    ev_match = re.search(r'(?:remit|pay|fee).*?(?:western union|bitcoin|\$\d+|\d+ hours)', doc_lower)
                    ev_snippet = ev_match.group(0) if ev_match else "Payment or fee required to release certificate"
                    validated_reasoning.append({
                        "finding": "Advance Fee Demand to Release Certificate",
                        "severity": "CRITICAL",
                        "evidence": ev_snippet,
                        "explanation": "Demanding payment, administrative fees, or cryptocurrency to release or verify an award is an advance-fee fraud scheme.",
                        "impact_on_score": 80
                    })
            elif not has_explicit_fraud:
                # Normal certificate with no fraudulent behavior
                risk_score = min(risk_score, 10)
                validated_reasoning = []

        # --- 6. Validate classification strictly aligned with risk_score ---
        if risk_score >= 60:
            classification = "HIGH_RISK"
        elif risk_score >= 30:
            classification = "MEDIUM_RISK"
        else:
            classification = "LOW_RISK"

        # --- 7. Validate summary ---
        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            if doc_type == "CERTIFICATE" and classification == "LOW_RISK":
                summary = "This appears to be a participation or completion certificate. No material scam indicators were identified in the supplied content."
            else:
                summary = f"Forensic analysis evaluated the document and classified it as {classification} with a risk score of {risk_score}/100."

        # --- 8. Validate positive signals ---
        raw_positives = parsed.get("positive_signals", [])
        validated_positives = []
        if isinstance(raw_positives, list):
            for item in raw_positives:
                if isinstance(item, dict):
                    f = str(item.get("finding", "")).strip()
                    if f:
                        validated_positives.append({
                            "finding": f,
                            "evidence": str(item.get("evidence", "")).strip(),
                            "explanation": str(item.get("explanation", "")).strip()
                        })

        # --- 9. Validate uncertainties ---
        raw_unc = parsed.get("uncertainties", [])
        validated_unc = []
        if isinstance(raw_unc, list):
            for u in raw_unc:
                if isinstance(u, str) and u.strip():
                    validated_unc.append(u.strip())

        if doc_type == "CERTIFICATE":
            if not any("primarily designed" in u.lower() for u in validated_unc):
                validated_unc.append("The system is primarily designed for recruitment and job-offer scam analysis.")
            if not any("authenticity" in u.lower() for u in validated_unc):
                validated_unc.append("Certificate authenticity could not be independently verified.")

        # --- 10. Validate document_assessment ---
        raw_doc_assess = parsed.get("document_assessment", {})
        if not isinstance(raw_doc_assess, dict):
            raw_doc_assess = {}
        synth = bool(raw_doc_assess.get("possible_synthetic_document", False))
        try:
            synth_conf = max(0, min(100, int(round(float(raw_doc_assess.get("confidence", 50))))))
        except (ValueError, TypeError):
            synth_conf = 50
        synth_exp = str(raw_doc_assess.get("explanation", "")).strip()

        document_assessment = {
            "possible_synthetic_document": synth,
            "confidence": synth_conf,
            "explanation": synth_exp or "Standard document linguistic structure."
        }

        # --- 11. Validate recommendations ---
        raw_recs = parsed.get("recommendations", [])
        validated_recs = []
        if isinstance(raw_recs, list):
            for r in raw_recs:
                if isinstance(r, str) and r.strip():
                    validated_recs.append(r.strip())

        if not validated_recs:
            if doc_type == "CERTIFICATE":
                validated_recs = [
                    "If required for verification, check the credential code directly via the issuing platform's official registry.",
                    "Verify the issuer's public domain before providing any personal details to third parties."
                ]
            else:
                validated_recs = [
                    "Verify recruiter identities directly through the company's official corporate directory or switchboard.",
                    "Never send advance fees, security deposits, or cryptocurrency for employment equipment.",
                    "Review offer details with independent contacts before signing or disclosing sensitive personal data."
                ]

        return {
            "document_type": doc_type,
            "document_type_confidence": doc_type_conf,
            "risk_score": risk_score,
            "confidence": confidence,
            "classification": classification,
            "summary": summary,
            "reasoning": validated_reasoning,
            "positive_signals": validated_positives,
            "uncertainties": validated_unc,
            "document_assessment": document_assessment,
            "recommendations": validated_recs,
            "model_name": self.model
        }
