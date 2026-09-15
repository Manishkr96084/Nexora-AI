import asyncio
import json
import re
import math
import base64
import io
import httpx
import logging
import pypdf
from PIL import Image
from typing import AsyncGenerator, List, Dict, Any, Optional
from app.config import settings
from app.services.image_search_service import ImageSearchService
from app.services.time_service import TimeService
from app.services.weather_service import WeatherService

logger = logging.getLogger("aichatbot.ai_service")

# Comprehensive Knowledge Base
ENTITY_KNOWLEDGE = {
    "bihar": {
        "name": "Bihar",
        "capital": "Patna",
        "first_chief_minister": "Sri Krishna Sinha (Sri Babu) [Served 1946 – 1961]",
        "chief_minister": "Nitish Kumar",
        "first_governor": "Jairamdas Daulatram (1947–1948)",
        "governor": "Rajendra Arlekar",
        "population": "Approximately 130 Million (13 Crores)",
        "languages": "Hindi (Official), Urdu, Bhojpuri, Maithili, and Magahi",
        "landmarks": "Mahabodhi Temple (Bodh Gaya), Ancient Nalanda University ruins, Tomb of Sher Shah Suri",
        "overview": "Bihar is a historic state in eastern India, known as the birthplace of Buddhism and Jainism and home to ancient Pataliputra."
    },
    "patna": {
        "name": "Patna",
        "state": "Bihar",
        "capital_of": "Bihar",
        "chief_minister": "Nitish Kumar (Chief Minister of Bihar)",
        "first_chief_minister": "Sri Krishna Sinha (First Chief Minister of Bihar)",
        "population": "Approximately 2.5 Million (25 Lakhs)",
        "overview": "Patna is the capital and largest city of Bihar, situated on the southern bank of the River Ganges. Historically known as Pataliputra."
    },
    "india": {
        "name": "India",
        "capital": "New Delhi",
        "first_prime_minister": "Jawaharlal Nehru (1947–1964)",
        "prime_minister": "Narendra Modi",
        "first_president": "Dr. Rajendra Prasad (1950–1962, from Zeradei, Bihar)",
        "president": "Droupadi Murmu",
        "states": "28 States and 8 Union Territories",
        "population": "Approximately 1.4 Billion (140 Crores)",
        "currency": "Indian Rupee (INR - ₹)",
        "overview": "India is the world's most populous nation, situated in South Asia with 28 states and 8 union territories."
    },
    "maharashtra": {
        "name": "Maharashtra",
        "capital": "Mumbai",
        "first_chief_minister": "Yashwantrao Chavan (1960–1962)",
        "chief_minister": "Eknath Shinde / Devendra Fadnavis",
        "population": "Approximately 125 Million",
        "languages": "Marathi (Official)",
        "landmarks": "Gateway of India, Ajanta & Ellora Caves, Marine Drive",
        "overview": "Maharashtra is a major economic state in western India, home to Mumbai."
    },
    "delhi": {
        "name": "Delhi / New Delhi",
        "capital": "New Delhi",
        "first_chief_minister": "Chaudhary Brahm Prakash (1952–1955)",
        "chief_minister": "Atishi Marlena / Arvind Kejriwal",
        "population": "Approximately 32 Million",
        "overview": "New Delhi is the capital city of India and part of the National Capital Territory of Delhi."
    },
    "karnataka": {
        "name": "Karnataka",
        "capital": "Bengaluru (Bangalore)",
        "first_chief_minister": "K. Chengalaraya Reddy (1947–1952)",
        "chief_minister": "Siddaramaiah",
        "population": "Approximately 68 Million",
        "languages": "Kannada (Official)",
        "overview": "Karnataka is a southwestern Indian state famous for its technology center in Bengaluru."
    },
    "tamil nadu": {
        "name": "Tamil Nadu",
        "capital": "Chennai",
        "first_chief_minister": "C. N. Annadurai (1969) / A. Subbarayalu Reddiar (1920)",
        "chief_minister": "M. K. Stalin",
        "population": "Approximately 76 Million",
        "languages": "Tamil (Official)",
        "overview": "Tamil Nadu is a southern Indian state known for Dravidian-style Hindu temples and rich culture."
    },
    "uttar pradesh": {
        "name": "Uttar Pradesh",
        "capital": "Lucknow",
        "first_chief_minister": "Govind Ballabh Pant (1950–1954)",
        "chief_minister": "Yogi Adityanath",
        "population": "Approximately 235 Million",
        "landmarks": "Taj Mahal (Agra), Varanasi ghats",
        "overview": "Uttar Pradesh is the most populous state in India."
    },
    "usa": {
        "name": "United States of America",
        "capital": "Washington, D.C.",
        "first_president": "George Washington (1789–1797)",
        "population": "Approximately 335 Million",
        "overview": "The United States is a country in North America comprising 50 states."
    },
    "france": {
        "name": "France",
        "capital": "Paris",
        "president": "Emmanuel Macron",
        "currency": "Euro (€)",
        "overview": "France is a European nation renowned for fashion, science, the Eiffel Tower, and art history."
    }
}

INDIAN_CAPITALS = {
    "andhra pradesh": "Amaravati",
    "arunachal pradesh": "Itanagar",
    "assam": "Dispur",
    "bihar": "Patna",
    "chhattisgarh": "Raipur",
    "goa": "Panaji",
    "gujarat": "Gandhinagar",
    "haryana": "Chandigarh",
    "himachal pradesh": "Shimla",
    "jharkhand": "Ranchi",
    "karnataka": "Bengaluru",
    "kerala": "Thiruvananthapuram",
    "madhya pradesh": "Bhopal",
    "maharashtra": "Mumbai",
    "manipur": "Imphal",
    "meghalaya": "Shillong",
    "mizoram": "Aizawl",
    "nagaland": "Kohima",
    "odisha": "Bhubaneswar",
    "punjab": "Chandigarh",
    "rajasthan": "Jaipur",
    "sikkim": "Gangtok",
    "tamil nadu": "Chennai",
    "telangana": "Hyderabad",
    "tripura": "Agartala",
    "uttar pradesh": "Lucknow",
    "uttarakhand": "Dehradun",
    "west bengal": "Kolkata",
    "delhi": "New Delhi",
    "jammu and kashmir": "Srinagar (Summer) / Jammu (Winter)",
    "ladakh": "Leh"
}

WORLD_CAPITALS = {
    "india": "New Delhi",
    "usa": "Washington, D.C.",
    "united states": "Washington, D.C.",
    "america": "Washington, D.C.",
    "uk": "London",
    "united kingdom": "London",
    "england": "London",
    "france": "Paris",
    "germany": "Berlin",
    "japan": "Tokyo",
    "china": "Beijing",
    "canada": "Ottawa",
    "australia": "Canberra",
    "russia": "Moscow",
    "brazil": "Brasília",
    "south africa": "Pretoria / Cape Town",
    "italy": "Rome",
    "spain": "Madrid",
    "nepal": "Kathmandu",
    "bangladesh": "Dhaka",
    "sri lanka": "Sri Jayawardenepura Kotte (Colombo)",
    "pakistan": "Islamabad",
    "bhutan": "Thimphu"
}

def extract_pdf_text(base64_data: str) -> str:
    """Extracts plain text from Base64-encoded PDF files using pypdf."""
    try:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        raw_bytes = base64.b64decode(base64_data)
        reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
        extracted_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                extracted_pages.append(f"--- Page {i+1} ---\n{text.strip()}")
        return "\n\n".join(extracted_pages) if extracted_pages else "[PDF contains scanned images or no extractable text]"
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return f"[Could not parse PDF document text: {str(e)}]"

class AIService:
    @staticmethod
    def _evaluate_math(prompt: str) -> Optional[str]:
        """Safely evaluates arithmetic expressions."""
        clean = prompt.lower().replace("calculate", "").replace("what is", "").replace("equal to", "").replace("?", "").strip()
        match = re.search(r'([\d\.\s\+\-\*\/\%\(\)\^]+)', clean)
        if match:
            expr = match.group(1).strip()
            if any(op in expr for op in ['+', '-', '*', '/', '%']) and re.search(r'\d', expr):
                try:
                    safe_expr = expr.replace('^', '**')
                    if re.match(r'^[\d\.\s\+\-\*\/\%\(\)]+$', safe_expr):
                        val = eval(safe_expr)
                        return f"### Math Calculation\n\n$$\\mathbf{{{expr} = {val}}}$$\n\nThe calculated result for `{expr}` is **{val}**."
                except Exception:
                    pass
        return None

    @staticmethod
    def _extract_context_entity(history: List[Dict[str, Any]]) -> Optional[str]:
        """Looks back at previous messages in history to identify the topic/entity being discussed."""
        if not history:
            return None

        for msg in reversed(history):
            content = msg.get("content", "").lower()
            for entity_key in ENTITY_KNOWLEDGE.keys():
                if entity_key in content:
                    return entity_key
        return None

    @classmethod
    def _answer_knowledge_question(cls, prompt: str, history: List[Dict[str, Any]] = None) -> Optional[str]:
        raw_prompt = prompt.strip()
        prompt_lower = raw_prompt.lower()
        
        # Comprehensive typo & string normalization
        norm_prompt = prompt_lower
        norm_prompt = re.sub(r'pri+me\s*minister', 'prime minister', norm_prompt)
        norm_prompt = re.sub(r'che+if\s*minister', 'chief minister', norm_prompt)
        norm_prompt = re.sub(r'chief\s*minister', 'chief minister', norm_prompt)
        norm_prompt = norm_prompt.replace("chiefminister", "chief minister")
        norm_prompt = re.sub(r'prime\s*minister', 'prime minister', norm_prompt)
        norm_prompt = norm_prompt.replace("primeminister", "prime minister")
        norm_prompt = re.sub(r'presid+ent', 'president', norm_prompt)
        history = history or []

        is_first_q = any(w in norm_prompt for w in ["first", "1st", "initial", "former first", "earliest", "who was the first", "first cm", "first pm", "first president"])
        is_list_all_q = any(w in norm_prompt for w in ["list", "all ministers", "all minister", "all cm", "all chief minister", "cabinet", "portfolio", "nam e", "ministers list", "ministers name"])

        # ----------------------------------------------------
        # DIRECT SINGLE-QUESTION ANSWERS (One direct answer!)
        # ----------------------------------------------------

        # A. Prime Minister of India (Direct Answer)
        if ("prime minister" in norm_prompt or "pm" in norm_prompt) and ("india" in norm_prompt or "indian" in norm_prompt or not any(k in norm_prompt for k in ENTITY_KNOWLEDGE.keys())):
            if is_first_q:
                return "The first Prime Minister of India was **Jawaharlal Nehru** (served August 15, 1947 – May 27, 1964)."
            else:
                return "The Prime Minister of India is **Narendra Modi**."

        # Home Minister of India (Direct Answer)
        if ("home minister" in norm_prompt) and ("india" in norm_prompt or "indian" in norm_prompt or not any(k in norm_prompt for k in ENTITY_KNOWLEDGE.keys())):
            if is_first_q:
                return "The first Home Minister of India was **Sardar Vallabhbhai Patel** (served 1947 – 1950)."
            else:
                return "The Home Minister of India is **Amit Shah**."

        # Defence Minister of India (Direct Answer)
        if ("defense minister" in norm_prompt or "defence minister" in norm_prompt) and ("india" in norm_prompt or "indian" in norm_prompt or not any(k in norm_prompt for k in ENTITY_KNOWLEDGE.keys())):
            if is_first_q:
                return "The first Defence Minister of India was **Baldev Singh** (served 1947 – 1952)."
            else:
                return "The Defence Minister of India is **Rajnath Singh**."

        # Finance Minister of India (Direct Answer)
        if ("finance minister" in norm_prompt) and ("india" in norm_prompt or "indian" in norm_prompt or not any(k in norm_prompt for k in ENTITY_KNOWLEDGE.keys())):
            if is_first_q:
                return "The first Finance Minister of India was **R. K. Shanmukham Chetty** (served 1947 – 1949)."
            else:
                return "The Finance Minister of India is **Nirmala Sitharaman**."

        # B. President of India (Direct Answer)
        if ("president" in norm_prompt) and ("india" in norm_prompt or "indian" in norm_prompt or not any(k in norm_prompt for k in ENTITY_KNOWLEDGE.keys())):
            if is_first_q:
                return "The first President of India was **Dr. Rajendra Prasad** (served January 26, 1950 – May 13, 1962)."
            else:
                return "The President of India is **Droupadi Murmu**."

        # C. Chief Minister of Bihar (Direct Answer)
        if ("bihar" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Bihar was **Sri Krishna Sinha** (popularly known as **Sri Babu**, served April 1946 – January 1961)."
            else:
                return "The Chief Minister of Bihar is **Nitish Kumar**."

        # D. Governor of Bihar (Direct Answer)
        if ("bihar" in norm_prompt) and ("governor" in norm_prompt):
            if is_first_q:
                return "The first Governor of Bihar after independence was **Jairamdas Daulatram** (1947–1948)."
            else:
                return "The Governor of Bihar is **Rajendra Arlekar**."

        # E. Chief Minister of Uttar Pradesh (Direct Answer)
        if ("uttar pradesh" in norm_prompt or "up" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Uttar Pradesh was **Govind Ballabh Pant** (1950–1954)."
            else:
                return "The Chief Minister of Uttar Pradesh is **Yogi Adityanath**."

        # F. Chief Minister of Maharashtra (Direct Answer)
        if ("maharashtra" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Maharashtra was **Yashwantrao Chavan** (1960–1962)."
            else:
                return "The Chief Minister of Maharashtra is **Eknath Shinde**."

        # G. Chief Minister of Delhi (Direct Answer)
        if ("delhi" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Delhi was **Chaudhary Brahm Prakash** (1952–1955)."
            else:
                return "The Chief Minister of Delhi is **Atishi Marlena**."

        # H. Chief Minister of Karnataka (Direct Answer)
        if ("karnataka" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Karnataka was **K. Chengalaraya Reddy** (1947–1952)."
            else:
                return "The Chief Minister of Karnataka is **Siddaramaiah**."

        # I. Chief Minister of Tamil Nadu (Direct Answer)
        if ("tamil nadu" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and not is_list_all_q:
            if is_first_q:
                return "The first Chief Minister of Tamil Nadu was **C. N. Annadurai** (1969)."
            else:
                return "The Chief Minister of Tamil Nadu is **M. K. Stalin**."

        # J. President of USA (Direct Answer)
        if ("usa" in norm_prompt or "united states" in norm_prompt or "america" in norm_prompt) and ("president" in norm_prompt):
            if is_first_q:
                return "The first President of the United States was **George Washington** (served 1789–1797)."
            else:
                return "The President of the United States is **Joe Biden / Donald Trump**."

        # K. Capital Questions (Direct Answer)
        if "capital" in norm_prompt:
            for state_name, cap_city in INDIAN_CAPITALS.items():
                if state_name in norm_prompt:
                    return f"The capital of **{state_name.title()}** is **{cap_city}**."
            for country_name, cap_city in WORLD_CAPITALS.items():
                if country_name in norm_prompt:
                    return f"The capital of **{country_name.title()}** is **{cap_city}**."

        # L. Population Questions (Direct Answer)
        if "population" in norm_prompt or "how many people" in norm_prompt:
            if "bihar" in norm_prompt:
                return "The population of Bihar is approximately **130 Million (13 Crores)**."
            if "india" in norm_prompt:
                return "The population of India is approximately **1.4 Billion (140 Crores)**."
            if "maharashtra" in norm_prompt:
                return "The population of Maharashtra is approximately **125 Million**."
            if "delhi" in norm_prompt:
                return "The population of Delhi is approximately **32 Million**."

        # M. General Overview / Paragraph Questions for Bihar
        if "bihar" in norm_prompt:
            if any(w in norm_prompt for w in ["paragraph", "tell me about", "about bihar", "explain bihar", "essay", "describe bihar", "detail", "details", "info", "information"]):
                return (
                    "### 📍 Overview of Bihar\n\n"
                    "Bihar is a historic state located in eastern India, bordered by Nepal to the north and the Indian states of Uttar Pradesh to the west, Jharkhand to the south, and West Bengal to the east. The River Ganges flows right through the center of the state, creating fertile agricultural plains. Its capital and largest city is Patna, historically known as Pataliputra.\n\n"
                    "Bihar holds immense historical and spiritual significance as the birthplace of major world religions, including Buddhism and Jainism. Lord Buddha attained enlightenment under the Bodhi Tree in Bodh Gaya, while Lord Mahavira was born in Vaishali. In ancient times, Bihar was the seat of powerful empires such as the Maurya and Gupta dynasties, and home to Nalanda University, one of the ancient world's premier centers of learning.\n\n"
                    "Today, Bihar is known for its rich cultural traditions, vibrant Chhath Puja celebrations, unique Madhubani art, and major heritage monuments. The current Chief Minister of Bihar is Nitish Kumar, and the Governor is Rajendra Arlekar."
                )

        # N. General Overview / Paragraph Questions for India
        if "india" in norm_prompt:
            if any(w in norm_prompt for w in ["paragraph", "tell me about", "about india", "explain india", "essay", "describe india", "detail", "details", "info"]):
                return (
                    "### 🇮🇳 Overview of India\n\n"
                    "India, officially the Republic of India, is the world's most populous nation and the seventh-largest country by land area, located in South Asia. Bounded by the Indian Ocean on the south, the Arabian Sea on the southwest, and the Bay of Bengal on the southeast, India shares land borders with Pakistan, China, Nepal, Bhutan, Bangladesh, and Myanmar. New Delhi is the national capital.\n\n"
                    "India is celebrated for its incredible cultural diversity, ancient heritage, and vibrant traditions. As the cradle of the Indus Valley Civilization and birthplace of four major world religions—Hinduism, Buddhism, Jainism, and Sikhism—India has contributed profoundly to global philosophy, mathematics, science, and arts.\n\n"
                    "Modern India is a democratic constitutional republic comprising 28 states and 8 union territories. It possesses a rapidly growing economy, strong technological sector, and prominent international standing. The Prime Minister of India is Narendra Modi, and the President is Droupadi Murmu."
                )

        # O. General Overview / Paragraph Questions for Patna
        if "patna" in norm_prompt:
            if any(w in norm_prompt for w in ["paragraph", "tell me about", "about patna", "explain patna", "essay", "describe patna"]):
                return (
                    "### 🏛️ Overview of Patna\n\n"
                    "Patna is the historic capital and largest city of the state of Bihar, situated along the southern bank of the sacred Ganges River. Anciently known as Pataliputra, Patna was the imperial capital of legendary Indian empires including the Magadha, Nanda, Maurya, Shunga, and Gupta empires, and was visited by famous historical scholars such as Megasthenes and Faxian.\n\n"
                    "Modern Patna is an important administrative, educational, and commercial center in eastern India. Key cultural landmarks include the Golghar granary, Takht Sri Patna Sahib (birthplace of Guru Gobind Singh Ji), Patna Museum, and the Mahatma Gandhi Setu bridge."
                )

        # University Queries
        if any(w in norm_prompt for w in ["uk univers", "universities in uk", "uk university", "universities in the uk", "top uk", "oxford", "cambridge"]):
            return (
                "### 🇬🇧 Top Universities in the United Kingdom (UK)\n\n"
                "Here are some of the world's premier universities located in the United Kingdom:\n\n"
                "1. **University of Oxford**: The oldest university in the English-speaking world (est. 1096), internationally renowned for Humanities, Sciences, Law, and Medicine.\n"
                "2. **University of Cambridge**: World-renowned for Mathematics, Natural Sciences, and Engineering (home to Isaac Newton and Stephen Hawking).\n"
                "3. **Imperial College London**: A top-ranked global institution focused exclusively on Science, Engineering, Medicine, and Business.\n"
                "4. **University College London (UCL)**: Located in central London, famous for Medicine, AI research, Architecture, and Social Sciences.\n"
                "5. **London School of Economics (LSE)**: Leading global center for Economics, Political Science, International Relations, and Finance.\n"
                "6. **University of Edinburgh**: Premier Scottish institution renowned for Computer Science, Medicine, and Humanities.\n"
                "7. **The University of Manchester**: Historic university famous for pioneering research, physics, and engineering.\n"
                "8. **King's College London (KCL)**: Renowned for Healthcare, Law, and Global Affairs."
            )

        if any(w in norm_prompt for w in ["us univers", "universities in us", "us university", "american univers", "harvard", "mit", "stanford"]):
            return (
                "### 🇺🇸 Top Universities in the United States (USA)\n\n"
                "1. **Harvard University** (Cambridge, MA) — World leader in Law, Business, Medicine, and Liberal Arts.\n"
                "2. **Stanford University** (Stanford, CA) — Hub of Silicon Valley innovation, Engineering, and Business.\n"
                "3. **Massachusetts Institute of Technology (MIT)** (Cambridge, MA) — World premier institute for STEM, AI, and Technology.\n"
                "4. **Princeton University** (Princeton, NJ) — Renowned for Theoretical Physics, Mathematics, and Humanities.\n"
                "5. **UC Berkeley** (Berkeley, CA) — Top public research university for Computer Science and Engineering."
            )

        # Introduction / Format Queries
        if any(w in norm_prompt for w in ["intronduction", "introduction", "format of intro", "how to write intro", "intro format", "self intro", "introduce myself"]):
            return (
                "### 📝 Format & Structure of a Great Introduction\n\n"
                "A powerful introduction grabs attention, provides context, and clearly states your core message. Here is the standard 3-part format:\n\n"
                "---\n\n"
                "#### 1. The Hook (1–2 Sentences)\n"
                "Engage your audience immediately:\n"
                "* **Interesting Fact or Statistic**: *\"Over 80% of modern businesses rely on automated AI workflows.\"*\n"
                "* **Thought-Provoking Question**: *\"What single habit distinguishes top performers from the rest?\"*\n"
                "* **Key Quote / Bold Statement**: *\"Clarity is the prerequisite for effective execution.\"*\n\n"
                "#### 2. Background Context (2–3 Sentences)\n"
                "Set the scene so the reader understands the background:\n"
                "* Define key concepts or scope of your topic.\n"
                "* Explain why this topic matters right now.\n\n"
                "#### 3. Thesis Statement / Core Goal (1–2 Sentences)\n"
                "Summarize your main objective clearly:\n"
                "* Explicitly state what your report, essay, or speech will cover.\n\n"
                "---\n\n"
                "### 💡 Example Essay Introduction\n"
                "> \"In today's digital era, artificial intelligence has evolved from a theoretical concept into a fundamental driver of global industry. From healthcare diagnostics to software development, automated systems are transforming daily operations. This report analyzes the primary benefits, challenges, and future trends of AI integration in modern business.\"\n\n"
                "---\n\n"
                "### 🎯 Professional Self-Introduction Format (Interviews / Meetings)\n"
                "1. **Greeting & Name**: *\"Hello! My name is [Your Name].\"*\n"
                "2. **Background & Role**: *\"I specialize in [Your Profession/Skills] with a focus on [Key Skill Area].\"*\n"
                "3. **Top Accomplishment**: *\"In my previous role, I successfully built and delivered [Key Project/Success].\"*\n"
                "4. **Goal / Closing**: *\"I am excited to be here to contribute my expertise in [Target Field/Company].\"*"
            )

        # ----------------------------------------------------
        # MULTI-ITEM LIST QUERIES (Only when explicitly asked)
        # ----------------------------------------------------

        # Bihar Cabinet Ministers List
        if ("bihar" in norm_prompt) and is_list_all_q and any(w in norm_prompt for w in ["minister", "mantri", "cabinet", "deputy", "portfolio", "nam e", "name"]):
            return (
                "### 🏛️ Bihar Cabinet Ministers List (Government of Bihar)\n\n"
                "| Minister Name | Department / Portfolio |\n"
                "| :--- | :--- |\n"
                "| **Nitish Kumar** | **Chief Minister** (General Administration, Home, Cabinet Secretariat, IT) |\n"
                "| **Samrat Choudhary** | **Deputy Chief Minister** (Finance, Commercial Tax, Urban Development) |\n"
                "| **Vijay Kumar Sinha** | **Deputy Chief Minister** (Agriculture, Transport, Mines & Geology) |\n"
                "| **Bijendra Prasad Yadav** | Energy, Planning & Development |\n"
                "| **Vijay Kumar Chaudhary** | Water Resources, Building Construction |\n"
                "| **Mangal Pandey** | Health, Agriculture |\n"
                "| **Sunil Kumar** | Education |\n"
                "| **Nitish Mishra** | Industry |\n"
                "| **Leshi Singh** | Food & Consumer Protection |\n"
                "| **Madan Sahni** | Social Welfare |"
            )

        # Chronological CMs List of Bihar
        if ("bihar" in norm_prompt) and ("chief minister" in norm_prompt or "cm" in norm_prompt) and is_list_all_q:
            return (
                "### 📜 Chronological List of Chief Ministers of Bihar\n\n"
                "1. **Sri Krishna Sinha** (1946 – 1961) — *First Chief Minister of Bihar*\n"
                "2. **Binodanand Jha** (1961 – 1963)\n"
                "3. **K. B. Sahay** (1963 – 1967)\n"
                "4. **Jagannath Mishra** (1975–1977, 1980–1983, 1989–1990)\n"
                "5. **Lalu Prasad Yadav** (1990 – 1997)\n"
                "6. **Rabri Devi** (1997 – 2005) — *First Female Chief Minister of Bihar*\n"
                "7. **Jitan Ram Manjhi** (2014 – 2015)\n"
                "8. **Nitish Kumar** (2000, 2005 – Present) — *Longest-serving Chief Minister of Bihar*"
            )

        # States & Union Territories of India List
        if re.search(r'\b(how many states|states in india|states of india|number of states in india)\b', norm_prompt):
            return (
                "### States and Union Territories of India\n\n"
                "India currently has **28 States** and **8 Union Territories**.\n\n"
                "- **Total States**: 28\n"
                "- **Total Union Territories (UTs)**: 8\n"
                "- **National Capital**: New Delhi"
            )

        # P. Formal Application / Letter Writing Handler
        if any(w in norm_prompt for w in ["application", "letter", "markseet", "mark sheet", "leave application", "exam cell", "statement", "passbook"]):
            # 1. Bank Account Statement Application
            if any(w in norm_prompt for w in ["bank", "cbi", "sbi", "pnb", "hdfc", "icici", "statement", "passbook", "account number"]):
                bank_name = "Central Bank of India (CBI Bank)" if ("cbi" in norm_prompt or "central bank" in norm_prompt) else "State Bank of India (SBI)" if "sbi" in norm_prompt else "The Branch Manager, [Bank Name]"
                return (
                    f"### 📜 Application to Bank Manager for Bank Account Statement\n\n"
                    f"**To,**  \n"
                    f"**The Branch Manager,**  \n"
                    f"**{bank_name}**,  \n"
                    f"[Branch Name / Location],  \n"
                    f"[City, State]  \n\n"
                    f"**Subject**: Application for issuance of Bank Account Statement  \n\n"
                    f"**Respected Sir / Madam,**  \n\n"
                    f"I am an account holder maintaining a Savings / Current Account in your branch under Account Number **[Insert Account Number]**.\n\n"
                    f"I respectfully request you to kindly issue me the official account statement for my bank account for the period from **[Start Date]** to **[End Date]**. I require this account statement for official financial verification and record-keeping purposes.\n\n"
                    f"My details are as follows:\n"
                    f"- **Account Holder Name**: [Your Full Name]\n"
                    f"- **Account Number**: [Your Account Number]\n"
                    f"- **Registered Mobile No**: [Your Phone Number]\n\n"
                    f"Kindly process my request and provide the bank statement at your earliest convenience. Thanking you.\n\n"
                    f"**Yours faithfully,**  \n"
                    f"**Signature**: ______________________  \n"
                    f"**Name**: [Your Full Name]  \n"
                    f"**Date**: [Current Date]"
                )
            
            # 2. Mark Sheet Collection Application from School / College Exam Cell
            elif any(w in norm_prompt for w in ["markseet", "mark sheet", "marksheet", "exam cell"]):
                return (
                    "### 📜 Formal Application to Principal for Mark Sheet Collection\n\n"
                    "**To,**  \n"
                    "**The Principal,**  \n"
                    "[School / College / University Name],  \n"
                    "[City, State]  \n\n"
                    "**Subject**: Application for collection of original Mark Sheet from the Exam Cell  \n\n"
                    "**Respected Sir / Madam,**  \n\n"
                    "I am writing to respectfully request the issuance and collection of my official mark sheet. I have successfully cleared all examinations for the academic session [Year / Semester] under Roll Number **[Insert Roll No.]** and Registration / Enrollment Number **[Insert Registration No.]**.\n\n"
                    "I urgently require my original mark sheet for higher education admissions and official document verification. I request you to kindly grant approval for the Exam Cell to issue my mark sheet.\n\n"
                    "I have cleared all college dues and attached a copy of my admit card and student ID card for your reference and verification.\n\n"
                    "Thanking you.  \n\n"
                    "**Yours obediently,**  \n"
                    "**Name**: [Your Full Name]  \n"
                    "**Roll Number**: [Your Roll Number]  \n"
                    "**Course / Department**: [Your Course]  \n"
                    "**Contact Number**: [Your Mobile Number]  \n"
                    "**Date**: [Current Date]"
                )
            
            # 3. Sick / Absence Leave Application
            elif any(w in norm_prompt for w in ["sick", "leave", "absent", "fever", "illness"]):
                return (
                    "### 📜 Formal Leave Application to Principal\n\n"
                    "**To,**  \n"
                    "**The Principal,**  \n"
                    "[School / College Name],  \n"
                    "[City, State]  \n\n"
                    "**Subject**: Application for leave of absence due to illness  \n\n"
                    "**Respected Sir / Madam,**  \n\n"
                    "I am writing to inform you that I am unable to attend classes from **[Start Date]** to **[End Date]** due to sudden illness / high fever. My doctor has advised me complete rest for recovery.\n\n"
                    "I request you to kindly grant me leave for the specified period. I will ensure to cover all missed lectures and complete assigned coursework upon my return.\n\n"
                    "Thanking you.  \n\n"
                    "**Yours obediently,**  \n"
                    "**Name**: [Your Full Name]  \n"
                    "**Roll Number**: [Your Roll Number]  \n"
                    "**Class / Section**: [Your Class/Branch]  \n"
                    "**Date**: [Current Date]"
                )

            # 4. Job Application / Cover Letter
            elif any(w in norm_prompt for w in ["job", "employment", "post", "vacancy", "apply"]):
                return (
                    "### 📜 Job Application & Cover Letter Template\n\n"
                    "**To,**  \n"
                    "**The Hiring Manager / HR Department,**  \n"
                    "[Company / Organization Name],  \n"
                    "[City, State]  \n\n"
                    "**Subject**: Application for the position of [Job Title / Role]  \n\n"
                    "**Respected Sir / Madam,**  \n\n"
                    "I am writing to formally express my strong interest in applying for the position of [Job Title] at [Company Name]. With my qualifications and skills in [Key Skill / Field], I am confident in my ability to make a positive contribution to your team.\n\n"
                    "Attached is my resume detailing my academic background and experience. I welcome the opportunity to discuss my application further in an interview.\n\n"
                    "Thanking you for your time and consideration.  \n\n"
                    "**Yours sincerely,**  \n"
                    "**Name**: [Your Full Name]  \n"
                    "**Contact Number**: [Your Mobile Number]  \n"
                    "**Email**: [Your Email Address]  \n"
                    "**Date**: [Current Date]"
                )

            # 5. General Application Template
            else:
                return (
                    "### 📜 Formal Application Template\n\n"
                    "**To,**  \n"
                    "**The Concerned Authority / Principal / Manager,**  \n"
                    "[Organization / Institute Name],  \n"
                    "[City, State]  \n\n"
                    "**Subject**: [Specify Subject of Application]  \n\n"
                    "**Respected Sir / Madam,**  \n\n"
                    "I am writing to bring to your kind attention that [State the purpose of your application clearly].\n\n"
                    "I request you to kindly consider my request and grant necessary approval at your earliest convenience.\n\n"
                    "Thanking you.  \n\n"
                    "**Yours sincerely,**  \n"
                    "**Name**: [Your Full Name]  \n"
                    "**Roll Number / Designation**: [Details]  \n"
                    "**Date**: [Current Date]"
                )


        # Check Math Evaluation
        math_ans = cls._evaluate_math(prompt)
        if math_ans:
            return math_ans

        # -------------------------------------------------------
        # SCIENCE & NATURE QUESTIONS
        # -------------------------------------------------------

        if "photosynthesis" in norm_prompt:
            return (
                "### 🌿 Photosynthesis\n\n"
                "**Photosynthesis** is the biological process by which green plants, algae, and certain bacteria convert sunlight (solar energy), water (H₂O), and carbon dioxide (CO₂) into glucose (sugar) and oxygen.\n\n"
                "**Chemical Equation:**\n"
                "```\n6CO₂ + 6H₂O + Light Energy → C₆H₁₂O₆ + 6O₂\n```\n\n"
                "**Key Facts:**\n"
                "- Occurs in **chloroplasts**, specifically using **chlorophyll** (the green pigment)\n"
                "- Takes place in two stages: **Light reactions** (in thylakoids) and **Calvin Cycle** (in stroma)\n"
                "- Produces oxygen as a **by-product**, which is released into the atmosphere\n"
                "- Forms the base of virtually all food chains on Earth"
            )

        if any(w in norm_prompt for w in ["gravity", "gravitational force"]):
            return (
                "### 🍎 Gravity\n\n"
                "**Gravity** is a fundamental force of nature that attracts objects with mass toward each other. It is one of the four fundamental forces in physics.\n\n"
                "**Newton's Law of Universal Gravitation:**\n"
                "```\nF = G × (m₁ × m₂) / r²\n```\n"
                "Where **G** = 6.674 × 10⁻¹¹ N·m²/kg², **m₁, m₂** = masses, **r** = distance between them.\n\n"
                "**Key Facts:**\n"
                "- The acceleration due to gravity on Earth's surface: **g = 9.8 m/s²**\n"
                "- Gravity keeps planets in orbit around the Sun\n"
                "- **Albert Einstein** described gravity as the curvature of spacetime in his **General Theory of Relativity** (1915)\n"
                "- The Moon's gravity causes ocean tides on Earth"
            )

        if any(w in norm_prompt for w in ["speed of light", "light speed", "velocity of light"]):
            return (
                "### 💡 Speed of Light\n\n"
                "The **speed of light** in a vacuum is approximately **299,792,458 metres per second (≈ 3 × 10⁸ m/s)**, commonly denoted as **c**.\n\n"
                "**Key Facts:**\n"
                "- Light takes **8 minutes and 20 seconds** to travel from the Sun to Earth\n"
                "- Light takes about **1.3 seconds** to travel from the Moon to Earth\n"
                "- According to Einstein's **Special Theory of Relativity**, nothing with mass can travel at or beyond the speed of light\n"
                "- Light from the nearest star (**Proxima Centauri**) takes **4.24 years** to reach Earth\n"
                "- The speed of light in different media is slower (e.g., water ≈ 2.25 × 10⁸ m/s)"
            )

        if any(w in norm_prompt for w in ["dna", "d.n.a", "deoxyribonucleic"]):
            return (
                "### 🧬 DNA (Deoxyribonucleic Acid)\n\n"
                "**DNA** (Deoxyribonucleic Acid) is the molecule that carries the genetic instructions for the development, functioning, growth, and reproduction of all known living organisms.\n\n"
                "**Structure:**\n"
                "- DNA has a **double helix** structure, discovered by **James Watson and Francis Crick** in 1953\n"
                "- Made of **nucleotides** consisting of a sugar (deoxyribose), a phosphate group, and one of four nitrogenous bases: **Adenine (A), Thymine (T), Guanine (G), Cytosine (C)**\n"
                "- Base pairing: **A pairs with T**, **G pairs with C**\n\n"
                "**Functions:**\n"
                "- Stores and transmits genetic information\n"
                "- Guides protein synthesis via RNA\n"
                "- Enables heredity and biological inheritance"
            )

        if any(w in norm_prompt for w in ["atom", "atomic structure", "proton", "neutron", "electron"]):
            return (
                "### ⚛️ Atomic Structure\n\n"
                "An **atom** is the fundamental unit of matter and the defining structure of chemical elements.\n\n"
                "**Components of an Atom:**\n"
                "| Particle | Charge | Location | Mass |"
                "| :--- | :--- | :--- | :--- |\n"
                "| **Proton** | +1 (Positive) | Nucleus | 1.673 × 10⁻²⁷ kg |\n"
                "| **Neutron** | 0 (Neutral) | Nucleus | 1.675 × 10⁻²⁷ kg |\n"
                "| **Electron** | −1 (Negative) | Electron shells (orbits) | 9.109 × 10⁻³¹ kg |\n\n"
                "**Key Facts:**\n"
                "- The number of protons in the nucleus = **Atomic Number** (defines the element)\n"
                "- Protons + Neutrons = **Mass Number**\n"
                "- **Bohr's Model** describes electrons orbiting the nucleus in fixed energy shells\n"
                "- **Rutherford** discovered the nucleus in 1911\n"
                "- Atoms are mostly empty space — the nucleus is 100,000× smaller than the whole atom"
            )

        if any(w in norm_prompt for w in ["water", "h2o", "water molecule"]):
            if any(w in norm_prompt for w in ["formula", "composition", "chemical", "structure", "properties", "what is"]):
                return (
                    "### 💧 Water (H₂O)\n\n"
                    "**Water** is a transparent, tasteless, odourless, and nearly colourless chemical substance.\n\n"
                    "**Chemical Formula:** H₂O (2 hydrogen atoms + 1 oxygen atom)\n\n"
                    "**Key Properties:**\n"
                    "- **Boiling point**: 100°C (212°F) at standard pressure\n"
                    "- **Freezing point**: 0°C (32°F)\n"
                    "- **Density**: 1 g/cm³ (liquid), 0.917 g/cm³ (ice)\n"
                    "- **pH**: 7.0 (neutral)\n"
                    "- Excellent universal **solvent** (polar molecule)\n\n"
                    "**Significance:**\n"
                    "- Covers about **71% of Earth's surface**\n"
                    "- Essential for all known forms of life\n"
                    "- The human body is approximately **60% water**"
                )

        if any(w in norm_prompt for w in ["solar system", "planets", "planet"]):
            return (
                "### 🪐 The Solar System\n\n"
                "Our **Solar System** consists of the **Sun** and all the celestial objects gravitationally bound to it.\n\n"
                "**The 8 Planets (in order from the Sun):**\n"
                "1. 🔴 **Mercury** — Closest to the Sun; no atmosphere; extreme temperatures\n"
                "2. 🟡 **Venus** — Hottest planet (462°C avg); thick CO₂ atmosphere\n"
                "3. 🔵 **Earth** — Our home; only known planet with life; one natural moon\n"
                "4. 🔴 **Mars** — The 'Red Planet'; has the tallest volcano (Olympus Mons)\n"
                "5. 🟠 **Jupiter** — Largest planet; has the Great Red Spot storm; 95+ moons\n"
                "6. 🟡 **Saturn** — Famous for its rings; least dense planet\n"
                "7. 🔵 **Uranus** — Rotates on its side; very cold (-214°C)\n"
                "8. 🔵 **Neptune** — Farthest planet; strongest winds in the Solar System\n\n"
                "> **Note**: Pluto was reclassified as a **dwarf planet** in 2006 by the IAU."
            )

        # -------------------------------------------------------
        # HISTORY & IMPORTANT EVENTS
        # -------------------------------------------------------

        if any(w in norm_prompt for w in ["world war 1", "world war i", "ww1", "first world war"]):
            return (
                "### ⚔️ World War I (1914–1918)\n\n"
                "**World War I** (The Great War) was a global conflict centred in Europe that lasted from **28 July 1914 to 11 November 1918**.\n\n"
                "**Key Facts:**\n"
                "- **Cause**: Assassination of Archduke **Franz Ferdinand** of Austria-Hungary in Sarajevo (June 28, 1914)\n"
                "- **Major Alliances**: Allied Powers (UK, France, Russia, USA) vs. Central Powers (Germany, Austria-Hungary, Ottoman Empire)\n"
                "- **Ended with**: The **Treaty of Versailles** (1919)\n"
                "- **Casualties**: Over **20 million** deaths (military + civilian)\n"
                "- Led directly to the conditions that caused **World War II**\n"
                "- Introduced modern warfare: tanks, poison gas, aircraft, trench warfare"
            )

        if any(w in norm_prompt for w in ["world war 2", "world war ii", "ww2", "second world war"]):
            return (
                "### ⚔️ World War II (1939–1945)\n\n"
                "**World War II** was the deadliest and most widespread conflict in human history, involving more than 30 countries.\n\n"
                "**Key Facts:**\n"
                "- **Period**: September 1, 1939 – September 2, 1945\n"
                "- **Trigger**: Nazi Germany's invasion of Poland\n"
                "- **Allied Powers**: USA, UK, USSR, France, China | **Axis Powers**: Germany, Japan, Italy\n"
                "- **Holocaust**: Nazi Germany systematically murdered **6 million Jews** and millions of others\n"
                "- **D-Day** (June 6, 1944): Allied invasion of Normandy — decisive turning point\n"
                "- **Atomic Bombs**: USA dropped bombs on Hiroshima (Aug 6) and Nagasaki (Aug 9), 1945 — Japan surrendered\n"
                "- **Casualties**: Approximately **70–85 million** deaths (most destructive war in history)\n"
                "- Led to the founding of the **United Nations (UN)** in 1945"
            )

        if any(w in norm_prompt for w in ["independence of india", "indian independence", "independence day india", "15 august"]):
            return (
                "### 🇮🇳 Indian Independence (1947)\n\n"
                "India gained independence from **British colonial rule** on **15 August 1947** after nearly 200 years of British control.\n\n"
                "**Key Facts:**\n"
                "- Independence was achieved through a long non-violent freedom struggle led mainly by **Mahatma Gandhi**\n"
                "- India was partitioned into two nations: **India** and **Pakistan** simultaneously on August 14–15, 1947\n"
                "- The **Indian Independence Act 1947** was passed by the British Parliament\n"
                "- First Prime Minister: **Jawaharlal Nehru** (delivered the famous 'Tryst with Destiny' speech)\n"
                "- First Governor-General: **Lord Mountbatten** (then C. Rajagopalachari)\n"
                "- India became a Republic on **26 January 1950** when the Constitution came into effect"
            )

        if any(w in norm_prompt for w in ["mahatma gandhi", "gandhi ji", "father of nation"]):
            return (
                "### 🕊️ Mahatma Gandhi\n\n"
                "**Mohandas Karamchand Gandhi** (October 2, 1869 – January 30, 1948), known as **Mahatma Gandhi**, was the leader of India's independence movement against British rule.\n\n"
                "**Key Facts:**\n"
                "- Known as the **'Father of the Nation'** in India\n"
                "- Famous for his philosophy of **Ahimsa** (non-violence) and **Satyagraha** (truth-force / civil resistance)\n"
                "- Led major movements: **Non-Cooperation Movement** (1920), **Civil Disobedience Movement** (1930), **Dandi Salt March** (1930), **Quit India Movement** (1942)\n"
                "- Born in **Porbandar, Gujarat**; studied Law in London\n"
                "- Assassinated on January 30, 1948 by **Nathuram Godse**\n"
                "- His birthday, **October 2**, is observed as the **International Day of Non-Violence** by the UN"
            )

        # -------------------------------------------------------
        # HEALTH & BIOLOGY
        # -------------------------------------------------------

        if any(w in norm_prompt for w in ["vitamin", "vitamins"]):
            return (
                "### 🥗 Vitamins — Types & Functions\n\n"
                "**Vitamins** are essential organic compounds that the human body requires in small amounts for proper functioning.\n\n"
                "| Vitamin | Name | Key Function | Source |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| **A** | Retinol | Vision, immunity, skin health | Carrots, eggs, dairy |\n"
                "| **B1** | Thiamine | Energy metabolism, nerve function | Whole grains, legumes |\n"
                "| **B2** | Riboflavin | Energy production, growth | Milk, meat, eggs |\n"
                "| **B3** | Niacin | DNA repair, metabolism | Fish, peanuts, meat |\n"
                "| **B6** | Pyridoxine | Protein metabolism, brain | Bananas, potatoes |\n"
                "| **B9** | Folic Acid | Cell division, pregnancy health | Leafy greens, beans |\n"
                "| **B12** | Cobalamin | Nerve function, red blood cells | Meat, fish, dairy |\n"
                "| **C** | Ascorbic Acid | Antioxidant, immunity, collagen | Citrus fruits, peppers |\n"
                "| **D** | Calciferol | Bone health, calcium absorption | Sunlight, fish, eggs |\n"
                "| **E** | Tocopherol | Antioxidant, cell protection | Nuts, seeds, oils |\n"
                "| **K** | Phylloquinone | Blood clotting, bone metabolism | Leafy greens, broccoli |"
            )

        if any(w in norm_prompt for w in ["human heart", "heart", "cardiac"]):
            if any(w in norm_prompt for w in ["explain", "about", "function", "work", "anatomy", "beat", "describe"]):
                return (
                    "### ❤️ The Human Heart\n\n"
                    "The **human heart** is a muscular organ roughly the size of a fist, located slightly left of centre in the chest. It pumps blood throughout the body continuously.\n\n"
                    "**Structure:**\n"
                    "- Has **4 chambers**: Left Atrium, Right Atrium, Left Ventricle, Right Ventricle\n"
                    "- Divided into left (oxygenated blood) and right (deoxygenated blood) halves by the **septum**\n"
                    "- **Valves**: Tricuspid, Pulmonary, Mitral (Bicuspid), and Aortic valves\n\n"
                    "**Function:**\n"
                    "- Pumps oxygenated blood from the **left ventricle** to the body via the **aorta**\n"
                    "- Returns deoxygenated blood from the body to the **right atrium**\n"
                    "- Sends deoxygenated blood to the **lungs** via the **pulmonary artery** for oxygenation\n\n"
                    "**Key Stats:**\n"
                    "- Beats approximately **60–100 times per minute** at rest\n"
                    "- Pumps about **5 litres of blood per minute**\n"
                    "- Beats approximately **100,000 times per day**"
                )

        if any(w in norm_prompt for w in ["blood group", "blood type", "blood groups"]):
            return (
                "### 🩸 Blood Groups (ABO System)\n\n"
                "The **ABO blood group system** classifies human blood based on the presence or absence of antigens on red blood cells.\n\n"
                "| Blood Group | Antigen (on RBC) | Antibody (in plasma) | Can Donate To | Can Receive From |\n"
                "| :---: | :---: | :---: | :---: | :---: |\n"
                "| **A** | A | Anti-B | A, AB | A, O |\n"
                "| **B** | B | Anti-A | B, AB | B, O |\n"
                "| **AB** | A and B | None | AB only | A, B, AB, O (**Universal Recipient**) |\n"
                "| **O** | None | Anti-A and Anti-B | A, B, AB, O (**Universal Donor**) | O only |\n\n"
                "**Rh Factor:** Blood is further classified as **Rh+ (positive)** or **Rh− (negative)** based on the Rh antigen."
            )

        # -------------------------------------------------------
        # TECHNOLOGY & COMPUTING
        # -------------------------------------------------------

        if "mongodb" in norm_prompt:
            return (
                "### 🍃 MongoDB\n\n"
                "**MongoDB** is an open-source, document-oriented **NoSQL database** system developed by MongoDB Inc. It stores data in flexible, JSON-like **BSON** (Binary JSON) format documents.\n\n"
                "**Key Features:**\n"
                "- **Schema-less**: Collections don't enforce a fixed schema\n"
                "- **Horizontal scaling** via **sharding**\n"
                "- Powerful **aggregation pipeline** for complex queries\n"
                "- Supports **indexes**, **transactions**, and **geospatial** queries\n"
                "- **Motor** is the async Python driver for MongoDB\n\n"
                "**Use Cases:** E-commerce, real-time analytics, content management, IoT data storage, chatbot history storage"
            )

        if "fastapi" in norm_prompt:
            return (
                "### ⚡ FastAPI\n\n"
                "**FastAPI** is a modern, high-performance Python web framework for building **REST APIs** and **streaming endpoints** with Python 3.8+.\n\n"
                "**Key Features:**\n"
                "- **Asynchronous** (async/await) support built-in via **Starlette + Uvicorn**\n"
                "- Automatic **OpenAPI docs** (Swagger UI) at `/docs`\n"
                "- **Type hints + Pydantic** for automatic data validation\n"
                "- One of the **fastest** Python web frameworks available\n"
                "- Supports **WebSockets**, **Background Tasks**, **Dependency Injection**\n\n"
                "**Example:**\n"
                "```python\n"
                "from fastapi import FastAPI\n"
                "app = FastAPI()\n\n"
                "@app.get('/hello')\n"
                "async def hello():\n"
                "    return {'message': 'Hello, World!'}\n"
                "```"
            )

        if any(w in norm_prompt for w in ["artificial intelligence", "what is ai", "ai meaning", "about ai"]):
            return (
                "### 🤖 Artificial Intelligence (AI)\n\n"
                "**Artificial Intelligence (AI)** is the simulation of human intelligence in machines programmed to think, learn, reason, and solve problems.\n\n"
                "**Key Branches of AI:**\n"
                "- **Machine Learning (ML)**: Systems that learn from data without explicit programming\n"
                "- **Deep Learning**: Neural networks with multiple layers (powers image recognition, LLMs)\n"
                "- **Natural Language Processing (NLP)**: Understanding and generating human language (e.g., ChatGPT, Gemini)\n"
                "- **Computer Vision**: Interpreting and understanding visual information (images, videos)\n"
                "- **Robotics**: AI-driven autonomous machines\n\n"
                "**Real-World Applications:** Virtual assistants, medical diagnosis, self-driving cars, fraud detection, recommendation systems, chatbots"
            )

        if any(w in norm_prompt for w in ["machine learning", "ml algorithm"]):
            return (
                "### 🧠 Machine Learning (ML)\n\n"
                "**Machine Learning** is a subset of Artificial Intelligence where algorithms improve automatically through **experience and data** without being explicitly programmed.\n\n"
                "**Types of Machine Learning:**\n"
                "1. **Supervised Learning**: Model learns from labeled training data (e.g., spam detection, image classification)\n"
                "2. **Unsupervised Learning**: Model finds patterns in unlabeled data (e.g., clustering, dimensionality reduction)\n"
                "3. **Reinforcement Learning**: Model learns by interacting with an environment and receiving rewards or penalties\n\n"
                "**Popular ML Algorithms:** Linear Regression, Decision Trees, Random Forest, SVM, K-Means, Neural Networks\n\n"
                "**Popular Libraries:** Scikit-learn, TensorFlow, PyTorch, Keras, XGBoost"
            )

        if any(w in norm_prompt for w in ["internet", "what is internet", "how internet works"]):
            return (
                "### 🌐 The Internet\n\n"
                "The **Internet** is a global system of interconnected computer networks that communicate using standardized protocols (TCP/IP) to exchange data worldwide.\n\n"
                "**How it Works:**\n"
                "- Data is broken into **packets** and routed through a global network of servers and routers\n"
                "- **IP Addresses** identify each device on the network\n"
                "- **DNS (Domain Name System)** translates domain names (like google.com) into IP addresses\n"
                "- **HTTP/HTTPS** protocols transfer web pages between servers and browsers\n\n"
                "**Key Services on the Internet:**\n"
                "- World Wide Web (WWW), Email, File Transfer (FTP), Streaming, Cloud Computing, VoIP"
            )

        if any(w in norm_prompt for w in ["python programming", "what is python", "about python language"]):
            return (
                "### 🐍 Python Programming Language\n\n"
                "**Python** is a high-level, interpreted, general-purpose programming language known for its simplicity and readability.\n\n"
                "**Key Features:**\n"
                "- **Easy to learn** with clean, English-like syntax\n"
                "- **Dynamically typed** (no need to declare variable types)\n"
                "- **Multi-paradigm**: supports procedural, OOP, and functional programming\n"
                "- **Massive ecosystem**: 450,000+ packages on PyPI\n"
                "- Created by **Guido van Rossum**, first released in **1991**\n\n"
                "**Popular Use Cases:** Web development (Django, FastAPI), Data Science (Pandas, NumPy), AI/ML (TensorFlow, PyTorch), Automation, Scripting, APIs"
            )

        # -------------------------------------------------------
        # GEOGRAPHY & WORLD KNOWLEDGE
        # -------------------------------------------------------

        if any(w in norm_prompt for w in ["largest country", "biggest country"]):
            if "population" in norm_prompt or "people" in norm_prompt:
                return "The **largest country by population** is **India** (≈ 1.44 Billion), surpassing China in 2023 according to the United Nations."
            else:
                return "The **largest country by land area** is **Russia** (17.1 million km²), covering approximately 11% of Earth's total land mass."

        if any(w in norm_prompt for w in ["longest river", "biggest river"]):
            return (
                "### 🏞️ Longest Rivers in the World\n\n"
                "| Rank | River | Length | Countries |"
                "| :---: | :--- | :--- | :--- |\n"
                "| 1 | **Nile** | 6,650 km | Egypt, Sudan, Uganda |\n"
                "| 2 | **Amazon** | 6,400 km | Brazil, Peru, Colombia |\n"
                "| 3 | **Yangtze** | 6,300 km | China |\n"
                "| 4 | **Mississippi-Missouri** | 6,275 km | USA |\n"
                "| 5 | **Yenisei-Angara** | 5,539 km | Russia |\n\n"
                "**India's Longest River:** The **Ganga (Ganges)** flows approximately 2,525 km across India."
            )

        if any(w in norm_prompt for w in ["mount everest", "highest mountain", "tallest mountain", "highest peak"]):
            return (
                "### 🏔️ Mount Everest\n\n"
                "**Mount Everest** is the **highest mountain** on Earth above sea level, located in the **Himalayas** on the border of **Nepal and Tibet (China)**.\n\n"
                "**Key Facts:**\n"
                "- **Height**: 8,848.86 metres (29,031.7 feet) — revised measurement by China and Nepal in 2020\n"
                "- **First ascent**: **Edmund Hillary** (New Zealand) and **Tenzing Norgay** (Nepal) on **May 29, 1953**\n"
                "- Named after British surveyor **Sir George Everest**\n"
                "- Called **Sagarmatha** in Nepal and **Chomolungma** in Tibet/China\n"
                "- The summit temperature can fall to **-60°C (−76°F)** in winter"
            )

        if any(w in norm_prompt for w in ["amazon rainforest", "amazon forest", "amazon jungle"]):
            return (
                "### 🌳 Amazon Rainforest\n\n"
                "The **Amazon Rainforest** is the world's largest tropical rainforest, located primarily in **Brazil**, with portions in 8 other South American countries.\n\n"
                "**Key Facts:**\n"
                "- Covers approximately **5.5 million km²** (larger than the entire continent of Europe)\n"
                "- Called the **'Lungs of the Earth'** — produces about **20% of the world's oxygen**\n"
                "- Home to **10% of all species** on Earth\n"
                "- The **Amazon River** flows through it — the world's largest river by water discharge\n"
                "- Facing severe deforestation due to agriculture, logging, and mining"
            )

        # -------------------------------------------------------
        # SPORTS
        # -------------------------------------------------------

        if any(w in norm_prompt for w in ["cricket", "cricket world cup"]):
            return (
                "### 🏏 Cricket\n\n"
                "**Cricket** is a bat-and-ball sport played between two teams of 11 players, popular in the Commonwealth countries (India, England, Australia, Pakistan, West Indies, etc.).\n\n"
                "**Formats:**\n"
                "- **Test Cricket**: 5-day format (traditional and oldest form)\n"
                "- **One Day International (ODI)**: 50 overs per side\n"
                "- **Twenty20 (T20)**: 20 overs per side (fastest format)\n\n"
                "**ICC Cricket World Cup Winners:**\n"
                "- 🏆 Most titles: **Australia** (6 times: 1987, 1999, 2003, 2007, 2015, 2023)\n"
                "- 🇮🇳 **India**: Won in **1983** (Kapil Dev) and **2011** (MS Dhoni) and **2024 T20 World Cup**\n"
                "- **West Indies**: Won 1975 and 1979\n\n"
                "**Governing Body**: **ICC** (International Cricket Council)"
            )

        if any(w in norm_prompt for w in ["football", "soccer", "fifa world cup"]):
            return (
                "### ⚽ Football (Soccer) & FIFA World Cup\n\n"
                "**Football (Soccer)** is the world's most popular sport, played by over **250 million players** in more than 200 countries.\n\n"
                "**FIFA World Cup — All-Time Champions:**\n"
                "- 🏆 **Brazil**: 5 titles (1958, 1962, 1970, 1994, 2002)\n"
                "- 🇩🇪 **Germany / West Germany**: 4 titles (1954, 1974, 1990, 2014)\n"
                "- 🇮🇹 **Italy**: 4 titles (1934, 1938, 1966, 1982)\n"
                "- 🇦🇷 **Argentina**: 3 titles (1978, 1986, 2022 — Lionel Messi)\n"
                "- 🇫🇷 **France**: 2 titles (1998, 2018)\n\n"
                "**Latest**: **Argentina** won the 2022 FIFA World Cup in Qatar, led by **Lionel Messi**."
            )

        # -------------------------------------------------------
        # ECONOMICS & GENERAL KNOWLEDGE
        # -------------------------------------------------------

        if any(w in norm_prompt for w in ["gdp", "gross domestic product"]):
            return (
                "### 📊 GDP (Gross Domestic Product)\n\n"
                "**GDP (Gross Domestic Product)** is the total monetary value of all goods and services produced within a country's borders in a specific period (usually one year).\n\n"
                "**Measurement Methods:**\n"
                "1. **Expenditure Approach**: GDP = C + I + G + (X − M) [Consumption + Investment + Government + Net Exports]\n"
                "2. **Income Approach**: Sum of all incomes earned in an economy\n"
                "3. **Production Approach**: Sum of value added at each production stage\n\n"
                "**World's Largest Economies by GDP (2024):**\n"
                "1. 🇺🇸 USA — ~$27 Trillion | 2. 🇨🇳 China — ~$18 Trillion | 3. 🇩🇪 Germany | 4. 🇯🇵 Japan | 5. 🇮🇳 India"
            )

        if any(w in norm_prompt for w in ["global warming", "climate change"]):
            return (
                "### 🌡️ Global Warming & Climate Change\n\n"
                "**Global Warming** refers to the long-term rise in Earth's average surface temperature due to human activities, primarily **burning fossil fuels**, that release **greenhouse gases (GHGs)**.\n\n"
                "**Key Greenhouse Gases:** CO₂, Methane (CH₄), Nitrous Oxide (N₂O), Water vapour\n\n"
                "**Major Effects:**\n"
                "- 🌊 Rising sea levels (melting glaciers and ice caps)\n"
                "- 🌪️ More frequent and severe extreme weather events\n"
                "- 🔥 Increased droughts, heatwaves, and wildfires\n"
                "- 🐠 Loss of biodiversity and ecosystem disruption\n\n"
                "**Paris Agreement (2015)**: International treaty where countries pledged to limit global temperature rise to **1.5°C above pre-industrial levels**."
            )

        if any(w in norm_prompt for w in ["newton", "isaac newton", "newton laws", "law of motion"]):
            return (
                "### 🍎 Isaac Newton & Laws of Motion\n\n"
                "**Sir Isaac Newton** (1643–1727) was an English mathematician, physicist, and astronomer — one of the most influential scientists in history.\n\n"
                "**Newton's Three Laws of Motion:**\n"
                "1. **First Law (Law of Inertia)**: An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an external force.\n"
                "2. **Second Law**: Force = Mass × Acceleration → **F = ma**\n"
                "3. **Third Law**: For every action, there is an equal and opposite reaction.\n\n"
                "**Other Major Contributions:**\n"
                "- Discovered **Universal Gravitation**\n"
                "- Developed **Calculus** (independently with Leibniz)\n"
                "- Studied **optics** and discovered white light is a spectrum of colours"
            )

        if any(w in norm_prompt for w in ["albert einstein", "einstein", "theory of relativity", "e=mc2", "e = mc"]):
            return (
                "### 🧑‍🔬 Albert Einstein\n\n"
                "**Albert Einstein** (March 14, 1879 – April 18, 1955) was a German-born theoretical physicist widely regarded as one of the greatest scientists of all time.\n\n"
                "**Major Contributions:**\n"
                "- **Special Theory of Relativity** (1905): Time and space are relative; the famous equation **E = mc²** (energy equals mass times speed of light squared)\n"
                "- **General Theory of Relativity** (1915): Gravity is the curvature of spacetime caused by mass\n"
                "- Explained the **Photoelectric Effect** (which earned him the **Nobel Prize in Physics** in 1921)\n"
                "- Contributed to **Brownian Motion** and quantum theory\n\n"
                "**Famous Quote**: *\"Imagination is more important than knowledge.\"*"
            )

        if any(w in norm_prompt for w in ["periodic table", "elements"]):
            return (
                "### ⚗️ The Periodic Table\n\n"
                "The **Periodic Table** organises all known **118 chemical elements** in rows (periods) and columns (groups) based on atomic number, electron configuration, and chemical properties.\n\n"
                "**Structure:**\n"
                "- **18 Groups (Columns)**: Elements in the same group share similar chemical properties\n"
                "- **7 Periods (Rows)**: Indicate the number of electron shells\n"
                "- Developed by **Dmitri Mendeleev** in **1869**\n\n"
                "**Key Element Groups:**\n"
                "- Group 1: **Alkali Metals** (Li, Na, K...) | Group 17: **Halogens** (F, Cl, Br...)\n"
                "- Group 18: **Noble Gases** (He, Ne, Ar...) — extremely stable, rarely react\n"
                "- **Lightest element**: Hydrogen (H, atomic no. 1) | **Heaviest stable**: Uranium (U, 92)"
            )

        if any(w in norm_prompt for w in ["black hole", "blackhole"]):
            return (
                "### 🌑 Black Holes\n\n"
                "A **black hole** is a region of spacetime where gravity is so strong that **nothing — not even light** — can escape from it once it crosses the **event horizon**.\n\n"
                "**Key Facts:**\n"
                "- Formed when a **massive star collapses** at the end of its life in a supernova explosion\n"
                "- The boundary of a black hole is called the **Event Horizon**\n"
                "- The centre is called the **Singularity** — where density becomes infinite\n"
                "- **Stephen Hawking** proposed that black holes emit **Hawking Radiation** and slowly evaporate\n"
                "- First **image of a black hole** captured in 2019 by the **Event Horizon Telescope (EHT)** — M87 galaxy black hole\n"
                "- Our galaxy, the **Milky Way**, has a supermassive black hole at its centre called **Sagittarius A***"
            )

        if any(w in norm_prompt for w in ["constitution of india", "indian constitution"]):
            return (
                "### 📜 Constitution of India\n\n"
                "The **Constitution of India** is the supreme law of India, adopted on **November 26, 1949** and came into effect on **January 26, 1950** (celebrated as **Republic Day**).\n\n"
                "**Key Facts:**\n"
                "- Drafted by the **Constituent Assembly** chaired by **Dr. B.R. Ambedkar** (Chairman of Drafting Committee — 'Father of the Indian Constitution')\n"
                "- **Longest written constitution** in the world\n"
                "- Originally had 395 Articles, 8 Schedules, and 22 Parts (now 448 articles, 12 schedules, 25 parts)\n"
                "- **Preamble** declares India a **Sovereign, Socialist, Secular, Democratic Republic**\n"
                "- **Fundamental Rights**: Articles 12–35 (Right to Equality, Freedom, Life, Education, etc.)\n"
                "- **Directive Principles of State Policy**: Articles 36–51 (guidelines for governance)"
            )

        if any(w in norm_prompt for w in ["computer", "what is computer", "about computer"]):
            if any(w in norm_prompt for w in ["what is", "define", "explain", "describe", "about", "meaning"]):
                return (
                    "### 💻 Computer\n\n"
                    "A **computer** is an electronic device that processes data according to a set of instructions (programs) to produce meaningful results.\n\n"
                    "**Main Components:**\n"
                    "- **Hardware**: Physical components — CPU, RAM, HDD/SSD, Monitor, Keyboard, Mouse\n"
                    "- **Software**: Programs and operating systems — Windows, Linux, macOS\n\n"
                    "**Types of Computers:**\n"
                    "- **Supercomputer** (most powerful), **Mainframe**, **Minicomputer**, **Personal Computer (PC)**, **Laptop**, **Tablet**, **Smartphone**\n\n"
                    "**Generations of Computers:**\n"
                    "1. **1st Gen** (1940–56): Vacuum tubes | 2. **2nd Gen** (1956–63): Transistors\n"
                    "3. **3rd Gen** (1964–71): Integrated Circuits | 4. **4th Gen** (1971–present): Microprocessors\n"
                    "5. **5th Gen** (present–future): AI & Quantum Computing"
                )

        if any(w in norm_prompt for w in ["ozone layer", "ozone depletion"]):
            return (
                "### 🌍 Ozone Layer\n\n"
                "The **Ozone Layer** is a region of Earth's stratosphere (about 15–35 km above the surface) that contains high concentrations of **ozone (O₃)** molecules.\n\n"
                "**Function:**\n"
                "- Absorbs **95–99% of the Sun's harmful ultraviolet (UV-B and UV-C) radiation**\n"
                "- Protects living organisms from UV-induced damage (skin cancer, cataracts, ecosystem damage)\n\n"
                "**Ozone Depletion:**\n"
                "- Caused mainly by **Chlorofluorocarbons (CFCs)**, halons, and other human-made chemicals\n"
                "- A significant **ozone hole** was discovered over **Antarctica** in the 1980s\n"
                "- **Montreal Protocol (1987)**: International treaty that phased out ozone-depleting substances — considered highly successful"
            )

        # Check Math Evaluation
        math_ans = cls._evaluate_math(prompt)
        if math_ans:
            return math_ans

        return None



    @classmethod
    def _analyze_document_content(cls, files: List[Dict[str, Any]], prompt: str) -> str:
        extracted_info = []
        for f in files:
            fname = f.get("filename", "attached_file")
            is_pdf = f.get("is_pdf", False) or fname.lower().endswith(".pdf")
            raw_data = f.get("data", "")
            
            if is_pdf:
                text = extract_pdf_text(raw_data)
            else:
                text = raw_data
                if "," in text and text.startswith("data:"):
                    try:
                        text = base64.b64decode(text.split(",", 1)[1]).decode("utf-8", errors="ignore")
                    except Exception:
                        pass

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            word_count = len(text.split())
            
            extracted_info.append({
                "filename": fname,
                "text": text,
                "lines": lines,
                "word_count": word_count,
                "is_pdf": is_pdf
            })

        response_lines = ["### 📄 Document Analysis & Content Insight\n"]
        for doc in extracted_info:
            fname = doc["filename"]
            text = doc["text"]
            lines = doc["lines"]
            word_count = doc["word_count"]
            
            response_lines.append(f"#### **Attached File**: `{fname}`")
            response_lines.append(f"- **Format**: {'PDF Document' if doc['is_pdf'] else 'Text / Code File'}")
            response_lines.append(f"- **Document Size**: ~{word_count} words | {len(lines)} lines of extracted text\n")
            
            if "Could not parse" in text or "scanned images" in text:
                response_lines.append(f"> ⚠️ *{text}*\n")
            else:
                preview_snippet = "\n".join(lines[:30]) if len(lines) > 30 else text
                if len(preview_snippet) > 2500:
                    preview_snippet = preview_snippet[:2500] + "\n\n[...Content truncated for display...]"
                
                response_lines.append("##### 📌 Key Content & Extracted Text Summary:")
                response_lines.append(f"```text\n{preview_snippet}\n```\n")

        if prompt and prompt.strip():
            user_q = prompt.strip()
            response_lines.append(f"#### 💡 Document Answer for: *\"{user_q}\"*")
            response_lines.append("The document text has been decoded and processed above.")

        return "\n".join(response_lines)

    @classmethod
    def _analyze_image_content(cls, images: List[Dict[str, str]], prompt: str) -> str:
        analyzed_images = []
        for idx, img in enumerate(images):
            mime_type = img.get("mime_type", "image/jpeg")
            data_str = img.get("data", "")
            if "," in data_str:
                data_str = data_str.split(",", 1)[1]

            width, height, fmt, mode = None, None, None, None
            try:
                raw_bytes = base64.b64decode(data_str)
                with Image.open(io.BytesIO(raw_bytes)) as pil_img:
                    width, height = pil_img.size
                    fmt = pil_img.format
                    mode = pil_img.mode
            except Exception as e:
                logger.error(f"Image processing error: {e}")

            analyzed_images.append({
                "index": idx + 1,
                "mime_type": mime_type,
                "width": width,
                "height": height,
                "format": fmt,
                "mode": mode
            })

        response_lines = [f"### 📷 Attached Image Received ({len(images)} File{'s' if len(images) > 1 else ''})\n"]
        for img in analyzed_images:
            dim_str = f"{img['width']} × {img['height']} pixels" if img['width'] else "Image File"
            fmt_str = img['format'] or img['mime_type'].split('/')[-1].upper()
            
            response_lines.append(f"- **Image #{img['index']}**: `{dim_str}` | Format: `{fmt_str}` | Type: `{img['mime_type']}`")

        response_lines.append(
            "\n> 💡 **Notice**: To analyze image details, perform OCR, or verify certificate authenticity using Vision AI, please configure a **Google Gemini API Key** in **Settings (⚙️)**.\n\n"
            "1. Open **Settings (⚙️)** in the navbar.\n"
            "2. Enter your Gemini API key (free from [aistudio.google.com](https://aistudio.google.com/app/apikey)).\n"
            "3. Select **Google Gemini 1.5** in the model selector and try again!"
        )

        return "\n".join(response_lines)

    @staticmethod
    def _generate_code_response(prompt_lower: str) -> str:
        """Generates specific, accurate multi-language code snippets (Java, C++, JS, Python, C#, HTML, SQL, etc.)."""
        
        # 1. Detect requested programming language
        lang = "python"
        if re.search(r'\b(java)\b', prompt_lower) and not re.search(r'\b(javascript)\b', prompt_lower):
            lang = "java"
        elif re.search(r'\b(javascript|js|node|react|express)\b', prompt_lower):
            lang = "javascript"
        elif re.search(r'\b(cpp|c\+\+)\b', prompt_lower):
            lang = "cpp"
        elif re.search(r'\b(c#|csharp|dotnet|\.net)\b', prompt_lower):
            lang = "csharp"
        elif re.search(r'\b(html|css|web)\b', prompt_lower):
            lang = "html"
        elif re.search(r'\b(sql|database|query|mysql|postgresql)\b', prompt_lower):
            lang = "sql"
        elif re.search(r'\b(typescript|ts)\b', prompt_lower):
            lang = "typescript"
        elif re.search(r'\b(php)\b', prompt_lower):
            lang = "php"
        elif re.search(r'\b(go|golang)\b', prompt_lower):
            lang = "go"
        elif re.search(r'\b(rust)\b', prompt_lower):
            lang = "rust"
        elif re.search(r'\b(python|py)\b', prompt_lower):
            lang = "python"

        # 2. Detect requested operation
        is_multiply_divide = any(w in prompt_lower for w in ["multiply", "multiplication", "divide", "division", "mult", "div"])
        is_calculator = any(w in prompt_lower for w in ["calculator", "calc", "add subtract"])
        is_prime = any(w in prompt_lower for w in ["prime", "prime number"])
        is_fibonacci = any(w in prompt_lower for w in ["fibonacci", "series"])
        is_factorial = any(w in prompt_lower for w in ["factorial"])
        is_palindrome = any(w in prompt_lower for w in ["palindrome", "reverse string", "reverse"])

        # 3. Generate Code per Language & Task
        
        # --- JAVA ---
        if lang == "java":
            if is_multiply_divide:
                return (
                    "### ☕ Java - Multiply and Divide Program\n\n"
                    "Here is a clean Java program to perform multiplication and division:\n\n"
                    "```java\n"
                    "// Java Program: Multiplication & Division\n"
                    "public class MultiplyDivide {\n"
                    "    public static void main(String[] args) {\n"
                    "        double num1 = 20.0;\n"
                    "        double num2 = 4.0;\n\n"
                    "        double product = multiply(num1, num2);\n"
                    "        double quotient = divide(num1, num2);\n\n"
                    "        System.out.println(\"Multiplication (\" + num1 + \" * \" + num2 + \") = \" + product);\n"
                    "        System.out.println(\"Division (\" + num1 + \" / \" + num2 + \") = \" + quotient);\n"
                    "    }\n\n"
                    "    public static double multiply(double a, double b) {\n"
                    "        return a * b;\n"
                    "    }\n\n"
                    "    public static double divide(double a, double b) {\n"
                    "        if (b == 0) {\n"
                    "            System.out.println(\"Error: Cannot divide by zero!\");\n"
                    "            return 0;\n"
                    "        }\n"
                    "        return a / b;\n"
                    "    }\n"
                    "}\n"
                    "```"
                )
            elif is_calculator:
                return (
                    "### ☕ Java - Calculator Program\n\n"
                    "```java\n"
                    "public class Calculator {\n"
                    "    public static void main(String[] args) {\n"
                    "        double a = 15.0, b = 5.0;\n"
                    "        System.out.println(\"Addition: \" + (a + b));\n"
                    "        System.out.println(\"Subtraction: \" + (a - b));\n"
                    "        System.out.println(\"Multiplication: \" + (a * b));\n"
                    "        System.out.println(\"Division: \" + (b != 0 ? (a / b) : \"Error\"));\n"
                    "    }\n"
                    "}\n"
                    "```"
                )
            elif is_prime:
                return (
                    "### ☕ Java - Prime Number Checker\n\n"
                    "```java\n"
                    "public class PrimeChecker {\n"
                    "    public static boolean isPrime(int n) {\n"
                    "        if (n <= 1) return false;\n"
                    "        for (int i = 2; i <= Math.sqrt(n); i++) {\n"
                    "            if (n % i == 0) return false;\n"
                    "        }\n"
                    "        return true;\n"
                    "    }\n"
                    "    public static void main(String[] args) {\n"
                    "        int num = 29;\n"
                    "        System.out.println(num + \" is prime? \" + isPrime(num));\n"
                    "    }\n"
                    "}\n"
                    "```"
                )
            else:
                return (
                    "### ☕ Java - Simple Program Example\n\n"
                    "Here is a clean Java program demonstrating class structure and array iteration:\n\n"
                    "```java\n"
                    "public class Main {\n"
                    "    public static void main(String[] args) {\n"
                    "        System.out.println(\"Hello, World! Welcome to Java Programming.\");\n\n"
                    "        int[] numbers = {10, 20, 30, 40, 50};\n"
                    "        int sum = 0;\n"
                    "        for (int num : numbers) {\n"
                    "            sum += num;\n"
                    "        }\n"
                    "        System.out.println(\"Sum of elements: \" + sum);\n"
                    "    }\n"
                    "}\n"
                    "```"
                )

        # --- C++ ---
        elif lang == "cpp":
            if is_multiply_divide:
                return (
                    "### ⚡ C++ - Multiply and Divide Program\n\n"
                    "```cpp\n"
                    "#include <iostream>\n"
                    "using namespace std;\n\n"
                    "double multiply(double a, double b) {\n"
                    "    return a * b;\n"
                    "}\n\n"
                    "double divide(double a, double b) {\n"
                    "    if (b == 0) {\n"
                    "        cout << \"Error: Division by zero!\" << endl;\n"
                    "        return 0;\n"
                    "    }\n"
                    "    return a / b;\n"
                    "}\n\n"
                    "int main() {\n"
                    "    double x = 12.0, y = 3.0;\n"
                    "    cout << \"Multiplication: \" << multiply(x, y) << endl;\n"
                    "    cout << \"Division: \" << divide(x, y) << endl;\n"
                    "    return 0;\n"
                    "}\n"
                    "```"
                )
            else:
                return (
                    "### ⚡ C++ - Basic Program Example\n\n"
                    "```cpp\n"
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    cout << \"Hello World in C++!\" << endl;\n"
                    "    vector<int> nums = {1, 2, 3, 4, 5};\n"
                    "    for(int n : nums) {\n"
                    "        cout << n << \" \";\n"
                    "    }\n"
                    "    cout << endl;\n"
                    "    return 0;\n"
                    "}\n"
                    "```"
                )

        # --- JAVASCRIPT ---
        elif lang == "javascript":
            if is_multiply_divide:
                return (
                    "### 💛 JavaScript - Multiply and Divide Code\n\n"
                    "```javascript\n"
                    "function multiply(a, b) {\n"
                    "    return a * b;\n"
                    "}\n\n"
                    "function divide(a, b) {\n"
                    "    if (b === 0) {\n"
                    "        console.error('Error: Cannot divide by zero');\n"
                    "        return null;\n"
                    "    }\n"
                    "    return a / b;\n"
                    "}\n\n"
                    "const x = 30, y = 5;\n"
                    "console.log(`Multiplication: ${x} * ${y} = ${multiply(x, y)}`);\n"
                    "console.log(`Division: ${x} / ${y} = ${divide(x, y)}`);\n"
                    "```"
                )
            else:
                return (
                    "### 💛 JavaScript - Beginner Code Example\n\n"
                    "```javascript\n"
                    "// JavaScript Array Filter & Map Example\n"
                    "const numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];\n"
                    "const doubledEvens = numbers\n"
                    "    .filter(n => n % 2 === 0)\n"
                    "    .map(n => n * 2);\n\n"
                    "console.log('Doubled even numbers:', doubledEvens);\n"
                    "```"
                )

        # --- C# ---
        elif lang == "csharp":
            return (
                "### 🔷 C# - Multiply and Divide Example\n\n"
                "```csharp\n"
                "using System;\n\n"
                "class Program {\n"
                "    static void Main() {\n"
                "        double a = 50.0, b = 5.0;\n"
                "        Console.WriteLine($\"Multiplication: {a * b}\");\n"
                "        Console.WriteLine($\"Division: {(b != 0 ? (a / b).ToString() : \"Error\")}\");\n"
                "    }\n"
                "}\n"
                "```"
            )

        # --- HTML / CSS ---
        elif lang == "html":
            return (
                "### 🌐 HTML5 & CSS3 Web Layout\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "    <meta charset=\"UTF-8\">\n"
                "    <title>AI BOT Web Page</title>\n"
                "    <style>\n"
                "        body { font-family: sans-serif; background: #131314; color: #fff; padding: 2rem; }\n"
                "        .card { background: #1E1F20; padding: 1.5rem; border-radius: 12px; max-width: 400px; }\n"
                "    </style>\n"
                "</head>\n"
                "<body>\n"
                "    <div class=\"card\">\n"
                "        <h2>Hello Developer</h2>\n"
                "        <p>This is a clean HTML5 web page container.</p>\n"
                "    </div>\n"
                "</body>\n"
                "</html>\n"
                "```"
            )

        # --- SQL ---
        elif lang == "sql":
            return (
                "### 🗄️ SQL Query Example\n\n"
                "```sql\n"
                "-- Create Table\n"
                "CREATE TABLE users (\n"
                "    id INT PRIMARY KEY AUTO_INCREMENT,\n"
                "    username VARCHAR(50) NOT NULL,\n"
                "    email VARCHAR(100) UNIQUE NOT NULL,\n"
                "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                ");\n\n"
                "-- Query with Join and Aggregate\n"
                "SELECT username, COUNT(id) AS total_orders\n"
                "FROM users\n"
                "WHERE created_at >= '2026-01-01'\n"
                "GROUP BY username;\n"
                "```"
            )

        # --- PYTHON (Default) ---
        else:
            if is_multiply_divide:
                return (
                    "### 🐍 Python - Multiply and Divide Code\n\n"
                    "Here is Python code to multiply and divide numbers:\n\n"
                    "```python\n"
                    "def multiply(a, b):\n"
                    "    return a * b\n\n"
                    "def divide(a, b):\n"
                    "    if b == 0:\n"
                    "        return 'Error: Division by zero'\n"
                    "    return a / b\n\n"
                    "x, y = 20, 4\n"
                    "print(f'Multiplication ({x} * {y}): {multiply(x, y)}')\n"
                    "print(f'Division ({x} / {y}): {divide(x, y)}')\n"
                    "```"
                )
            elif is_calculator:
                return (
                    "### 🧮 Python - Calculator Program\n\n"
                    "```python\n"
                    "def add(a, b): return a + b\n"
                    "def subtract(a, b): return a - b\n"
                    "def multiply(a, b): return a * b\n"
                    "def divide(a, b): return a / b if b != 0 else 'Error'\n\n"
                    "a, b = 15, 3\n"
                    "print('Add:', add(a, b))\n"
                    "print('Multiply:', multiply(a, b))\n"
                    "print('Divide:', divide(a, b))\n"
                    "```"
                )
            elif is_prime:
                return (
                    "### 🔢 Python - Prime Number Checker\n\n"
                    "```python\n"
                    "def is_prime(n):\n"
                    "    if n <= 1: return False\n"
                    "    for i in range(2, int(n**0.5) + 1):\n"
                    "        if n % i == 0: return False\n"
                    "    return True\n\n"
                    "num = 29\n"
                    "print(f'{num} is prime? {is_prime(num)}')\n"
                    "```"
                )
            else:
                return (
                    "### 🐍 Python - Simple Code Example\n\n"
                    "```python\n"
                    "# Simple Python Greetings & List Filtering Example\n\n"
                    "def greet_user(name):\n"
                    "    print(f'Hello, {name}! Welcome to Python.')\n\n"
                    "numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\n"
                    "evens = [n for n in numbers if n % 2 == 0]\n\n"
                    "greet_user('Developer')\n"
                    "print('Even Numbers:', evens)\n"
                    "```"
                )

    @classmethod
    def _extract_active_topic(cls, history: List[Dict[str, Any]]) -> str:
        """Inspects previous conversation history to determine the active topic."""
        if not history:
            return "aiml_roadmap"
            
        for msg in reversed(history[-6:]):
            text = str(msg.get("content", "")).lower()
            if any(w in text for w in ["roadmap", "road map", "aiml", "ai engineer", "ml engineer", "learning path", "study plan"]):
                return "aiml_roadmap"
            elif any(w in text for w in ["neural network", "neural net", "ann", "cnn", "rnn", "deep learning"]):
                return "neural_network"
            elif any(w in text for w in ["machine learning", "supervised", "unsupervised", "reinforcement"]):
                return "machine_learning"
            elif any(w in text for w in ["python", "list", "tuple", "decorator", "gil"]):
                return "python"
            elif any(w in text for w in ["sql", "table", "database", "query"]):
                return "database_sql"
            elif any(w in text for w in ["html", "css", "javascript", "web"]):
                return "web_dev"

        return "aiml_roadmap"

    @classmethod
    def _detect_followup_intent(cls, prompt_lower: str) -> Optional[str]:
        """Classifies follow-up intent types from user query."""
        if any(w in prompt_lower for w in ["diagram", "flowchart", "architecture", "visual", "diagrammatic", "structure diagram", "draw", "box diagram", "diagram based"]):
            return "DIAGRAM"
        elif any(w in prompt_lower for w in ["give example", "give me example", "examples", "with example", "show example", "sample"]):
            return "EXAMPLE"
        elif any(w in prompt_lower for w in ["give code", "show code", "in python", "code snippet", "write code", "implementation"]):
            return "CODE"
        elif any(w in prompt_lower for w in ["make it simple", "explain simply", "easier", "beginner level", "simple words", "layman"]):
            return "SIMPLIFY"
        elif any(w in prompt_lower for w in ["continue", "tell me more", "next", "more details", "expand", "go on", "elaborate"]):
            return "CONTINUE"
        elif any(w in prompt_lower for w in ["summarize", "summary", "short answer", "in short", "briefly"]):
            return "SUMMARY"
        elif any(w in prompt_lower for w in ["project", "projects", "project idea", "hands on project"]):
            return "PROJECT"
        elif any(w in prompt_lower for w in ["interview question", "interview q&a", "interview questions"]):
            return "INTERVIEW"
        elif any(w in prompt_lower for w in ["table", "matrix", "comparison table"]):
            return "TABLE"

        return None

    @classmethod
    def _generate_diagram_for_topic(cls, topic: str, prompt_raw: str) -> str:
        """Renders visual ASCII / text diagrams for topics."""
        if topic == "aiml_roadmap" or any(w in prompt_raw.lower() for w in ["roadmap", "aiml", "study", "path", "engineer"]):
            return (
                "### 🗺️ AI/ML Engineer Roadmap Diagram\n\n"
                "```text\n"
                "                    AI/ML ENGINEER ROADMAP\n"
                "                               |\n"
                "              ┌────────────┴────────────┐\n"
                "              |                         |\n"
                "        PROGRAMMING                MATHEMATICS\n"
                "              |                         |\n"
                "           Python              Linear Algebra\n"
                "              |                 Probability\n"
                "              |                   Statistics\n"
                "              |\n"
                "       DATA ANALYSIS\n"
                "              |\n"
                "      NumPy → Pandas → Matplotlib\n"
                "              |\n"
                "       MACHINE LEARNING\n"
                "              |\n"
                "   Regression → Classification\n"
                "              |\n"
                "      Decision Trees\n"
                "      Random Forest\n"
                "      XGBoost\n"
                "              |\n"
                "       DEEP LEARNING\n"
                "              |\n"
                "    Neural Networks → CNN → RNN\n"
                "              |\n"
                "       GENERATIVE AI\n"
                "              |\n"
                "      LLMs → RAG → Agents\n"
                "              |\n"
                "        DEPLOYMENT\n"
                "              |\n"
                "     FastAPI → Docker → Cloud\n"
                "              |\n"
                "        AI/ML ENGINEER\n"
                "        JOB READY 🚀\n"
                "```\n\n"
                "#### Detailed Stage Breakdown:\n\n"
                "1. **Programming Foundations (Month 1)**: Python syntax, functions, OOP, data structures (`list`, `dict`, `tuple`, `set`).\n"
                "2. **Mathematics & Statistics (Month 1)**: Linear Algebra (Vectors, Matrices), Calculus (Gradients), Probability & Inferential Statistics.\n"
                "3. **Data Analysis & Visualization (Month 2)**: **NumPy**, **Pandas**, **Matplotlib** & **Seaborn** for EDA.\n"
                "4. **Classical Machine Learning (Months 3–4)**: Supervised & Unsupervised Learning algorithms using **Scikit-Learn**.\n"
                "5. **Deep Learning (Months 5–6)**: Neural Networks, **PyTorch** / **TensorFlow**, CNNs (Vision), RNNs/Transformers (NLP).\n"
                "6. **Generative AI & LLMs (Month 7)**: LangChain, Embeddings, Vector DBs (Chroma/Pinecone), RAG, and Agents.\n"
                "7. **MLOps & Production (Month 8)**: **FastAPI**, **Docker**, Model Serving, MLflow, and Cloud Deployment (AWS/GCP)."
            )
        elif topic == "machine_learning":
            return (
                "### 🧠 Machine Learning Architecture Diagram\n\n"
                "```text\n"
                "                   MACHINE LEARNING SYSTEM\n"
                "                              |\n"
                "       ┌──────────────────────┼──────────────────────┐\n"
                "       |                      |                      |\n"
                "  SUPERVISED             UNSUPERVISED           REINFORCEMENT\n"
                "   LEARNING               LEARNING                LEARNING\n"
                "       |                      |                      |\n"
                "┌──────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐\n"
                "|             |        |             |        |             |\n"
                "Regression  Classif.  Clustering  Dim. Red.  Agent       Reward\n"
                " (Linear)   (Random   (K-Means)    (PCA)   (Trial/Error) System\n"
                "            Forest)\n"
                "```\n\n"
                "#### Key Components:\n"
                "- **Supervised Learning**: Model learns mapping from labeled input data to output targets.\n"
                "- **Unsupervised Learning**: Model discovers intrinsic structures and clusters in unlabeled data.\n"
                "- **Reinforcement Learning**: Agent maximizes cumulative rewards through environment interaction."
            )
        elif topic == "neural_network":
            return (
                "### 🕸️ Neural Network Layer Diagram\n\n"
                "```text\n"
                "                    ARTIFICIAL NEURAL NETWORK\n"
                "                               |\n"
                "        INPUT LAYER       HIDDEN LAYERS       OUTPUT LAYER\n"
                "       ┌───────────┐      ┌───────────┐      ┌───────────┐\n"
                "       |  Feature  | ───> | Neuron W1 | ───> | Prediction|\n"
                "       |  Vector   | ───> | Neuron W2 | ───> |   Score   |\n"
                "       └───────────┘      └───────────┘      └───────────┘\n"
                "                                |\n"
                "                        ACTIVATION (ReLU)\n"
                "                                |\n"
                "                        BACKPROPAGATION\n"
                "```\n\n"
                "#### Core Components:\n"
                "1. **Input Layer**: Receives features or raw token embeddings.\n"
                "2. **Hidden Layers**: Calculates `W * X + b` across weighted neurons.\n"
                "3. **Activation**: Applies non-linear function (ReLU, Sigmoid, Softmax).\n"
                "4. **Backpropagation**: Adjusts weights backward using gradient descent."
            )
        else:
            return (
                f"### 📊 Visual Structure: {topic.replace('_', ' ').title()}\n\n"
                "```text\n"
                "                 DEVELOPMENT & WORKFLOW PIPELINE\n"
                "                               |\n"
                "        Requirements → System Design → Implementation\n"
                "                               |\n"
                "                   Testing & Quality Assurance\n"
                "                               |\n"
                "                    Deployment & Monitoring 🚀\n"
                "```\n\n"
                "1. **Requirements & Scope**: Define clear objectives and data schema.\n"
                "2. **Implementation**: Write clean, efficient, modular code.\n"
                "3. **Verification**: Run unit testing and edge case validation."
            )

    @classmethod
    async def generate_smart_fallback_stream(cls, prompt: str, history: List[Dict[str, Any]] = None, files: List[Dict[str, Any]] = None, images: List[Dict[str, str]] = None) -> AsyncGenerator[str, None]:
        history = history or []
        prompt_raw = prompt.strip()
        prompt_lower = prompt_raw.lower()

        # Check if file attachments exist
        if files:
            doc_analysis = cls._analyze_document_content(files, prompt)
            words = doc_analysis.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
                await asyncio.sleep(0.01)
            return

        # Check if image attachments exist
        if images:
            img_analysis = cls._analyze_image_content(images, prompt)
            words = img_analysis.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
                await asyncio.sleep(0.01)
            return

        # Context Resolution for follow-up questions
        active_topic = cls._extract_active_topic(history)
        followup_intent = cls._detect_followup_intent(prompt_lower)

        # 0. FOLLOW-UP INTENT HANDLERS (e.g. "with proper diagram", "give example", "make it simple", "give code")
        if followup_intent == "DIAGRAM" or any(w in prompt_lower for w in ["diagram", "flowchart", "architecture", "visual"]):
            response_text = cls._generate_diagram_for_topic(active_topic, prompt_raw)

        elif followup_intent == "EXAMPLE":
            if active_topic == "python":
                response_text = "### 🐍 Python Code Examples\n\n```python\n# Filter even numbers & double them\nnumbers = [1, 2, 3, 4, 5, 6]\nevencopy = [n * 2 for n in numbers if n % 2 == 0]\nprint(evencopy)  # [4, 8, 12]\n```"
            elif active_topic == "machine_learning":
                response_text = "### 🧠 Machine Learning Code Example\n\n```python\nfrom sklearn.ensemble import RandomForestClassifier\n\nX = [[0, 0], [1, 1]]\ny = [0, 1]\nmodel = RandomForestClassifier()\nmodel.fit(X, y)\nprint('Prediction:', model.predict([[0.8, 0.8]])) # [1]\n```"
            else:
                response_text = f"### 💡 Practical Example for {active_topic.replace('_', ' ').title()}\n\nHere is a practical example showing real-world implementation step-by-step!"

        elif followup_intent == "CODE":
            response_text = cls._generate_code_response(active_topic)

        elif followup_intent == "SIMPLIFY":
            response_text = f"### 💡 Simplified Explanation ({active_topic.replace('_', ' ').title()})\n\nThink of it simply: It breaks complex tasks into small, manageable steps so anyone can follow along step-by-step!"

        # 1. TIME & DATE QUERIES
        elif any(w in prompt_lower for w in ["what time", "current time", "time right now", "time now", "what is the time", "today date", "what date", "time is it"]):
            t_data = TimeService.get_time_for_tz("Asia/Kolkata", "Local Time")
            response_text = f"🕒 **Current Local Time**: **{t_data['time_formatted']}** ({t_data['time_short']})\n\n📅 **Date**: **{t_data['date_formatted']}**"

        # 2. WEATHER QUERIES
        elif WeatherService.is_weather_intent(prompt_lower):
            loc = WeatherService.extract_location(prompt_lower) or "Maharashtra"
            w_res = await WeatherService.get_weather_by_city(loc)
            response_text = WeatherService.format_weather_markdown(w_res, original_query=prompt_lower)

        # 3. AI / ML ENGINEER ROADMAP QUERIES (Handles typos like 'aiml', 'begineer', 'fulent')
        elif any(w in prompt_lower for w in [
            "roadmap", "road map", "aiml", "ai engineer", "ml engineer", "learning path", "study plan",
            "how study", "how to study", "how learn", "how to learn", "beginner to fluent", "fulent", "begineer", "ai/ml"
        ]) and any(w in prompt_lower for w in ["ai", "ml", "engineer", "machine learning", "roadmap", "aiml", "study", "student"]):
            response_text = (
                "### 🚀 Complete AI/ML Engineer Roadmap (Beginner to Fluent / Job-Ready)\n\n"
                "Here is a comprehensive, step-by-step learning path to master Artificial Intelligence and Machine Learning:\n\n"
                "#### Phase 1: Foundations & Programming (Month 1)\n"
                "- **Python Fundamentals**: Master variables, loops, data structures (`list`, `dict`, `set`, `tuple`), functions, and OOP.\n"
                "- **Math Essentials**: Linear Algebra (Vectors, Matrices, Dot Product), Calculus (Gradients, Derivatives), and Probability & Statistics.\n\n"
                "#### Phase 2: Data Manipulation & Visualization (Month 2)\n"
                "- **NumPy & Pandas**: Data cleaning, indexing, aggregation, and preprocessing.\n"
                "- **Matplotlib & Seaborn**: Exploratory Data Analysis (EDA) and data visualization.\n\n"
                "#### Phase 3: Classical Machine Learning (Months 3–4)\n"
                "- **Scikit-Learn**: Supervised Learning (Linear/Logistic Regression, Decision Trees, Random Forests, SVMs, XGBoost) and Unsupervised Learning (K-Means, PCA).\n"
                "- **Model Evaluation**: Metrics (Accuracy, Precision, Recall, F1-Score, ROC-AUC) & Cross-Validation.\n\n"
                "#### Phase 4: Deep Learning & Frameworks (Months 5–6)\n"
                "- **Neural Networks**: Artificial Neurons, Activation Functions (ReLU, Sigmoid), Backpropagation, and Loss Functions.\n"
                "- **Frameworks**: PyTorch or TensorFlow.\n"
                "- **Specializations**: Computer Vision (CNNs) and Natural Language Processing (RNNs/LSTMs, Attention Mechanisms).\n\n"
                "#### Phase 5: Generative AI, LLMs & MLOps (Months 7+)\n"
                "- **Generative AI & LLMs**: Transformers, Hugging Face, LangChain, Embeddings, Vector Databases (Chroma/Pinecone), and RAG.\n"
                "- **MLOps & Deployment**: FastAPI, Docker, Model Tracking (MLflow), and Cloud Serving (AWS/GCP).\n\n"
                "💡 **Study Recommendation**: Dedicate 2 hours daily: 1 hour for concepts and 1 hour building hands-on projects!"
            )

        # 4. NEURAL NETWORK EXPLANATIONS
        elif any(w in prompt_lower for w in ["neural network", "neural net", "explain neural network", "what is neural network", "deep neural network"]):
            response_text = (
                "### 🕸️ Understanding Artificial Neural Networks\n\n"
                "An **Artificial Neural Network (ANN)** is a machine learning model inspired by the biological neural networks in the human brain. It forms the core foundation of **Deep Learning**.\n\n"
                "#### Core Architecture:\n"
                "1. **Input Layer**: Receives raw data (e.g. image pixels, text tokens, or sensor values).\n"
                "2. **Hidden Layers**: Intermediate layers of artificial neurons (nodes) that learn mathematical features using **Weights** and **Biases**.\n"
                "3. **Activation Function**: Introduces non-linearity (e.g., **ReLU**, **Sigmoid**, **Softmax**), enabling the network to learn complex patterns.\n"
                "4. **Output Layer**: Produces the final prediction (e.g. classifying an image as 'Cat' or 'Dog').\n\n"
                "#### How Training Works:\n"
                "- **Forward Pass**: Input data passes through the network to calculate a prediction.\n"
                "- **Loss Function**: Measures the error between predicted output and true target.\n"
                "- **Backpropagation**: Calculates gradients using calculus and updates weights backward using **Gradient Descent** to minimize loss."
            )

        # 5. MACHINE LEARNING EXPLANATIONS
        elif any(w in prompt_lower for w in ["what is machine learning", "explain machine learning", "tell me about machine learning", "define machine learning"]):
            response_text = (
                "### 🧠 What is Machine Learning?\n\n"
                "**Machine Learning (ML)** is a subset of Artificial Intelligence (AI) focused on building systems that learn patterns from historical data and make predictions without being explicitly programmed.\n\n"
                "#### 3 Core Types of Machine Learning:\n"
                "1. **Supervised Learning**: Algorithms trained on labeled dataset (e.g. Email Spam Detection, House Price Prediction).\n"
                "2. **Unsupervised Learning**: Algorithms that discover hidden structures in unlabeled data (e.g. Customer Segmentation, K-Means Clustering).\n"
                "3. **Reinforcement Learning**: Agents learning optimal decisions via rewards and penalties in an environment (e.g. Self-driving cars, Game AI like AlphaGo).\n\n"
                "#### Real-World Example:\n"
                "- **Email Spam Filter**: Analyzes thousands of past emails (sender info, keywords) to automatically flag incoming spam messages."
            )

        # 6. PYTHON INTERVIEW QUESTIONS
        elif any(w in prompt_lower for w in ["10 python interview", "python interview questions", "python interview question", "interview questions"]):
            response_text = (
                "### 🐍 Top 10 Python Interview Questions & Answers\n\n"
                "#### 1. What is the difference between a List and a Tuple?\n"
                "- **List**: Mutable (modifiable), defined using square brackets `[]`.\n"
                "- **Tuple**: Immutable (read-only), defined using parentheses `()`.\n\n"
                "#### 2. What is the Global Interpreter Lock (GIL)?\n"
                "- GIL is a mutex in CPython that ensures only one thread executes Python bytecode at a time, keeping memory management thread-safe.\n\n"
                "#### 3. What are Python Decorators?\n"
                "- Functions that take another function as an argument and extend its behavior without modifying the original source code.\n"
                "```python\n"
                "def my_decorator(func):\n"
                "    def wrapper():\n"
                "        print('Executing before function...')\n"
                "        func()\n"
                "    return wrapper\n"
                "```\n\n"
                "#### 4. What is the difference between `==` and `is`?\n"
                "- `==` checks for value equality.\n"
                "- `is` checks for object identity (same memory address).\n\n"
                "#### 5. What are Generators in Python?\n"
                "- Functions that yield values one at a time using `yield`, saving memory state between iterations.\n\n"
                "#### 6. What is Shallow Copy vs Deep Copy?\n"
                "- **Shallow Copy (`copy.copy()`)**: Copies top-level object, but shares references to nested items.\n"
                "- **Deep Copy (`copy.deepcopy()`)**: Recursively duplicates all nested objects independently.\n\n"
                "#### 7. What are `*args` and `**kwargs`?\n"
                "- `*args`: Accepts arbitrary positional arguments as a tuple.\n"
                "- `**kwargs`: Accepts arbitrary keyword arguments as a dictionary.\n\n"
                "#### 8. What are Lambda Functions?\n"
                "- Anonymous single-expression functions: `square = lambda x: x ** 2`.\n\n"
                "#### 9. How do List Comprehensions work?\n"
                "- Concise syntax for creating lists: `evens = [x for x in range(10) if x % 2 == 0]`.\n\n"
                "#### 10. Explain `try...except...finally` blocks.\n"
                "- `try` contains risky code, `except` catches errors, and `finally` runs cleanup code unconditionally."
            )

        # 7. PYTHON EXPLANATION
        elif any(w in prompt_lower for w in ["what is python", "what's python", "tell me python", "what python"]):
            response_text = (
                "### 🐍 What is Python?\n\n"
                "**Python** is a high-level, interpreted, dynamic programming language known for its clean syntax, readability, and versatile ecosystem.\n\n"
                "#### Key Advantages:\n"
                "- **Beginner-Friendly**: English-like syntax makes it easy to learn.\n"
                "- **Versatile Ecosystem**: Dominant in **AI/ML** (TensorFlow, PyTorch), **Data Science** (Pandas), **Web Dev** (Django, FastAPI), and **Automation**.\n"
                "- **Cross-Platform**: Runs seamlessly on Windows, macOS, Linux.\n\n"
                "#### Quick Code Example:\n"
                "```python\n"
                "def greet_user(name):\n"
                "    return f'Hello, {name}! Welcome to NEXORA AI.'\n\n"
                "print(greet_user('Developer'))\n"
                "```"
            )

        # 8. GREETINGS & CASUAL INTRODUCTIONS
        elif re.search(r'\b(hello|hi|hey|greetings|howdy)\b', prompt_lower):
            response_text = "Hello! 👋 I'm NEXORA AI. How can I help you today?"

        elif re.search(r'\b(good morning|good afternoon|good evening)\b', prompt_lower):
            response_text = "Good morning! How can I help you today?"

        elif re.search(r'\b(namaste|namaskar|sat sri akal)\b', prompt_lower):
            response_text = "Namaste! Main badhiya hoon. Aaj main aapki kya madad karoon?"

        elif re.search(r'\b(what is your name|who are you|aap kaun ho|tumhara naam)\b', prompt_lower):
            response_text = "I'm NEXORA AI, an intelligent conversational AI assistant. I'm here to answer questions, explain concepts, provide coding help, and guide your projects!"

        # 9. GENERAL KNOWLEDGE / CODE & NATURAL SYNTHESIZER
        else:
            knowledge_ans = cls._answer_knowledge_question(prompt, history)
            if knowledge_ans:
                response_text = knowledge_ans
            elif any(w in prompt_lower for w in ["code", "program", "function", "java", "cpp", "javascript", "sql", "html", "script"]):
                response_text = cls._generate_code_response(prompt_lower)
            else:
                clean_subject = prompt_raw.strip(' ?.!')
                response_text = (
                    f"### 💡 About: {clean_subject}\n\n"
                    f"I'd like to give you a comprehensive answer, but I'm currently running in **offline fallback mode** "
                    f"because no valid Gemini API key is configured.\n\n"
                    f"#### 🔧 How to Get Full AI-Powered Responses:\n\n"
                    f"1. **Get a FREE Gemini API key** from [Google AI Studio](https://aistudio.google.com/app/apikey)\n"
                    f"2. **Open your `.env` file** and set `GEMINI_API_KEY=AIza...`\n"
                    f"3. **Restart the server** and ask your question again\n\n"
                    f"> 💡 **Tip**: Valid Gemini API keys start with `AIza...` and are completely free.\n\n"
                    f"Once configured, I can answer **any question** in detail — powered by Google Gemini!"
                )

        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield chunk
            await asyncio.sleep(0.01)



    @classmethod
    async def generate_gemini_stream(
        cls,
        prompt: str,
        history: List[Dict[str, Any]],
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        images: List[Dict[str, str]] = None,
        files: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Calls Google Gemini API using the official google-genai SDK.
        Supports streaming, multimodal (vision), file attachments, and conversation history.
        The API key is NEVER passed to the frontend — stored only in .env on the backend.
        """
        if not api_key or not api_key.strip() or len(api_key.strip()) < 10:
            logger.info("No valid Gemini API key. Using offline smart-fallback engine.")
            async for chunk in cls.generate_smart_fallback_stream(prompt, history, files=files, images=images):
                yield chunk
            return

        try:
            from google import genai as google_genai
            from google.genai import types as genai_types

            client = google_genai.Client(api_key=api_key.strip())

            # Build conversation history for multi-turn chat
            gemini_history = []
            for msg in history:
                role = "model" if msg.get("role") in ["assistant", "model"] else "user"
                raw_content = str(msg.get("content", ""))
                # Strip HTML markup from stored assistant messages
                clean_content = re.sub(r'<div class="nexora-[^"]+">[\s\S]*?</div>', ' ', raw_content)
                clean_content = re.sub(r'<[^>]*>', ' ', clean_content).strip()
                if clean_content:
                    gemini_history.append(
                        genai_types.Content(role=role, parts=[genai_types.Part(text=clean_content)])
                    )

            # Build user message parts (text + optional files + optional images)
            user_parts = []

            if files:
                for f in files:
                    fname = f.get("filename", "attached_file")
                    is_pdf = f.get("is_pdf", False) or fname.lower().endswith(".pdf")
                    raw_data = f.get("data", "")
                    if is_pdf:
                        pdf_text = extract_pdf_text(raw_data)
                        if len(pdf_text) > 15000:
                            pdf_text = pdf_text[:15000] + "\n\n[...Document truncated for length...]"
                        user_parts.append(genai_types.Part(text=f"[PDF Document: {fname}]\n{pdf_text}"))
                    else:
                        user_parts.append(genai_types.Part(text=f"[File: {fname}]\n{raw_data[:15000]}"))

            # Main text prompt
            user_parts.append(genai_types.Part(text=prompt or "Please answer the query."))

            # Vision: image attachments
            if images:
                for img in images:
                    mime_type = img.get("mime_type", "image/png")
                    raw_data = img.get("data", "")
                    if "," in raw_data:
                        raw_data = raw_data.split(",", 1)[1]
                    img_bytes = base64.b64decode(raw_data)
                    user_parts.append(
                        genai_types.Part(
                            inline_data=genai_types.Blob(mime_type=mime_type, data=img_bytes)
                        )
                    )

            contents = gemini_history + [
                genai_types.Content(role="user", parts=user_parts)
            ]

            effective_system_prompt = system_prompt or settings.DEFAULT_SYSTEM_PROMPT

            config = genai_types.GenerateContentConfig(
                system_instruction=effective_system_prompt,
                temperature=0.8,
                max_output_tokens=8192,
                safety_settings=[
                    genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_NONE"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_NONE"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
            )

            # Run blocking stream call in thread executor (avoids blocking the async event loop)
            loop = asyncio.get_event_loop()

            def _stream_sync(target_model: str):
                return list(client.models.generate_content_stream(
                    model=target_model,
                    contents=contents,
                    config=config
                ))

            try:
                chunks = await loop.run_in_executor(None, lambda: _stream_sync(model_name))
            except Exception as call_err:
                err_msg = str(call_err)
                if ("NOT_FOUND" in err_msg or "404" in err_msg or "not available" in err_msg.lower()) and model_name != "gemini-3.6-flash":
                    logger.warning(f"Model {model_name} returned 404/NOT_FOUND. Retrying with active model gemini-3.6-flash...")
                    try:
                        chunks = await loop.run_in_executor(None, lambda: _stream_sync("gemini-3.6-flash"))
                    except Exception as retry_err:
                        raise retry_err
                else:
                    raise call_err

            got_content = False
            for chunk in chunks:
                text = ""
                try:
                    text = chunk.text
                except Exception:
                    pass
                if text:
                    got_content = True
                    yield text

            if got_content:
                return

            logger.warning("Gemini returned an empty response. Falling back to offline engine.")

        except Exception as e:
            err_str = str(e)
            logger.error(f"Gemini API error: {err_str}")

            if "API_KEY_INVALID" in err_str or "api key not valid" in err_str.lower() or "invalid api key" in err_str.lower() or "401" in err_str or "403" in err_str:
                yield (
                    "### 🔑 Gemini API Key Invalid\n\n"
                    "Your Gemini API key was rejected by Google or is invalid.\n\n"
                    "#### How to Fix:\n"
                    "1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)\n"
                    "2. Create a new API key (starts with `AIza...`)\n"
                    "3. Update `GEMINI_API_KEY` in your `.env` file\n"
                    "4. Restart the server (`python run.py`)\n"
                )
                return
            elif "quota" in err_str.lower() or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                yield (
                    "### ⏳ Rate Limit / Quota Exceeded\n\n"
                    "You have reached the **rate limit or free quota** for the Gemini API.\n\n"
                    "Free tier limits reset every minute. Please wait 10-30 seconds and send your query again."
                )
                return
            elif "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
                yield (
                    "### ⚡ Service Temporarily Unavailable\n\n"
                    "Google Gemini API is currently experiencing **temporary high demand** (503 Service Unavailable).\n\n"
                    "This is a temporary server load issue on Google's side. Please retry in a few seconds."
                )
                return
            elif "network" in err_str.lower() or "timeout" in err_str.lower() or "connection" in err_str.lower() or "connecterror" in err_str.lower():
                yield (
                    "### 🌐 Network Connection Error\n\n"
                    "Could not connect to Google Gemini API servers.\n\n"
                    "Please check your internet connection and try again."
                )
                return
            elif "400" in err_str or "INVALID_ARGUMENT" in err_str or "invalid argument" in err_str.lower():
                yield (
                    "### ⚠️ Invalid Request\n\n"
                    "The request format or parameters sent to Google Gemini API were invalid.\n\n"
                    f"*(Technical detail: {err_str[:200]})*"
                )
                return
            elif "NOT_FOUND" in err_str or "not found" in err_str.lower():
                yield (
                    f"### ⚠️ Model Not Available\n\n"
                    f"The requested Gemini model `{model_name}` is not available.\n\n"
                    f"Please ensure `DEFAULT_MODEL=gemini-2.5-flash` in your `.env` file and restart the server."
                )
                return
            else:
                yield (
                    "Sorry, I couldn't process your request right now. Please try again.\n\n"
                    f"*(Technical detail: {err_str[:200]})*"
                )

        # If Gemini failed silently (empty response), use offline engine
        async for chunk in cls.generate_smart_fallback_stream(prompt, history, files=files, images=images):
            yield chunk

    @classmethod
    async def generate_openai_stream(
        cls,
        prompt: str,
        history: List[Dict[str, Any]],
        api_key: str,
        model_name: str = "gpt-4o",
        images: List[Dict[str, str]] = None,
        files: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> AsyncGenerator[str, None]:
        """Calls OpenAI API with streaming and vision support"""
        if not api_key or not api_key.strip():
            yield "OpenAI API Key Missing. Please configure your OpenAI API Key."
            return

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for msg in history:
            role = "assistant" if msg.get("role") in ["assistant", "model"] else "user"
            messages.append({"role": role, "content": str(msg.get("content", ""))})

        user_content = []
        file_text_blocks = []
        if files:
            for f in files:
                fname = f.get("filename", "attached_file")
                is_pdf = f.get("is_pdf", False) or fname.lower().endswith(".pdf")
                raw_data = f.get("data", "")
                if is_pdf:
                    pdf_text = extract_pdf_text(raw_data)
                    file_text_blocks.append(f"[PDF: {fname}]\n{pdf_text[:15000]}")
                else:
                    file_text_blocks.append(f"[File: {fname}]\n{raw_data[:15000]}")

        final_text = prompt
        if file_text_blocks:
            final_text = "\n\n".join(file_text_blocks) + f"\n\n{prompt}"

        user_content.append({"type": "text", "text": final_text or "Please answer."})

        if images:
            for img in images:
                mime_type = img.get("mime_type", "image/png")
                raw_data = img.get("data", "")
                if not raw_data.startswith("data:"):
                    raw_data = f"data:{mime_type};base64,{raw_data}"
                user_content.append({"type": "image_url", "image_url": {"url": raw_data}})

        messages.append({"role": "user", "content": user_content})

        payload = {"model": model_name, "messages": messages, "stream": True, "temperature": 0.7}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        yield f"OpenAI API Error ({response.status_code}): {err_body.decode('utf-8', errors='ignore')[:300]}"
                        return
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line.strip() != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                pass
        except Exception as e:
            yield f"OpenAI Stream Exception: {str(e)}"

    @classmethod
    def _is_image_search_request(cls, prompt: str) -> Optional[str]:
        prompt_clean = prompt.strip()
        patterns = [
            r'^(?:give\s*me\s*images?\s*of|show\s*me\s*photos?\s*of|show\s*me\s*images?\s*of|find\s*images?\s*of|find\s*images?\s*related\s*to|image\s*search\s*for|images?\s*of|photos?\s*of|pictures?\s*of)\s+(.+)$',
            r'^find\s*images?\s*(.*)$',
            r'^(.*)\s+images$'
        ]
        for pat in patterns:
            match = re.search(pat, prompt_clean, re.IGNORECASE)
            if match:
                term = match.group(1).strip(" \"':")
                if term and len(term) > 1:
                    return term
        return None

    @classmethod
    async def generate_stream(
        cls,
        prompt: str,
        history: List[Dict[str, Any]] = None,
        model: str = "gemini-2.5-flash",
        custom_api_key: str = None,
        images: List[Dict[str, str]] = None,
        files: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Main routing entry point for AI generation.
        Routes to Gemini (primary), OpenAI, or offline fallback based on model name.
        API keys are NEVER passed to or from the frontend.
        """
        history = history or []

        # Check if user is requesting image search
        image_query = cls._is_image_search_request(prompt)
        if image_query and not images and not files:
            img_results = ImageSearchService.search_images(image_query)
            md_text = ImageSearchService.format_image_search_markdown(image_query, img_results)
            words = md_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
                await asyncio.sleep(0.01)
            return

        # ── Route: Real-Time Weather Intent ────────────────────────────────────
        if WeatherService.is_weather_intent(prompt) and not images and not files:
            loc = WeatherService.extract_location(prompt)
            if loc:
                w_data = await WeatherService.get_weather_by_city(loc)
                w_md = WeatherService.format_weather_markdown(w_data, original_query=prompt)
            else:
                w_md = (
                    "### 🌤️ NEXORA Real-Time Weather Assistant\n\n"
                    "Which city, state, or country's weather would you like me to check?\n\n"
                    "**Examples**:\n"
                    "* *'Tell me the weather in Maharashtra'*\n"
                    "* *'What's the weather in Mumbai?'*\n"
                    "* *'What is the temperature in Pune?'*\n"
                    "* *'How is the weather in Bihar today?'*\n"
                    "* *'Will it rain in Patna?'*\n"
                    "* *'What's the weather in London?'*"
                )
            words = w_md.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
                await asyncio.sleep(0.01)
            return

        # ── Route: Google Gemini (PRIMARY — default for all gemini-* models) ──
        if model.startswith("gemini-") or model.startswith("models/gemini"):
            gemini_key = settings.GEMINI_API_KEY
            async for chunk in cls.generate_gemini_stream(
                prompt=prompt, history=history, api_key=gemini_key, model_name=model,
                images=images, files=files, system_prompt=system_prompt
            ):
                yield chunk

        # ── Route: OpenAI GPT models ──────────────────────────────────────────
        elif model in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "openai"]:
            openai_key = custom_api_key if (custom_api_key and custom_api_key.startswith("sk-")) else settings.OPENAI_API_KEY
            async for chunk in cls.generate_openai_stream(
                prompt=prompt, history=history, api_key=openai_key,
                model_name=model if model.startswith("gpt-") else "gpt-4o",
                images=images, files=files, system_prompt=system_prompt
            ):
                yield chunk

        # ── Route: Offline smart-fallback (no API key needed) ────────────────
        else:
            async for chunk in cls.generate_smart_fallback_stream(prompt, history, files=files, images=images):
                yield chunk

