from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re

CITATION_SITES = [
    "google.com/maps", "yelp.com", "facebook.com", "linkedin.com",
    "yellowpages.com", "bing.com/maps", "foursquare.com", "manta.com",
    "bbb.org", "trustpilot.com", "tripadvisor.com", "hotfrog.com",
    "superpages.com", "citysearch.com", "mapquest.com", "thumbtack.com",
    "bark.com", "clutch.co", "g2.com", "houzz.com", "angi.com",
    "brownbook.net", "showmelocal.com", "cylex.us.com", "n49.com",
]

CITATION_NAMES = {
    "google.com/maps": "Google Business Profile",
    "yelp.com": "Yelp",
    "facebook.com": "Facebook Business",
    "linkedin.com": "LinkedIn",
    "yellowpages.com": "Yellow Pages",
    "bing.com/maps": "Bing Places",
    "foursquare.com": "Foursquare",
    "manta.com": "Manta",
    "bbb.org": "Better Business Bureau",
    "trustpilot.com": "Trustpilot",
    "tripadvisor.com": "TripAdvisor",
    "hotfrog.com": "Hotfrog",
    "superpages.com": "Superpages",
    "citysearch.com": "Citysearch",
    "mapquest.com": "MapQuest",
    "thumbtack.com": "Thumbtack",
    "bark.com": "Bark.com",
    "clutch.co": "Clutch.co",
    "g2.com": "G2",
    "houzz.com": "Houzz",
    "angi.com": "Angi",
    "brownbook.net": "Brownbook",
    "showmelocal.com": "ShowMeLocal",
    "cylex.us.com": "Cylex",
    "n49.com": "n49",
}

def get_domain(url):
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0]

def search_google(query, num=5):
    """Search Google and return result URLs"""
    try:
        encoded = urllib.parse.quote(query)
        req_url = f"https://www.google.com/search?q={encoded}&num={num}"
        req = urllib.request.Request(req_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        urls = re.findall(r'href="(https://[^"]+)"', html)
        clean = []
        skip = ["google.", "youtube.", "accounts.", "support.", "maps.google"]
        for u in urls:
            if not any(s in u for s in skip) and u not in clean:
                clean.append(u)
        return clean[:num]
    except Exception as e:
        return []

def find_citations(business_name, domain):
    """Find where a business has citations"""
    found = []
    query = f'"{business_name}" OR site:*.{domain}'
    results = search_google(query + " business listing directory", 20)
    
    for result_url in results:
        for site in CITATION_SITES:
            if site in result_url and CITATION_NAMES.get(site) not in [f["name"] for f in found]:
                found.append({
                    "name": CITATION_NAMES.get(site, site),
                    "url": result_url,
                    "site": site
                })
    return found

def find_competitors(site_url, niche, location):
    """Find real competitors via Google search"""
    domain = get_domain(site_url)
    query = f'{niche} {location} -site:{domain}'
    results = search_google(query, 8)
    
    competitors = []
    seen = set()
    for url in results:
        d = get_domain(url)
        if d not in seen and domain not in d:
            seen.add(d)
            competitors.append({
                "domain": d,
                "url": url,
                "citations": [],
                "citationCount": 0
            })
    return competitors[:5]

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            site_url = body.get("url", "")
            niche = body.get("niche", "business")
            location = body.get("location", "")

            domain = get_domain(site_url)

            # Step 1: Find competitors
            competitors = find_competitors(site_url, niche, location)

            # Step 2: For each competitor find citations
            for comp in competitors:
                biz_name = comp["domain"].split(".")[0]
                citations = find_citations(biz_name, comp["domain"])
                comp["citations"] = citations
                comp["citationCount"] = len(citations)

            result = {
                "domain": domain,
                "competitors": competitors,
                "totalFound": len(competitors)
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass
