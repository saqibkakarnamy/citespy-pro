from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import os

CITATION_SITES = {
    "google.com": "Google Business Profile",
    "yelp.com": "Yelp",
    "facebook.com": "Facebook Business",
    "linkedin.com": "LinkedIn",
    "yellowpages.com": "Yellow Pages",
    "bing.com": "Bing Places",
    "foursquare.com": "Foursquare",
    "manta.com": "Manta",
    "bbb.org": "Better Business Bureau",
    "trustpilot.com": "Trustpilot",
    "tripadvisor.com": "TripAdvisor",
    "hotfrog.com": "Hotfrog",
    "superpages.com": "Superpages",
    "mapquest.com": "MapQuest",
    "thumbtack.com": "Thumbtack",
    "bark.com": "Bark.com",
    "clutch.co": "Clutch.co",
    "g2.com": "G2",
    "houzz.com": "Houzz",
    "angi.com": "Angi",
    "brownbook.net": "Brownbook",
    "showmelocal.com": "ShowMeLocal",
    "citysearch.com": "Citysearch",
    "n49.com": "n49",
    "chamberofcommerce.com": "Chamber of Commerce",
    "spoke.com": "Spoke",
}

def get_domain(url):
    url = url.replace("https://","").replace("http://","").replace("www.","")
    return url.split("/")[0].split("?")[0]

def serpapi_search(query, api_key, num=10):
    """Search using SerpApi"""
    params = urllib.parse.urlencode({
        "q": query,
        "num": num,
        "api_key": api_key,
        "engine": "google"
    })
    req_url = f"https://serpapi.com/search?{params}"
    req = urllib.request.Request(req_url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    results = []
    for r in data.get("organic_results", []):
        link = r.get("link","")
        title = r.get("title","")
        if link:
            results.append({"url": link, "title": title})
    return results

def find_citations(business_name, serpapi_key):
    """Find citations for a business using SerpApi"""
    query = f'"{business_name}"'
    try:
        results = serpapi_search(query, serpapi_key, 20)
        found = []
        seen_sites = set()
        for r in results:
            url = r["url"]
            domain = get_domain(url)
            for site_key, site_name in CITATION_SITES.items():
                if site_key in domain and site_name not in seen_sites:
                    seen_sites.add(site_name)
                    found.append({
                        "name": site_name,
                        "url": url,
                        "title": r["title"]
                    })
        return found
    except:
        return []

def find_competitors(site_url, niche, location, serpapi_key):
    """Find real competitors via SerpApi"""
    domain = get_domain(site_url)
    query = f'{niche} {location} -site:{domain}'
    try:
        results = serpapi_search(query, serpapi_key, 10)
        competitors = []
        seen = set()
        for r in results:
            d = get_domain(r["url"])
            if d not in seen and domain not in d and "google" not in d and "yelp" not in d:
                seen.add(d)
                competitors.append({
                    "domain": d,
                    "url": r["url"],
                    "title": r.get("title",""),
                    "citations": [],
                    "citationCount": 0
                })
        return competitors[:5]
    except Exception as e:
        raise Exception(f"Search failed: {str(e)}")

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(length))
            site_url = body.get("url","")
            niche = body.get("niche","business")
            location = body.get("location","")
            serpapi_key = body.get("serpapi_key","")

            if not serpapi_key:
                raise Exception("SerpApi key missing")

            domain = get_domain(site_url)
            competitors = find_competitors(site_url, niche, location, serpapi_key)

            # Find citations for each competitor
            for comp in competitors:
                biz_name = comp["title"] or comp["domain"].split(".")[0]
                comp["citations"] = find_citations(biz_name, serpapi_key)
                comp["citationCount"] = len(comp["citations"])

            result = {
                "domain": domain,
                "competitors": competitors,
                "totalFound": len(competitors)
            }

            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass
