from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class RecommendationStatus(str, Enum):
    APPLY = "apply"
    SKIP = "skip"
    MAYBE = "maybe"

class CVData(BaseModel):
    id: str
    name: str
    content: str
    skills: List[str] = []
    experience_years: int = 0
    education: List[str] = []
    certifications: List[str] = []
    job_titles: List[str] = []
    industries: List[str] = []
    parsed_data: Dict[str, Any] = {}
    upload_date: datetime = Field(default_factory=datetime.now)

class JobPosting(BaseModel):
    id: str
    url: str
    title: str
    company: str
    location: str
    description: str
    requirements: List[str] = []
    skills_required: List[str] = []
    experience_required: int = 0
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    industry: Optional[str] = None
    scraped_date: datetime = Field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = {}

class MatchScore(BaseModel):
    qualification_score: float = Field(ge=0, le=100)
    competition_score: float = Field(ge=0, le=100)
    strategic_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)

class JobAnalysis(BaseModel):
    id: str
    cv_id: str
    job_id: str
    match_score: MatchScore
    recommendation: RecommendationStatus
    reasoning: str
    key_matches: List[str] = []
    gaps: List[str] = []
    analysis_date: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class ApplicationHistory(BaseModel):
    id: str
    job_analysis_id: str
    applied: bool
    application_date: Optional[datetime] = None
    response_received: bool = False
    interview_scheduled: bool = False
    outcome: Optional[str] = None
    notes: Optional[str] = None