#!/usr/bin/env python
"""Test review functionality by making a direct API call"""

import requests
import json
import re

def test_review_submission():
    """Test submitting a review via API"""
    
    # First, let's get the home page to get a session
    session = requests.Session()
    
    try:
        # Get the login page to establish session and get CSRF token
        print("Getting session and CSRF token...")
        response = session.get('http://127.0.0.1:8080/auth/login')
        print(f"Login page status: {response.status_code}")
        
        # Extract CSRF token from the response
        csrf_token = None
        if response.status_code == 200:
            # Look for CSRF token in the HTML
            csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"Found CSRF token: {csrf_token[:20]}...")
            else:
                print("Could not find CSRF token in login page")
                return
        
        # Try to login as admin
        print("Logging in as admin...")
        login_data = {
            'username_or_email': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        login_response = session.post('http://127.0.0.1:8080/auth/login', data=login_data)
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code == 200 and 'Invalid' not in login_response.text:
            print("Login successful!")
            
            # Now try to submit a review
            print("Submitting review...")
            review_data = {
                'rating': 4,
                'review_text': 'This is a test review submitted via API'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token
            }
            
            review_response = session.post(
                'http://127.0.0.1:8080/api/books/1/reviews', 
                data=json.dumps(review_data),
                headers=headers
            )
            
            print(f"Review submission status: {review_response.status_code}")
            print(f"Response: {review_response.text}")
            
        else:
            print("Login failed!")
            print(f"Response contains: {login_response.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_review_submission()