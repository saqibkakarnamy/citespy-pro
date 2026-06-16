from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

CITATION_SITES = [
    ("yelp.com", "Yelp"),
    ("facebook.com", "Facebook Business"),
    ("linkedin.com", "LinkedIn"),
    ("yellowpages.com", "Yellow Pages"),
    ("bing.com", "Bing Places"),
    ("foursquare.com", "Foursquare"),
    ("manta.com", "Manta"),
    ("bbb.org", "Better Business Bureau"),
    ("trustpilot.com", "Trustpilot"),
    ("tripadvisor.com", "TripAdvisor"),
    ("hotfrog.com", "Hotfrog"),
    ("superpages.com", "Superpages"),
    ("mapquest.com", "MapQuest"),
    ("thumbtack.com", "Thumbtack"),
    ("bark.com", "Bark.com"),
    ("clutch.co", "Clutch.co"),
    ("g2.com", "G2"),
    ("houzz.com", "Houzz"),
    ("angi.com", "Angi"),
    ("brownbook.net", "Brownbook"),
    ("showmelocal.com", "ShowMeLocal"),
    ("citysearch.com", "Citysearch"),
    ("chamberofcommerce.com", "Chamber of Commerce"),
    ("spoke.com", "Spoke"),
    ("n49.com", "n49"),
    ("cylex.us.com", "Cylex"),
    ("elocal.com", "eLocal"),
    ("alignable.com", "Alignable"),
    ("nextdoor.com", "Nextdoor"),
    ("merchantcircle.com", "MerchantCircle"),
    ("dexknows.com", "DexKnows"),
    ("whitepages.com", "Whitepages"),
    ("ezlocal.com", "EZlocal"),
    ("opendi.us", "Opendi"),
    ("zipleaf.com", "Zipleaf"),
]

def get_domain(url):
    url = url.replace("https://","").replace("http://","").replace("www.","")
    return url.split("/")[0].split("?")[0]

def serpapi_search(query, api_key, num=10):
    params = urllib.parse.urlencode({
        "q": query,
        "num": num,
        "api_key": api_key,
        "engine": "google"
    })
    req = urllib.request.Request(
        f"https://serpapi.com/search?{params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    results = []
    for r in data.get("organic_results", []):
        if r.get("link"):
            results.append({"url": r["link"], "title": r.get("title","")})
    return results

def find_citations_deep(domain, title, api_key):
    """Deep citation search — check each major directory individually"""
    found = []
    seen = set()

    # Build site query — check all citation sites at once
    site_query = " OR ".join([f"site:{s}" for s, _ in CITATION_SITES])
    queries = [
        f'"{domain}" ({site_query})',
        f'"{title}" ({site_query})',
    ]

    for query in queries:
        try:
            results = serpapi_search(query, api_key, 20)
            for r in results:
                url = r["url"]
                rd = get_domain(url)
                for site_domain, site_name in CITATION_SITES:
                    if site_domain in rd and site_name not in seen:
                        seen.add(site_name)
                        found.append({
                            "name": site_name,
                            "url": url,
                            "title": r["title"]
                        })
        except:
            continue

    return found

def find_competitors(site_url, niche, location, api_key):
    domain = get_domain(site_url)
    query = f'{niche} {location} -site:{domain}'
    try:
        results = serpapi_search(query, api_key, 10)
        competitors = []
        seen = set()
        skip = ["google.", "yelp.", "yellowpages.", "facebook.", "bbb.", "bing."]
        for r in results:
            d = get_domain(r["url"])
            if d not in seen and domain not in d and not any(s in d for s in skip):
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
            api_key = body.get("serpapi_key","")

            if not api_key:
                raise Exception("SerpApi key missing")

            domain = get_domain(site_url)
            competitors = find_competitors(site_url, niche, location, api_key)

            for comp in competitors:
                title = comp["title"].split("|")[0].split("-")[0].strip()
                comp["citations"] = find_citations_deep(comp["domain"], title, api_key)
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
