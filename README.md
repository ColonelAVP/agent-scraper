# AI-Based Website Scraper API

This is a FastAPI-based application that scrapes website homepage content and extracts the following information:
- **Industry**
- **Company Size**
- **Location**

The application is secured with an Authorization header and returns structured JSON responses.

---

## Features
- Extracts information from the homepage of a given URL.
- Secure API endpoint with a secret key.
- Provides industry insights, company size estimation, and location detection.
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
