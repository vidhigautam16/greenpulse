"""
GreenPulse — Langchain RAG Engine (Production Vector Version)
Embeddings : Google text-embedding-004 via google-generativeai SDK (no download)
Vector DB  : FAISS              (in-memory, saved to disk, instant reload)
LLM        : Gemini 2.5 Flash   (streaming responses)
"""

import os, asyncio, threading
from typing import List, Dict, AsyncGenerator, Optional

import requests
from langchain_core.embeddings import Embeddings

# Langchain imports
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document  # type: ignore

from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiEmbeddings(Embeddings):
    """
    LangChain-compatible embeddings using Gemini REST API directly (v1, not v1beta).
    Avoids all SDK version issues — just plain HTTP to the stable v1 endpoint.
    Model: text-embedding-004 (768-dim, Google's best free embedding model).
    """

    # v1beta is correct — text-embedding-004 is not on v1 stable
    BASE = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _embed_one(self, text: str, task_type: str) -> List[float]:
        resp = requests.post(
            f"{self.BASE}:embedContent",
            params={"key": self.api_key},
            json={"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}, "taskType": task_type},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]["values"]

    def _batch_embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        # batchEmbedContents on v1beta
        resp = requests.post(
            f"{self.BASE}:batchEmbedContents",
            params={"key": self.api_key},
            json={"requests": [
                {"model": "models/text-embedding-004", "content": {"parts": [{"text": t}]}, "taskType": task_type}
                for t in texts
            ]},
            timeout=60,
        )
        if resp.status_code == 404:
            # fallback: embed one by one
            return [self._embed_one(t, task_type) for t in texts]
        resp.raise_for_status()
        return [item["values"] for item in resp.json()["embeddings"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._batch_embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> List[float]:
        return self._batch_embed([text], "RETRIEVAL_QUERY")[0]


# ── 8 Indian Climate Policy Documents ─────────────────────────────
POLICIES = [
    {
        "id": "NCAP_2019",
        "title": "National Clean Air Programme (NCAP) 2019",
        "content": "NCAP 2019 targets 20-30% reduction in PM2.5/PM10 by 2024 across 122 non-attainment cities including Delhi, Mumbai, Kolkata, Chennai, and Prayagraj. Key measures: Real-time CAAQMS monitoring for Tier-1 cities. Rs 4000 crore allocated. BS-VI fuel norms. EV incentives. Biomass burning ban. Industrial stack emissions tightened by 30%. Green belt target: 33% tree cover. For AQI>200: Activate GRAP immediately.",
    },
    {
        "id": "GRAP_2023",
        "title": "Graded Response Action Plan (GRAP) 2023",
        "content": "GRAP emergency protocol for high pollution: Stage I (AQI 201-300): Ban biomass burning, mechanised sweeping, water sprinkling 3x/day. Stage II (AQI 301-400): Diesel genset ban, stone crushers shut, +25% public transport. Stage III (AQI 401-450): Ban BS-III petrol BS-IV diesel, schools online, heavy trucks banned. Stage IV (AQI>450): 50% WFH government, stop non-essential construction. Response: Command Centre T+0, advisory T+30min, source ID T+4hr.",
    },
    {
        "id": "SMART_ENERGY_2022",
        "title": "Smart City Energy Efficiency MoHUA 2022",
        "content": "Demand Response mandatory for industrial consumers >1MW. Time-of-use tariffs shift 15% load from 6-10PM peak. Smart meters 15-minute data for all commercial buildings. ECBC mandatory buildings >500sqm. 100% LED street lighting saves 60%. Adaptive dimming 11PM-5AM. Power Factor Controllers in substations save 8-12%. 30% city electricity from renewables by 2025. 500MW rooftop solar target Tier-1 cities.",
    },
    {
        "id": "TRAFFIC_CPCB",
        "title": "Urban Traffic Emission Reduction CPCB Guidelines",
        "content": "Traffic signal synchronisation reduces idling 20%, cuts emissions 15%. Divert heavy vehicles to bypass roads 7AM-10PM. Freight trucks city limits 11PM-5AM only. Metro/BRTS frequency +25% during rush hours. Odd-even scheme in highest emission zones. Diesel vehicles >10 years require permits. Real-time parking guidance saves 8% fuel. 30% EV bus fleet target. CNG autorickshaws where AQI>150.",
    },
    {
        "id": "INDUSTRIAL_BEE",
        "title": "Industrial Zone Emission Control BEE Standards",
        "content": "CEMS mandatory for all industries >100 TPD, online to CPCB every 15 minutes. Spike response: Reduce production 20-30% within 2 hours. Activate wet scrubbers + ESP at full capacity. Switch to natural gas from coal. Waste heat recovery saves 15-20%. Variable Frequency Drives on pumps/fans saves 30-40%. ISO 50001 Energy Management mandatory facilities >500MW.",
    },
    {
        "id": "NDC_INDIA",
        "title": "India NDC Paris Agreement Climate Commitments",
        "content": "India NDC: 45% reduction emission intensity of GDP by 2030 vs 2005. 50% cumulative power from non-fossil sources by 2030. Carbon sink 2.5-3 Gt CO2 equivalent by 2030. Cities target <5 tonnes CO2 per capita per year by 2030 vs current 8-12 tonnes. Transport: 50% EV penetration by 2030. Buildings: ECBC compliance. Industry: 20-30% efficiency gains. Green bonds, carbon credit trading system, GCF financing.",
    },
    {
        "id": "GREEN_BHARAT_2024",
        "title": "Green Bharat Mission 2024 Carbon Neutral Cities",
        "content": "Vision: Carbon-neutral cities by India@100 2047. Five pillars: Clean Air AQI<60, Clean Energy 100% municipal renewables, Green Mobility 40% public transport and non-motorized transport, Green Buildings 50% LEED/GRIHA certified, Digital Governance real-time monitoring. 2024-25 priorities: Smart grid 50 cities, 10000 EV charging stations, green hydrogen 5 industrial clusters. Urban forest 100 million trees by 2026. AQI reduction -30% by 2026. EV fleet 25% by 2026. Green cover +15% by 2028.",
    },
    {
        "id": "EMERGENCY_SOP",
        "title": "City Emergency Response SOP Pollution Events",
        "content": "Trigger conditions: CO2 spike >200% of 60-minute rolling average OR AQI suddenly >300 in any monitored zone. T+0 to T+30min: Alert City Command Centre, deploy mobile AQ monitoring units to affected zone, issue public advisory via SMS. Activate emergency traffic diversions, notify industrial units to reduce output immediately. T+30min to T+4hr: Source identification — industrial vs traffic vs biomass burning. Dispatch rapid response team. Recovery T+4hr+: Root cause analysis, show-cause notice to violators, FIR if deliberate, 48-hour public report.",
    },
]

# FAISS index save path
FAISS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index")


class LangchainRAG:
    """
    Production RAG: HuggingFace local embeddings + FAISS + Gemini streaming.
    - all-MiniLM-L6-v2: 22MB, downloads once, loads in <1s after
    - FAISS: saved to disk, reloaded instantly on restart
    - Gemini 2.0 Flash: streaming AI responses
    - Server never blocked — all heavy work in background thread
    """

    def __init__(self):
        self.vectorstore: Optional[FAISS] = None
        self.embeddings: Optional[GeminiEmbeddings] = None
        self.llm: Optional[ChatGoogleGenerativeAI] = None
        self._ready = False
        self._init_error: Optional[str] = None
        self._init_stage: str = "starting"
        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        try:
            os.makedirs(os.path.dirname(FAISS_PATH) if os.path.dirname(FAISS_PATH) else ".", exist_ok=True)

            # ── Step 1: Google API embeddings (instant, no download) ─
            self._init_stage = "initializing_embeddings"
            print("  🔧  RAG: initializing Google embeddings API...")
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key or api_key == "your_key_here":
                raise ValueError("GOOGLE_API_KEY environment variable is required")

            self.embeddings = GeminiEmbeddings(api_key=api_key)
            print("  ✅  RAG: Google embeddings API ready!")

            # ── Step 2: FAISS vector store ──────────────────────────
            self._init_stage = "loading_vectors"
            faiss_file = FAISS_PATH + ".faiss"
            if os.path.exists(faiss_file):
                # Load saved index from disk (instant)
                self.vectorstore = FAISS.load_local(
                    FAISS_PATH,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                print("  ⚡  RAG: FAISS index loaded from disk!")
            else:
                # Build and save index (runs once)
                print("  🔧  RAG: building FAISS vector index...")
                docs = [
                    Document(
                        page_content=f"{p['title']}\n\n{p['content']}",
                        metadata={"id": p["id"], "title": p["title"]},
                    )
                    for p in POLICIES
                ]
                splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
                split_docs = splitter.split_documents(docs)
                self.vectorstore = FAISS.from_documents(split_docs, self.embeddings)
                os.makedirs(FAISS_PATH, exist_ok=True)
                self.vectorstore.save_local(FAISS_PATH)
                print("  💾  RAG: FAISS index saved to disk!")

            # ── Step 3: Gemini LLM ──────────────────────────────────
            self._init_stage = "loading_llm"
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.4,
                streaming=True,
            )
            print("  ✅  RAG ready! (FAISS + Google Embeddings + Gemini 2.5-flash)")

            self._init_stage = "ready"
            self._ready = True

        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
            print(f"  ⚠️  RAG init error: {error_msg}")
            self._init_error = f"{error_msg}\n{traceback.format_exc()}"
            self._init_stage = "error"

    def _build_live_context(self, live: Dict) -> str:
        cities = live.get("cities", {})
        city_lines = "\n".join(
            f"  • {name}: CO₂ {d.get('total_co2', 0):.1f} kg/hr | "
            f"AQI {d.get('avg_aqi', 0):.0f} | PM2.5 {d.get('avg_pm25', 0):.1f}"
            for name, d in cities.items()
        )
        readings = live.get("readings", [])
        top = sorted(readings, key=lambda x: x.get("co2_kg_hr", 0), reverse=True)[:3]
        top_lines = "\n".join(
            f"  {i+1}. {z['zone_name']} ({z['city']}): "
            f"CO₂={z['co2_kg_hr']:.1f} AQI={z['aqi']:.0f}"
            for i, z in enumerate(top)
        )
        return (
            f"=== LIVE WAQI/CPCB SENSOR DATA ===\n"
            f"Timestamp: {live.get('timestamp', 'now')}\n\n"
            f"City Summary:\n{city_lines}\n\n"
            f"Combined: Total CO₂ = {live.get('total_co2', 0):.1f} kg/hr | "
            f"Avg AQI = {live.get('avg_aqi', 0):.0f}\n\n"
            f"Top Emitting Zones:\n{top_lines}"
        )

    async def query_stream(self, question: str, live: Dict) -> AsyncGenerator[str, None]:
        # Wait up to 180 seconds for RAG to initialize (Render cold start: model download ~3-5 min)
        import time
        start_time = time.time()
        timeout = 180  # 3 minutes - Render free tier is slow
        check_interval = 1.0
        
        last_progress = -10
        elapsed = 0
        while not self._ready and elapsed < timeout:
            elapsed = time.time() - start_time
            
            if self._init_error:
                yield f"❌ RAG initialization failed: {self._init_error[:200]}...\n"
                return
            
                # Show progress every 5 seconds
            if int(elapsed) - last_progress >= 5:
                stage_msg = {
                    "starting": "Initializing...",
                    "initializing_embeddings": "Initializing embeddings API...",
                    "loading_vectors": "Loading vector database...",
                    "loading_llm": "Loading language model..."
                }.get(self._init_stage, f"Working... ({self._init_stage})")
                
                yield f"⏳ {stage_msg} ({int(elapsed)}s elapsed)\n"
                last_progress = int(elapsed)
            
            await asyncio.sleep(check_interval)
        
        if not self._ready:
            if self._init_error:
                yield f"❌ RAG initialization failed: {self._init_error[:200]}...\n"
            else:
                yield f"⏳ RAG initialization timed out after {timeout}s. Please check backend logs.\n"
            return

        # Vector similarity search
        try:
            retrieved = self.vectorstore.similarity_search(question, k=3)
            policy_ctx = "\n\n".join(
                f"[{doc.metadata.get('title', 'Policy')}]\n{doc.page_content}"
                for doc in retrieved
            )
        except Exception as e:
            yield f"⚠️ Retrieval error: {e}"
            return

        if not self.llm:
            async for t in self._mock_stream(question, live, retrieved):
                yield t
            return

        prompt = (
            "You are GreenPulse AI — real-time carbon intelligence for Indian cities.\n"
            "You monitor Delhi, Mumbai, Kolkata, Chennai, and Prayagraj via live WAQI/CPCB sensors.\n\n"
            f"{self._build_live_context(live)}\n\n"
            f"Retrieved Policy Documents:\n{policy_ctx}\n\n"
            f"Question: {question}\n\n"
            "Provide a concise, data-driven answer with bullet points. "
            "Cite specific policies (NCAP, GRAP, Green Bharat etc.) and reference the live data. "
            "Be specific about cities and zones.\n\nAnswer:"
        )

        try:
            async for chunk in self.llm.astream(prompt):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"⚠️ Gemini error: {e}\n\n"
            async for t in self._mock_stream(question, live, retrieved):
                yield t

    async def _mock_stream(self, q: str, live: Dict, docs: List) -> AsyncGenerator[str, None]:
        cities = live.get("cities", {})
        summary = " | ".join(
            f"{n}: AQI {d.get('avg_aqi', 0):.0f}" for n, d in cities.items()
        ) or "Fetching live data..."
        sources = ", ".join(doc.metadata.get("title", "") for doc in docs)
        text = (
            f"🌿 **Live City Status**\n{summary}\n"
            f"Total CO₂: {live.get('total_co2', 0):.1f} kg/hr\n\n"
            f"**Retrieved Policies:** {sources}\n\n"
            "**Recommended Actions (NCAP/GRAP):**\n"
            "• Traffic signal synchronisation → −20% idle emissions\n"
            "• Industrial output reduction → −25% in high-emission zones\n"
            "• Public transport frequency +25% during peak hours\n\n"
            "*(Add GOOGLE_API_KEY in .env for full Gemini AI analysis)*"
        )
        for word in text.split():
            yield word + " "
            await asyncio.sleep(0.012)

    def get_sources(self, question: str) -> List[Dict]:
        if not self._ready or not self.vectorstore:
            return []
        try:
            docs = self.vectorstore.similarity_search(question, k=3)
            return [
                {"title": d.metadata.get("title", "Policy"), "id": d.metadata.get("id", "")}
                for d in docs
            ]
        except Exception:
            return []


# ── Singleton ──────────────────────────────────────────────────────
_rag: Optional[LangchainRAG] = None

def get_rag() -> LangchainRAG:
    global _rag
    if _rag is None:
        _rag = LangchainRAG()
    return _rag
