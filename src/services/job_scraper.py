import requests
import re
import time
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
import json
from src.models.data_models import JobPosting

class JobOutputParser(BaseOutputParser):
    def parse(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._extract_fallback(text)
    
    def _extract_fallback(self, text: str) -> Dict[str, Any]:
        result = {
            "requirements": [],
            "skills_required": [],
            "experience_required": 0,
            "job_type": None,
            "industry": None,
            "key_responsibilities": []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'requirements:' in line.lower():
                current_section = 'requirements'
            elif 'skills:' in line.lower():
                current_section = 'skills_required'
            elif 'experience:' in line.lower():
                current_section = 'experience'
            elif 'responsibilities:' in line.lower():
                current_section = 'key_responsibilities'
            elif line and current_section:
                if current_section == 'experience' and any(char.isdigit() for char in line):
                    years = re.findall(r'\d+', line)
                    if years:
                        result['experience_required'] = int(years[0])
                elif current_section in ['requirements', 'skills_required', 'key_responsibilities']:
                    if line.startswith('-') or line.startswith('•'):
                        result[current_section].append(line[1:].strip())
                    elif ',' in line:
                        result[current_section].extend([item.strip() for item in line.split(',')])
                    else:
                        result[current_section].append(line)
        
        return result

class LinkedInJobScraper:
    def __init__(self, openai_api_key: str):
        self.llm = OpenAI(
            openai_api_key=openai_api_key,
            temperature=0.1,
            model_name="gpt-3.5-turbo-instruct"
        )
        self.parser = JobOutputParser()
        self._setup_chain()
        self.driver = None
    
    def _setup_chain(self):
        template = """
        Analyze the following job posting text and extract structured information in JSON format.
        
        Job Posting Text:
        {job_text}
        
        Extract the following information and return as valid JSON:
        {{
            "requirements": [list of job requirements and qualifications],
            "skills_required": [list of technical and soft skills required],
            "experience_required": minimum years of experience required (integer, 0 if not specified),
            "job_type": "full-time/part-time/contract/internship/remote",
            "industry": "industry or sector",
            "key_responsibilities": [list of main job responsibilities],
            "education_required": [list of education requirements],
            "preferred_qualifications": [list of preferred but not required qualifications],
            "company_benefits": [list of benefits mentioned],
            "salary_indicators": "any salary or compensation information mentioned"
        }}
        
        Be thorough and extract as much relevant information as possible. Focus especially on technical skills, years of experience, and specific requirements.
        """
        
        self.prompt = PromptTemplate(
            input_variables=["job_text"],
            template=template
        )
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    def _setup_driver(self):
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                raise Exception(f"Failed to initialize Chrome driver: {str(e)}")
    
    def _close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _extract_linkedin_job_id(self, url: str) -> Optional[str]:
        job_id_pattern = r'/jobs/view/(\d+)'
        match = re.search(job_id_pattern, url)
        return match.group(1) if match else None
    
    def _scrape_with_selenium(self, url: str) -> Dict[str, str]:
        self._setup_driver()
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            result = {
                'title': '',
                'company': '',
                'location': '',
                'description': ''
            }
            
            try:
                title_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.top-card-layout__title, h1[data-automation-id='jobPostingHeader'], .jobs-unified-top-card__job-title"))
                )
                result['title'] = title_element.text.strip()
            except TimeoutException:
                pass
            
            try:
                company_selectors = [
                    ".jobs-unified-top-card__company-name a",
                    ".jobs-unified-top-card__company-name",
                    "[data-automation-id='jobPostingCompanyLink']",
                    ".top-card-layout__card .top-card-layout__entity-info a"
                ]
                
                for selector in company_selectors:
                    try:
                        company_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        result['company'] = company_element.text.strip()
                        break
                    except:
                        continue
            except:
                pass
            
            try:
                location_selectors = [
                    ".jobs-unified-top-card__bullet",
                    ".jobs-unified-top-card__primary-description",
                    "[data-automation-id='jobPostingLocation']"
                ]
                
                for selector in location_selectors:
                    try:
                        location_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        result['location'] = location_element.text.strip()
                        break
                    except:
                        continue
            except:
                pass
            
            try:
                description_selectors = [
                    ".jobs-description-content__text",
                    ".jobs-box__html-content",
                    "[data-automation-id='jobPostingDescription']",
                    ".jobs-description__content"
                ]
                
                for selector in description_selectors:
                    try:
                        description_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        result['description'] = description_element.text.strip()
                        break
                    except:
                        continue
            except:
                pass
            
            return result
            
        except Exception as e:
            raise Exception(f"Error scraping with Selenium: {str(e)}")
    
    def _scrape_with_requests(self, url: str) -> Dict[str, str]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            result = {
                'title': '',
                'company': '',
                'location': '',
                'description': ''
            }
            
            title_selectors = ['h1', '.job-title', '[data-automation-id="jobPostingHeader"]']
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            
            company_selectors = ['.company', '.company-name', '[data-automation-id="jobPostingCompanyLink"]']
            for selector in company_selectors:
                element = soup.select_one(selector)
                if element:
                    result['company'] = element.get_text(strip=True)
                    break
            
            location_selectors = ['.location', '.job-location', '[data-automation-id="jobPostingLocation"]']
            for selector in location_selectors:
                element = soup.select_one(selector)
                if element:
                    result['location'] = element.get_text(strip=True)
                    break
            
            description_selectors = ['.job-description', '.description', '[data-automation-id="jobPostingDescription"]']
            for selector in description_selectors:
                element = soup.select_one(selector)
                if element:
                    result['description'] = element.get_text(strip=True)
                    break
            
            return result
            
        except Exception as e:
            raise Exception(f"Error scraping with requests: {str(e)}")
    
    def scrape_job(self, url: str) -> JobPosting:
        if 'linkedin.com' not in url.lower():
            raise ValueError("Only LinkedIn job URLs are supported")
        
        job_data = None
        error_messages = []
        
        try:
            job_data = self._scrape_with_selenium(url)
        except Exception as e:
            error_messages.append(f"Selenium scraping failed: {str(e)}")
            
            try:
                job_data = self._scrape_with_requests(url)
            except Exception as e2:
                error_messages.append(f"Requests scraping failed: {str(e2)}")
                raise Exception(f"All scraping methods failed: {'; '.join(error_messages)}")
        finally:
            self._close_driver()
        
        if not job_data or not job_data.get('description'):
            raise ValueError("Could not extract job description from the provided URL")
        
        try:
            parsed_job_data = self.chain.run(job_text=job_data['description'])
        except Exception as e:
            parsed_job_data = {
                "requirements": [],
                "skills_required": [],
                "experience_required": 0,
                "job_type": None,
                "industry": None,
                "parse_error": str(e)
            }
        
        job_id = self._extract_linkedin_job_id(url) or f"job_{hash(url)}_{int(time.time())}"
        
        return JobPosting(
            id=job_id,
            url=url,
            title=job_data.get('title', 'Unknown Title'),
            company=job_data.get('company', 'Unknown Company'),
            location=job_data.get('location', 'Unknown Location'),
            description=job_data.get('description', ''),
            requirements=parsed_job_data.get('requirements', []),
            skills_required=parsed_job_data.get('skills_required', []),
            experience_required=parsed_job_data.get('experience_required', 0),
            job_type=parsed_job_data.get('job_type'),
            industry=parsed_job_data.get('industry'),
            raw_data=parsed_job_data
        )
    
    def __del__(self):
        self._close_driver()