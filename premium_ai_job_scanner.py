#!/usr/bin/env python3
"""
Premium AI Jobs Daily Scanner v1.0
===================================
Searches for GenAI Developer, Applied AI Engineer, RAG Architect and
related senior AI/ML roles across:
  1. Greenhouse ATS public API (30+ premium companies)
  2. Lever ATS public API (15+ premium companies)
  3. LinkedIn public guest job search

Filters:
  - Only AI/ML/GenAI-relevant titles
  - Blocks IT-services / staffing / generic companies
  - Blocks junior / intern / entry-level roles
  - Targets India locations (Mumbai, Bengaluru, Remote, Hyderabad, etc.)
  - Scores listings by quality; surfaces top picks

Output: daily_premium_ai_jobs.md
"""

import json
import re
import logging
import urllib.request
import urllib.parse
import urllib.error
import ssl
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR
OUTPUT_FILE = OUTPUT_DIR / "daily_premium_ai_jobs.md"
LOG_FILE = OUTPUT_DIR / "scanner.log"

# Also write a copy here for the user's convenience
WORKSPACE_OUTPUT = Path.home() / ".gemini" / "antigravity" / "scratch" / "daily_premium_ai_jobs.md"

SEARCH_ROLES = [
    "GenAI Developer",
    "Applied AI Engineer",
    "RAG Architect",
    "Generative AI Engineer",
    "LLM Engineer",
    "AI ML Engineer",
    "Machine Learning Engineer GenAI",
    "NLP Engineer",
    "AI Platform Engineer",
    "Staff ML Engineer",
]

TARGET_LOCATIONS_LOOSE = [
    "mumbai", "bengaluru", "bangalore", "remote", "india", "hybrid",
    "anywhere", "flexible", "pune", "hyderabad", "gurgaon", "gurugram",
    "noida", "delhi", "ncr", "chennai", "kolkata",
]

# Companies to reject outright (IT-services / staffing / body-shops)
COMPANY_BLOCKLIST_TOKENS = [
    "infosys", "wipro", "tcs", "hcl", "tech mahindra", "cognizant",
    "capgemini", "accenture", "mphasis", "mindtree", "ltimindtree",
    "hexaware", "cyient", "persistent", "zensar", "niit",
    "birlasoft", "sonata software", "mastek", "l&t infotech",
    "lti ", "ltimindtree",
    # Staffing agencies
    "staffing", "manpower", "randstad", "adecco", "teamlease",
    "quess", "genius consultants", "kelly services", "robert half",
    "naukri", "foundit", "hirist",
]

# Titles to reject
TITLE_BLOCKLIST_TOKENS = [
    "intern", "trainee", "fresher", "junior", "associate",
    "entry level", "entry-level", "graduate", "co-op", "apprentice",
    "support", "analyst i ", "analyst i,", "level 1", "l1 ",
]

# ---------------------------------------------------------------------------
# Greenhouse board slugs (public API: boards-api.greenhouse.io)
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES: dict[str, str] = {
    # Big Tech / Platform
    "Stripe": "stripe",
    "Databricks": "databricks",
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "NVIDIA": "nvidia",
    "Atlassian": "atlassian",
    "Salesforce": "salesforce",
    "ServiceNow": "servicenow",
    "Adobe": "adobe",
    "Uber": "uber",
    "Notion": "notion",
    "Figma": "figma",
    "Cloudflare": "cloudflare",
    "Twilio": "twilio",
    "Elastic": "elastic",
    "Confluent": "confluent",
    "Snowflake": "snowflakecomputing",
    "Datadog": "datadoghq",
    "MongoDB": "mongodb",
    "HashiCorp": "hashicorp",
    "Cohere": "cohere",
    # India premium product / fintech
    "Razorpay": "razorpay",
    "Dream11": "dream11",
    "Swiggy": "swiggy",
    "Flipkart": "flipkart",
    "Meesho": "meesho",
    "Postman": "postman",
    "Freshworks": "freshworks",
    "BrowserStack": "browserstack",
    "Harness": "harness",
    "Hasura": "hasura",
    # Fintech (global)
    "Square": "squareup",
    "Plaid": "plaid",
    "Brex": "brex",
    "Affirm": "affirm",
    "Robinhood": "robinhood",
    "Ramp": "ramp",
    "Coinbase": "coinbase",
}

# ---------------------------------------------------------------------------
# Lever posting slugs (public API: api.lever.co)
# ---------------------------------------------------------------------------
LEVER_COMPANIES: dict[str, str] = {
    "PhonePe": "phonepe",
    "CRED": "cred",
    "Groww": "groww-in",
    "Paytm": "paytm",
    "Zomato": "zomato",
    "CureFit": "curefit",
    "Lenskart": "lenskart",
    "Ola": "olacabs",
    "Jupiter": "jupiter-2",
    "Slice": "sliceit",
    "Upstox": "upstox",
    "Smallcase": "smallcase",
    "Niyo": "niyo",
    "Fi.Money": "epifi",
    "Zepto": "zeptonow",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    apply_link: str
    compensation: str = "Not disclosed"
    source: str = "Unknown"
    posted_date: str = ""
    description_snippet: str = ""

    def quality_score(self) -> int:
        """Higher is better. Used to rank and filter listings."""
        score = 0
        t = self.title.lower()

        # --- Role relevance ---
        high_value = [
            "genai", "gen ai", "generative ai", "llm", "rag",
            "large language model", "retrieval augmented",
            "applied ai", "ai architect", "ml architect",
        ]
        medium_value = [
            "nlp", "natural language", "machine learning", "ml engineer",
            "ai engineer", "ai/ml", "deep learning", "transformer",
            "language model", "vector", "embedding", "inference",
            "foundation model", "prompt engineer", "data scientist",
        ]
        for kw in high_value:
            if kw in t:
                score += 15
        for kw in medium_value:
            if kw in t:
                score += 8

        # --- Seniority ---
        senior = ["senior", "staff", "principal", "lead", "architect",
                   "sr.", "sr ", "head", "director", "distinguished"]
        for kw in senior:
            if kw in t:
                score += 5

        # --- Location fit ---
        loc = self.location.lower()
        for term in ["mumbai", "bengaluru", "bangalore", "remote", "hybrid"]:
            if term in loc:
                score += 3

        # --- Compensation available ---
        if self.compensation != "Not disclosed":
            score += 3

        return score


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def http_get(url: str, timeout: int = 8) -> Optional[Union[dict, list, str]]:
    """GET request returning parsed JSON (dict/list) or raw text."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
    except urllib.error.HTTPError as e:
        logging.warning("HTTP %s for %s", e.code, url)
        return None
    except Exception as e:
        logging.warning("Request failed for %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def is_relevant_title(title: str) -> bool:
    t = title.lower()
    relevant = [
        "ai", "ml", "machine learning", "deep learning", "genai",
        "gen ai", "generative", "llm", "rag", "nlp",
        "natural language", "transformer", "neural",
        "data scientist", "applied scientist", "research engineer",
        "research scientist", "language model", "vector", "embedding",
        "retrieval", "inference", "foundation model", "prompt engineer",
        "computer vision", "cv engineer",
    ]
    if not any(kw in t for kw in relevant):
        return False
    for blk in TITLE_BLOCKLIST_TOKENS:
        if blk in t:
            return False
    return True


def is_blocked_company(name: str) -> bool:
    n = name.lower()
    return any(tok in n for tok in COMPANY_BLOCKLIST_TOKENS)


def is_target_location(loc: str) -> bool:
    if not loc:
        return True  # keep unknowns – might be remote
    l = loc.lower()
    return any(tok in l for tok in TARGET_LOCATIONS_LOOSE)


_COMP_PATTERNS = [
    re.compile(r"₹\s*[\d,.]+\s*(?:LPA|lpa|L|lakh|lakhs?)", re.I),
    re.compile(r"(?:INR|Rs\.?)\s*[\d,.]+\s*(?:LPA|lpa|L|lakh|lakhs?)", re.I),
    re.compile(r"\$\s*[\d,.]+(?:k|K)?\s*(?:[-–]|to)\s*\$?\s*[\d,.]+(?:k|K)?"),
    re.compile(r"(?:salary|compensation|pay|ctc|package)[\s:]*(?:₹|INR|Rs\.?|\$)\s*[\d,.]+", re.I),
    re.compile(r"[\d,.]+\s*(?:LPA|lpa|CTC|ctc)"),
    re.compile(r"\$\s*[\d,]+\s*(?:per year|annually|/yr|/year)", re.I),
]


def extract_compensation(text: str) -> str:
    if not text:
        return "Not disclosed"
    for pat in _COMP_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0).strip()
    return "Not disclosed"


def _html_to_text(html: str) -> str:
    """Very lightweight HTML tag stripper."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Source: Greenhouse
# ---------------------------------------------------------------------------

def search_greenhouse(display_name: str, board_slug: str) -> list[JobListing]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
    logging.info("  Greenhouse %-18s (%s)", display_name, board_slug)

    data = http_get(url)
    if not data or not isinstance(data, dict):
        return []

    results: list[JobListing] = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not is_relevant_title(title):
            continue

        loc_name = job.get("location", {}).get("name", "")
        if not is_target_location(loc_name):
            continue

        content_html = job.get("content", "")
        content_text = _html_to_text(content_html)
        comp = extract_compensation(content_text)

        apply_url = job.get("absolute_url", "")
        if not apply_url:
            jid = job.get("id", "")
            apply_url = f"https://boards.greenhouse.io/{board_slug}/jobs/{jid}"

        updated = (job.get("updated_at") or "")[:10]

        listing = JobListing(
            title=title,
            company=display_name,
            location=loc_name,
            apply_link=apply_url,
            compensation=comp,
            source="Greenhouse",
            posted_date=updated,
            description_snippet=content_text[:200],
        )
        if listing.quality_score() >= 5:
            results.append(listing)

    return results


# ---------------------------------------------------------------------------
# Source: Lever
# ---------------------------------------------------------------------------

def search_lever(display_name: str, lever_slug: str) -> list[JobListing]:
    url = f"https://api.lever.co/v0/postings/{lever_slug}?mode=json"
    logging.info("  Lever      %-18s (%s)", display_name, lever_slug)

    data = http_get(url)
    if not data or not isinstance(data, list):
        return []

    results: list[JobListing] = []
    for posting in data:
        title = posting.get("text", "")
        if not is_relevant_title(title):
            continue

        loc = posting.get("categories", {}).get("location", "")
        if not is_target_location(loc):
            continue

        # Gather text to search for compensation
        desc = posting.get("descriptionPlain", "")
        addl = posting.get("additionalPlain", "")
        lists_text = " ".join(
            lst.get("content", "") for lst in posting.get("lists", [])
        )
        comp = extract_compensation(f"{desc} {addl} {lists_text}")

        apply_url = posting.get("applyUrl") or posting.get("hostedUrl", "")

        created_ms = posting.get("createdAt", 0)
        posted = ""
        if created_ms:
            try:
                posted = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")
            except Exception:
                pass

        listing = JobListing(
            title=title,
            company=display_name,
            location=loc,
            apply_link=apply_url,
            compensation=comp,
            source="Lever",
            posted_date=posted,
            description_snippet=(desc or "")[:200],
        )
        if listing.quality_score() >= 5:
            results.append(listing)

    return results


# ---------------------------------------------------------------------------
# Source: LinkedIn (public guest API – no auth)
# ---------------------------------------------------------------------------

def search_linkedin(role: str, geo: str = "India") -> list[JobListing]:
    """
    Scrape LinkedIn's guest job-search endpoint (HTML).
    f_E=4,5,6 = Mid-Senior, Director, Executive experience levels.
    f_TPR=r172800 = posted in the last 48 hours (ensures actively open roles).
    Filters out any listing marked 'no longer accepting applications'.
    """
    query = urllib.parse.quote_plus(role)
    geo_q = urllib.parse.quote_plus(geo)
    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        f"keywords={query}&location={geo_q}"
        f"&f_E=4%2C5%2C6"
        f"&f_TPR=r172800"
        f"&start=0&count=25"
    )
    logging.info("  LinkedIn   '%s' in %s", role, geo)

    html = http_get(url, timeout=12)
    if not html or not isinstance(html, str):
        return []

    results: list[JobListing] = []
    # Extract each job card individually so we check closure badges per card
    cards = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL)
    for card in cards:
        card_lower = card.lower()
        if "no longer accepting applications" in card_lower or "closed" in card_lower:
            continue

        title_m = re.search(r'<h3[^>]*class="base-search-card__title[^"]*"[^>]*>\s*([^<]+)', card)
        company_m = re.search(r'<h4[^>]*class="base-search-card__subtitle[^"]*"[^>]*>\s*(?:<a[^>]*>)?\s*([^<]+)', card)
        loc_m = re.search(r'<span[^>]*class="job-search-card__location[^"]*"[^>]*>\s*([^<]+)', card)
        link_m = re.search(r'<a[^>]*class="base-card__full-link[^"]*"[^>]*href="([^"]*)"', card)

        if not (title_m and company_m and loc_m and link_m):
            continue

        t = title_m.group(1).strip()
        c = company_m.group(1).strip()
        loc = loc_m.group(1).strip()
        raw_link = link_m.group(1).strip().replace("&amp;", "&")

        # Clean URL to canonical job URL
        clean_m = re.search(r'(https://[a-z]{2,3}\.linkedin\.com/jobs/view/[^?]+)', raw_link)
        link = clean_m.group(1) if clean_m else raw_link.split("?")[0]

        if not is_relevant_title(t):
            continue
        if is_blocked_company(c):
            continue
        if not is_target_location(loc):
            continue

        listing = JobListing(
            title=t,
            company=c,
            location=loc,
            apply_link=link,
            source="LinkedIn",
        )
        if listing.quality_score() >= 5:
            results.append(listing)

    return results


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------

def deduplicate(jobs: list[JobListing]) -> list[JobListing]:
    seen: set[tuple[str, str]] = set()
    out: list[JobListing] = []
    for j in jobs:
        key = (j.title.lower().strip(), j.company.lower().strip())
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------

def generate_report(jobs: list[JobListing], scan_time: datetime) -> str:
    jobs.sort(key=lambda j: j.quality_score(), reverse=True)

    lines: list[str] = []
    a = lines.append

    a("# 🎯 Daily Premium AI Jobs Report")
    a("")
    a(f"**Scan Date:** {scan_time.strftime('%A, %B %d, %Y at %I:%M %p IST')}  ")
    a(f"**Total Listings:** {len(jobs)}  ")
    a("**Target Roles:** GenAI Developer · Applied AI Engineer · RAG Architect  ")
    a("**Locations:** Mumbai · Bengaluru · Remote (India)  ")
    a("**Experience:** 7 years · ₹50 LPA+ target  ")
    a("")
    a("---")
    a("")

    if not jobs:
        a("> [!WARNING]")
        a("> No matching premium AI jobs found in this scan. Possible reasons:")
        a("> - Rate-limiting by job platforms")
        a("> - No new postings matching all criteria today")
        a("> - Transient network errors")
        a(">")
        a("> The scanner will retry at the next scheduled run.")
        return "\n".join(lines)

    # Source summary
    by_source: dict[str, list[JobListing]] = {}
    for j in jobs:
        by_source.setdefault(j.source, []).append(j)

    a("## 📊 Summary by Source")
    a("")
    a("| Source | Jobs Found |")
    a("|--------|-----------|")
    for src, sj in sorted(by_source.items()):
        a(f"| {src} | {len(sj)} |")
    a("")

    # Top picks
    top = [j for j in jobs if j.quality_score() >= 15]
    if top:
        a("## ⭐ Top Picks (highest relevance)")
        a("")
        for i, j in enumerate(top[:15], 1):
            a(f"### {i}. {j.title}")
            a(f"- **Company:** {j.company}")
            a(f"- **Location:** {j.location}")
            a(f"- **Compensation:** {j.compensation}")
            a(f"- **Source:** {j.source}")
            if j.posted_date:
                a(f"- **Posted:** {j.posted_date}")
            a(f"- 🔗 **[Apply Now]({j.apply_link})**")
            a("")
        a("---")
        a("")

    # Full table
    a("## 📋 All Listings")
    a("")
    a("| # | Title | Company | Location | Compensation | Source | Apply |")
    a("|---|-------|---------|----------|--------------|--------|-------|")
    for i, j in enumerate(jobs, 1):
        t = (j.title[:45] + "…") if len(j.title) > 45 else j.title
        c = (j.compensation[:28] + "…") if len(j.compensation) > 28 else j.compensation
        link = f"[Apply]({j.apply_link})" if j.apply_link else "—"
        a(f"| {i} | {t} | {j.company} | {j.location} | {c} | {j.source} | {link} |")

    a("")
    a("---")
    a(f"*Generated by Premium AI Job Scanner v1.0 · {scan_time.strftime('%Y-%m-%d %H:%M IST')}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="a"),
            logging.StreamHandler(),
        ],
    )

    scan_time = datetime.now()
    logging.info("=" * 64)
    logging.info("Premium AI Job Scanner — starting")
    logging.info("=" * 64)

    all_jobs: list[JobListing] = []

    # ---- Greenhouse ----
    logging.info("--- Greenhouse ATS (%d companies) ---", len(GREENHOUSE_COMPANIES))
    for name, slug in GREENHOUSE_COMPANIES.items():
        try:
            found = search_greenhouse(name, slug)
            all_jobs.extend(found)
            if found:
                logging.info("    → %d jobs from %s", len(found), name)
            time.sleep(0.3)
        except Exception as exc:
            logging.error("    ✗ %s: %s", name, exc)

    # ---- Lever ----
    logging.info("--- Lever ATS (%d companies) ---", len(LEVER_COMPANIES))
    for name, slug in LEVER_COMPANIES.items():
        try:
            found = search_lever(name, slug)
            all_jobs.extend(found)
            if found:
                logging.info("    → %d jobs from %s", len(found), name)
            time.sleep(0.3)
        except Exception as exc:
            logging.error("    ✗ %s: %s", name, exc)

    # ---- LinkedIn ----
    logging.info("--- LinkedIn guest search ---")
    for role in SEARCH_ROLES[:6]:
        try:
            found = search_linkedin(role)
            all_jobs.extend(found)
            if found:
                logging.info("    → %d jobs for '%s'", len(found), role)
            time.sleep(1.5)
        except Exception as exc:
            logging.error("    ✗ LinkedIn '%s': %s", role, exc)

    # ---- De-dup & report ----
    all_jobs = deduplicate(all_jobs)
    logging.info("Total unique relevant jobs: %d", len(all_jobs))

    jobs_json_path = SCRIPT_DIR / "jobs.json"

    # Safety check: if 0 jobs found (e.g. network failure / sandboxing), do NOT overwrite existing database!
    if len(all_jobs) == 0 and jobs_json_path.exists():
        try:
            existing = json.loads(jobs_json_path.read_text(encoding="utf-8"))
            if len(existing) > 0:
                logging.warning(
                    "⚠️  Scan returned 0 jobs (possible network outage / sandbox restriction). "
                    "Preserving existing database of %d jobs to avoid wiping data.",
                    len(existing)
                )
                print(f"\n⚠️ Scan returned 0 jobs. Preserved existing database of {len(existing)} jobs.")
                return
        except Exception:
            pass

    report = generate_report(all_jobs, scan_time)

    OUTPUT_FILE.write_text(report, encoding="utf-8")
    logging.info("Report → %s", OUTPUT_FILE)

    WORKSPACE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_OUTPUT.write_text(report, encoding="utf-8")
    logging.info("Report → %s", WORKSPACE_OUTPUT)

    # Save JSON for the UI dashboard
    jobs_dict_list = [
        {
            "id": idx + 1,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "compensation": j.compensation,
            "source": j.source,
            "apply_link": j.apply_link,
            "posted_date": j.posted_date,
            "quality_score": j.quality_score(),
            "description_snippet": j.description_snippet,
        }
        for idx, j in enumerate(all_jobs)
    ]
    jobs_json_path.write_text(json.dumps(jobs_dict_list, indent=2), encoding="utf-8")
    logging.info("JSON Database → %s", jobs_json_path)

    print(f"\n{'=' * 64}")
    print(f"  SCAN COMPLETE — {len(all_jobs)} premium AI jobs found")
    print(f"  Report: {OUTPUT_FILE}")
    print(f"  JSON Database: {jobs_json_path}")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
