import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from src.models.data_models import CVData, JobPosting, JobAnalysis, ApplicationHistory

class DatabaseManager:
    def __init__(self, db_path: str = "data/job_analyzer.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cvs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    skills TEXT,
                    experience_years INTEGER,
                    education TEXT,
                    certifications TEXT,
                    job_titles TEXT,
                    industries TEXT,
                    parsed_data TEXT,
                    upload_date TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_postings (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requirements TEXT,
                    skills_required TEXT,
                    experience_required INTEGER,
                    salary_range TEXT,
                    job_type TEXT,
                    industry TEXT,
                    scraped_date TEXT,
                    raw_data TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_analyses (
                    id TEXT PRIMARY KEY,
                    cv_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    qualification_score REAL,
                    competition_score REAL,
                    strategic_score REAL,
                    overall_score REAL,
                    confidence REAL,
                    recommendation TEXT,
                    reasoning TEXT,
                    key_matches TEXT,
                    gaps TEXT,
                    analysis_date TEXT,
                    metadata TEXT,
                    FOREIGN KEY (cv_id) REFERENCES cvs (id),
                    FOREIGN KEY (job_id) REFERENCES job_postings (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_history (
                    id TEXT PRIMARY KEY,
                    job_analysis_id TEXT NOT NULL,
                    applied BOOLEAN,
                    application_date TEXT,
                    response_received BOOLEAN,
                    interview_scheduled BOOLEAN,
                    outcome TEXT,
                    notes TEXT,
                    FOREIGN KEY (job_analysis_id) REFERENCES job_analyses (id)
                )
            """)
            
            conn.commit()
    
    def save_cv(self, cv: CVData) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cvs (
                        id, name, content, skills, experience_years, education,
                        certifications, job_titles, industries, parsed_data, upload_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cv.id, cv.name, cv.content, json.dumps(cv.skills),
                    cv.experience_years, json.dumps(cv.education),
                    json.dumps(cv.certifications), json.dumps(cv.job_titles),
                    json.dumps(cv.industries), json.dumps(cv.parsed_data),
                    cv.upload_date.isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving CV: {e}")
            return False
    
    def get_cv(self, cv_id: str) -> Optional[CVData]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cvs WHERE id = ?", (cv_id,))
                row = cursor.fetchone()
                
                if row:
                    return CVData(
                        id=row[0], name=row[1], content=row[2],
                        skills=json.loads(row[3]) if row[3] else [],
                        experience_years=row[4],
                        education=json.loads(row[5]) if row[5] else [],
                        certifications=json.loads(row[6]) if row[6] else [],
                        job_titles=json.loads(row[7]) if row[7] else [],
                        industries=json.loads(row[8]) if row[8] else [],
                        parsed_data=json.loads(row[9]) if row[9] else {},
                        upload_date=datetime.fromisoformat(row[10])
                    )
        except Exception as e:
            print(f"Error getting CV: {e}")
        return None
    
    def get_all_cvs(self) -> List[CVData]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cvs ORDER BY upload_date DESC")
                rows = cursor.fetchall()
                
                cvs = []
                for row in rows:
                    cvs.append(CVData(
                        id=row[0], name=row[1], content=row[2],
                        skills=json.loads(row[3]) if row[3] else [],
                        experience_years=row[4],
                        education=json.loads(row[5]) if row[5] else [],
                        certifications=json.loads(row[6]) if row[6] else [],
                        job_titles=json.loads(row[7]) if row[7] else [],
                        industries=json.loads(row[8]) if row[8] else [],
                        parsed_data=json.loads(row[9]) if row[9] else {},
                        upload_date=datetime.fromisoformat(row[10])
                    ))
                return cvs
        except Exception as e:
            print(f"Error getting all CVs: {e}")
        return []
    
    def save_job_posting(self, job: JobPosting) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO job_postings (
                        id, url, title, company, location, description,
                        requirements, skills_required, experience_required,
                        salary_range, job_type, industry, scraped_date, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id, job.url, job.title, job.company, job.location,
                    job.description, json.dumps(job.requirements),
                    json.dumps(job.skills_required), job.experience_required,
                    job.salary_range, job.job_type, job.industry,
                    job.scraped_date.isoformat(), json.dumps(job.raw_data)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving job posting: {e}")
            return False
    
    def get_job_posting(self, job_id: str) -> Optional[JobPosting]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM job_postings WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return JobPosting(
                        id=row[0], url=row[1], title=row[2], company=row[3],
                        location=row[4], description=row[5],
                        requirements=json.loads(row[6]) if row[6] else [],
                        skills_required=json.loads(row[7]) if row[7] else [],
                        experience_required=row[8], salary_range=row[9],
                        job_type=row[10], industry=row[11],
                        scraped_date=datetime.fromisoformat(row[12]),
                        raw_data=json.loads(row[13]) if row[13] else {}
                    )
        except Exception as e:
            print(f"Error getting job posting: {e}")
        return None
    
    def save_job_analysis(self, analysis: JobAnalysis) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO job_analyses (
                        id, cv_id, job_id, qualification_score, competition_score,
                        strategic_score, overall_score, confidence, recommendation,
                        reasoning, key_matches, gaps, analysis_date, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis.id, analysis.cv_id, analysis.job_id,
                    analysis.match_score.qualification_score,
                    analysis.match_score.competition_score,
                    analysis.match_score.strategic_score,
                    analysis.match_score.overall_score,
                    analysis.match_score.confidence,
                    analysis.recommendation.value,
                    analysis.reasoning, json.dumps(analysis.key_matches),
                    json.dumps(analysis.gaps), analysis.analysis_date.isoformat(),
                    json.dumps(analysis.metadata)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving job analysis: {e}")
            return False
    
    def get_job_analysis(self, analysis_id: str) -> Optional[JobAnalysis]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM job_analyses WHERE id = ?", (analysis_id,))
                row = cursor.fetchone()
                
                if row:
                    from src.models.data_models import MatchScore, RecommendationStatus
                    
                    match_score = MatchScore(
                        qualification_score=row[3],
                        competition_score=row[4],
                        strategic_score=row[5],
                        overall_score=row[6],
                        confidence=row[7]
                    )
                    
                    return JobAnalysis(
                        id=row[0], cv_id=row[1], job_id=row[2],
                        match_score=match_score,
                        recommendation=RecommendationStatus(row[8]),
                        reasoning=row[9],
                        key_matches=json.loads(row[10]) if row[10] else [],
                        gaps=json.loads(row[11]) if row[11] else [],
                        analysis_date=datetime.fromisoformat(row[12]),
                        metadata=json.loads(row[13]) if row[13] else {}
                    )
        except Exception as e:
            print(f"Error getting job analysis: {e}")
        return None
    
    def get_analyses_by_cv(self, cv_id: str) -> List[JobAnalysis]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM job_analyses 
                    WHERE cv_id = ? 
                    ORDER BY analysis_date DESC
                """, (cv_id,))
                rows = cursor.fetchall()
                
                analyses = []
                for row in rows:
                    from src.models.data_models import MatchScore, RecommendationStatus
                    
                    match_score = MatchScore(
                        qualification_score=row[3],
                        competition_score=row[4],
                        strategic_score=row[5],
                        overall_score=row[6],
                        confidence=row[7]
                    )
                    
                    analyses.append(JobAnalysis(
                        id=row[0], cv_id=row[1], job_id=row[2],
                        match_score=match_score,
                        recommendation=RecommendationStatus(row[8]),
                        reasoning=row[9],
                        key_matches=json.loads(row[10]) if row[10] else [],
                        gaps=json.loads(row[11]) if row[11] else [],
                        analysis_date=datetime.fromisoformat(row[12]),
                        metadata=json.loads(row[13]) if row[13] else {}
                    ))
                return analyses
        except Exception as e:
            print(f"Error getting analyses by CV: {e}")
        return []
    
    def save_application_history(self, history: ApplicationHistory) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO application_history (
                        id, job_analysis_id, applied, application_date,
                        response_received, interview_scheduled, outcome, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    history.id, history.job_analysis_id, history.applied,
                    history.application_date.isoformat() if history.application_date else None,
                    history.response_received, history.interview_scheduled,
                    history.outcome, history.notes
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving application history: {e}")
            return False
    
    def get_application_history(self, analysis_id: str) -> Optional[ApplicationHistory]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM application_history 
                    WHERE job_analysis_id = ?
                """, (analysis_id,))
                row = cursor.fetchone()
                
                if row:
                    return ApplicationHistory(
                        id=row[0], job_analysis_id=row[1], applied=row[2],
                        application_date=datetime.fromisoformat(row[3]) if row[3] else None,
                        response_received=row[4], interview_scheduled=row[5],
                        outcome=row[6], notes=row[7]
                    )
        except Exception as e:
            print(f"Error getting application history: {e}")
        return None
    
    def get_success_statistics(self, cv_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                base_query = """
                    SELECT ja.recommendation, ah.applied, ah.response_received, 
                           ah.interview_scheduled, ah.outcome
                    FROM job_analyses ja
                    LEFT JOIN application_history ah ON ja.id = ah.job_analysis_id
                """
                
                if cv_id:
                    cursor.execute(base_query + " WHERE ja.cv_id = ?", (cv_id,))
                else:
                    cursor.execute(base_query)
                
                rows = cursor.fetchall()
                
                stats = {
                    'total_analyses': len(rows),
                    'recommendations': {'apply': 0, 'maybe': 0, 'skip': 0},
                    'applications': {'sent': 0, 'responses': 0, 'interviews': 0},
                    'success_rates': {},
                    'outcomes': {}
                }
                
                for row in rows:
                    recommendation, applied, response, interview, outcome = row
                    
                    if recommendation:
                        stats['recommendations'][recommendation] = stats['recommendations'].get(recommendation, 0) + 1
                    
                    if applied:
                        stats['applications']['sent'] += 1
                        if response:
                            stats['applications']['responses'] += 1
                        if interview:
                            stats['applications']['interviews'] += 1
                        if outcome:
                            stats['outcomes'][outcome] = stats['outcomes'].get(outcome, 0) + 1
                
                if stats['applications']['sent'] > 0:
                    stats['success_rates']['response_rate'] = stats['applications']['responses'] / stats['applications']['sent']
                    stats['success_rates']['interview_rate'] = stats['applications']['interviews'] / stats['applications']['sent']
                
                return stats
        except Exception as e:
            print(f"Error getting success statistics: {e}")
        return {}
    
    def cleanup_old_data(self, days_old: int = 90):
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM application_history 
                    WHERE job_analysis_id IN (
                        SELECT id FROM job_analyses 
                        WHERE analysis_date < ?
                    )
                """, (cutoff_date.isoformat(),))
                
                cursor.execute("""
                    DELETE FROM job_analyses 
                    WHERE analysis_date < ?
                """, (cutoff_date.isoformat(),))
                
                cursor.execute("""
                    DELETE FROM job_postings 
                    WHERE scraped_date < ? AND id NOT IN (
                        SELECT DISTINCT job_id FROM job_analyses
                    )
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return False