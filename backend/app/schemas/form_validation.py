import re
from typing import Literal, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BaseValidationRules(BaseModel):
    required: bool = False


class TextValidationRules(BaseValidationRules):
    min_length: Optional[int] = Field(None, ge=0)
    max_length: Optional[int] = Field(None, gt=0)
    
    @model_validator(mode='after')
    def check_lengths(self) -> 'TextValidationRules':
        if self.min_length is not None and self.max_length is not None:
            if self.min_length > self.max_length:
                raise ValueError("min_length cannot be greater than max_length")
        return self


class NumberValidationRules(BaseValidationRules):
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    @model_validator(mode='after')
    def check_values(self) -> 'NumberValidationRules':
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value cannot be greater than max_value")
        return self


class EmailValidationRules(BaseValidationRules):
    allowed_domains: Optional[List[str]] = None
    
    @field_validator('allowed_domains')
    @classmethod
    def clean_domains(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = []
            for d in v:
                d = d.strip().lower()
                if d:
                    cleaned.append(d)
            return cleaned
        return v


class SelectValidationRules(BaseValidationRules):
    options: List[str] = Field(default_factory=list)
    
    @field_validator('options')
    @classmethod
    def check_options(cls, v: List[str]) -> List[str]:
        cleaned = []
        for opt in v:
            opt = opt.strip()
            if opt and opt not in cleaned:
                cleaned.append(opt)
        if not cleaned:
            raise ValueError("Select field must have at least one valid option")
        return cleaned


class DateValidationRules(BaseValidationRules):
    pass


class PhoneValidationRules(BaseValidationRules):
    pass


# Combine rules into a Union based on type
FieldType = Literal["text", "textarea", "number", "email", "phone", "date", "select"]

class FieldValidationConfig(BaseModel):
    type: FieldType
    rules: Union[
        TextValidationRules,
        NumberValidationRules,
        EmailValidationRules,
        SelectValidationRules,
        DateValidationRules,
        PhoneValidationRules,
        BaseValidationRules,
    ] = Field(default_factory=BaseValidationRules)
    
    @model_validator(mode='before')
    @classmethod
    def parse_config(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
            
        field_type = data.get("type", "text")
        raw_rules = data.get("rules", {})
        
        # Ensure rules match the type (filtering out incompatible properties)
        # We will parse via the specific Pydantic model by passing it explicitly if we want,
        # but Pydantic's union logic might be messy if not discriminated.
        # It's better to manually map type -> model to strip out stale rules.
        rule_class_map = {
            "text": TextValidationRules,
            "textarea": TextValidationRules, # textarea shares text rules for now
            "number": NumberValidationRules,
            "email": EmailValidationRules,
            "phone": PhoneValidationRules,
            "date": DateValidationRules,
            "select": SelectValidationRules,
        }
        
        target_rule_class = rule_class_map.get(field_type, BaseValidationRules)
        
        # Filter raw_rules to only fields that exist on target_rule_class to safely ignore stale
        valid_fields = target_rule_class.model_fields.keys()
        cleaned_rules = {k: v for k, v in raw_rules.items() if k in valid_fields}
        
        # Instantiate directly to force validation errors to bubble up
        parsed_rules = target_rule_class(**cleaned_rules)
        
        data["type"] = field_type
        data["rules"] = parsed_rules
        return data

    @model_validator(mode='after')
    def ensure_correct_rule_type(self) -> 'FieldValidationConfig':
        # Validation is already strictly handled in parse_config.
        return self

from datetime import datetime

def validate_field_value(value: str | None, config: FieldValidationConfig) -> str | None:
    """
    Validates a student's input value against the backend configuration rules.
    Returns the normalized value if valid, or raises ValueError with a user-friendly message.
    """
    rules = config.rules
    
    # 1. Required check
    if value is None or str(value).strip() == "":
        if rules.required:
            raise ValueError("This field is required.")
        return None
        
    # Normalize basic string
    value = str(value).strip()
    
    # 2. Type-specific validation
    if config.type in ("text", "textarea"):
        if isinstance(rules, TextValidationRules):
            if rules.min_length is not None and len(value) < rules.min_length:
                raise ValueError(f"Value must be at least {rules.min_length} characters.")
            if rules.max_length is not None and len(value) > rules.max_length:
                raise ValueError(f"Value cannot exceed {rules.max_length} characters.")
        return value
        
    elif config.type == "number":
        try:
            num_val = float(value)
        except ValueError:
            raise ValueError("Please enter a valid number.")
            
        if isinstance(rules, NumberValidationRules):
            if rules.min_value is not None and num_val < rules.min_value:
                raise ValueError(f"Value must be at least {rules.min_value}.")
            if rules.max_value is not None and num_val > rules.max_value:
                raise ValueError(f"Value cannot exceed {rules.max_value}.")
        # Normalize to string representation of float or int
        return str(int(num_val)) if num_val.is_integer() else str(num_val)
        
    elif config.type == "email":
        # Basic email regex
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Please enter a valid email address.")
            
        if isinstance(rules, EmailValidationRules) and rules.allowed_domains:
            domain = value.split("@")[-1].lower()
            if domain not in [d.lower() for d in rules.allowed_domains]:
                raise ValueError(f"Email domain must be one of: {', '.join(rules.allowed_domains)}")
        return value.lower()
        
    elif config.type == "phone":
        # Strip all non-numeric characters for validation
        digits = re.sub(r"\D", "", value)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Please enter a valid phone number.")
        return digits
        
    elif config.type == "date":
        try:
            # Enforce YYYY-MM-DD
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Please enter a valid date in YYYY-MM-DD format.")
        return value
        
    elif config.type == "select":
        if isinstance(rules, SelectValidationRules):
            if value not in rules.options:
                raise ValueError("Please select a valid option from the list.")
        return value

    return value
