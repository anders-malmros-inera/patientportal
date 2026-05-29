import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from ..schemas import Prescription


@dataclass(frozen=True)
class ParsedScrapeResult:
    personnummer: str | None
    printed_at: str | None
    high_cost_period_end: date | None
    raw_document_text: str
    prescriptions: list[Prescription]


class ScrapeParserService:
    _stop_phrases = (
        "lakemedel",
        "verksamt amne",
        "patient formansberattigad",
        "lakare",
        "galler tom",
        "minsta tid mellan",
        "nasta uttag",
        "listan galler ej",
        "kalla",
    )

    _unit_pattern = r"(?:kapse[l1i](?:/kapse[l1i]ar)?|kapse[l1i]ar|tablett(?:\(er\)|er)?)"
    _date_pattern = r"\d{4}[-/]\d{2}[-/]\d{2}"
    _prescriber_pattern = re.compile(r"([A-ZÅÄÖ][A-Za-zÅÄÖåäö\-\s]+),,\s*Läkare")
    _package_row_pattern = re.compile(r"^[\dOil]+\s*[xX]\s*[\dOil]+")
    _token_pattern = re.compile(r"^[A-ZÅÄÖa-zåäö][A-Za-zÅÄÖåäö-]+")
    _line_token_pattern = re.compile(r"^[A-Za-zÅÄÖåäö][A-Za-zÅÄÖåäö-]+$")
    _refill_pattern = re.compile(r"^\d+\s+av\s+\d+")
    _parenthesized_pattern = re.compile(r"^\([^)]+\)$")
    _person_identity_pattern = re.compile(r",\s*[\dOil]{8}(?:[\dOil]{4})?\b")
    _product_unit_tokens = ("kapsel", "tablett", "filmdragerad")
    _label_starts_active_substance = ("ej", "patient", "galler", "minsta", "utskrivet", "listan")
    _label_starts_medication_name = ("ej", "patient", "galler", "minsta")
    _ignored_medication_tokens = {"aktuella", "recept", "forskrivet", "anvandning"}
    _ignored_active_substance_tokens = {"lakemedel", "verksamt", "patient", "galler", "aktuella", "recept", "utskrivet"}
    _valid_until_pattern = re.compile(
        r"g[aä]ll?er\s*t\.?\s*o\.?\s*m\.?\s*:?\s*([0-9oOil]{4}[-/][0-9oOil]{2}[-/][0-9oOil]{2})",
        flags=re.IGNORECASE,
    )

    def parse(self, raw_text: str) -> ParsedScrapeResult:
        text = self._normalize_line_breaks(raw_text)
        personnummer = self._extract_personnummer(text)
        printed_at = self._extract_printed_at(text)
        high_cost_period_end = self._extract_high_cost_period_end(text)
        blocks = self._split_medication_blocks(text)

        prescriptions: list[Prescription] = []
        for index, block in enumerate(blocks, start=1):
            parsed = self._parse_block(block, index, printed_at, high_cost_period_end)
            if parsed is not None:
                prescriptions.append(parsed)

        if not prescriptions:
            raise ValueError("Kunde inte tolka några läkemedel från filen")

        return ParsedScrapeResult(
            personnummer=personnummer,
            printed_at=printed_at,
            high_cost_period_end=high_cost_period_end,
            raw_document_text=text,
            prescriptions=prescriptions,
        )

    @staticmethod
    def _normalize_line_breaks(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _fold_text(value: str) -> str:
        lowered = value.casefold()
        normalized = unicodedata.normalize("NFKD", lowered)
        ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", ascii_only).strip()

    @staticmethod
    def _ocr_digit_fix(value: str) -> str:
        return value.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"}))

    def _parse_date_token(self, value: str) -> date:
        cleaned = self._ocr_digit_fix(value.strip()).replace("/", "-")
        return date.fromisoformat(cleaned)

    def _is_stop_line(self, line: str) -> bool:
        folded = self._fold_text(line)
        if not folded:
            return True
        return any(phrase in folded for phrase in self._stop_phrases)

    @staticmethod
    def _non_empty_lines(block: str) -> list[str]:
        return [line.strip() for line in block.splitlines() if line.strip()]

    def _contains_date(self, line: str) -> bool:
        return bool(re.search(self._date_pattern, line))

    def _is_refill_summary_line(self, line: str) -> bool:
        return bool(self._refill_pattern.match(line))

    def _is_parenthesized_line(self, line: str) -> bool:
        return bool(self._parenthesized_pattern.match(line))

    def _is_recent_dispense_line(self, line: str) -> bool:
        return "," in line and self._contains_date(line)

    def _is_labeled_line(self, line: str, labels: tuple[str, ...]) -> bool:
        folded = self._fold_text(line)
        return any(folded.startswith(label) for label in labels)

    def _is_patient_identity_line(self, line: str) -> bool:
        return bool(self._person_identity_pattern.search(line))

    def _extract_personnummer(self, text: str) -> str | None:
        match = re.search(r",\s*([\dOil]{8}(?:[\dOil]{4})?)\b", text)
        if not match:
            return None
        return self._ocr_digit_fix(match.group(1))

    def _extract_printed_at(self, text: str) -> str | None:
        match = re.search(r"Utskrivet\s*:\s*([^\n]+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    def _extract_high_cost_period_end(self, text: str) -> date | None:
        match = re.search(
            r"H[öo]gkostnadsperiod\s*t\.?o\.?m\s*:?\s*([0-9oOil]{4}[-/][0-9oOil]{2}[-/][0-9oOil]{2})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        try:
            return self._parse_date_token(match.group(1))
        except ValueError:
            return None

    def _split_medication_blocks(self, text: str) -> list[str]:
        start = re.search(r"läkemedel|lakemedel", text, flags=re.IGNORECASE)
        relevant = text[start.start():] if start else text

        matches = list(self._valid_until_pattern.finditer(relevant))
        if not matches:
            return []

        blocks: list[str] = []
        previous_index = 0
        for match in matches:
            blocks.append(relevant[previous_index:match.end()])
            previous_index = match.end()
        return blocks

    def _parse_block(
        self,
        block: str,
        index: int,
        printed_at: str | None,
        high_cost_period_end: date | None,
    ) -> Prescription | None:
        valid_until_match = self._valid_until_pattern.search(block)
        if not valid_until_match:
            return None

        valid_until = self._parse_date_token(valid_until_match.group(1))
        prescribed_product = self._extract_prescribed_product(block)
        active_substance_name = self._extract_medication_name(block)
        medication_name = self._build_display_medication_name(active_substance_name, prescribed_product)
        product_based_substance = self._extract_active_substance_from_product(medication_name)
        active_substance = self._extract_active_substance(block, product_based_substance or active_substance_name)
        dispensed_product = self._extract_dispensed_product(block)
        prescriber_name = self._extract_prescriber_name(block)
        prescriber_organization = self._extract_prescriber_organization(block)
        prescriber_location = self._extract_prescriber_location(block)
        prescriber_phone = self._extract_prescriber_phone(block)
        package_size = self._extract_package_size(block)
        package_text = self._extract_package_text(block)
        remaining_packages = self._extract_remaining_packages(block)
        refill_remaining, refill_total = self._extract_refill_info(block)
        latest_dispense_date = self._extract_latest_dispense_date(block)
        minimum_interval_text = self._extract_minimum_interval_text(block)
        next_benefit_dispense_date = self._extract_next_benefit_dispense_date(block)
        subsidy_eligible = self._extract_subsidy_eligible(block)
        instruction_text = self._extract_instruction_text(block)
        dose_per_intake, dose_unit = self._extract_dose(block, instruction_text)
        administration_times = self._extract_administration_times(instruction_text)

        times_count = len(administration_times) if administration_times else 1
        base_dose = dose_per_intake if dose_per_intake is not None else 1.0
        prescribed_daily_dose = max(base_dose * times_count, 1.0)

        slug = re.sub(r"[^a-z0-9]+", "-", medication_name.casefold()).strip("-") or f"med-{index}"

        return Prescription(
            id=f"scrape-{slug}-{valid_until.isoformat()}",
            medication_name=medication_name,
            active_substance=active_substance,
            prescribed_product=prescribed_product,
            dispensed_product=dispensed_product,
            prescriber_name=prescriber_name,
            prescriber_organization=prescriber_organization,
            prescriber_location=prescriber_location,
            prescriber_phone=prescriber_phone,
            prescribed_daily_dose=prescribed_daily_dose,
            package_size=package_size,
            remaining_packages=remaining_packages,
            valid_until=valid_until,
            latest_dispense_date=latest_dispense_date,
            refill_remaining=refill_remaining,
            refill_total=refill_total,
            package_text=package_text,
            minimum_interval_text=minimum_interval_text,
            next_benefit_dispense_date=next_benefit_dispense_date,
            subsidy_eligible=subsidy_eligible,
            dose_per_intake=dose_per_intake,
            dose_unit=dose_unit,
            administration_times=administration_times,
            instruction_text=instruction_text,
            has_active_prescription=True,
            source_printed_at=printed_at,
            source_high_cost_period_end=high_cost_period_end,
            raw_prescription_text=block.strip(),
        )

    def _extract_active_substance(self, block: str, fallback: str) -> str:
        lines = self._non_empty_lines(block)
        for line in lines:
            if self._is_recent_dispense_line(line):
                continue
            if self._is_patient_identity_line(line):
                continue
            if self._is_labeled_line(line, self._label_starts_active_substance):
                continue
            if self._is_refill_summary_line(line):
                continue
            if self._is_parenthesized_line(line):
                continue

            token = line.split()[0] if line.split() else ""
            if token and self._line_token_pattern.match(token):
                token_folded = self._fold_text(token)
                if token_folded not in self._ignored_active_substance_tokens:
                    return token
        return fallback

    def _extract_active_substance_from_product(self, product_name: str | None) -> str | None:
        if not product_name:
            return None
        match = re.match(r"^([A-ZÅÄÖa-zåäö][A-Za-zÅÄÖåäö-]+)", product_name.strip())
        return match.group(1) if match else None

    def _build_display_medication_name(self, active_substance: str, prescribed_product: str | None) -> str:
        if not prescribed_product:
            return active_substance

        normalized = " ".join(prescribed_product.split())
        duplicate_prefix = re.compile(
            rf"^({re.escape(active_substance)})\s+({re.escape(active_substance)}\b.*)$",
            flags=re.IGNORECASE,
        )
        match = duplicate_prefix.match(normalized)
        if match:
            normalized = match.group(2)

        # Normalize noisy product qualifiers from the PDF table extraction.
        normalized = re.sub(r",\s*h[åa]rd\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\b(kapsel|tablett),\s+(?=\d)", r"\1 ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+AB$", "", normalized)
        return " ".join(normalized.split())

    def _extract_prescribed_product(self, block: str) -> str | None:
        lines = self._non_empty_lines(block)
        package_index = next(
            (idx for idx, line in enumerate(lines) if self._package_row_pattern.match(line)),
            len(lines),
        )
        header_lines = lines[:package_index]

        collecting = False
        collected: list[str] = []
        for idx, line in enumerate(header_lines):
            folded = self._fold_text(line)
            if not collecting:
                has_date = self._contains_date(line)
                if self._is_stop_line(line) or self._is_parenthesized_line(line) or self._is_patient_identity_line(line):
                    continue

                has_unit = any(unit in folded for unit in self._product_unit_tokens)
                if "," in line and has_unit and not has_date:
                    collecting = True
                    collected.append(line)
                    continue

                # Handle wrapped product names where the first line ends with a comma
                # and the dosage/form (tablett/kapsel/filmdragerad) appears on next line.
                if "," in line and not has_date and idx + 1 < len(header_lines):
                    next_line = header_lines[idx + 1]
                    next_folded = self._fold_text(next_line)
                    next_has_unit = any(unit in next_folded for unit in self._product_unit_tokens)
                    if next_has_unit and not self._contains_date(next_line):
                        collecting = True
                        collected.append(line)
                continue

            if self._is_stop_line(line):
                break
            if self._is_parenthesized_line(line):
                break
            if self._contains_date(line):
                break
            if re.search(r",,\s*Läkare", line):
                break

            collected.append(line)

        if collected:
            return " ".join(collected)
        return None

    def _extract_dispensed_product(self, block: str) -> str | None:
        lines = self._non_empty_lines(block)
        for idx, line in enumerate(lines):
            if self._contains_date(line) and idx > 0:
                candidate = lines[idx - 1]
                if any(unit in self._fold_text(candidate) for unit in ("kapsel", "tablett", "filmdragerad")):
                    return candidate
        return None

    def _extract_prescriber_name(self, block: str) -> str | None:
        match = self._prescriber_pattern.search(block)
        if match:
            return match.group(1).strip()
        return None

    def _extract_prescriber_line(self, block: str, offset: int) -> str | None:
        lines = self._non_empty_lines(block)
        for idx, line in enumerate(lines):
            if "Läkare" in line and idx + offset < len(lines):
                return lines[idx + offset]
        return None

    def _extract_prescriber_organization(self, block: str) -> str | None:
        return self._extract_prescriber_line(block, offset=1)

    def _extract_prescriber_location(self, block: str) -> str | None:
        return self._extract_prescriber_line(block, offset=2)

    def _extract_prescriber_phone(self, block: str) -> str | None:
        match = re.search(r"\b\d{2,3}[-\s]?\d{2,3}[-\s]?\d{2,3}\b", block)
        return match.group(0) if match else None

    def _extract_package_text(self, block: str) -> str | None:
        match = re.search(r"\b\d+\s*(?:kapsel/kapslar|kapslar|kapsel|tablett\(er\)|tabletter|tablett)\b", block, flags=re.IGNORECASE)
        return match.group(0) if match else None

    def _extract_refill_info(self, block: str) -> tuple[int | None, int | None]:
        match = re.search(r"([\dOil]+)\s+av\s+([\dOil]+)\s+uttag\s+kvar", block, flags=re.IGNORECASE)
        if not match:
            return None, None
        return int(self._ocr_digit_fix(match.group(1))), int(self._ocr_digit_fix(match.group(2)))

    def _extract_latest_dispense_date(self, block: str) -> date | None:
        dates = re.findall(r"([\dOil]{4}[-/][\dOil]{2}[-/][\dOil]{2})", block)
        for raw in dates:
            try:
                parsed = self._parse_date_token(raw)
            except ValueError:
                continue
            # first non-validity date is usually latest dispense in this document format
            return parsed
        return None

    def _extract_minimum_interval_text(self, block: str) -> str | None:
        match = re.search(r"Minsta tid mellan\s*uttag\s*:\s*([^\n]+)", block, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_next_benefit_dispense_date(self, block: str) -> date | None:
        match = re.search(r"Nästa uttag inom\s*förmånen\s*tidigast\s*:\s*([\dOil]{4}[-/][\dOil]{2}[-/][\dOil]{2})", block, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return self._parse_date_token(match.group(1))
        except ValueError:
            return None

    def _extract_subsidy_eligible(self, block: str) -> bool | None:
        match = re.search(r"Patient\s+förmånsberättigad\s*:\s*(Ja|Nej)", block, flags=re.IGNORECASE)
        if not match:
            return None
        return self._fold_text(match.group(1)) == "ja"

    def _extract_medication_name(self, block: str) -> str:
        lines = self._non_empty_lines(block)
        for line in lines:
            if self._is_stop_line(line):
                continue
            if self._is_patient_identity_line(line):
                continue
            folded = self._fold_text(line)
            if folded.startswith("utskrivet") or folded.startswith("hogkostnadsperiod"):
                continue
            if re.search(rf"^{self._date_pattern}$", line):
                continue
            if self._is_recent_dispense_line(line):
                continue
            if self._is_labeled_line(line, self._label_starts_medication_name):
                continue
            if self._is_refill_summary_line(line):
                continue
            if self._is_parenthesized_line(line):
                continue

            token_match = self._token_pattern.match(line)
            if token_match:
                token = token_match.group(0)
                if self._fold_text(token) in self._ignored_medication_tokens:
                    continue
                return token
        return "Okänt läkemedel"

    def _extract_package_size(self, block: str) -> int:
        match = re.search(rf"1\s*[xX]\s*([\dOil]+)\s*{self._unit_pattern}", block, flags=re.IGNORECASE)
        if match:
            return int(self._ocr_digit_fix(match.group(1)))

        matches = re.findall(rf"([\dOil]+)\s*{self._unit_pattern}", block, flags=re.IGNORECASE)
        if matches:
            values = [int(self._ocr_digit_fix(value)) for value in matches]
            return max(values)
        return 1

    def _extract_remaining_packages(self, block: str) -> int:
        match = re.search(r"([\dOil]+)\s+av\s+[\dOil]+\s+uttag\s+kvar", block, flags=re.IGNORECASE)
        if match:
            return int(self._ocr_digit_fix(match.group(1)))
        return 0

    def _extract_dose(self, block: str, instruction_text: str | None = None) -> tuple[float | None, str | None]:
        if instruction_text:
            instruction_match = re.search(
                rf"^\s*([\dOil]+(?:[\.,][\dOil]+)?)\s+({self._unit_pattern})\b",
                instruction_text,
                flags=re.IGNORECASE,
            )
            if instruction_match:
                dose_per_intake = float(self._ocr_digit_fix(instruction_match.group(1)).replace(",", "."))
                raw_unit = instruction_match.group(2).lower()
                dose_unit = "kapsel" if "kapsel" in raw_unit else "tablett"
                return dose_per_intake, dose_unit

        # Fallback for documents without a parseable instruction text.
        lines = self._non_empty_lines(block)
        for line in lines:
            folded = self._fold_text(line)
            if folded.startswith("1 x") or self._package_row_pattern.match(line):
                continue

            match = re.match(
                rf"^([\dOil]+(?:[\.,][\dOil]+)?)\s+({self._unit_pattern})\b",
                line,
                flags=re.IGNORECASE,
            )
            if not match:
                continue

            if not any(token in folded for token in (" morgon", " kvall", " kväll", " natt", " daglig", " till ", " for ", " för ")):
                continue

            dose_per_intake = float(self._ocr_digit_fix(match.group(1)).replace(",", "."))
            raw_unit = match.group(2).lower()
            dose_unit = "kapsel" if "kapsel" in raw_unit else "tablett"
            return dose_per_intake, dose_unit

        return None, None

    def _extract_instruction_text(self, block: str) -> str | None:
        lines = self._non_empty_lines(block)
        start_index: int | None = None
        for index, line in enumerate(lines):
            if re.match(rf"^[\dOil]+(?:[\.,][\dOil]+)?\s+{self._unit_pattern}", line, flags=re.IGNORECASE):
                start_index = index
                break

        if start_index is None:
            return None

        collected: list[str] = []
        for line in lines[start_index:]:
            if self._is_stop_line(line):
                break
            if re.fullmatch(rf"[\dOil]{{4}}[-/][\dOil]{{2}}[-/][\dOil]{{2}}", line):
                break
            if re.search(r"[\dOil]+\s+av\s+[\dOil]+\s+uttag\s+kvar", line, flags=re.IGNORECASE):
                break
            collected.append(line)

        return " ".join(collected).strip() or None

    def _extract_administration_times(self, instruction_text: str | None) -> list[str]:
        if not instruction_text:
            return []

        lowered = instruction_text.casefold()
        times: list[str] = []
        if "morgon" in lowered:
            times.append("morgon")
        if "lunch" in lowered or "middag" in lowered or "eftermiddag" in lowered:
            times.append("dag")
        if "kväll" in lowered or "kvall" in lowered:
            times.append("kväll")
        if "natt" in lowered:
            times.append("natt")
        if "dagligen" in lowered and not times:
            times.append("dag")

        return times
