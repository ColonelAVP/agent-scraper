# Agent Scraper (AI-Based Website Scraper API)

This is a FastAPI-based application that scrapes website homepage content and extracts the following information:
- **Industry**
- **Company Size**
- **Location**

The application is secured with an Authorization header and returns structured JSON responses.

---

## Features
- Extracts information from the homepage of a given URL.
- Secure API endpoint with a secret key.
- Provides industry insights, company size estimation, and location detection with additional information like name of the org, contact info if available, tagline if available
- Deployed on Render with public access.

---

## Requirements
- **Python 3.10+**
- **Docker** (optional for containerized deployment)
- API keys for secure authentication and geolocation services.

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository_url>
cd <repository_name>
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables
Create a .env file in the root directory with the following content:
```bash
SECRET_KEY=<your_secret_key>
OPENCAGE_API_KEY=<your_opencage_api_key>
```

### 5. Run the Application
```bash
uvicorn main:app --reload
```

## Deployment
This application is deployed on Render. You can access it using the link below: [Deployment](https://agent-scraper.onrender.com/)

---
## API Usage
- Endpoint

  ```
  POST  /scrape
  ```
  
- Headers
**Authorization**: Must include the secret key.

#### Request Body
```
{
  "url": "https://example.com"
}
```

#### Response Example
```
{
  "company_name": "Example Inc.",
  "locations": ["New York, USA"],
  "industry": "Technology",
  "industry_size": "Medium",
  "tagline": "Connecting the world.",
  "contact_info": {
    "emails": ["contact@example.com"],
    "phones": ["+123456789"]
  }
}
```

- Error Responses
- **401 Unauthorized**: Secret key is missing or invalid.
  
- **400 Bad Request**: Invalid URL or inaccessible website.

---

## Technologies Used
- **FastAPI**: For building the web application.
- **BeautifulSoup**: For scraping HTML content.
- **SpaCy**: For natural language processing.
- **OpenCage Geocoder**: For location parsing and geocoding.
