from flask import Flask, jsonify, render_template, request
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import ast
import csv
import html
import json
import os
import re
import ssl
import xml.etree.ElementTree as ET
from duckduckgo_search import DDGS

# Disable SSL verification for macOS Python environments
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
 
app = Flask(__name__)
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYWORDS_FILE = os.path.join(BASE_DIR, "keywords.csv")
SEARCH_EXAMPLES_FILE = os.path.join(BASE_DIR, "searchexamples.txt")
 
LOCATION_DATA = {
    "India": {
        "Andhra Pradesh": [], "Arunachal Pradesh": [], "Assam": [], "Bihar": [],
        "Chhattisgarh": [], "Goa": [], "Gujarat": [], "Haryana": [],
        "Himachal Pradesh": [], "Jharkhand": [], "Karnataka": [], "Kerala": [],
        "Madhya Pradesh": [], "Maharashtra": [], "Manipur": [], "Meghalaya": [],
        "Mizoram": [], "Nagaland": [], "Odisha": [], "Punjab": [],
        "Rajasthan": [], "Sikkim": [], "Tamil Nadu": [], "Telangana": [],
        "Tripura": [], "Uttar Pradesh": [], "Uttarakhand": [], "West Bengal": [],
        "Andaman and Nicobar Islands": [], "Chandigarh": [], 
        "Dadra and Nagar Haveli and Daman and Diu": [], "Delhi": [], 
        "Jammu and Kashmir": [], "Ladakh": [], "Lakshadweep": [], "Puducherry": []
    }
}
 
ALL_COUNTRIES = sorted([
    "Afghanistan", "Australia", "Austria", "Bangladesh", "Belgium", "Brazil",
    "Canada", "China", "Denmark", "Egypt", "Finland", "France", "Germany",
    "India", "Indonesia", "Ireland", "Italy", "Japan", "Malaysia", "Mexico",
    "Netherlands", "New Zealand", "Norway", "Oman", "Pakistan", "Philippines",
    "Qatar", "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain",
    "Sri Lanka", "Sweden", "Switzerland", "Thailand", "Turkey",
    "United Arab Emirates", "United Kingdom", "United States", "Vietnam"
])
 
DEFAULT_KEYWORDS = [
    {"keyword": "investment", "weight": 10},
    {"keyword": "invest", "weight": 8},
    {"keyword": "mou", "weight": 10},
    {"keyword": "expansion", "weight": 8},
    {"keyword": "plant", "weight": 8},
    {"keyword": "factory", "weight": 8},
    {"keyword": "government", "weight": 5},
    {"keyword": "crore", "weight": 7},
    {"keyword": "million", "weight": 6},
    {"keyword": "billion", "weight": 7},
    {"keyword": "logistics", "weight": 8},
    {"keyword": "solar", "weight": 8},
    {"keyword": "renewable", "weight": 8},
    {"keyword": "tourism", "weight": 8},
    {"keyword": "agriculture", "weight": 8},
    {"keyword": "education", "weight": 8}
]
 
def load_keywords():
    if not os.path.exists(KEYWORDS_FILE):
        return DEFAULT_KEYWORDS
 
    keywords = []
    try:
        with open(KEYWORDS_FILE, "r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file))
 
        if not rows:
            return DEFAULT_KEYWORDS
 
        first_row = [cell.strip().lower() for cell in rows[0]]
        if "keyword" in first_row:
            with open(KEYWORDS_FILE, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    keyword = str(row.get("keyword", "")).strip()
                    if not keyword:
                        continue
                    try:
                        weight = int(row.get("weight", 5))
                    except (TypeError, ValueError):
                        weight = 5
                    keywords.append({"keyword": keyword, "weight": weight})
        else:
            for row in rows:
                for cell in row:
                    keyword = cell.strip()
                    if keyword:
                        keywords.append({"keyword": keyword, "weight": 5})
    except (OSError, csv.Error) as error:
        print("Keyword file error:", error)
        return DEFAULT_KEYWORDS
 
    unique = {item["keyword"].casefold(): item for item in keywords}
    return list(unique.values()) or DEFAULT_KEYWORDS
 
def load_search_examples():
    if not os.path.exists(SEARCH_EXAMPLES_FILE):
        return []
 
    try:
        with open(SEARCH_EXAMPLES_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()
        if not content:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = ast.literal_eval(content)
    except (OSError, SyntaxError, ValueError) as error:
        print("Search examples file error:", error)
        return []
 
    examples = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                examples.append({"query": str(item[0]).strip(), "region": str(item[1]).strip()})
            elif isinstance(item, dict):
                examples.append({
                    "query": str(item.get("query", "")).strip(),
                    "region": str(item.get("region", item.get("state", ""))).strip()
                })
    return examples
 
def clean_html(value):
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()
 
def parse_news_date(value):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None
 
def calculate_score(text, keywords, sector, country, state):
    text_lower = text.casefold()
    score = 0
    matched = []
 
    for item in keywords:
        keyword = str(item.get("keyword", "")).strip()
        if keyword and keyword.casefold() in text_lower:
            score += int(item.get("weight", 5))
            matched.append(keyword)
 
    for term in (sector, country, state):
        if term and term.casefold() in text_lower:
            score += 8
            matched.append(term)
            
    # Determine Viability for the Target State
    if score >= 15:
        target_name = state if state else (country if country else "Region")
        viability_msg = f"✓ Viable for {target_name}"
        is_viable = True
    else:
        target_name = state if state else (country if country else "Region")
        viability_msg = f"✗ Not Viable for {target_name}"
        is_viable = False
 
    return score, list(dict.fromkeys(matched)), viability_msg, is_viable
 
def build_queries(sector):
    queries = [
        f'{sector} investment',
        f'{sector} (expansion OR plant OR facility)',
        f'{sector} cap-ex' 
    ]
 
    clean_queries = []
    for query in queries:
        query = " ".join(query.split())
        if query and query not in clean_queries:
            clean_queries.append(query)
    return clean_queries[:3]
 
def fetch_google_news(query, keywords, sector, country, state):
    articles = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30) # Back to 1 month
    encoded_query = quote_plus(query + " when:30d")
    rss_url = (
        "https://news.google.com/rss/search?"
        + "q=" + encoded_query
        + "&hl=en-US&gl=US&ceid=US:en"
    )
 
    try:
        request_object = Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request_object, context=ssl_context, timeout=20) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
    except Exception as error:
        print("News fetch failed for query", repr(query), ":", repr(error))
        return articles
 
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = clean_html(item.findtext("description") or "")
        source = (item.findtext("source") or "News source").strip()
        published = parse_news_date(item.findtext("pubDate") or "")
 
        if not title or not link or not published or published < cutoff_date:
            continue
 
        score, matched_keywords, viability_msg, is_viable = calculate_score(
            f"{title} {description}", keywords, sector, country, state
        )
        if score <= 0:
            continue
 
        articles.append({
            "title": title,
            "link": link,
            "description": description,
            "source": source,
            "published_at": published.isoformat(),
            "published_display": published.strftime("%d %b %Y, %I:%M %p UTC"),
            "score": score,
            "matched_keywords": matched_keywords,
            "viability_msg": viability_msg,
            "is_viable": is_viable,
            "category": "news"
        })
    return articles
 
def fetch_duckduckgo_results(sector, keywords, country, state, doc_type):
    articles = []
    state_str = f'"{state}" ' if state else ""
    if doc_type == "reports":
        query = f'{state_str}{sector} investment annual report'
        source_name = "Annual Report"
        category = "reports"
    else:
        query = f'{state_str}{sector} investment filetype:pdf'
        source_name = "PDF Document"
        category = "pdfs"
        
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=10)
            if not results: return []
            
            for item in results:
                title = item.get("title", "")
                link = item.get("href", "")
                description = item.get("body", "")
                
                score, matched_keywords, viability_msg, is_viable = calculate_score(
                    f"{title} {description}", keywords, sector, country, state
                )
                if score <= 0: continue
                
                articles.append({
                    "title": title,
                    "link": link,
                    "description": description,
                    "source": source_name,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "published_display": "Recent Web Document",
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "viability_msg": viability_msg,
                    "is_viable": is_viable,
                    "category": category
                })
    except Exception as error:
        print(f"DDG Fetch failed for {doc_type}:", repr(error))
    return articles
 
@app.get("/")
def home():
    return render_template("index.html")
 
@app.get("/api/locations")
def api_locations():
    return jsonify({"countries": ALL_COUNTRIES, "locationData": LOCATION_DATA})
 
@app.get("/api/news")
def api_news():
    sector = request.args.get("sector", "").strip()
    country = request.args.get("country", "").strip()
    state = request.args.get("state", "").strip()
 
    if not sector:
        return jsonify({
            "success": False,
            "message": "Please select a sector.",
            "articles": []
        }), 400
 
    keywords = load_keywords()
    queries = build_queries(sector)
    all_articles = []
 
    for query in queries:
        all_articles.extend(fetch_google_news(
            query, keywords, sector, country, state
        ))
 
    articles_by_title = {}
    for article in all_articles:
        key = article["title"].casefold().strip()
        current = articles_by_title.get(key)
        if current is None or article["score"] > current["score"]:
            articles_by_title[key] = article
 
    articles = list(articles_by_title.values())
    articles.sort(key=lambda item: item["published_at"], reverse=True)
    high_priority = sum(1 for article in articles if article.get("is_viable"))
 
    return jsonify({
        "success": True,
        "total": len(articles),
        "high_priority": high_priority,
        "queries_used": queries,
        "articles": articles
    })
 
def extract_company_name(title):
    """Extract the most likely company/investor name from a news headline."""
    # Remove common noise words from the start
    noise_starts = ["india ", "govt ", "government ", "centre ", "center ",
                    "report:", "analysis:", "exclusive:"]
    clean = title.strip()
    for noise in noise_starts:
        if clean.lower().startswith(noise):
            clean = clean[len(noise):]
    
    # Try to get the subject before common verbs
    split_patterns = [
        r'\s+plans?\s+', r'\s+invests?\s+', r'\s+announces?\s+', r'\s+launches?\s+',
        r'\s+signs?\s+', r'\s+partners?\s+', r'\s+acquires?\s+', r'\s+raises?\s+',
        r'\s+to\s+invest\s+', r'\s+bags?\s+', r'\s+gets?\s+', r'\s+wins?\s+'
    ]
    for pattern in split_patterns:
        parts = re.split(pattern, clean, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1 and len(parts[0].strip()) > 3:
            return parts[0].strip()
    
    # Fallback: first 4 words
    words = clean.split()
    return " ".join(words[:4])

@app.post("/api/find-investor")
def api_find_investor():
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    source = data.get("source", "").strip()
    
    if not title:
        return jsonify({"success": False, "results": []})
    
    company = extract_company_name(title)
    results = []
    
    try:
        with DDGS() as ddgs:
            # Search 1: LinkedIn company page
            linkedin_query = f'"{company}" site:linkedin.com/company'
            linkedin_results = ddgs.text(linkedin_query, max_results=3) or []
            for item in linkedin_results:
                if "linkedin.com" in item.get("href", ""):
                    results.append({
                        "type": "linkedin",
                        "label": "LinkedIn Profile",
                        "title": item.get("title", company),
                        "url": item.get("href", ""),
                        "description": item.get("body", "")[:200]
                    })
            
            # Search 2: LinkedIn people (decision makers)
            people_query = f'"{company}" CEO OR "Managing Director" OR "Head of Investment" site:linkedin.com/in'
            people_results = ddgs.text(people_query, max_results=3) or []
            for item in people_results:
                if "linkedin.com/in" in item.get("href", ""):
                    results.append({
                        "type": "person",
                        "label": "Key Person",
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "description": item.get("body", "")[:200]
                    })
            
            # Search 3: Official website / contact page
            contact_query = f'"{company}" official website contact investor relations'
            contact_results = ddgs.text(contact_query, max_results=2) or []
            for item in contact_results:
                href = item.get("href", "")
                if "linkedin.com" not in href:
                    results.append({
                        "type": "website",
                        "label": "Website / Contact",
                        "title": item.get("title", ""),
                        "url": href,
                        "description": item.get("body", "")[:200]
                    })
    except Exception as e:
        print("Investor search error:", repr(e))
    
    return jsonify({
        "success": True,
        "company": company,
        "results": results[:7]  # limit to 7 results
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
