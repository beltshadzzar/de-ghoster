import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import logging

from src.services.cv_parser import CVParser
from src.services.job_scraper import LinkedInJobScraper
from src.services.job_matcher import JobMatcher
from src.services.database import DatabaseManager
from src.models.data_models import CVData, JobPosting, JobAnalysis, ApplicationHistory, RecommendationStatus
from src.utils.logger import setup_logger
from src.utils.validators import (
    validate_linkedin_url, validate_file_upload, validate_cv_name,
    validate_score_thresholds, validate_application_data, validate_environment_variables,
    ValidationError
)

load_dotenv()

st.set_page_config(
    page_title="LinkedIn Job Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_services():
    logger = setup_logger()
    
    try:
        warnings = validate_environment_variables()
        for warning in warnings:
            logger.warning(warning)
        
        openai_key = os.getenv('OPENAI_API_KEY')
        logger.info("Initializing services...")
        
        cv_parser = CVParser(openai_key)
        job_scraper = LinkedInJobScraper(openai_key)
        job_matcher = JobMatcher(openai_key)
        db_manager = DatabaseManager()
        
        logger.info("Services initialized successfully")
        return cv_parser, job_scraper, job_matcher, db_manager
        
    except ValidationError as e:
        logger.error(f"Environment validation failed: {str(e)}")
        st.error(f"Configuration Error: {str(e)}")
        st.stop()
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        st.error(f"Failed to initialize application: {str(e)}")
        st.stop()

def sidebar_settings():
    st.sidebar.title("⚙️ Settings")
    
    confidence_threshold = st.sidebar.slider(
        "Confidence Threshold",
        min_value=20,
        max_value=95,
        value=70,
        help="Minimum confidence level for recommendations"
    )
    
    score_threshold = st.sidebar.slider(
        "Score Threshold",
        min_value=30,
        max_value=90,
        value=60,
        help="Minimum overall score for 'Apply' recommendation"
    )
    
    auto_save = st.sidebar.checkbox(
        "Auto-save analyses",
        value=True,
        help="Automatically save job analyses to database"
    )
    
    try:
        validate_score_thresholds(confidence_threshold, score_threshold)
    except ValidationError as e:
        st.sidebar.error(f"Settings Error: {str(e)}")
    
    return {
        'confidence_threshold': confidence_threshold,
        'score_threshold': score_threshold,
        'auto_save': auto_save
    }

def upload_cv_section(cv_parser, db_manager):
    st.header("📄 Upload & Manage CVs")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your CV/Resume",
            type=['pdf', 'docx', 'txt'],
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        cv_name = st.text_input(
            "CV Name/Version",
            placeholder="e.g., Software Engineer CV v2.1"
        )
        
        if uploaded_file and cv_name:
            if st.button("Parse CV", type="primary"):
                logger = logging.getLogger("job_analyzer")
                
                with st.spinner("Parsing CV..."):
                    try:
                        validate_cv_name(cv_name)
                        
                        file_content = uploaded_file.read()
                        validate_file_upload(file_content, uploaded_file.name)
                        
                        logger.info(f"Parsing CV: {cv_name} ({uploaded_file.name})")
                        cv_data = cv_parser.parse_cv(file_content, uploaded_file.name, cv_name)
                        
                        if db_manager.save_cv(cv_data):
                            logger.info(f"CV saved successfully: {cv_data.id}")
                            st.success(f"CV '{cv_name}' parsed and saved successfully!")
                            st.session_state['current_cv'] = cv_data
                        else:
                            logger.error("Failed to save CV to database")
                            st.error("Failed to save CV to database")
                            
                    except ValidationError as e:
                        logger.warning(f"CV validation failed: {str(e)}")
                        st.error(f"Validation Error: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error parsing CV: {str(e)}", exc_info=True)
                        st.error(f"Error parsing CV: {str(e)}")
    
    with col2:
        st.subheader("Saved CVs")
        saved_cvs = db_manager.get_all_cvs()
        
        if saved_cvs:
            cv_options = {f"{cv.name} ({cv.upload_date.strftime('%Y-%m-%d')})": cv for cv in saved_cvs}
            selected_cv = st.selectbox("Select CV", list(cv_options.keys()))
            
            if selected_cv and st.button("Load CV"):
                st.session_state['current_cv'] = cv_options[selected_cv]
                st.success(f"Loaded CV: {cv_options[selected_cv].name}")
        else:
            st.info("No saved CVs found")
    
    if 'current_cv' in st.session_state:
        cv = st.session_state['current_cv']
        st.subheader(f"Current CV: {cv.name}")
        
        with st.expander("CV Details"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Experience", f"{cv.experience_years} years")
                st.write("**Skills:**")
                for skill in cv.skills[:10]:
                    st.write(f"• {skill}")
                if len(cv.skills) > 10:
                    st.write(f"... and {len(cv.skills) - 10} more")
            
            with col2:
                st.write("**Education:**")
                for edu in cv.education:
                    st.write(f"• {edu}")
                
                st.write("**Certifications:**")
                for cert in cv.certifications:
                    st.write(f"• {cert}")
            
            with col3:
                st.write("**Previous Roles:**")
                for title in cv.job_titles:
                    st.write(f"• {title}")
                
                st.write("**Industries:**")
                for industry in cv.industries:
                    st.write(f"• {industry}")

def job_analysis_section(job_scraper, job_matcher, db_manager, settings):
    st.header("🎯 Job Analysis")
    
    if 'current_cv' not in st.session_state:
        st.warning("Please upload and select a CV first.")
        return
    
    cv = st.session_state['current_cv']
    
    job_url = st.text_input(
        "LinkedIn Job URL",
        placeholder="https://www.linkedin.com/jobs/view/123456789",
        help="Paste the LinkedIn job posting URL here"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyze Job", type="primary", disabled=not job_url):
            if job_url:
                logger = logging.getLogger("job_analyzer")
                
                try:
                    validate_linkedin_url(job_url)
                    logger.info(f"Starting job analysis for URL: {job_url}")
                    
                    with st.spinner("Scraping job posting..."):
                        job_posting = job_scraper.scrape_job(job_url)
                        if settings['auto_save']:
                            db_manager.save_job_posting(job_posting)
                        
                        logger.info(f"Job scraped successfully: {job_posting.title} at {job_posting.company}")
                        st.success("Job scraped successfully!")
                        st.session_state['current_job'] = job_posting
                    
                    with st.spinner("Analyzing job match..."):
                        analysis = job_matcher.analyze_job_match(cv, job_posting)
                        if settings['auto_save']:
                            db_manager.save_job_analysis(analysis)
                        
                        logger.info(f"Job analysis completed: {analysis.recommendation.value} with {analysis.match_score.overall_score:.1f}% score")
                        st.session_state['current_analysis'] = analysis
                        
                except ValidationError as e:
                    logger.warning(f"Job URL validation failed: {str(e)}")
                    st.error(f"Validation Error: {str(e)}")
                except Exception as e:
                    logger.error(f"Error in job analysis: {str(e)}", exc_info=True)
                    st.error(f"Error analyzing job: {str(e)}")
                    return
    
    with col2:
        if st.button("View Analysis History"):
            st.session_state['show_history'] = True
    
    if 'current_job' in st.session_state and 'current_analysis' in st.session_state:
        display_job_analysis(st.session_state['current_job'], st.session_state['current_analysis'], settings)

def display_job_analysis(job: JobPosting, analysis: JobAnalysis, settings: Dict[str, Any]):
    st.subheader(f"Analysis: {job.title} at {job.company}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Overall Score",
            f"{analysis.match_score.overall_score:.1f}%",
            delta=f"Confidence: {analysis.match_score.confidence:.1f}%"
        )
    
    with col2:
        rec_color = {
            RecommendationStatus.APPLY: "🟢",
            RecommendationStatus.MAYBE: "🟡",
            RecommendationStatus.SKIP: "🔴"
        }
        st.metric(
            "Recommendation",
            f"{rec_color.get(analysis.recommendation, '⚪')} {analysis.recommendation.value.upper()}"
        )
    
    with col3:
        meets_threshold = (
            analysis.match_score.overall_score >= settings['score_threshold'] and
            analysis.match_score.confidence >= settings['confidence_threshold']
        )
        st.metric(
            "Meets Thresholds",
            "✅ Yes" if meets_threshold else "❌ No"
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Score Breakdown")
        
        scores_df = pd.DataFrame({
            'Component': ['Qualification (60%)', 'Competition (25%)', 'Strategic (15%)'],
            'Score': [
                analysis.match_score.qualification_score,
                analysis.match_score.competition_score,
                analysis.match_score.strategic_score
            ],
            'Weight': [0.6, 0.25, 0.15]
        })
        
        fig = px.bar(
            scores_df,
            x='Component',
            y='Score',
            title='Score Components',
            color='Score',
            color_continuous_scale='RdYlGn'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Match Analysis")
        
        tab1, tab2, tab3 = st.tabs(["Strengths", "Gaps", "Reasoning"])
        
        with tab1:
            st.write("**Key Matches:**")
            for match in analysis.key_matches:
                st.write(f"✅ {match}")
        
        with tab2:
            st.write("**Areas for Improvement:**")
            for gap in analysis.gaps:
                st.write(f"❌ {gap}")
        
        with tab3:
            st.write(analysis.reasoning)
    
    st.subheader("Job Details")
    with st.expander("Job Information"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Location:** {job.location}")
            st.write(f"**Experience Required:** {job.experience_required} years")
            st.write(f"**Job Type:** {job.job_type or 'Not specified'}")
            st.write(f"**Industry:** {job.industry or 'Not specified'}")
        
        with col2:
            st.write("**Required Skills:**")
            for skill in job.skills_required:
                st.write(f"• {skill}")
        
        st.write("**Job Description:**")
        st.text_area("", job.description, height=200, disabled=True)
    
    st.subheader("Application Tracking")
    track_application(analysis.id)

def track_application(analysis_id: str):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        applied = st.checkbox("Applied", key=f"applied_{analysis_id}")
    
    with col2:
        if applied:
            application_date = st.date_input("Application Date", key=f"app_date_{analysis_id}")
        else:
            application_date = None
    
    with col3:
        if applied:
            response_received = st.checkbox("Response Received", key=f"response_{analysis_id}")
            interview_scheduled = st.checkbox("Interview Scheduled", key=f"interview_{analysis_id}")
        else:
            response_received = False
            interview_scheduled = False
    
    if applied:
        outcome = st.selectbox(
            "Outcome",
            ["", "Pending", "Rejected", "Interview", "Offer", "Hired"],
            key=f"outcome_{analysis_id}"
        )
        
        notes = st.text_area(
            "Notes",
            placeholder="Add any notes about the application...",
            key=f"notes_{analysis_id}"
        )
        
        if st.button("Save Application Status", key=f"save_{analysis_id}"):
            logger = logging.getLogger("job_analyzer")
            
            try:
                app_data = {
                    'applied': applied,
                    'application_date': application_date,
                    'response_received': response_received,
                    'interview_scheduled': interview_scheduled,
                    'outcome': outcome,
                    'notes': notes
                }
                
                validate_application_data(app_data)
                
                history = ApplicationHistory(
                    id=f"app_{analysis_id}_{uuid.uuid4().hex[:8]}",
                    job_analysis_id=analysis_id,
                    applied=applied,
                    application_date=datetime.combine(application_date, datetime.min.time()) if application_date else None,
                    response_received=response_received,
                    interview_scheduled=interview_scheduled,
                    outcome=outcome if outcome else None,
                    notes=notes if notes else None
                )
                
                db_manager = DatabaseManager()
                if db_manager.save_application_history(history):
                    logger.info(f"Application status saved for analysis: {analysis_id}")
                    st.success("Application status saved!")
                else:
                    logger.error("Failed to save application status to database")
                    st.error("Failed to save application status")
                    
            except ValidationError as e:
                logger.warning(f"Application data validation failed: {str(e)}")
                st.error(f"Validation Error: {str(e)}")
            except Exception as e:
                logger.error(f"Error saving application status: {str(e)}", exc_info=True)
                st.error(f"Error saving application status: {str(e)}")

def analytics_dashboard(db_manager):
    st.header("📊 Analytics Dashboard")
    
    if 'current_cv' not in st.session_state:
        st.warning("Please select a CV to view analytics.")
        return
    
    cv = st.session_state['current_cv']
    
    tab1, tab2, tab3 = st.tabs(["Application Stats", "Score Analysis", "Success Rates"])
    
    with tab1:
        stats = db_manager.get_success_statistics(cv.id)
        
        if stats['total_analyses'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Analyses", stats['total_analyses'])
            
            with col2:
                st.metric("Applications Sent", stats['applications']['sent'])
            
            with col3:
                st.metric("Responses Received", stats['applications']['responses'])
            
            with col4:
                st.metric("Interviews Scheduled", stats['applications']['interviews'])
            
            rec_df = pd.DataFrame(list(stats['recommendations'].items()), columns=['Recommendation', 'Count'])
            fig = px.pie(rec_df, values='Count', names='Recommendation', title='Recommendation Distribution')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No analysis data available yet.")
    
    with tab2:
        analyses = db_manager.get_analyses_by_cv(cv.id)
        
        if analyses:
            scores_data = []
            for analysis in analyses:
                job = db_manager.get_job_posting(analysis.job_id)
                scores_data.append({
                    'Job': f"{job.title[:30]}..." if job and len(job.title) > 30 else (job.title if job else "Unknown"),
                    'Overall Score': analysis.match_score.overall_score,
                    'Qualification': analysis.match_score.qualification_score,
                    'Competition': analysis.match_score.competition_score,
                    'Strategic': analysis.match_score.strategic_score,
                    'Confidence': analysis.match_score.confidence,
                    'Recommendation': analysis.recommendation.value
                })
            
            scores_df = pd.DataFrame(scores_data)
            
            fig = px.scatter(
                scores_df,
                x='Overall Score',
                y='Confidence',
                color='Recommendation',
                size='Qualification',
                hover_data=['Job'],
                title='Score vs Confidence Analysis'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Score History")
            st.dataframe(scores_df[['Job', 'Overall Score', 'Qualification', 'Competition', 'Strategic', 'Recommendation']])
        else:
            st.info("No analysis data available yet.")
    
    with tab3:
        if stats.get('success_rates'):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Response Rate",
                    f"{stats['success_rates']['response_rate']:.1%}"
                )
            
            with col2:
                st.metric(
                    "Interview Rate",
                    f"{stats['success_rates']['interview_rate']:.1%}"
                )
            
            if stats.get('outcomes'):
                outcomes_df = pd.DataFrame(list(stats['outcomes'].items()), columns=['Outcome', 'Count'])
                fig = px.bar(outcomes_df, x='Outcome', y='Count', title='Application Outcomes')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No application data available yet.")

def main():
    logger = logging.getLogger("job_analyzer")
    
    try:
        st.title("🎯 LinkedIn Job Analyzer")
        st.markdown("### AI-powered job matching and application success prediction")
        
        cv_parser, job_scraper, job_matcher, db_manager = init_services()
        settings = sidebar_settings()
        
        tab1, tab2, tab3 = st.tabs(["📄 CV Management", "🎯 Job Analysis", "📊 Analytics"])
        
        with tab1:
            upload_cv_section(cv_parser, db_manager)
        
        with tab2:
            job_analysis_section(job_scraper, job_matcher, db_manager, settings)
        
        with tab3:
            analytics_dashboard(db_manager)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**About this app:**")
        st.sidebar.markdown("Analyze LinkedIn job postings against your CV using AI to get data-driven application recommendations.")
        
        logger.info("Application session completed successfully")
        
    except Exception as e:
        logger.error(f"Fatal error in main application: {str(e)}", exc_info=True)
        st.error("A critical error occurred. Please check the logs and try again.")
        st.error(f"Error details: {str(e)}")

if __name__ == "__main__":
    main()