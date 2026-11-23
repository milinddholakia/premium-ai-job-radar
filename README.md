# 🎯 Apex GenAI Job Radar (7+ YOE · ₹50 LPA+ Target)

> Automated daily intelligence radar tracking verified **GenAI Developer**, **Applied AI Engineer**, and **RAG Architect** roles tailored for candidates with **7+ years of experience** targeting **₹50 LPA+ packages**.

[![Daily Scan & Deploy](https://github.com/milinddholakia/premium-ai-job-radar/actions/workflows/daily_scan.yml/badge.svg)](https://github.com/milinddholakia/premium-ai-job-radar/actions/workflows/daily_scan.yml)
[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-6366f1?style=flat&logo=github)](https://milinddholakia.github.io/premium-ai-job-radar/)

---

### 🌐 Live Web Dashboard

Explore and search all active listings directly in your browser:
### 👉 **[https://milinddholakia.github.io/premium-ai-job-radar/](https://milinddholakia.github.io/premium-ai-job-radar/)**

---

## ⚡ What it Does

1. **Scrapes Premium Sources Every Morning at 4:00 AM IST:**
   - **Direct Greenhouse ATS:** 38+ top tier firms (Anthropic, Databricks, Stripe, Coinbase, Cloudflare, Twilio, Affirm, Elastic, MongoDB, etc.)
   - **Direct Lever ATS:** 15+ high-growth fintechs & unicorns (Paytm, CRED, Groww, etc.)
   - **LinkedIn Guest Search:** Fresh 48-hour queries for high-seniority GenAI & RAG roles in India.
2. **Quality & Seniority Filtering:**
   - 🛡️ Strict keyword relevance (GenAI, RAG, LLM, Agentic, Applied AI, Vector, Architecture).
   - 🚫 Auto-discards IT services & body-shops (Infosys, TCS, Wipro, Cognizant, etc.).
   - 🚫 Auto-prunes intern, junior, and entry-level positions.
   - 🚫 Auto-filters listings marked *"No longer accepting applications"*.
3. **Automated Serverless Daily Scans:**
   - GitHub Actions runs daily at 4:00 AM IST, updates `jobs.json` and `daily_premium_ai_jobs.md`, and redeploys the dashboard to GitHub Pages automatically.

---

## 💻 Local Quickstart

To run the dashboard locally on your machine:

```bash
# Clone the repository
git clone https://github.com/milinddholakia/premium-ai-job-radar.git
cd premium-ai-job-radar

# Boot the web dashboard
./start_ui.sh
# or: python3 app.py
```

Then open `http://localhost:5050` in your browser.

---

## 📊 Summary Output

In addition to the Web Dashboard, each scan generates a comprehensive markdown summary at [`daily_premium_ai_jobs.md`](./daily_premium_ai_jobs.md).

---

## 📜 License

MIT © 2026 [Milind Dholakia](https://github.com/milinddholakia)
