import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import mimetypes

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_linkedin_url(url: str) -> bool:
    """
    Validate if URL is a valid LinkedIn job posting URL
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError("URL must start with http:// or https://")
        
        if 'linkedin.com' not in parsed.netloc.lower():
            raise ValidationError("URL must be from linkedin.com")
        
        if '/jobs/view/' not in parsed.path:
            raise ValidationError("URL must be a LinkedIn job posting (/jobs/view/)")
        
        job_id_match = re.search(r'/jobs/view/(\d+)', parsed.path)
        if not job_id_match:
            raise ValidationError("Invalid LinkedIn job ID in URL")
        
        return True
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Invalid URL format: {str(e)}")

def validate_file_upload(file_content: bytes, filename: str, max_size_mb: int = 10) -> bool:
    """
    Validate uploaded file for CV parsing
    """
    if not file_content:
        raise ValidationError("File cannot be empty")
    
    if len(file_content) > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size cannot exceed {max_size_mb}MB")
    
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_extension = '.' + filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_extensions)}")
    
    mime_type, _ = mimetypes.guess_type(filename)
    allowed_mime_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain'
    ]
    
    if mime_type and mime_type not in allowed_mime_types:
        raise ValidationError(f"MIME type {mime_type} not supported")
    
    return True

def validate_cv_name(name: str) -> bool:
    """
    Validate CV name
    """
    if not name or not name.strip():
        raise ValidationError("CV name cannot be empty")
    
    if len(name.strip()) < 3:
        raise ValidationError("CV name must be at least 3 characters long")
    
    if len(name.strip()) > 100:
        raise ValidationError("CV name cannot exceed 100 characters")
    
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    if any(char in name for char in invalid_chars):
        raise ValidationError(f"CV name cannot contain these characters: {', '.join(invalid_chars)}")
    
    return True

def validate_score_thresholds(confidence_threshold: float, score_threshold: float) -> bool:
    """
    Validate scoring thresholds
    """
    if not isinstance(confidence_threshold, (int, float)):
        raise ValidationError("Confidence threshold must be a number")
    
    if not isinstance(score_threshold, (int, float)):
        raise ValidationError("Score threshold must be a number")
    
    if confidence_threshold < 0 or confidence_threshold > 100:
        raise ValidationError("Confidence threshold must be between 0 and 100")
    
    if score_threshold < 0 or score_threshold > 100:
        raise ValidationError("Score threshold must be between 0 and 100")
    
    return True

def sanitize_text_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize text input to prevent injection attacks and ensure valid format
    """
    if not text:
        return ""
    
    text = text.strip()
    
    if len(text) > max_length:
        text = text[:max_length]
    
    text = re.sub(r'[<>\"\';&]', '', text)
    
    text = re.sub(r'\s+', ' ', text)
    
    return text

def validate_application_data(data: Dict[str, Any]) -> bool:
    """
    Validate application tracking data
    """
    required_fields = ['applied']
    
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    if not isinstance(data['applied'], bool):
        raise ValidationError("Applied field must be a boolean")
    
    if data.get('application_date') and data['applied'] is False:
        raise ValidationError("Cannot have application date if not applied")
    
    valid_outcomes = ['', 'Pending', 'Rejected', 'Interview', 'Offer', 'Hired']
    if data.get('outcome') and data['outcome'] not in valid_outcomes:
        raise ValidationError(f"Invalid outcome. Must be one of: {', '.join(valid_outcomes)}")
    
    if data.get('notes'):
        data['notes'] = sanitize_text_input(data['notes'], max_length=2000)
    
    return True

def validate_environment_variables() -> List[str]:
    """
    Validate that required environment variables are set
    """
    import os
    
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['LANGCHAIN_API_KEY', 'LANGCHAIN_TRACING_V2']
    
    missing_vars = []
    warnings = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            warnings.append(f"Optional variable {var} not set")
    
    if missing_vars:
        raise ValidationError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return warnings

def validate_api_key_format(api_key: str, key_type: str = "OpenAI") -> bool:
    """
    Basic validation of API key format
    """
    if not api_key:
        raise ValidationError(f"{key_type} API key cannot be empty")
    
    if key_type.lower() == "openai":
        if not api_key.startswith('sk-'):
            raise ValidationError("OpenAI API key must start with 'sk-'")
        
        if len(api_key) < 20:
            raise ValidationError("OpenAI API key appears to be too short")
    
    return True