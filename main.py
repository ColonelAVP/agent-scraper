from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
import spacy
from geopy.geocoders import Nominatim
from opencage.geocoder import OpenCageGeocode
import os
from dotenv import load_dotenv
from spacy.matcher import Matcher
# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "default_key")
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", "")

# Initialize FastAPI app and required models
app = FastAPI()
nlp = spacy.load("en_core_web_sm")

# Industry keywords for classification
industry_keywords = {
    "finance": ["banking", "financial", "investment", "insurance", "wealth"],
    "healthcare": ["medical", "healthcare", "hospital", "clinic", "pharma"],
    "technology": ["tech", "software", "cloud", "ai", "data science"],
    # Additional industries omitted for brevity...
}

# Pydantic models for request and response validation
class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapeResponse(BaseModel):
    company_name: str
    locations: list
    industry: str
    industry_size: str
    contact_info: dict
    tagline: str


def scrape_website(url: str) -> tuple:
    """
    Fetches and cleans HTML content from the provided URL.
    """
    headers = {"User-Agent": "MyAppScraper/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="Request timed out while accessing the website.")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Unable to connect to the website.")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=response.status_code, detail=f"HTTP error occurred: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Clean the HTML content by removing script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    cleaned_text = " ".join(soup.get_text().split())
    return response.text, cleaned_text


def extract_company_name(doc, cleaned_text: str, html: str) -> str:
    """
    Extracts the name of the company using a hybrid approach of spaCy and Transformers.

    Args:
        doc (spacy.tokens.Doc): Processed spaCy doc.
        cleaned_text (str): The cleaned text content of the webpage.
        html (str): The raw HTML content.

    Returns:
        str: The detected company name or 'Unknown' if no name is found.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else ""

    # Clean title
    for sep in ["|", "-", ":", "–", "•"]:
        if sep in title:
            title = title.split(sep)[0].strip()

    # Extract organizations from spaCy doc
    org_entities = [ent.text for ent in doc.ents if ent.label_ == "ORG"]

    # Filter out irrelevant terms
    blacklist = ["Financial", "Healthcare", "Solutions", "Lists", "Database", "Ecosystem"]
    org_entities = [org for org in org_entities if not any(kw.lower() in org.lower() for kw in blacklist)]
    print("org_entities", org_entities)
    # Count occurrences and add context-aware scoring
    entity_counts = Counter(org_entities)
    for org in org_entities:
        if org.lower() in title.lower():  # Boost if entity matches the title
            entity_counts[org] += 5
        if "company" in cleaned_text.lower() and org in cleaned_text:  # Boost for context
            entity_counts[org] += 3

    if entity_counts:
        return max(entity_counts, key=lambda x: entity_counts[x])
    return title if title else "Unknown"

def extract_locations(doc) -> list:
    """
    Extracts and refines location data using spaCy and OpenCage.
    """
    gpe_entities = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
    return parse_with_opencage(gpe_entities)

def extract_company_size(doc) -> str:
    """
    Extracts the company size using spaCy's NER and rule-based matching.

    Args:
        doc (spacy.tokens.Doc): Processed spaCy doc.

    Returns:
        str: Detected company size ('Small', 'Medium', 'Large', or 'Unknown').
    """
    matcher = Matcher(nlp.vocab)

    # Define patterns for explicit mentions
    patterns = [
        [{"LOWER": "team"}, {"LOWER": "of"}, {"IS_DIGIT": True}, {"LOWER": "people"}],
        [{"IS_DIGIT": True}, {"LOWER": "employees"}],
        [{"IS_DIGIT": True}, {"LOWER": "staff"}],
        [{"LOWER": "over"}, {"IS_DIGIT": True}, {"LOWER": "employees"}],
        [{"LOWER": "fewer"}, {"LOWER": "than"}, {"IS_DIGIT": True}, {"LOWER": "employees"}],
    ]
    matcher.add("COMPANY_SIZE", patterns)

    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        size = int("".join(filter(str.isdigit, span.text)))  # Extract the number

        # Categorize size
        if size < 50:
            return "Small"
        elif size < 500:
            return "Medium"
        else:
            return "Large"

    # If no explicit match is found
    return "Unknown"

def parse_with_opencage(locations: list) -> list:
    """
    Resolves raw location strings into structured city and country using OpenCage.
    """
    geocoder = OpenCageGeocode(OPENCAGE_API_KEY)
    structured_locations = []

    for location in set(locations):  # Deduplicate locations
        try:
            result = geocoder.geocode(location)
            if result:
                components = result[0]['components']
                city = components.get('city', components.get('town', components.get('village')))
                country = components.get('country')
                if country:
                    if city:
                        structured_locations.append({"city": city, "country": country})
                    else:
                        structured_locations.append({"country": country})
        except Exception:
            continue  # Skip problematic locations

    return structured_locations


def determine_specific_industry(doc, cleaned_text: str, industry_keywords: dict) -> dict:
    """
    Identifies the company's industry using keyword matching and context.
    """
    industry_scores = defaultdict(int)
    contextual_anchors = ["industry", "sector", "solutions for"]

    # Match keywords in text and prioritize near anchors
    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in cleaned_text.lower():
                for anchor in contextual_anchors:
                    if f"{anchor} {keyword}" in cleaned_text.lower() or f"{keyword} {anchor}" in cleaned_text.lower():
                        industry_scores[industry] += 2
                industry_scores[industry] += 1

    # Match keywords within organization entities
    for ent in doc.ents:
        if ent.label_ == "ORG":
            for industry, keywords in industry_keywords.items():
                for keyword in keywords:
                    if keyword in ent.text.lower():
                        industry_scores[industry] += 3

    # Return the top industry or "Unknown"
    sorted_scores = sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)
    if not sorted_scores or sorted_scores[0][1] == 0:
        return {"top_industry": "Unknown", "scores": []}

    max_score = sorted_scores[0][1]
    top_industries = [industry for industry, score in sorted_scores if score == max_score]
    return {"top_industry": ", ".join(top_industries), "scores": sorted_scores}


def extract_contact_info(html: str) -> dict:
    """
    Extracts email addresses and phone numbers from HTML content.
    """
    soup = BeautifulSoup(html, "html.parser")
    contact_info = {"emails": [], "phones": []}

    # Extract email addresses
    for link in soup.find_all("a", href=True):
        if "mailto:" in link["href"]:
            contact_info["emails"].append(link["href"].replace("mailto:", "").strip())

    # Extract phone numbers
    for link in soup.find_all("a", href=True):
        if "tel:" in link["href"]:
            contact_info["phones"].append(link["href"].replace("tel:", "").strip())

    # Deduplicate results
    contact_info["emails"] = list(set(contact_info["emails"]))
    contact_info["phones"] = list(set(contact_info["phones"]))

    return contact_info

def extract_tagline(html: str) -> str:
    """
    Extracts the tagline or mission statement from the HTML content.

    Args:
        html (str): The raw HTML content of the webpage.

    Returns:
        str: The extracted tagline or 'Unknown' if not found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Define a list of generic words to ignore
    generic_words = {"home", "welcome", "contact", "about"}

    # Step 1: Extract from headers (h1, h2, h3)
    for tag in ["h1", "h2", "h3"]:
        header = soup.find(tag)
        if header:
            text = header.get_text(strip=True)
            if text.lower() not in generic_words and len(text.split()) > 1:  # Avoid generic or too-short text
                return text

    # Step 2: Extract from title tag
    title = soup.title.string.strip() if soup.title else None
    if title and title.lower() not in generic_words and len(title.split()) > 1:
        return title

    # Step 3: Extract from meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"].strip()

    return "Unknown"

@app.post("/scrape", response_model=ScrapeResponse)
def scrape_homepage(request: ScrapeRequest, authorization: str = Header(None)):
    """
    Endpoint to scrape and classify homepage content.
    """
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        html_content, cleaned_text = scrape_website(request.url)
        doc = nlp(cleaned_text)

        return ScrapeResponse(
            company_name=extract_company_name(doc, cleaned_text, html_content),
            locations=extract_locations(doc),
            industry=determine_specific_industry(doc, cleaned_text, industry_keywords)["top_industry"],
            industry_size=extract_company_size(doc),
            contact_info=extract_contact_info(html_content),
            tagline=extract_tagline(html_content),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
