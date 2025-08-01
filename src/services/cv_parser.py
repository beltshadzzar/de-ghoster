import os
import re
from typing import Dict, List, Any
from io import BytesIO
import PyPDF2
from docx import Document
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
import json
from src.models.data_models import CVData

class CVOutputParser(BaseOutputParser):
    def parse(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._extract_fallback(text)
    
    def _extract_fallback(self, text: str) -> Dict[str, Any]:
        result = {
            "skills": [],
            "experience_years": 0,
            "education": [],
            "certifications": [],
            "job_titles": [],
            "industries": []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'skills:' in line.lower():
                current_section = 'skills'
            elif 'experience:' in line.lower():
                current_section = 'experience'
            elif 'education:' in line.lower():
                current_section = 'education'
            elif 'certifications:' in line.lower():
                current_section = 'certifications'
            elif 'job titles:' in line.lower() or 'positions:' in line.lower():
                current_section = 'job_titles'
            elif 'industries:' in line.lower():
                current_section = 'industries'
            elif line and current_section:
                if current_section == 'experience' and any(char.isdigit() for char in line):
                    years = re.findall(r'\d+', line)
                    if years:
                        result['experience_years'] = int(years[0])
                elif current_section in result:
                    if isinstance(result[current_section], list):
                        result[current_section].extend([item.strip() for item in line.split(',')])
        
        return result

class CVParser:
    def __init__(self, openai_api_key: str):
        self.llm = OpenAI(
            openai_api_key=openai_api_key,
            temperature=0.1,
            model_name="gpt-3.5-turbo-instruct"
        )
        self.parser = CVOutputParser()
        self._setup_chain()
    
    def _setup_chain(self):
        template = """
        Analyze the following CV/Resume text and extract structured information in JSON format.
        
        CV Text:
        {cv_text}
        
        Extract the following information and return as valid JSON:
        {{
            "skills": [list of technical and soft skills],
            "experience_years": total years of relevant work experience (integer),
            "education": [list of degrees, institutions, and graduation years],
            "certifications": [list of professional certifications],
            "job_titles": [list of previous job titles/positions],
            "industries": [list of industries worked in],
            "key_achievements": [list of notable achievements or accomplishments],
            "languages": [list of languages spoken],
            "summary": "brief professional summary"
        }}
        
        Be thorough and extract as much relevant information as possible. For skills, include both explicitly mentioned skills and those that can be inferred from job descriptions and projects.
        """
        
        self.prompt = PromptTemplate(
            input_variables=["cv_text"],
            template=template
        )
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file_content: bytes) -> str:
        try:
            doc_file = BytesIO(file_content)
            doc = Document(doc_file)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting text from DOCX: {str(e)}")
    
    def extract_text_from_txt(self, file_content: bytes) -> str:
        try:
            return file_content.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1').strip()
            except Exception as e:
                raise ValueError(f"Error extracting text from TXT: {str(e)}")
    
    def parse_cv(self, file_content: bytes, filename: str, cv_name: str) -> CVData:
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            cv_text = self.extract_text_from_pdf(file_content)
        elif file_extension in ['docx', 'doc']:
            cv_text = self.extract_text_from_docx(file_content)
        elif file_extension == 'txt':
            cv_text = self.extract_text_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        if not cv_text.strip():
            raise ValueError("No text content found in the uploaded file")
        
        try:
            parsed_data = self.chain.run(cv_text=cv_text)
        except Exception as e:
            parsed_data = {
                "skills": [],
                "experience_years": 0,
                "education": [],
                "certifications": [],
                "job_titles": [],
                "industries": [],
                "error": str(e)
            }
        
        cv_id = f"cv_{hash(cv_text + cv_name)}_{len(cv_text)}"
        
        return CVData(
            id=cv_id,
            name=cv_name,
            content=cv_text,
            skills=parsed_data.get("skills", []),
            experience_years=parsed_data.get("experience_years", 0),
            education=parsed_data.get("education", []),
            certifications=parsed_data.get("certifications", []),
            job_titles=parsed_data.get("job_titles", []),
            industries=parsed_data.get("industries", []),
            parsed_data=parsed_data
        )
    
    def update_cv_analysis(self, cv_data: CVData) -> CVData:
        try:
            updated_data = self.chain.run(cv_text=cv_data.content)
            cv_data.skills = updated_data.get("skills", cv_data.skills)
            cv_data.experience_years = updated_data.get("experience_years", cv_data.experience_years)
            cv_data.education = updated_data.get("education", cv_data.education)
            cv_data.certifications = updated_data.get("certifications", cv_data.certifications)
            cv_data.job_titles = updated_data.get("job_titles", cv_data.job_titles)
            cv_data.industries = updated_data.get("industries", cv_data.industries)
            cv_data.parsed_data = updated_data
        except Exception as e:
            cv_data.parsed_data["update_error"] = str(e)
        
        return cv_data