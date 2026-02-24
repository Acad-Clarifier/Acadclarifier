# backend/ml_client.py

import random


def query_ml(question, book_uid):
    if not book_uid:
        return "Please scan a book first.", 0.0

    responses = [
        "This topic is explained in chapter 2 of the book.",
        "You can find this concept in the introduction section.",
        "The answer relates to key principles discussed in the book.",
        "Please refer to the diagrams in the middle chapters."
    ]

    answer = random.choice(responses)
    confidence = round(random.uniform(0.5, 0.9), 2)

    return answer, confidence
