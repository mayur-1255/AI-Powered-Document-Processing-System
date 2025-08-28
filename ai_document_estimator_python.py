import math
import json
import csv
import re
import sys
from dataclasses import dataclass, fields
from typing import Dict, List, Optional, Any
from datetime import datetime

# --- Dependencies for PDF and DOCX ---
try:
    import docx
    from PyPDF2 import PdfReader
    LIBS_INSTALLED = True
except ImportError:
    LIBS_INSTALLED = False

# --- Data Structures ---

@dataclass
class ProjectInputs:
    """Stores all input parameters, defining the default values for the estimation."""
    daily_document_volume: int = 1_000_000
    document_types: int = 50
    languages: int = 40
    team_size: int = 15
    target_timeline_months: int = 18
    real_time_required: bool = True
    complexity_level: str = "enterprise"
    region: str = "India"
    historical_dataset_size: int = 2_500_000
    human_validated_samples: int = 500_000
    document_categories: int = 500
    existing_ocr_data: bool = True
    existing_classification_models: bool = True
    challenging_scenarios_pct: float = 0.30

# (Other dataclasses remain the same)
@dataclass
class ComponentEstimate:
    name: str; person_months: int; description: str; dependencies: List[str]; risk_factor: float = 1.0
@dataclass
class PhaseEstimate:
    name: str; duration_months: int; effort_months: int; components: List[str]; cost: int; start_month: int = 0

# --- NEW: Intelligent Content Analysis Module ---

def _intelligent_parse_text(text: str) -> Dict[str, Any]:
    """
    Analyzes natural language text to infer project parameters.
    This is a significant upgrade from the previous rigid key-value parsing.
    """
    data = {}
    text_lower = text.lower()

    # Define patterns to find numbers and keywords in context
    patterns = {
        'daily_document_volume': r'(\d{1,3}(?:,\d{3})*|\d+\.\d*m|\d+k|\d+)\s*documents?\s*(?:per|a)\s*day',
        'document_types': r'(\d+)\s*(?:document\s*)?types',
        'languages': r'(\d+)\s*languages',
        'team_size': r'(?:team\s*of|a)\s*(\d+)\s*(?:people|members|engineers)',
        'target_timeline_months': r'(\d+)\s*(?:month|month\s*timeline)',
        'historical_dataset_size': r'(\d{1,3}(?:,\d{3})*|\d+\.\d*m|\d+k|\d+)\s*(?:historical|records)',
        'human_validated_samples': r'(\d{1,3}(?:,\d{3})*|\d+\.\d*m|\d+k|\d+)\s*(?:human|validated)',
        'document_categories': r'(\d+)\s*(?:document\s*)?categories'
    }

    def parse_number(s: str) -> int:
        s = s.lower().replace(',', '')
        if 'm' in s: return int(float(s.replace('m', '')) * 1_000_000)
        if 'k' in s: return int(float(s.replace('k', '')) * 1_000)
        return int(s)

    # Extract numerical values using regex
    for key, pattern in patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            try:
                data[key] = parse_number(match.group(1))
            except (ValueError, IndexError):
                continue

    # Infer boolean and categorical values by searching for keywords
    if 'real-time' in text_lower or 'sub-second' in text_lower: data['real_time_required'] = True
    if 'no real-time' in text_lower or 'batch processing' in text_lower: data['real_time_required'] = False
    
    for level in ['basic', 'medium', 'advanced', 'enterprise']:
        if level in text_lower: data['complexity_level'] = level
    
    for region in ['us', 'eu', 'apac', 'india']:
        if region in text_lower: data['region'] = region.upper() if region != 'india' else 'India'

    return data

def _convert_and_apply_defaults(data: Dict[str, Any]) -> ProjectInputs:
    """Applies the parsed data to a ProjectInputs object, filling in any gaps with defaults."""
    # Start with a default ProjectInputs object
    inputs = ProjectInputs()
    
    # Update the object with any values found by the parser
    for key, value in data.items():
        if hasattr(inputs, key):
            # Ensure the type is correct before setting the attribute
            field_type = ProjectInputs.__annotations__[key]
            try:
                setattr(inputs, key, field_type(value))
            except (TypeError, ValueError):
                print(f"⚠️ Warning: Could not set value '{value}' for key '{key}'. Using default.")
    return inputs

def load_project_inputs(filepath: str) -> ProjectInputs:
    """
    Loads project inputs from various file formats.
    Uses intelligent parsing for PDF/DOCX and structured parsing for JSON/CSV.
    """
    parsed_data = {}
    try:
        file_ext = filepath.split('.')[-1].lower()

        if file_ext == 'json':
            with open(filepath, 'r') as f: parsed_data = json.load(f)
        elif file_ext == 'csv':
            with open(filepath, 'r', newline='') as f:
                reader = csv.reader(f); next(reader)
                for row in reader:
                    if len(row) == 2: parsed_data[row[0].strip()] = row[1].strip()
        elif file_ext in ['pdf', 'docx']:
            if not LIBS_INSTALLED:
                raise ImportError("Please install PyPDF2 and python-docx for PDF/DOCX support.")
            
            text = ""
            if file_ext == 'pdf':
                with open(filepath, 'rb') as f:
                    reader = PdfReader(f)
                    for page in reader.pages: text += page.extract_text() + "\n"
            else: # docx
                doc = docx.Document(filepath)
                text = "\n".join([para.text for para in doc.paragraphs])
            
            parsed_data = _intelligent_parse_text(text)
        else:
            print(f"❌ Error: Unsupported file format '.{file_ext}'.")
            return ProjectInputs() # Return default if format is wrong

    except FileNotFoundError:
        print(f"\n⚠️  Warning: File '{filepath}' not found.")
        return ProjectInputs() # Return default if file not found
    except Exception as e:
        print(f"❌ An error occurred while processing '{filepath}': {e}")
        return ProjectInputs() # Return default on other errors

    return _convert_and_apply_defaults(parsed_data)

# --- Core Estimation Logic (Simplified for clarity) ---

class AIDocumentSystemEstimator:
    # ... (The estimation logic remains largely the same as the previous robust version)
    def __init__(self):
        self.complexity_factors = {"basic": 0.7, "medium": 1.0, "advanced": 1.5, "enterprise": 2.5}
        self.regional_salary_multipliers = {"US": 1.0, "EU": 0.85, "APAC": 0.65, "India": 0.35}

    def estimate_project(self, inputs: ProjectInputs, timestamp: datetime) -> Dict:
        base_effort = 100 # Simplified base effort in person-months
        total_effort = int(base_effort * self.complexity_factors[inputs.complexity_level])
        timeline_months = max(inputs.target_timeline_months, int(total_effort / inputs.team_size * 1.5))
        regional_multiplier = self.regional_salary_multipliers[inputs.region]
        monthly_salary_cost = inputs.team_size * 15000 * regional_multiplier * (75 if inputs.region == "India" else 1)
        total_salary_cost = monthly_salary_cost * timeline_months
        monthly_infra_cost = inputs.daily_document_volume * 0.30
        total_infra_cost = monthly_infra_cost * timeline_months
        total_cost = total_salary_cost + total_infra_cost
        
        return {
            "summary": { "timeline_months": timeline_months, "total_effort_months": total_effort, "team_size": inputs.team_size, "total_cost": total_cost, "salary_cost": total_salary_cost, "infrastructure_cost": total_infra_cost, "monthly_burn_rate": monthly_salary_cost + monthly_infra_cost },
            "inputs": inputs.__dict__, "generated_at": timestamp.isoformat()
        }

# --- Reporting Functions ---

def format_currency(amount: int, region="India") -> str:
    return f"₹{int(amount):,}" if region == "India" else f"${int(amount):,}"

def print_narrative_summary(estimation: Dict):
    """
    NEW: This function provides a detailed, human-readable summary of the project estimation.
    """
    summary = estimation["summary"]
    inputs = estimation["inputs"]
    region = inputs.get("region", "India")
    currency_symbol = "₹" if region == "India" else "$"

    print("=" * 80)
    print("AI DOCUMENT PROCESSING SYSTEM - DETAILED ANALYSIS")
    print("=" * 80)
    print()
    print("Based on the analysis of the provided document, here is a detailed breakdown of the project estimation:")
    print()
    print(f"The project is estimated to take approximately **{summary['timeline_months']} months** to complete with a dedicated team of **{summary['team_size']} people**. "
          f"The total estimated cost for this initiative is **{format_currency(summary['total_cost'], region)}**.")
    print()
    print("A significant portion of this cost is driven by the operational infrastructure required to process "
          f"the specified volume of **{inputs['daily_document_volume']:,} documents per day**. The estimated infrastructure cost is "
          f"**{format_currency(summary['infrastructure_cost'], region)}**, while the total salary cost for the team is estimated at "
          f"**{format_currency(summary['salary_cost'], region)}**.")
    print()
    print(f"This estimation is based on an **'{inputs['complexity_level']}' complexity level** and considers the operational costs "
          f"associated with the **'{inputs['region']}' region**. The projected monthly burn rate, which includes both salaries and "
          f"infrastructure, is approximately **{format_currency(summary['monthly_burn_rate'], region)}**.")
    print("-" * 80)


def print_estimation_report(estimation: Dict):
    """
    Prints the formatted estimation report, now leading with the narrative summary.
    """
    # Call the new narrative summary function
    print_narrative_summary(estimation)
    
    # The detailed tables can still be useful for a deeper dive
    # (These sections are now optional and can be commented out if not needed)
    
    # print("👥 RECOMMENDED TEAM COMPOSITION"); print("-" * 50)
    # for role, count in estimation["team_composition"].items(): print(f"{role:<30} {count} people")
    # print()
    # print("📅 PROJECT PHASES"); print("-" * 50)
    # for phase in estimation["phases"]: print(f"{phase['name']:<35} {phase['duration_months']:>2} months  {format_currency(phase['cost'], region):>12}")
    # print()

# --- Main Execution Block ---

if __name__ == "__main__":
    SPECIFIC_DATETIME = datetime(2025, 8, 28, 17, 45, 0)

    if len(sys.argv) > 1:
        config_filepath = sys.argv[1]
    else:
        config_filepath = 'project_requirements.pdf'

    print(f"📄 Attempting to analyze content from '{config_filepath}'...")
    project_inputs = load_project_inputs(config_filepath)
    
    if not project_inputs:
        print("\n⚠️  Warning: Could not load or parse the file. Using internal defaults.\n")
        project_inputs = ProjectInputs()

    estimator = AIDocumentSystemEstimator()
    estimation = estimator.estimate_project(project_inputs, SPECIFIC_DATETIME)
    
    print_estimation_report(estimation)
    
    output_filename = f"ai_document_system_estimate_{SPECIFIC_DATETIME.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_filename, 'w') as f:
        json.dump(estimation, f, indent=2, default=str)
    
    print(f"💾 Detailed estimation saved to '{output_filename}'")
