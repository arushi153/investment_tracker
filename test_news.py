import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

query = '"Tourism" investment Jaipur Rajasthan India when:1y'
encoded_query = urllib.parse.quote_plus(query)
rss_url = "https://news.google.com/rss/search?q=" + encoded_query + "&hl=en-IN&gl=IN&ceid=IN:en"
print(rss_url)

req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=20) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    items = root.findall(".//item")
    print(f"Found {len(items)} items.")
    for item in items[:2]:
        print(item.findtext("title"))
except Exception as e:
    print(e)
