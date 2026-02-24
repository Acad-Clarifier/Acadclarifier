# import re
# from typing import List, Dict

# # ===============================
# # RERANK CONFIG
# # ===============================

# KEYWORD_BOOST = 0.15
# SECTION_BOOST = 0.20
# DEFINITION_BOOST = 0.25
# TRANSITION_PENALTY = 0.20

# # ===============================
# # HELPERS
# # ===============================

# def tokenize(text: str):
#     return set(re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()))

# def is_definition_like(text: str) -> bool:
#     triggers = [
#         "is defined as",
#         "refers to",
#         "means that",
#         "we define",
#         "can be defined",
#         "is the process"
#         "one of the fundamental",
#         "the goal of",
#         "to ensure that",
#         "is achieved through"
#     ]
#     t = text.lower()
#     return any(x in t for x in triggers)

# def is_transition_noise(text: str) -> bool:
#     triggers = [
#         "this page intentionally left blank",
#         "in the next chapter",
#         "we shall see",
#         "in chapter"
#     ]
#     t = text.lower()
#     return any(x in t for x in triggers)

# # ===============================
# # CORE RERANKER
# # ===============================

# def rerank(query: str, chroma_results: List[Dict]) -> List[Dict]:
#     query_terms = tokenize(query)
#     reranked = []

#     for r in chroma_results:
#         # Convert distance → similarity baseline
#         score = 1.0 - r["distance"]

#         text = r["text_preview"]
#         section = (r.get("section") or "").lower()

#         # 🔹 Keyword overlap boost
#         overlap = query_terms & tokenize(text)
#         score += KEYWORD_BOOST * len(overlap)

#         # 🔹 Section title relevance
#         if any(q in section for q in query_terms):
#             score += SECTION_BOOST

#         # 🔹 Definition-like text
#         if is_definition_like(text):
#             score += DEFINITION_BOOST

#         # 🔻 Penalize transition / noise text
#         if is_transition_noise(text):
#             score -= TRANSITION_PENALTY

#         reranked.append({
#             **r,
#             "rerank_score": round(score, 4)
#         })

#     reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
#     return reranked
