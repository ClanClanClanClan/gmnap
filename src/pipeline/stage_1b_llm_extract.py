"""
GMNAP v7.0 Pipeline Stage 1b: LLM Extraction for ETD
Handles LLM-based extraction for Electronic Theses and Dissertations.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from ..core.ai_intelligence import AIIntelligence
from ..core.errors import ExtractionError


class LLMExtractETDStage:
    """Stage 1b: LLM extraction for Electronic Theses and Dissertations"""

    def __init__(self):
        """Initialize LLM extraction stage"""
        self.ai_intelligence = AIIntelligence()
        self.etd_patterns = {
            "title": [
                r"title[:\s]*(.+?)(?:\n|$)",
                r"dissertation[:\s]+(.+?)(?:\n|$)",
                r"thesis[:\s]+(.+?)(?:\n|$)",
            ],
            "author": [
                r"author[:\s]*(.+?)(?:\n|$)",
                r"by[:\s]+(.+?)(?:\n|$)",
                r"candidate[:\s]*(.+?)(?:\n|$)",
            ],
            "advisor": [
                r"advisor[:\s]*(.+?)(?:\n|$)",
                r"supervisor[:\s]*(.+?)(?:\n|$)",
                r"committee[:\s]+chair[:\s]*(.+?)(?:\n|$)",
            ],
            "institution": [
                r"university[:\s]*(.+?)(?:\n|$)",
                r"institution[:\s]*(.+?)(?:\n|$)",
                r"college[:\s]*(.+?)(?:\n|$)",
            ],
        }

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from ETD documents using LLM

        Args:
            context: Pipeline execution context with raw data

        Returns:
            Updated context with extracted ETD data
        """
        try:
            raw_data = context.get("raw_data", [])
            config = context.get("config", {})

            # Check if LLM extraction is enabled
            pipeline_config = config.get("pipeline", {})
            if not pipeline_config.get("enable_llm_extraction", False):
                # Skip this stage if LLM extraction is disabled
                context["stage_1b_completed"] = True
                context["llm_extraction_skipped"] = True
                return context

            # Filter for ETD documents
            etd_documents = self._identify_etd_documents(raw_data)

            if not etd_documents:
                # No ETD documents found, skip processing
                context["stage_1b_completed"] = True
                context["etd_documents_found"] = 0
                return context

            # Extract structured data from ETD documents
            extracted_data = []
            for doc in etd_documents:
                extracted = self._extract_from_etd(doc)
                if extracted:
                    extracted_data.append(extracted)

            # Merge extracted data with raw data
            enhanced_data = raw_data + extracted_data

            # Update context
            context["raw_data"] = enhanced_data
            context["stage_1b_completed"] = True
            context["etd_documents_found"] = len(etd_documents)
            context["etd_records_extracted"] = len(extracted_data)

            return context

        except Exception as e:
            raise ExtractionError(f"Stage 1b LLM extraction failed: {str(e)}")

    def _identify_etd_documents(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify documents that are likely ETDs (theses/dissertations)"""
        etd_documents = []

        etd_keywords = [
            "thesis",
            "dissertation",
            "phd",
            "ph.d",
            "doctoral",
            "master",
            "masters",
            "graduate",
            "undergraduate",
            "committee",
            "advisor",
            "supervisor",
            "defended",
        ]

        for record in data:
            # Check for ETD indicators in various fields
            text_content = self._extract_text_content(record)
            text_lower = text_content.lower()

            # Count ETD keyword matches
            keyword_matches = sum(
                1 for keyword in etd_keywords if keyword in text_lower
            )

            # Consider it an ETD if multiple keywords are present
            if keyword_matches >= 2:
                etd_documents.append(record)

        return etd_documents

    def _extract_text_content(self, record: Dict[str, Any]) -> str:
        """Extract all text content from a record for analysis"""
        text_parts = []

        # Common fields that might contain text
        text_fields = ["title", "abstract", "description", "content", "text", "body"]

        for field in text_fields:
            if field in record and isinstance(record[field], str):
                text_parts.append(record[field])

        return " ".join(text_parts)

    def _extract_from_etd(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract structured data from an ETD document"""
        try:
            text_content = self._extract_text_content(document)

            # Try pattern-based extraction first
            extracted = self._pattern_based_extraction(text_content)

            # If pattern extraction is insufficient, use LLM
            if self._needs_llm_extraction(extracted):
                extracted = self._llm_based_extraction(text_content, extracted)

            # Validate and format the extracted data
            if self._validate_extraction(extracted):
                return self._format_extracted_data(extracted, document)

            return None

        except Exception as e:
            logger.warning(f"ETD extraction failed for document: {str(e)}")
            return None

    def _pattern_based_extraction(self, text: str) -> Dict[str, Any]:
        """Extract data using regular expression patterns"""
        extracted = {}

        for field, patterns in self.etd_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    extracted[field] = match.group(1).strip()
                    break

        return extracted

    def _needs_llm_extraction(self, extracted: Dict[str, Any]) -> bool:
        """Determine if LLM extraction is needed based on pattern extraction results"""
        # Use LLM if critical fields are missing
        critical_fields = ["author", "title"]
        missing_critical = any(
            field not in extracted or not extracted[field] for field in critical_fields
        )

        # Or if we have very little information
        return missing_critical or len(extracted) < 2

    def _llm_based_extraction(
        self, text: str, initial_extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to extract structured data from text"""
        try:
            # Prepare prompt for LLM
            prompt = self._create_extraction_prompt(text, initial_extracted)

            # Get LLM response
            response = self.ai_intelligence.extract_structured_data(prompt)

            # Parse and merge with initial extraction
            llm_extracted = self._parse_llm_response(response)

            # Merge with initial extraction (LLM takes precedence for conflicts)
            merged = initial_extracted.copy()
            merged.update(llm_extracted)

            return merged

        except Exception as e:
            logger.warning(
                f"LLM extraction failed, using pattern-based results: {str(e)}"
            )
            return initial_extracted

    def _create_extraction_prompt(
        self, text: str, initial_extracted: Dict[str, Any]
    ) -> str:
        """Create a prompt for LLM extraction"""
        prompt = f"""
Extract structured information from this academic document text:

{text[:2000]}...

Please identify and extract:
1. Author name(s)
2. Document title
3. Advisor/supervisor name(s)
4. Institution/university
5. Degree type (PhD, Master's, etc.)
6. Department/field of study

Current extracted data: {initial_extracted}

Return the information in JSON format with keys: author, title, advisor, institution, degree, department.
"""
        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract structured data"""
        try:
            import json

            # Try to parse as JSON
            return json.loads(response)
        except (ValueError, KeyError):
            # Fallback to pattern-based parsing of the response
            return self._pattern_based_extraction(response)

    def _validate_extraction(self, extracted: Dict[str, Any]) -> bool:
        """Validate that extraction contains useful information"""
        if not extracted:
            return False

        # Must have at least author or title
        has_author = "author" in extracted and extracted["author"]
        has_title = "title" in extracted and extracted["title"]

        return has_author or has_title

    def _format_extracted_data(
        self, extracted: Dict[str, Any], original: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format extracted data into standard record format"""
        record = {
            "GlobalID": f"etd_{hash(str(extracted))}",
            "source": "llm_etd_extraction",
            "extraction_method": "stage_1b_llm",
            "original_record": original.get("id", "unknown"),
        }

        # Map extracted fields to standard format
        if "author" in extracted:
            record["CanonicalLatin"] = extracted["author"]

        if "title" in extracted:
            record["DocumentTitle"] = extracted["title"]

        if "advisor" in extracted:
            record["Advisor"] = extracted["advisor"]

        if "institution" in extracted:
            record["Institution"] = extracted["institution"]

        if "degree" in extracted:
            record["DegreeType"] = extracted["degree"]

        if "department" in extracted:
            record["Department"] = extracted["department"]

        return record
