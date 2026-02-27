"""
GreenPulse — Simple Gemini Chatbot
No embeddings/vectors - just direct context + Gemini API
"""

import os
import re
import asyncio
import threading
from typing import List, Dict, AsyncGenerator, Optional

from langchain_google_genai import ChatGoogleGenerativeAI


# ── 8 Indian Climate Policy Documents ─────────────────────────────
POLICIES = [
    {
        "id": "NCAP_2019",
        "title": "National Clean Air Programme (NCAP) 2019",
        "content": "NCAP 2019 targets 20-30% reduction in PM2.5/PM10 by 2024 across 122 non-attainment cities including Delhi, Mumbai, Kolkata, Chennai, and Prayagraj. Key measures: Real-time CAAQMS monitoring for Tier-1 cities. Rs 4000 crore allocated. BS-VI fuel norms. EV incentives. Biomass burning ban. Industrial stack emissions tightened by 30%. Green belt target: 33% tree cover. For AQI>200: Activate GRAP immediately.",
        "keywords": ["ncap", "clean air", "pm2.5", "pm10", "122 cities", "non attainment", "caaqms", "bs-vi", "ev", "biomass", "grap"],
    },
    {
        "id": "GRAP_2023",
        "title": "Graded Response Action Plan (GRAP) 2023",
        "content": "GRAP emergency protocol for high pollution: Stage I (AQI 201-300): Ban biomass burning, mechanised sweeping, water sprinkling 3x/day. Stage II (AQI 301-400): Diesel genset ban, stone crushers shut, +25% public transport. Stage III (AQI 401-450): Ban BS-III petrol BS-IV diesel, schools online, heavy trucks banned. Stage IV (AQI>450): 50% WFH government, stop non-essential construction. Response: Command Centre T+0, advisory T+30min, source ID T+4hr.",
        "keywords": ["grap", "stage", "aqi", "emergency", "biomass", "wfh", "construction", "schools", "trucks"],
    },
    {
        "id": "SMART_ENERGY_2022",
        "title": "Smart City Energy Efficiency MoHUA 2022",
        "content": "Demand Response mandatory for industrial consumers >1MW. Time-of-use tariffs shift 15% load from 6-10PM peak. Smart meters 15-minute data for all commercial buildings. ECBC mandatory buildings >500sqm. 100% LED street lighting saves 60%. Adaptive dimming 11PM-5AM. Power Factor Controllers in substations save 8-12%. 30% city electricity from renewables by 2025. 500MW rooftop solar target Tier-1 cities.",
        "keywords": ["energy", "smart", "demand response", "solar", "rooftop", "led", "renewable", "ecbc", "power factor"],
    },
    {
        "id": "TRAFFIC_CPCB",
        "title": "CPCB Traffic Pollution Guidelines 2023",
        "content": "National Ambient Air Quality Standards (NAAQS): PM2.5 60μg/m³, PM10 100μg/m³ annual; 24hr: PM2.5 75μg/m³, PM10 150μg/m³. Emission factors: diesel 0.5g/km, petrol 0.2g/km, 2W 0.25g/km. Idling ban >3min enforceable. Parking pricing zones reduce 15% traffic. Metro rail corridor cuts 40% road PM. Electric bus fleet target 2027: 40% of STU buses.",
        "keywords": ["traffic", "cpcb", "naaqs", "pm2.5", "pm10", "idling", "parking", "metro", "electric bus"],
    },
    {
        "id": "GREEN_BHARAT",
        "title": "Green Bharat Mission 2023",
        "content": "Urban forestry target: 3 crore trees by 2026. Miyawaki mini-forests in urban areas. Lake & wetland conservation. Solar city program: 60 cities target 10% renewable. Waste-to-energy plants in 100 cities. Plastic ban: single-use plastic >50 microns. Compulsory rainwater harvesting buildings >500sqm. Urban lake revival: 150 lakes targeted. Climate-resilient infrastructure mandatory for new towns.",
        "keywords": ["green bharat", "tree", "forest", "miyawaki", "lake", "wetland", "solar", "plastic", "rainwater"],
    },
    {
        "id": "WASTE_MSW",
        "title": "Swachh Bharat 2.0 - MSW Rules 2023",
        "content": "Source segregation mandatory: dry/wet/marine litter. Door-to-door collection 100% towns. Bio-mining of legacy dumpsites. RDF production target 15MT/year. Landfill diversion 70% by 2025. Compost subsidy ₹1500/tonne. Incineration only for HCW/special waste. Informal sector integration in waste management. Extended Producer Responsibility for packaging.",
        "keywords": ["waste", "msw", "segregation", "compost", "landfill", "rdf", "swachh", "dump"],
    },
    {
        "id": "WATER_URBAN",
        "title": "Urban Water Supply & Sewerage 2024",
        "content": "Per capita water 135 lpcd mandatory. 24x7 pressure testing in all ULBs. STP reuse for gardening/industry 20% target. Rainwater harvesting mandatory all buildings >300sqm. Groundwater recharge through artificial lakes. Waste water treatment 100% coverage by 2026. Smart water meters mandatory >500 connections. Non-revenue water <20% target.",
        "keywords": ["water", "sewerage", "stp", "rainwater", "groundwater", "meter", "non-revenue"],
    },
    {
        "id": "BUILDING_ECO",
        "title": "Eco-Niwas Samhita 2024 (Energy Conservation)",
        "content": "ECBC 2017 mandatory all commercial >100sqm. Energy performance certificate mandatory sale/rent. Building envelope standards: U-value ≤0.4 W/m²K. Cool roof mandatory tropical climate. Solar-ready buildings 30% load. 5-star labeling mandatory appliances. LED lighting 100% by 2025. HVAC efficiency SEER ≥14. Whole-building simulation mandatory >10,000sqm.",
        "keywords": ["building", "ecbc", "energy", "cool roof", "solar", "led", "hvac", "star", "envelope"],
    },
]


def _match_policies(question: str, max_docs: int = 3) -> List[Dict]:
    """
    Simple keyword-based policy matching.
    No embeddings/vectors - just string matching.
    """
    q = question.lower()
    scored = []
    for p in POLICIES:
        score = 0
        title_words = p["title"].lower().split()
        for w in title_words:
            if w in q:
                score += 3
        for kw in p.get("keywords", []):
            if kw in q:
                score += 2
        if score > 0:
            scored.append((score, p))
    scored.sort(reverse=True)
    return [p for _, p in scored[:max_docs]]


class LangchainRAG:
    """
    Simple chatbot: keyword matching + Gemini.
    No embeddings, no vectors - just direct prompt with matched context.
    """

    def __init__(self):
        self.llm: Optional[ChatGoogleGenerativeAI] = None
        self._ready = False
        self._init_error: Optional[str] = None
        self._init_stage: str = "starting"
        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        try:
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key or api_key == "your_key_here":
                raise ValueError("GOOGLE_API_KEY environment variable is required")

            self._init_stage = "loading_llm"
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=api_key,
                temperature=0.4,
                streaming=True,
            )
            print("  ✅  RAG ready! (keyword matching + Gemini 2.0-flash)")
            self._init_stage = "ready"
            self._ready = True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ⚠️  RAG init error: {e}")
            self._init_error = str(e)
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
        import time
        start_time = time.time()
        timeout = 60
        last_progress = -10
        elapsed = 0

        while not self._ready and elapsed < timeout:
            elapsed = time.time() - start_time

            if self._init_error:
                yield f"❌ RAG initialization failed: {self._init_error[:200]}...\n"
                return

            if int(elapsed) - last_progress >= 5:
                stage_msg = {
                    "starting": "Initializing...",
                    "loading_llm": "Loading language model..."
                }.get(self._init_stage, f"Working... ({self._init_stage})")
                yield f"⏳ {stage_msg} ({int(elapsed)}s elapsed)\n"
                last_progress = int(elapsed)

            await asyncio.sleep(1.0)

        if not self._ready:
            if self._init_error:
                yield f"❌ RAG initialization failed: {self._init_error[:200]}...\n"
            else:
                yield f"⏳ RAG initialization timed out after {timeout}s.\n"
            return

        matched = _match_policies(question)
        policy_ctx = "\n\n".join(
            f"[{p['title']}]\n{p['content']}"
            for p in matched
        )

        prompt = (
            "You are GreenPulse AI — real-time carbon intelligence for Indian cities.\n"
            "You monitor Delhi, Mumbai, Kolkata, Chennai, and Prayagraj via live WAQI/CPCB sensors.\n\n"
            f"{self._build_live_context(live)}\n\n"
            f"Relevant Policy Documents:\n{policy_ctx}\n\n"
            f"Question: {question}\n\n"
            "Provide a concise, data-driven answer with bullet points. "
            "Cite specific policies (NCAP, GRAP, Green Bharat etc.) and reference the live data. "
            "Be specific about cities and zones.\n\nAnswer:"
        )

        if not self.llm:
            yield "⚠️ Gemini not initialized. Add GOOGLE_API_KEY to enable AI responses.\n"
            return

        try:
            async for chunk in self.llm.astream(prompt):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"⚠️ Gemini error: {e}\n"

    def get_sources(self, question: str) -> List[Dict]:
        matched = _match_policies(question)
        return [{"title": p["title"], "id": p["id"]} for p in matched]


# ── Singleton ──────────────────────────────────────────────────────
_rag: Optional[LangchainRAG] = None


def get_rag() -> LangchainRAG:
    global _rag
    if _rag is None:
        _rag = LangchainRAG()
    return _rag
