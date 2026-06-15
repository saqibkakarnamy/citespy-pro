from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

CITATION_SITES = {
    "google.com": "Google Business Profile",
    "yelp.com": "Yelp",
    "facebook.com": "Facebook Business",
    "linkedin.com": "LinkedIn",
    "yellowpages.com": "Yellow Pages",
    "bingplaces.com": "Bing Places",
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
    "showmelocal.com": "ShowMeLocal",
    "brownbook.net": "Brownbook",
    "cylex.us.com": "Cylex",
    "n49.com": "n49",
    "nextdoor.com": "Nextdoor",
}

SERPAPI_KEY = "YOUR_SERPAPI_KEY"  # Free: serpapi.com

def get_domain(url):
    url = url.replace("https://","").replace("http://","").replace("www.","")
    return url.split("/")[0]

def serpapi_search(query, num=10):
    try:
        params = urllib.parse.urlencode({
            "q": query,
            "num": num,
            "api_key": SERPAPI_KEY,
            "engine": "google"
        })
        req = urllib.request.Request(
            f"https://serpapi.com/search.json?{params}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        for r in data.get("organic_results", []):
            link = r.get("link","")
            title = r.get("title","")
            snippet = r.get("snippet","")
            if link:
                results.append({"url": link, "title": title, "snippet": snippet})
        return results
    except Exception as e:
        return []

def find_competitors(site_url, niche, location):
    domain = get_domain(site_url)
    query = f'{niche} {location} -site:{domain}'
    results = serpapi_search(query, 8)
    competitors = []
    seen = set()
    for r in results:
        d = get_domain(r["url"])
        if d not in seen and domain not in d and len(d) > 3:
            seen.add(d)
            competitors.append({
                "domain": d,
                "url": r["url"],
                "title": r.get("title",""),
                "citations": [],
                "citationCount": 0
            })
    return competitors[:5]

def find_citations(domain):
    biz_name = domain.split(".")[0]
    query = f'"{biz_name}" business listing'
    results = serpapi_search(query, 15)
    found = []
    seen_names = set()
    for r in results:
        url = r["url"]
        for site, name in CITATION_SITES.items():
            if site in url and name not in seen_names:
                seen_names.add(name)
                found.append({"name": name, "url": url})
    return found

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(length))
            site_url = body.get("url","")
            niche = body.get("niche","business")
            location = body.get("location","")

            if SERPAPI_KEY == "YOUR_SERPAPI_KEY":
                raise Exception("SERPAPI_KEY nahi daali — analyze.py mein key add karo")

            domain = get_domain(site_url)
            competitors = find_competitors(site_url, niche, location)
            for comp in competitors:
                citations = find_citations(comp["domain"])
                comp["citations"] = citations
                comp["citationCount"] = len(citations)

            result = {"domain": domain, "competitors": competitors, "totalFound": len(competitors)}
            self._respond(200, result)
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
