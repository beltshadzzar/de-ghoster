import re
from typing import Dict, List, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
import json
from src.models.data_models import CVData, JobPosting, JobAnalysis, MatchScore, RecommendationStatus

class MatchOutputParser(BaseOutputParser):
    def parse(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._extract_fallback(text)
    
    def _extract_fallback(self, text: str) -> Dict[str, Any]:
        result = {
            "qualification_analysis": "",
            "competition_analysis": "",
            "strategic_analysis": "",
            "key_matches": [],
            "gaps": [],
            "reasoning": text[:500] + "..." if len(text) > 500 else text
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'matches:' in line.lower() or 'strengths:' in line.lower():
                current_section = 'key_matches'
            elif 'gaps:' in line.lower() or 'weaknesses:' in line.lower():
                current_section = 'gaps'
            elif line and current_section and (line.startswith('-') or line.startswith('•')):
                result[current_section].append(line[1:].strip())
        
        return result

class JobMatcher:
    def __init__(self, openai_api_key: str):
        self.llm = OpenAI(
            openai_api_key=openai_api_key,
            temperature=0.2,
            model_name="gpt-3.5-turbo-instruct"
        )
        self.parser = MatchOutputParser()
        self._setup_chain()
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    
    def _setup_chain(self):
        template = """
        Analyze the match between this CV and job posting. Provide detailed analysis for each scoring dimension.
        
        CV Information:
        Skills: {cv_skills}
        Experience: {cv_experience} years
        Education: {cv_education}
        Previous Roles: {cv_roles}
        Industries: {cv_industries}
        
        Job Requirements:
        Title: {job_title}
        Required Skills: {job_skills}
        Experience Required: {job_experience} years
        Requirements: {job_requirements}
        Industry: {job_industry}
        
        Provide analysis in JSON format:
        {{
            "qualification_analysis": "Detailed analysis of how candidate's qualifications match job requirements",
            "competition_analysis": "Assessment of how competitive the candidate would be against other applicants",
            "strategic_analysis": "Analysis of career growth potential, company fit, and strategic value",
            "key_matches": [list of specific strengths and matching qualifications],
            "gaps": [list of areas where candidate doesn't meet requirements],
            "reasoning": "Overall reasoning for the recommendation",
            "confidence_factors": [list of factors that increase or decrease confidence in the analysis]
        }}
        
        Be specific and focus on concrete skills, experience levels, and requirements matching.
        """
        
        self.prompt = PromptTemplate(
            input_variables=[
                "cv_skills", "cv_experience", "cv_education", "cv_roles", "cv_industries",
                "job_title", "job_skills", "job_experience", "job_requirements", "job_industry"
            ],
            template=template
        )
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    def _calculate_skill_similarity(self, cv_skills: List[str], job_skills: List[str]) -> float:
        if not cv_skills or not job_skills:
            return 0.0
        
        cv_skills_text = ' '.join(cv_skills)
        job_skills_text = ' '.join(job_skills)
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform([cv_skills_text, job_skills_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return self._basic_skill_match(cv_skills, job_skills)
    
    def _basic_skill_match(self, cv_skills: List[str], job_skills: List[str]) -> float:
        cv_skills_lower = [skill.lower().strip() for skill in cv_skills]
        job_skills_lower = [skill.lower().strip() for skill in job_skills]
        
        matches = 0
        for job_skill in job_skills_lower:
            for cv_skill in cv_skills_lower:
                if job_skill in cv_skill or cv_skill in job_skill:
                    matches += 1
                    break
        
        return matches / len(job_skills_lower) if job_skills_lower else 0.0
    
    def _calculate_experience_match(self, cv_experience: int, job_experience: int) -> float:
        if job_experience == 0:
            return 1.0
        
        if cv_experience >= job_experience:
            return 1.0
        elif cv_experience >= job_experience * 0.8:
            return 0.8
        elif cv_experience >= job_experience * 0.6:
            return 0.6
        elif cv_experience >= job_experience * 0.4:
            return 0.4
        else:
            return 0.2
    
    def _calculate_qualification_score(self, cv: CVData, job: JobPosting) -> Tuple[float, Dict[str, Any]]:
        skill_similarity = self._calculate_skill_similarity(cv.skills, job.skills_required)
        experience_match = self._calculate_experience_match(cv.experience_years, job.experience_required)
        
        education_bonus = 0.0
        if cv.education and any(edu for edu in cv.education if any(keyword in edu.lower() for keyword in ['bachelor', 'master', 'phd', 'degree'])):
            education_bonus = 0.1
        
        certification_bonus = 0.0
        if cv.certifications:
            relevant_certs = 0
            for cert in cv.certifications:
                for skill in job.skills_required:
                    if skill.lower() in cert.lower():
                        relevant_certs += 1
                        break
            certification_bonus = min(0.1, relevant_certs * 0.05)
        
        base_score = (skill_similarity * 0.6 + experience_match * 0.4) * 100
        bonus_score = (education_bonus + certification_bonus) * 100
        final_score = min(100, base_score + bonus_score)
        
        details = {
            "skill_similarity": skill_similarity,
            "experience_match": experience_match,
            "education_bonus": education_bonus,
            "certification_bonus": certification_bonus,
            "base_score": base_score,
            "bonus_score": bonus_score
        }
        
        return final_score, details
    
    def _calculate_competition_score(self, cv: CVData, job: JobPosting) -> Tuple[float, Dict[str, Any]]:
        base_competition = 50.0
        
        overqualification_penalty = 0.0
        if cv.experience_years > job.experience_required * 1.5:
            overqualification_penalty = min(20.0, (cv.experience_years - job.experience_required) * 2)
        
        unique_skills_bonus = 0.0
        specialized_skills = ['ai', 'machine learning', 'blockchain', 'quantum', 'cloud architecture']
        for skill in cv.skills:
            if any(spec in skill.lower() for spec in specialized_skills):
                unique_skills_bonus += 5.0
        unique_skills_bonus = min(20.0, unique_skills_bonus)
        
        industry_experience_bonus = 0.0
        if job.industry and cv.industries:
            for cv_industry in cv.industries:
                if job.industry.lower() in cv_industry.lower() or cv_industry.lower() in job.industry.lower():
                    industry_experience_bonus = 15.0
                    break
        
        leadership_bonus = 0.0
        leadership_keywords = ['lead', 'manager', 'director', 'senior', 'principal', 'architect']
        for title in cv.job_titles:
            if any(keyword in title.lower() for keyword in leadership_keywords):
                leadership_bonus = 10.0
                break
        
        final_score = base_competition - overqualification_penalty + unique_skills_bonus + industry_experience_bonus + leadership_bonus
        final_score = max(0, min(100, final_score))
        
        details = {
            "base_competition": base_competition,
            "overqualification_penalty": overqualification_penalty,
            "unique_skills_bonus": unique_skills_bonus,
            "industry_experience_bonus": industry_experience_bonus,
            "leadership_bonus": leadership_bonus
        }
        
        return final_score, details
    
    def _calculate_strategic_score(self, cv: CVData, job: JobPosting, analysis_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        base_strategic = 60.0
        
        career_growth_potential = 0.0
        growth_indicators = ['senior', 'lead', 'principal', 'manager', 'director']
        current_level = 0
        target_level = 0
        
        for i, indicator in enumerate(growth_indicators):
            if cv.job_titles and any(indicator in title.lower() for title in cv.job_titles):
                current_level = max(current_level, i + 1)
            if indicator in job.title.lower():
                target_level = i + 1
        
        if target_level > current_level:
            career_growth_potential = 20.0
        elif target_level == current_level:
            career_growth_potential = 10.0
        
        skill_development_bonus = 0.0
        emerging_skills = ['ai', 'ml', 'cloud', 'devops', 'kubernetes', 'react', 'python', 'aws']
        job_emerging_skills = sum(1 for skill in job.skills_required if any(emerging in skill.lower() for emerging in emerging_skills))
        if job_emerging_skills > 0:
            skill_development_bonus = min(15.0, job_emerging_skills * 3)
        
        company_size_fit = 5.0
        if 'startup' in job.company.lower() or 'small' in job.description.lower():
            if cv.experience_years < 5:
                company_size_fit = 10.0
        elif 'enterprise' in job.company.lower() or 'fortune' in job.description.lower():
            if cv.experience_years > 3:
                company_size_fit = 10.0
        
        final_score = base_strategic + career_growth_potential + skill_development_bonus + company_size_fit
        final_score = max(0, min(100, final_score))
        
        details = {
            "base_strategic": base_strategic,
            "career_growth_potential": career_growth_potential,
            "skill_development_bonus": skill_development_bonus,
            "company_size_fit": company_size_fit,
            "current_level": current_level,
            "target_level": target_level
        }
        
        return final_score, details
    
    def _calculate_confidence(self, qualification_score: float, competition_score: float, 
                            strategic_score: float, analysis_data: Dict[str, Any]) -> float:
        base_confidence = 70.0
        
        if qualification_score > 80:
            base_confidence += 15
        elif qualification_score > 60:
            base_confidence += 5
        elif qualification_score < 40:
            base_confidence -= 15
        
        if len(analysis_data.get('key_matches', [])) > 3:
            base_confidence += 10
        
        if len(analysis_data.get('gaps', [])) > 2:
            base_confidence -= 10
        
        score_variance = np.std([qualification_score, competition_score, strategic_score])
        if score_variance > 20:
            base_confidence -= 10
        
        return max(20, min(95, base_confidence))
    
    def _determine_recommendation(self, overall_score: float, confidence: float, 
                                qualification_score: float) -> RecommendationStatus:
        if overall_score >= 75 and confidence >= 70:
            return RecommendationStatus.APPLY
        elif overall_score >= 60 and qualification_score >= 60:
            return RecommendationStatus.APPLY
        elif overall_score >= 45 and confidence >= 60:
            return RecommendationStatus.MAYBE
        else:
            return RecommendationStatus.SKIP
    
    def analyze_job_match(self, cv: CVData, job: JobPosting) -> JobAnalysis:
        try:
            analysis_data = self.chain.run(
                cv_skills=', '.join(cv.skills),
                cv_experience=cv.experience_years,
                cv_education=', '.join(cv.education),
                cv_roles=', '.join(cv.job_titles),
                cv_industries=', '.join(cv.industries),
                job_title=job.title,
                job_skills=', '.join(job.skills_required),
                job_experience=job.experience_required,
                job_requirements=', '.join(job.requirements),
                job_industry=job.industry or 'Not specified'
            )
        except Exception as e:
            analysis_data = {
                "qualification_analysis": f"Analysis error: {str(e)}",
                "competition_analysis": "Unable to analyze competition factors",
                "strategic_analysis": "Unable to analyze strategic factors",
                "key_matches": [],
                "gaps": [],
                "reasoning": f"Analysis failed due to error: {str(e)}",
                "confidence_factors": []
            }
        
        qualification_score, qual_details = self._calculate_qualification_score(cv, job)
        competition_score, comp_details = self._calculate_competition_score(cv, job)
        strategic_score, strat_details = self._calculate_strategic_score(cv, job, analysis_data)
        
        overall_score = (
            qualification_score * 0.6 +
            competition_score * 0.25 +
            strategic_score * 0.15
        )
        
        confidence = self._calculate_confidence(
            qualification_score, competition_score, strategic_score, analysis_data
        )
        
        recommendation = self._determine_recommendation(
            overall_score, confidence, qualification_score
        )
        
        match_score = MatchScore(
            qualification_score=qualification_score,
            competition_score=competition_score,
            strategic_score=strategic_score,
            overall_score=overall_score,
            confidence=confidence
        )
        
        analysis_id = f"analysis_{cv.id}_{job.id}_{int(overall_score)}"
        
        return JobAnalysis(
            id=analysis_id,
            cv_id=cv.id,
            job_id=job.id,
            match_score=match_score,
            recommendation=recommendation,
            reasoning=analysis_data.get('reasoning', 'No reasoning provided'),
            key_matches=analysis_data.get('key_matches', []),
            gaps=analysis_data.get('gaps', []),
            metadata={
                'qualification_details': qual_details,
                'competition_details': comp_details,
                'strategic_details': strat_details,
                'analysis_data': analysis_data
            }
        )