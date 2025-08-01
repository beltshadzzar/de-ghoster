# LinkedIn Job Analyzer

An AI-powered web application that analyzes LinkedIn job postings against multiple CV versions to calculate application success probability and provide data-driven recommendations.

## Features

- **CV Management**: Upload and parse multiple CV versions (PDF, DOCX, TXT)
- **Job Analysis**: Scrape LinkedIn job postings and analyze match quality
- **AI-Powered Scoring**: 
  - Qualification fit (60%)
  - Competition analysis (25%) 
  - Strategic factors (15%)
- **Smart Recommendations**: Apply/Skip/Maybe recommendations with confidence thresholds
- **Historical Tracking**: Track applications, responses, and success rates
- **Analytics Dashboard**: Visualize your job search performance
- **Streamlit Interface**: User-friendly web interface

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd de-ghoster
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langchain_api_key_here
LANGCHAIN_PROJECT=linkedin-job-analyzer
```

### 3. Run the Application

```bash
streamlit run main.py
```

## Usage

### Step 1: Upload Your CV
- Go to the "CV Management" tab
- Upload your CV in PDF, DOCX, or TXT format
- Give it a descriptive name (e.g., "Software Engineer CV v2.1")
- The AI will automatically extract skills, experience, education, and other relevant information

### Step 2: Analyze Jobs
- Go to the "Job Analysis" tab
- Paste a LinkedIn job URL
- Click "Analyze Job"
- View your match score, recommendation, and detailed analysis

### Step 3: Track Applications
- Use the application tracking section to log when you apply
- Track responses, interviews, and outcomes
- Build a history of your job search performance

### Step 4: Review Analytics
- Go to the "Analytics" tab
- View success rates, score distributions, and trends
- Optimize your job search strategy based on data

## Scoring System

The application uses a weighted scoring system:

- **Qualification Score (60%)**: How well your skills and experience match the job requirements
- **Competition Score (25%)**: How competitive you are against other candidates
- **Strategic Score (15%)**: Career growth potential and strategic fit

## Deployment on Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add your environment variables in the secrets section
5. Deploy!

### Required Secrets for Streamlit Cloud

In your Streamlit Cloud secrets, add:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
LANGCHAIN_TRACING_V2 = "true"
LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
LANGCHAIN_API_KEY = "your_langchain_api_key_here"
LANGCHAIN_PROJECT = "linkedin-job-analyzer"
```

## File Structure

```
de-ghoster/
├── main.py                 # Main Streamlit application
├── requirements.txt        # Python dependencies
├── packages.txt           # System packages for Streamlit Cloud
├── .env.example           # Environment variables template
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py # Pydantic data models
│   └── services/
│       ├── cv_parser.py   # CV parsing with LangChain
│       ├── job_scraper.py # LinkedIn job scraping
│       ├── job_matcher.py # AI matching algorithm
│       └── database.py    # SQLite database management
├── data/                  # Database and file storage
└── logs/                  # Application logs
```

## API Keys Required

- **OpenAI API Key**: For CV parsing and job analysis
- **LangChain API Key** (optional): For tracing and monitoring

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**: If you encounter selenium/chrome driver issues, ensure chromium is installed (handled automatically on Streamlit Cloud)

2. **OpenAI API Errors**: Check your API key and usage limits

3. **LinkedIn Scraping Issues**: LinkedIn may block requests; the app includes fallback mechanisms

### Local Development

For local development, you may need to install Chrome/Chromium:

```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# macOS
brew install chromium
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational and defensive security purposes only. Please respect LinkedIn's terms of service and rate limits when scraping job postings.

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the logs in the `logs/` directory
3. Open an issue on GitHub with error details

---

Built with ❤️ using Streamlit, LangChain, and OpenAI