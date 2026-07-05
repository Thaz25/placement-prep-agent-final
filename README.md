# 🎯 Placement Prep Agent

> Turn any job description into a personalized placement prep kit — powered by AI

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Mistral](https://img.shields.io/badge/Mistral_AI-F97316?style=for-the-badge&logo=mistral&logoColor=white)](https://mistral.ai)

**Track:** Agents for Good (Education/Student Outcomes)

---

## 🚀 What It Does

Placement Prep Agent takes a **job description** and your **resume** as input, then runs a **6-step AI pipeline** to generate:

| Output | Description |
|:-------|:------------|
| 📋 **JD Breakdown** | Extracts must-have & nice-to-have skills with exact JD citations |
| 🔍 **Gap Analysis** | Side-by-side comparison with severity flags (🔴 Missing / 🟡 Weak / 🟢 Strong) and copy-paste resume rewrite suggestions |
| 💻 **Practice Set** | 8-12 curated coding problems matched to the JD's focus areas, with reasons |
| 🎤 **Mock Interview** | 6-10 technical + behavioral questions, each citing the JD or resume line it probes |

### Why This Matters

Final-year students facing back-to-back placement drives spend hours manually reverse-engineering what each company wants from a JD, then separately hunting for practice problems and interview questions. **This agent collapses that into one pass**, and reasons transparently about *why* it's recommending what it recommends.

---

## 🏗️ Architecture

```
Student → [Guardrails] → parse_jd → parse_resume → gap_analysis → practice_set → interview_qs → report
                                                        ↑                ↓
                                                   [SQLite Memory]  [Problem Dataset]
                                                   (session diff)   (134 curated problems)
```

### Pipeline Steps

| Step | Function | LLM? | Purpose |
|:-----|:---------|:------|:--------|
| 0 | `check_guardrails()` | No | Regex/heuristic prompt injection detection |
| 1 | `parse_jd()` | ✅ | Extract skills, evaluation focus, with JD line citations |
| 2 | `parse_resume()` | ✅ | Extract skills, projects, experience into structured format |
| 3 | `gap_analysis()` | ✅ | Compare JD vs resume; flag missing/weak/strong; generate rewrites |
| 4 | `generate_practice_set()` | Hybrid | LLM identifies topics → local dataset query returns matched problems |
| 5 | `generate_interview_questions()` | ✅ | Generate questions citing specific JD/resume lines |
| 6 | `compile_report()` | No | Assemble all outputs into display + downloadable Markdown |

### Course Concept Mapping

| Day | Concept | Implementation |
|:----|:--------|:---------------|
| 1-2 | Multi-step agent + tools | 6-step pipeline; problem dataset is a real tool call |
| 3 | Memory / skilled agent | SQLite session memory; returning sessions diff against prior runs |
| 4 | Quality & security | Guardrail check; eval harness with 5 fixture pairs |
| 5 | Production framing | Config separation, Streamlit Cloud deployment, scaling notes |

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/placement-prep-agent.git
cd placement-prep-agent
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your Mistral API key:
# XAI_API_KEY=your_mistral_api_key_here
```

Get your key from [console.mistral.ai](https://console.mistral.ai).

> **No API key?** The app runs in **mock mode** automatically, showing sample data so you can explore the UI.

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 4. Run Tests

```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
placement-prep-agent/
├── app.py                          # 🚀 Main entry point
├── pages/
│   └── 01_Session_History.py       # Past sessions page
├── src/
│   ├── config.py                   # Centralized configuration
│   ├── llm_client.py               # Mistral API wrapper + mock mode
│   ├── guardrails.py               # Prompt injection detection
│   ├── pipeline/                   # 6 pipeline steps
│   │   ├── parse_jd.py
│   │   ├── parse_resume.py
│   │   ├── gap_analysis.py
│   │   ├── practice_set.py
│   │   ├── interview_questions.py
│   │   └── compile_report.py
│   ├── memory/
│   │   └── session_store.py        # SQLite session memory
│   └── tools/
│       └── problem_matcher.py      # Curated problem dataset query
├── data/
│   └── problems.json               # 134 curated coding problems
├── tests/
│   ├── fixtures/                   # 5 test JD+resume pairs
│   ├── test_guardrails.py          # Injection detection tests
│   ├── test_pipeline.py            # End-to-end pipeline tests
│   └── test_gap_categories.py      # Eval harness
├── .env.example                    # Environment variable template
├── .streamlit/config.toml          # Theme configuration
├── requirements.txt
└── README.md
```

---

## 🛡️ Guardrails & Safety

- **Prompt injection detection:** All inputs are scanned for 15+ injection patterns before reaching the LLM
- **Grounding constraint:** Every LLM prompt includes explicit instruction to only reference information present in the provided text — no fabrication
- **Input validation:** Length limits, control character stripping, base64 payload detection

---

## 🧪 Eval Harness

The `tests/test_gap_categories.py` file runs 5 realistic JD+resume fixture pairs through the pipeline and validates:

1. Gap analysis produces valid severity categories (missing/weak/strong)
2. Match scores fall in valid range (0-100)
3. Interview questions include both technical and behavioral types
4. All expected must-have gaps are identified

Run: `pytest tests/test_gap_categories.py -v`

---

## 📈 How This Would Scale

| Current (Capstone) | Production |
|:-------------------|:-----------|
| SQLite local storage | PostgreSQL / Supabase |
| Single user | Per-student auth (Supabase Auth) |
| Synchronous pipeline | Job queue (Celery + Redis) |
| No caching | Redis cache for identical JDs |
| Mock problems dataset | Live integration with LeetCode/HackerRank APIs |
| No feedback loop | Students rate suggestions → improve prompts |

---

## 📝 License

Built for the 5-Day Gen AI Intensive Capstone Project.

---

*Built with ❤️ for students facing placement season*
