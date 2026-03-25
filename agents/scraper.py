import httpx
from bs4 import BeautifulSoup
from groq import Groq
import os

client = Groq(api_key=os.environ["GROQ_API_KEY"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_and_clean(url: str) -> str:
    try:
        response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP fetch failed for {url}: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()
    
    raw_text = soup.get_text(separator="\n", strip=True)[:8000]

    system_prompt = """You are a web content cleaner for a competitive intelligence system.
Your job is to extract ONLY the commercially relevant sections from raw webpage text.

Keep:
- Pricing plans, prices, and billing information
- Product features and capabilities
- "New" or "just launched" features
- Call-to-action text (e.g. "Start free trial", "Get started")
- Target customer descriptions
- Company name and main product headline

Remove:
- Legal boilerplate, cookie notices, privacy policies
- Navigation menus, breadcrumbs
- Blog posts, press releases (unless they announce a new feature/price)
- Testimonials and social proof
- Footer links

Return only the cleaned, relevant text. No commentary. No markdown headers."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"URL: {url}\n\nRAW TEXT:\n{raw_text}"}
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    
    cleaned = response.choices[0].message.content.strip()
    return cleaned