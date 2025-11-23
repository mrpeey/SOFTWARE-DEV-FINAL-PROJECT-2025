#!/usr/bin/env python3
"""Test /books/my-books route for user book display and fallback message."""

import requests
import re

BASE_URL = 'http://127.0.0.1:8080'
LOGIN_URL = f'{BASE_URL}/auth/login'
MY_BOOKS_URL = f'{BASE_URL}/books/my-books'

TEST_USERS = [
    {'username_or_email': 'admin', 'password': 'admin123'},
    # Add more test users as needed
]

def get_csrf_token(session, url):
    response = session.get(url)
    if response.status_code == 200:
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', response.text)
        if match:
            return match.group(1)
    return None

def test_my_books_page():
    for user in TEST_USERS:
        session = requests.Session()
        csrf_token = get_csrf_token(session, LOGIN_URL)
        if not csrf_token:
            print(f"Could not get CSRF token for {user['username_or_email']}")
            continue
        login_data = {
            'username_or_email': user['username_or_email'],
            'password': user['password'],
            'csrf_token': csrf_token
        }
        login_response = session.post(LOGIN_URL, data=login_data)
        if login_response.status_code != 200 or 'Invalid' in login_response.text:
            print(f"Login failed for {user['username_or_email']}")
            continue
        page_response = session.get(MY_BOOKS_URL)
        print(f"Testing {user['username_or_email']} - Status: {page_response.status_code}")
        if 'You have no subscribed books.' in page_response.text:
            print("Fallback message displayed for empty book list.")
        elif 'card-title' in page_response.text:
            print("Book information displayed.")
        else:
            print("No book info or fallback message found.")

if __name__ == '__main__':
    test_my_books_page()
