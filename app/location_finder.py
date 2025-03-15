import requests
import re
import spacy
import time
import os
import gc
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading required language model...")
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Google API credentials
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
    raise ValueError("Missing API credentials. Please check your .env file.")


# Add these lists at the top of your file with other constants
KNOWN_COUNTRIES = {
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium",
    "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia", "Botswana", "Brazil", "Brunei", "Bulgaria",
    "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Chad", "Chile", 
    "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador",
    "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon",
    "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guyana",
    "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kuwait", "Kyrgyzstan",
    "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Mauritania",
    "Mauritius", "Mexico", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique",
    "Myanmar", "Namibia", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria",
    "North Korea", "Norway", "Oman", "Pakistan", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saudi Arabia",
    "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia",
    "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan",
    "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
    "Togo", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
}

COUNTRY_MAPPING = {
    "U.S.": "United States",
    "USA": "United States",
    "U.S.A.": "United States",
    "America": "United States",
    "United States of America": "United States",
    "UK": "United Kingdom",
    "U.K.": "United Kingdom",
    "Britain": "United Kingdom",
    "Great Britain": "United Kingdom",
    "England": "United Kingdom",
    "UAE": "United Arab Emirates",
    "ROK": "South Korea",
    "PRC": "China",
    "ROC": "Taiwan"
}


def extract_main_domain(url):
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    parsed_url = urlparse(url)
    domain = parsed_url.netloc or parsed_url.path
    domain = domain.replace("www.", "")
    return domain

def google_search(company_domain):
    search_queries = [
        f"site:{company_domain} global locations",
        f"site:{company_domain} worldwide offices",
        f"site:{company_domain} international presence"
    ]
    
    all_links = []
    for query in search_queries:
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}"
        try:
            response = requests.get(url)
            results = response.json()
            if "items" in results:
                all_links.extend(item["link"] for item in results["items"])
            time.sleep(1)
        except Exception as e:
            print(f"Search error: {e}")
    
    return list(set(all_links))

def scrape_locations(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract only relevant text to reduce memory
        relevant_tags = soup.find_all(['p', 'div', 'span'], limit=200)  # Limit number of elements
        text = ' '.join(p.get_text() for p in relevant_tags)
        
        # Clean up memory
        del soup
        del response
        gc.collect()
        
        # Process with spaCy in chunks if text is large
        locations = set()
        chunk_size = 10000  # Process text in chunks
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            doc = nlp(chunk)
            
            # Extract locations from named entities
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    locations.add(ent.text)
            
            # Release memory
            del doc
            gc.collect()
        
        return list(locations)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def process_company_domain(domain):
    try:
        print(f"Processing domain: {domain}")
        main_domain = extract_main_domain(domain)
        search_results = google_search(main_domain)
        
        if not search_results:
            return {
                'error': 'No relevant pages found',
                'countries': [],
                'cities': [],
                'others': [],
                'domain': main_domain
            }
        
        # Track mentions
        location_counter = Counter()
        
        # Analyze pages
        for url in search_results[:2]:
            locations = scrape_locations(url)
            for loc in locations:
                # Normalize country names using mapping
                normalized_loc = COUNTRY_MAPPING.get(loc, loc)
                location_counter[normalized_loc] += 1

        gc.collect()
        
        # Separate countries and cities
        countries = []
        cities = []
        others = []
        
        # Process locations and categorize them
        for location, count in location_counter.items():
            confidence = "High" if count > 2 else "Medium" if count == 2 else "Low"
            
            # Check if it's a country
            if location in KNOWN_COUNTRIES or location in COUNTRY_MAPPING:
                normalized_country = COUNTRY_MAPPING.get(location, location)
                # Check if this country is already in the list
                existing_country = next((c for c in countries if c[0] == normalized_country), None)
                if existing_country:
                    existing_country[1] += count
                else:
                    countries.append([normalized_country, count, confidence])
            else:
                # If it's not a country, it's probably a city or other location
                if len(location) > 2 and not location.isnumeric():
                    cities.append([location, count, confidence, ""])
                else:
                    others.append([location, count, confidence])
        
        # Sort strictly alphabetically by name (first element of each list)
        countries = sorted(countries, key=lambda x: x[0].lower())
        cities = sorted(cities, key=lambda x: x[0].lower())
        others = sorted(others, key=lambda x: x[0].lower())
        
        return {
            'countries': countries,
            'cities': cities,
            'others': others,
            'domain': main_domain
        }
        
    except Exception as e:
        print(f"Error in process_company_domain: {e}")
        return {
            'error': str(e),
            'countries': [],
            'cities': [],
            'others': [],
            'domain': domain
        }
