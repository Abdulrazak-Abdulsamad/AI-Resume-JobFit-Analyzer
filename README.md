# AI Resume Analyzer

A modular pipeline that parses a resume, retrieves the most relevant jobs from a job database via Retrieval-Augmented Generation (RAG), and produces an ATS-style fit analysis for each match — served through a FastAPI backend
and a React (Vite + Tailwind) frontend.

```
Resume File (PDF/DOCX)
        │
        ▼
 Resume Parsing  ──►  structured ParsedResume (skills, education, experience, YOE)
        │
        ▼
     RAG          ──►  top-K relevant jobs, retrieved from job_db.json via
                        embeddings + ChromaDB vector search
        │
        ▼
 Job Analyzer     ──►  similarity, skill-gap, experience-match, ATS score,
                        rating, strengths, weaknesses, improvement suggestions
        │
        ▼
Skill Gap Detection ─►  missing_skills (already computed above, by
                        job_analyzer/skill_gap.py)
        │
        ▼
Course              ─►  per-skill course recommendations, sourced from a
Recommendations         curated catalog of trusted platforms (YouTube,
                        Coursera, Udemy, edX, LinkedIn Learning,
                        freeCodeCamp, DataCamp, Codecademy, Microsoft Learn,
                        AWS Skill Builder, Google Cloud Skills Boost)
        │
        ▼
Learning Roadmap    ─►  all recommended courses grouped into a beginner ->
                        intermediate -> advanced roadmap
```

## What changed from the three original projects

This is a refactor and integration of `RESUME PARSER`, `JOB ANALYZER`, and `RAG_MODULE` into one project, not a file-by-file merge:

- **Recommendation system removed.** `JOB ANALYZER/recommendation.py` (hardcoded course/job dictionaries) and all of its UI panels are gone.
  Job matching is now done exclusively by the RAG pipeline against the real job database.
- **`job_db.json` is the single source of truth.** It lives at `data/job_db.json` and is loaded exactly once by `database/job_repository.py`. Nothing else reads that file directly - the
  RAG module ingests jobs through the repository.
- **One embedding model, not three.** The original projects each created
  their own `SentenceTransformer("all-MiniLM-L6-v2")` (in
  `skill_extractor.py`, `feature_extraction.py`, and `embedder.py`). These
  are now a single cached `services/embedding_service.py` singleton shared
  by Resume Parsing, RAG, and Job Analyzer.
- **One skill taxonomy, not two.** `utils/skills_taxonomy.py` is now the
  canonical skill vocabulary for both extracting skills from a resume and
  matching them against a job's `required_skills` - so the two sides can
  never drift apart.
- **Duplicate code removed.** `ner.py` in the original Resume Parser
  accidentally defined `parse_date` four times via copy/paste; `analyzer.py`
  duplicated `extract_education` calls; `role_prediction.py` defined
  `predict()` twice. These are cleaned up. The legacy ML `role_predictor`
  (trained on an 8-row toy CSV, unrelated to job matching) was dropped as
  out of scope rather than carried forward as dead weight.
- **New capability: experience matching.** Neither original project scored
  years-of-experience against a job's minimum requirement as a standalone,
  weighted signal; `job_analyzer/experience_matcher.py` does this now.
- **New capability: course recommendations + learning roadmap.** The
  standalone `course_recommender/` module turns each job match's
  `missing_skills` into concrete courses on trusted platforms (with title,
  platform, difficulty, duration, URL, and recommended order) and rolls
  every missing skill's courses up into one beginner -> advanced learning
  roadmap. This is deliberately separate from the old, removed
  `recommendation.py`: recommendations here are always derived live from
  the RAG-sourced `missing_skills`, never a static, hand-maintained mapping
  of job titles to courses.
- **Modules only do one job each** (see structure below), each with a single
  public entry point other modules call into.
- **Presentation layer swapped: Streamlit -> FastAPI + React.** The old
  `app.py` Streamlit UI (and the `streamlit` dependency) has been removed
  entirely. `api.py` now exposes the exact same `ResumeAnalysisService`
  facade over HTTP (`POST /api/analyze`, `GET /api/health`), and a new
  `frontend/` React app (Vite + Tailwind) consumes that API. No backend
  logic changed - only how results reach the user.

## Project structure

```
resume_analyzer/
├── main.py                    # CLI entry point
├── api.py                     # FastAPI presentation layer (replaces Streamlit app.py)
├── config.py                  # Central settings (paths, weights, model names, API/CORS)
├── requirements.txt
├── run_backend.sh             # uvicorn convenience script
├── run_frontend.sh            # npm install + vite dev convenience script
├── frontend/                  # React (Vite + Tailwind) SPA - the ONLY presentation layer
│   ├── src/
│   │   ├── api/resumeApi.js         #   Single module that calls the backend
│   │   ├── components/              #   UploadCard, JobMatchCard, CourseRecommendations, ...
│   │   └── App.jsx                  #   Orchestrates state, no direct fetch calls
│   └── README.md               # Frontend-specific setup instructions
├── data/
│   └── job_db.json            # Single source of truth for job data
├── database/
│   └── job_repository.py      # Loads job_db.json once (cached)
├── services/
│   ├── embedding_service.py         # Shared SentenceTransformer singleton
│   └── resume_analysis_service.py   # Facade: Parsing -> RAG -> Analysis
├── resume_parsing/            # Extraction ONLY (PDF/DOCX/OCR, NER, skills)
│   ├── text_extractor.py      #   PDF/DOCX text extraction + OCR fallback
│   ├── preprocessor.py        #   Cleaning + section segmentation
│   ├── nlp_model.py           #   Shared spaCy singleton
│   ├── contact_extractor.py   #   Name / email / phone
│   ├── education_experience_extractor.py
│   ├── experience_duration.py #   Total years-of-experience calculation
│   ├── skill_extractor.py     #   Taxonomy + embedding-based skill extraction
│   ├── schema.py              #   ParsedResume pydantic model
│   └── pipeline.py            #   Orchestrates the above
├── rag/                       # Document loading, embeddings, retrieval ONLY
│   ├── vector_store.py        #   ChromaDB collection, seeded from JobRepository
│   ├── retriever.py           #   Resume -> query -> top-K retrieved jobs
│   ├── context_builder.py     #   Formats retrieved jobs into context text
│   └── schemas.py
├── job_analyzer/              # Scoring & insights ONLY (retrieves jobs via RAG)
│   ├── similarity.py          #   TF-IDF + semantic similarity
│   ├── skill_gap.py           #   Matching/missing skills vs RAG job data
│   ├── experience_matcher.py  #   Candidate years vs job's minimum years
│   ├── scoring.py             #   Weighted ATS score + rating
│   ├── insights.py            #   Strengths / weaknesses / suggestions
│   └── engine.py              #   Orchestrates the above (now also calls
│                               #   course_recommender per missing_skills)
├── course_recommender/        # Course recommendations & roadmap ONLY
│   ├── course_catalog.py      #   skill -> curated courses (+ search fallback)
│   ├── roadmap_builder.py     #   Groups courses into beginner->advanced phases
│   ├── schemas.py             #   CourseRecommendation / LearningRoadmap models
│   └── recommender_service.py #   Facade: missing_skills -> bundle + roadmap
├── utils/
│   ├── logging_config.py
│   ├── skills_taxonomy.py     # Canonical skill list (shared)
│   └── file_utils.py
└── tests/
    └── test_pipeline_smoke.py # End-to-end wiring test (fake embedder DI)
```

## Setup for fresh checkout

If you cloned or downloaded a distribution archive of this project, run:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python build_vector_db.py
cd frontend && npm install
```

Then start the backend and frontend as described below.

## Cleanup before distribution

To reduce project size before sharing, run:

```bash
python scripts/cleanup_project.py
```

This removes generated caches, build outputs, `node_modules/`, `.venv/`,
`__pycache__/`, and the ChromaDB vector store. All of these can be restored
by following the setup steps above.

## Usage

### CLI

```bash
python main.py path/to/resume.pdf
python main.py path/to/resume.docx --top-k 5
```

Prints the parsed resume and ranked job matches as JSON.

### Backend API

```bash
./run_backend.sh
# or directly:
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Exposes:

- `POST /api/analyze` - multipart file upload (`file` field, `.pdf`/`.docx`),
  returns the full `ResumeAnalysisReport` as JSON (parsed resume + ranked
  job matches, each carrying similarity/skill-gap/experience scores,
  insights, course recommendations, and the learning roadmap).
- `GET /api/health` - readiness probe (`{"status": "ok"}`).

Interactive API docs are available at `http://localhost:8000/docs` once
the server is running (auto-generated by FastAPI).

### Frontend (React + Vite + Tailwind)

```bash
./run_frontend.sh
# or directly:
cd frontend && npm install && npm run dev
```

Opens at `http://localhost:5173`. Upload a PDF/DOCX resume and view
skills, ranked job matches, ATS fit scores, improvement suggestions,
per-skill course recommendations, and a personalized learning roadmap for
each job's missing skills - all rendered from the backend API's JSON, with
zero hardcoded/mock data. See `frontend/README.md` for details.

> Run the backend first - the frontend's upload button will show a clear
> inline error if it can't reach `http://localhost:8000`.

## Configuration

All tunable values live in `config.py`:

- `job_db_path` - location of the job database (defaults to
  `data/job_db.json`, overridable via `RESUME_ANALYZER_JOB_DB`).
- `embedding.model_name` - the shared SentenceTransformer model.
- `retrieval.top_k` - how many jobs the RAG pipeline retrieves.
- `scoring_weights` - how similarity / skill-match / experience-match are
  combined into the final ATS score (must sum to 1.0).
- `rating_bands` - score thresholds for the rating labels.
- `api.host` / `api.port` - bind address for `uvicorn` (overridable via
  `RESUME_ANALYZER_API_HOST` / `RESUME_ANALYZER_API_PORT`).
- `api.cors_origins` - allowed frontend origins for CORS (overridable via
  `RESUME_ANALYZER_CORS_ORIGINS`, comma-separated). Defaults to the Vite
  dev server's default ports.

## Testing

```bash
python tests/test_pipeline_smoke.py
```

This smoke test wires together the real `JobRepository`, `VectorStoreManager`, `JobRetriever`, and `JobAnalyzer` against the real `job_db.json`, but injects a deterministic fake embedder so it can run without downloading the actual
~90MB sentence-transformers model. It verifies: the job database loads all 10 records, the vector store seeds and is queryable, results come back ranked by fit score, and every result carries required skills sourced from the job database. 
Run the CLI or UI (which use the real embedding model) for a full end-to-end check with genuine semantic embeddings.

## Design principles applied

- **DRY** - one embedding model, one skill taxonomy, one job data loader.
- **Single Responsibility** - each module does exactly one thing (extraction,
  preprocessing, retrieval, scoring, etc.).
- **Separation of Concerns** - Resume Parsing never sees job data; the Job
  Analyzer never touches raw files or the vector database directly, only
  the `JobRetriever` interface.
- **Dependency Injection** - every class accepts its collaborators as
  constructor arguments with sensible cached defaults, which is what makes
  the smoke test possible without a network connection.

## Acknowledgements

Special thanks and sincere appreciation to:
- **Group 3 Team Members**: **Abdulsamad Abdulrazak**, **Abdallah Bako**, **Auwal Ahmad**, **Bede Agwu**, **Bennaan Longdet**, **Favour Nwaulune**, **Jennifer Usiobaifo**, **Maryam Laminga**, **Maureen Kyesmen**, and **Mfon Okon** for their hard work, collaboration, and dedication in developing this AI Resume Analyzer system.
- **Facilitators**: **Victor Rizama** and **Stephen Acham** for their invaluable guidance, support, and mentorship throughout the project.
- **Organization**: **National Centre for Artificial Intelligence and Robotics (NCAIR / NITDA)** ([https://ncair.nitda.gov.ng](https://ncair.nitda.gov.ng)) for providing the platform, research environment, and resources to advance AI and robotics innovation.
