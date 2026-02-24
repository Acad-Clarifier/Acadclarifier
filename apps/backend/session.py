# backend/session.py

active_book_uid = None


def set_active_book(uid):
    global active_book_uid
    active_book_uid = uid
    print(f"[SESSION] Active book updated: {uid}")


def get_active_book():
    return active_book_uid
