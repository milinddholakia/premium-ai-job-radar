#!/usr/bin/env python3
"""
Premium AI Job Scanner - Web UI Dashboard
=========================================
Standalone zero-dependency local web dashboard.
Run:
    python3 app.py
Open:
    http://localhost:5050
"""

import json
import os
import sys
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from datetime import datetime

PORT = int(os.environ.get("PORT", 5050))
BASE_DIR = Path(__file__).resolve().parent
JOBS_JSON_PATH = BASE_DIR / "jobs.json"
MD_REPORT_PATH = BASE_DIR / "daily_premium_ai_jobs.md"
SCANNER_SCRIPT = BASE_DIR / "premium_ai_job_scanner.py"
SCANNER_LOG = BASE_DIR / "scanner.log"

scan_state = {
    "is_running": False,
    "started_at": None,
    "completed_at": None,
    "last_exit_code": 0,
    "message": "Idle"
}

HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Premium GenAI & RAG Architect Jobs (7+ YOE | ₹50 LPA+)</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: {
              50: '#eef2ff',
              100: '#e0e7ff',
              400: '#818cf8',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
            }
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #0b0f19;
      color: #f1f5f9;
      font-feature-settings: "cv02", "cv03", "cv04", "cv11";
    }
    .glass-card {
      background: rgba(17, 24, 39, 0.7);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .glass-card:hover {
      border-color: rgba(99, 102, 241, 0.3);
      box-shadow: 0 8px 32px -8px rgba(99, 102, 241, 0.2);
    }
    .glow-accent {
      background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #0f172a;
    }
    ::-webkit-scrollbar-thumb {
      background: #334155;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #475569;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col font-sans glow-accent selection:bg-indigo-500 selection:text-white">

  <!-- TOP HEADER -->
  <header class="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 font-bold text-lg text-white">
          AI
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="font-extrabold text-base sm:text-lg tracking-tight text-white">Apex GenAI Job Radar</h1>
            <span class="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Live</span>
          </div>
          <p class="text-xs text-slate-400 hidden sm:block">Senior, Lead & Architect Roles · 7+ YOE · Target ₹50 LPA+</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <!-- Scan Now Button -->
        <button id="btn-scan" onclick="triggerScan()" class="flex items-center gap-2 text-xs font-semibold px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all duration-200 active:scale-95">
          <svg id="scan-icon" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
          <span id="scan-btn-text">Run Scanner</span>
        </button>

        <!-- View Raw Markdown Button -->
        <button onclick="toggleMarkdownModal()" class="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors">
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <span class="hidden sm:inline">Markdown</span>
        </button>
      </div>
    </div>
  </header>

  <!-- LIVE SCAN BANNER (hidden by default) -->
  <div id="scan-banner" class="hidden bg-indigo-950/80 border-b border-indigo-500/30 py-2.5 px-4 text-xs text-indigo-200 flex items-center justify-between">
    <div class="max-w-7xl mx-auto w-full flex items-center justify-between">
      <div class="flex items-center gap-2">
        <svg class="animate-spin h-3.5 w-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span id="scan-status-text">Scanning Greenhouse, Lever, and LinkedIn for premium AI roles...</span>
      </div>
      <span class="font-mono text-[11px] text-indigo-300 opacity-80" id="scan-elapsed">In progress</span>
    </div>
  </div>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-6">

    <!-- METRICS GRID -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <!-- Total Jobs -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Filtered AI Roles</span>
          <div class="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-total">--</div>
          <p class="text-[11px] text-slate-400 mt-1">High-conviction listings</p>
        </div>
      </div>

      <!-- India Tech Hubs -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">India Tech Hubs</span>
          <div class="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-india">--</div>
          <p class="text-[11px] text-emerald-400 mt-1">BLR · BOM · Remote India</p>
        </div>
      </div>

      <!-- Top Tier Product / GCC -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Tier Product</span>
          <div class="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path></svg>
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-premium">--</div>
          <p class="text-[11px] text-amber-400 mt-1">Anthropic · Databricks · Stripe</p>
        </div>
      </div>

      <!-- Experience Match -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">7+ YOE Aligned</span>
          <div class="p-2 rounded-lg bg-violet-500/10 text-violet-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path></svg>
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-senior">--</div>
          <p class="text-[11px] text-violet-400 mt-1">Staff · Principal · Architect</p>
        </div>
      </div>
    </div>

    <!-- SEARCH & FILTER TOOLBAR -->
    <div class="glass-card rounded-2xl p-4 sm:p-5 space-y-4">
      <div class="flex flex-col sm:flex-row gap-3">
        <!-- Search bar -->
        <div class="relative flex-1">
          <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          </div>
          <input type="text" id="input-search" oninput="renderJobs()" placeholder="Search by title, company, skills (e.g. RAG, Anthropic, Agentic, Mumbai)..." class="w-full pl-10 pr-4 py-2.5 bg-slate-900/90 border border-slate-700/80 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all">
        </div>

        <!-- Saved Filter Toggle -->
        <button id="btn-filter-saved" onclick="toggleSavedFilter()" class="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-800 text-xs font-semibold text-slate-300 transition-colors">
          <svg class="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20"><path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z"></path></svg>
          <span>Saved (<span id="saved-count">0</span>)</span>
        </button>
      </div>

      <!-- Quick Filter Pills -->
      <div class="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
        <span class="text-xs font-semibold text-slate-400 mr-1">Locations:</span>
        <button onclick="setLocationFilter('all')" data-loc="all" class="loc-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors">All</button>
        <button onclick="setLocationFilter('bengaluru')" data-loc="bengaluru" class="loc-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Bengaluru</button>
        <button onclick="setLocationFilter('mumbai')" data-loc="mumbai" class="loc-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Mumbai</button>
        <button onclick="setLocationFilter('remote')" data-loc="remote" class="loc-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Remote</button>

        <span class="text-slate-600 mx-1">|</span>

        <span class="text-xs font-semibold text-slate-400 mr-1">Role Type:</span>
        <button onclick="setRoleFilter('all')" data-role="all" class="role-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors">All</button>
        <button onclick="setRoleFilter('architect')" data-role="architect" class="role-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Architects</button>
        <button onclick="setRoleFilter('rag')" data-role="rag" class="role-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">RAG / GenAI</button>
        <button onclick="setRoleFilter('applied')" data-role="applied" class="role-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Applied AI</button>

        <span class="text-slate-600 mx-1">|</span>

        <span class="text-xs font-semibold text-slate-400 mr-1">Source:</span>
        <button onclick="setSourceFilter('all')" data-src="all" class="src-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors">All</button>
        <button onclick="setSourceFilter('direct_ats')" data-src="direct_ats" class="src-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">✨ Direct ATS (100% Active)</button>
        <button onclick="setSourceFilter('Greenhouse')" data-src="Greenhouse" class="src-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Greenhouse</button>
        <button onclick="setSourceFilter('Lever')" data-src="Lever" class="src-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">Lever</button>
        <button onclick="setSourceFilter('LinkedIn')" data-src="LinkedIn" class="src-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors">LinkedIn (48h)</button>
      </div>
    </div>

    <!-- JOB CARDS CONTAINER -->
    <div class="space-y-3" id="jobs-container">
      <!-- Loading Skeleton -->
      <div class="glass-card rounded-2xl p-6 text-center text-slate-400 py-12">
        <svg class="animate-spin h-6 w-6 text-indigo-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-sm">Loading verified AI job listings...</p>
      </div>
    </div>

  </main>

  <!-- MARKDOWN REPORT MODAL -->
  <div id="modal-markdown" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4 sm:p-6">
    <div class="glass-card bg-slate-900 border border-slate-700 w-full max-w-4xl max-h-[85vh] rounded-2xl flex flex-col shadow-2xl">
      <div class="p-4 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="font-bold text-white text-sm sm:text-base">Daily Report Markdown (daily_premium_ai_jobs.md)</h3>
          <span class="text-[11px] font-mono text-slate-400">Read-Only</span>
        </div>
        <button onclick="toggleMarkdownModal()" class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>
      <div class="p-4 flex-1 overflow-y-auto">
        <pre id="markdown-content" class="font-mono text-xs text-slate-300 whitespace-pre-wrap selection:bg-indigo-600"></pre>
      </div>
      <div class="p-3 border-t border-slate-800 flex justify-end gap-2 bg-slate-950/40 rounded-b-2xl">
        <button onclick="copyMarkdown()" class="text-xs font-semibold px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg">Copy to Clipboard</button>
        <button onclick="toggleMarkdownModal()" class="text-xs px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg">Close</button>
      </div>
    </div>
  </div>

  <!-- SCRIPT -->
  <script>
    let allJobs = [];
    let savedJobIds = new Set(JSON.parse(localStorage.getItem('saved_ai_jobs') || '[]'));
    let hiddenJobIds = new Set(JSON.parse(localStorage.getItem('hidden_ai_jobs') || '[]'));
    let activeLocFilter = 'all';
    let activeRoleFilter = 'all';
    let activeSrcFilter = 'all';
    let onlySaved = false;

    async function loadJobs() {
      try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        allJobs = data.jobs || [];
        updateStats();
        renderJobs();
      } catch (err) {
        console.error('Failed to load jobs', err);
        document.getElementById('jobs-container').innerHTML = `
          <div class="glass-card rounded-2xl p-8 text-center text-rose-400">
            <p class="font-bold">Error loading jobs database</p>
            <p class="text-xs text-slate-400 mt-1">Please ensure jobs.json exists or trigger a new scan.</p>
          </div>
        `;
      }
    }

    function updateStats() {
      const visible = allJobs.filter(j => !hiddenJobIds.has(j.id));
      document.getElementById('stat-total').innerText = visible.length;

      // India Count
      const indiaRegex = /mumbai|bengaluru|bangalore|remote|india|hyderabad|pune|gurugram|noida|delhi|chennai/i;
      const indiaCount = visible.filter(j => indiaRegex.test(j.location)).length;
      document.getElementById('stat-india').innerText = indiaCount;

      // Top Tier Product
      const tierOne = /anthropic|databricks|stripe|coinbase|cloudflare|affirm|twilio|mongodb|elastic|paytm|barclays|american express/i;
      const premiumCount = visible.filter(j => tierOne.test(j.company)).length;
      document.getElementById('stat-premium').innerText = premiumCount;

      // Senior / Architect
      const seniorRegex = /architect|lead|staff|principal|sr\.|senior/i;
      const seniorCount = visible.filter(j => seniorRegex.test(j.title)).length;
      document.getElementById('stat-senior').innerText = seniorCount;

      document.getElementById('saved-count').innerText = savedJobIds.size;
    }

    function setLocationFilter(loc) {
      activeLocFilter = loc;
      document.querySelectorAll('.loc-pill').forEach(btn => {
        if (btn.getAttribute('data-loc') === loc) {
          btn.className = 'loc-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors';
        } else {
          btn.className = 'loc-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors';
        }
      });
      renderJobs();
    }

    function setRoleFilter(role) {
      activeRoleFilter = role;
      document.querySelectorAll('.role-pill').forEach(btn => {
        if (btn.getAttribute('data-role') === role) {
          btn.className = 'role-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors';
        } else {
          btn.className = 'role-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors';
        }
      });
      renderJobs();
    }

    function setSourceFilter(src) {
      activeSrcFilter = src;
      document.querySelectorAll('.src-pill').forEach(btn => {
        if (btn.getAttribute('data-src') === src) {
          btn.className = 'src-pill text-xs px-3 py-1 rounded-lg bg-indigo-600 text-white font-medium transition-colors';
        } else {
          btn.className = 'src-pill text-xs px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium transition-colors';
        }
      });
      renderJobs();
    }

    function toggleSavedFilter() {
      onlySaved = !onlySaved;
      const btn = document.getElementById('btn-filter-saved');
      if (onlySaved) {
        btn.classList.add('bg-indigo-600', 'text-white', 'border-indigo-500');
        btn.classList.remove('bg-slate-900/60', 'text-slate-300');
      } else {
        btn.classList.remove('bg-indigo-600', 'text-white', 'border-indigo-500');
        btn.classList.add('bg-slate-900/60', 'text-slate-300');
      }
      renderJobs();
    }

    function toggleSaveJob(id, e) {
      if (e) e.stopPropagation();
      if (savedJobIds.has(id)) {
        savedJobIds.delete(id);
      } else {
        savedJobIds.add(id);
      }
      localStorage.setItem('saved_ai_jobs', JSON.stringify(Array.from(savedJobIds)));
      document.getElementById('saved-count').innerText = savedJobIds.size;
      renderJobs();
    }

    function hideJob(id, e) {
      if (e) e.stopPropagation();
      hiddenJobIds.add(id);
      localStorage.setItem('hidden_ai_jobs', JSON.stringify(Array.from(hiddenJobIds)));
      updateStats();
      renderJobs();
    }

    function resetHiddenJobs() {
      hiddenJobIds.clear();
      localStorage.removeItem('hidden_ai_jobs');
      updateStats();
      renderJobs();
    }

    function renderJobs() {
      const query = (document.getElementById('input-search').value || '').toLowerCase().trim();
      const container = document.getElementById('jobs-container');

      const filtered = allJobs.filter(job => {
        if (hiddenJobIds.has(job.id)) return false;
        if (onlySaved && !savedJobIds.has(job.id)) return false;

        // Search query
        if (query) {
          const matchSearch =
            (job.title && job.title.toLowerCase().includes(query)) ||
            (job.company && job.company.toLowerCase().includes(query)) ||
            (job.location && job.location.toLowerCase().includes(query)) ||
            (job.source && job.source.toLowerCase().includes(query));
          if (!matchSearch) return false;
        }

        // Location filter
        if (activeLocFilter !== 'all') {
          const loc = (job.location || '').toLowerCase();
          if (activeLocFilter === 'bengaluru' && !loc.includes('bengaluru') && !loc.includes('bangalore')) return false;
          if (activeLocFilter === 'mumbai' && !loc.includes('mumbai')) return false;
          if (activeLocFilter === 'remote' && !loc.includes('remote')) return false;
        }

        // Role filter
        if (activeRoleFilter !== 'all') {
          const t = (job.title || '').toLowerCase();
          if (activeRoleFilter === 'architect' && !t.includes('architect')) return false;
          if (activeRoleFilter === 'rag' && !t.includes('rag') && !t.includes('genai') && !t.includes('generative')) return false;
          if (activeRoleFilter === 'applied' && !t.includes('applied')) return false;
        }

        // Source filter
        if (activeSrcFilter !== 'all') {
          if (activeSrcFilter === 'direct_ats') {
            if (job.source !== 'Greenhouse' && job.source !== 'Lever') return false;
          } else {
            if (job.source !== activeSrcFilter) return false;
          }
        }

        return true;
      });

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="glass-card rounded-2xl p-12 text-center text-slate-400">
            <svg class="w-12 h-12 mx-auto text-slate-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <p class="font-bold text-slate-300">No matching active jobs found</p>
            <p class="text-xs text-slate-500 mt-1">Try broadening your search term or clearing filters.</p>
            ${hiddenJobIds.size > 0 ? `<button onclick="resetHiddenJobs()" class="mt-4 text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-400 border border-slate-700">Restore ${hiddenJobIds.size} Hidden Jobs</button>` : ''}
          </div>
        `;
        return;
      }

      container.innerHTML = filtered.map(job => {
        const isSaved = savedJobIds.has(job.id);
        const hasComp = job.compensation && job.compensation !== 'Not disclosed';
        const isArchitect = /architect/i.test(job.title);
        const isStaff = /staff|principal|lead/i.test(job.title);
        const isDirect = job.source === 'Greenhouse' || job.source === 'Lever';

        let srcBadge = 'bg-slate-800 text-slate-300 border-slate-700';
        if (job.source === 'Greenhouse') srcBadge = 'bg-emerald-950/60 text-emerald-300 border-emerald-600/50';
        else if (job.source === 'Lever') srcBadge = 'bg-cyan-950/60 text-cyan-300 border-cyan-600/50';
        else if (job.source === 'LinkedIn') srcBadge = 'bg-blue-950/60 text-blue-300 border-blue-600/50';

        return `
          <div class="glass-card rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-200 group">
            <div class="flex-1 space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-lg border border-indigo-500/20">${escapeHtml(job.company)}</span>
                <span class="text-[11px] font-medium px-2 py-0.5 rounded-md border ${srcBadge}">${escapeHtml(job.source)}</span>
                ${isDirect ? '<span class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-emerald-950/40 text-emerald-400 border border-emerald-700/40">🟢 Direct Career Portal</span>' : '<span class="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700">⚡ Fast-Filling</span>'}
                ${isArchitect ? '<span class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-purple-950/60 text-purple-300 border border-purple-700/50">🏛️ Architect</span>' : ''}
                ${isStaff ? '<span class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-950/60 text-amber-300 border border-amber-700/50">⭐ Senior/Lead</span>' : ''}
                <span class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-indigo-950/40 text-indigo-300 border border-indigo-800/40">₹50 LPA+ Target</span>
              </div>

              <h2 class="text-base sm:text-lg font-bold text-white tracking-tight hover:text-indigo-300 transition-colors">
                ${escapeHtml(job.title)}
              </h2>

              <div class="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-400">
                <span class="flex items-center gap-1 text-slate-300">
                  <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                  ${escapeHtml(job.location || 'Remote / Unspecified')}
                </span>

                <span class="flex items-center gap-1 ${hasComp ? 'text-emerald-400 font-semibold' : 'text-slate-400'}">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  ${escapeHtml(job.compensation || 'Disclosed on application')}
                </span>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800">
              <!-- Mark Closed / Hide -->
              <button onclick="hideJob(${job.id}, event)" title="Dismiss / Mark Closed" class="p-2.5 rounded-xl border bg-slate-900 border-slate-700/80 text-slate-500 hover:text-rose-400 hover:border-rose-500/50 hover:bg-rose-950/20 transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>

              <!-- Bookmark -->
              <button onclick="toggleSaveJob(${job.id}, event)" title="${isSaved ? 'Remove from saved' : 'Save job'}" class="p-2.5 rounded-xl border ${isSaved ? 'bg-amber-500/20 border-amber-500/40 text-amber-400' : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'} transition-colors">
                <svg class="w-4 h-4" fill="${isSaved ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
              </button>

              <!-- Apply -->
              <a href="${job.apply_link}" target="_blank" rel="noopener noreferrer" class="flex-1 md:flex-initial flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all hover:scale-[1.02] active:scale-95">
                <span>Apply Direct</span>
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              </a>
            </div>
          </div>
        `;
      }).join('');
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // TRIGGER LIVE SCAN
    let scanInterval = null;
    let scanStart = 0;

    async function triggerScan() {
      const btn = document.getElementById('btn-scan');
      const text = document.getElementById('scan-btn-text');
      const icon = document.getElementById('scan-icon');
      const banner = document.getElementById('scan-banner');

      try {
        const res = await fetch('/api/scan', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'already_running') {
          alert('Scanner is already actively running!');
          return;
        }

        banner.classList.remove('hidden');
        text.innerText = 'Scanning...';
        icon.classList.add('animate-spin');
        btn.disabled = true;
        btn.classList.add('opacity-75');

        scanStart = Date.now();
        pollScanStatus();
      } catch (err) {
        console.error('Scan trigger error', err);
        alert('Failed to trigger scanner.');
      }
    }

    function pollScanStatus() {
      scanInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/scan-status');
          const status = await res.json();

          const elapsedSec = Math.round((Date.now() - scanStart) / 1000);
          document.getElementById('scan-elapsed').innerText = `${elapsedSec}s elapsed`;

          if (status.message) {
            document.getElementById('scan-status-text').innerText = status.message;
          }

          if (!status.is_running) {
            clearInterval(scanInterval);
            document.getElementById('scan-banner').classList.add('hidden');
            document.getElementById('scan-btn-text').innerText = 'Run Scanner';
            document.getElementById('scan-icon').classList.remove('animate-spin');
            document.getElementById('btn-scan').disabled = false;
            document.getElementById('btn-scan').classList.remove('opacity-75');
            await loadJobs();
          }
        } catch (e) {
          console.error(e);
        }
      }, 2500);
    }

    // MARKDOWN MODAL
    async function toggleMarkdownModal() {
      const modal = document.getElementById('modal-markdown');
      if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
        try {
          const res = await fetch('/api/report');
          const text = await res.text();
          document.getElementById('markdown-content').innerText = text;
        } catch (e) {
          document.getElementById('markdown-content').innerText = 'Failed to load markdown content.';
        }
      } else {
        modal.classList.add('hidden');
      }
    }

    function copyMarkdown() {
      const content = document.getElementById('markdown-content').innerText;
      navigator.clipboard.writeText(content).then(() => {
        alert('Copied daily markdown to clipboard!');
      });
    }

    // INIT
    loadJobs();
  </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default terminal request spam
        pass

    def send_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            index_file = BASE_DIR / "index.html"
            if index_file.exists():
                body = index_file.read_bytes()
            else:
                body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/jobs.json":
            if JOBS_JSON_PATH.exists():
                body = JOBS_JSON_PATH.read_bytes()
            else:
                body = b"[]"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/jobs":
            if JOBS_JSON_PATH.exists():
                try:
                    jobs_data = json.loads(JOBS_JSON_PATH.read_text(encoding="utf-8"))
                except Exception:
                    jobs_data = []
            else:
                jobs_data = []
            self.send_json(200, {"jobs": jobs_data, "count": len(jobs_data)})
            return

        if self.path == "/api/report":
            if MD_REPORT_PATH.exists():
                text = MD_REPORT_PATH.read_text(encoding="utf-8")
            else:
                text = "# No report found yet\nPlease trigger a scan."
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/scan-status":
            self.send_json(200, scan_state)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/scan":
            global scan_state
            if scan_state["is_running"]:
                self.send_json(200, {"status": "already_running"})
                return

            def run_scan_worker():
                global scan_state
                scan_state["is_running"] = True
                scan_state["started_at"] = datetime.now().isoformat()
                scan_state["message"] = "Scanning Greenhouse, Lever, and LinkedIn..."
                try:
                    res = subprocess.run(
                        [sys.executable, str(SCANNER_SCRIPT)],
                        capture_output=True,
                        text=True,
                        cwd=str(BASE_DIR)
                    )
                    scan_state["last_exit_code"] = res.returncode
                    scan_state["message"] = f"Finished with exit code {res.returncode}"
                except Exception as e:
                    scan_state["message"] = f"Error: {e}"
                finally:
                    scan_state["is_running"] = False
                    scan_state["completed_at"] = datetime.now().isoformat()

            th = threading.Thread(target=run_scan_worker, daemon=True)
            th.start()

            self.send_json(200, {"status": "started"})
            return

        self.send_response(404)
        self.end_headers()

def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print("=" * 64)
    print(f"  🎯 Apex GenAI Job Radar Dashboard is LIVE!")
    print(f"  URL: http://localhost:{PORT}")
    print(f"  Target: 7+ YOE · GenAI / Applied AI / RAG Architect · ₹50 LPA+")
    print("=" * 64)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()

if __name__ == "__main__":
    main()
