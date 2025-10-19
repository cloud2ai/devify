"""
Manual test script for registration API.

Run this to verify the registration flow works correctly.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_check_username():
    """Test username availability check."""
    print("\n1. Testing username availability check...")

    url = f"{BASE_URL}/api/v1/auth/check-username/john_doe"
    response = requests.get(url)

    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert 'available' in data
    print("   ✓ Username check works!")


def test_send_registration_email():
    """Test sending registration email."""
    print("\n2. Testing registration email sending...")

    url = f"{BASE_URL}/api/v1/auth/register/send-email"
    payload = {
        "email": "test@example.com",
        "language": "en-US"
    }

    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )

    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    if response.status_code == 200:
        print("   ✓ Registration email sent!")
    else:
        print("   Note: Check EMAIL_BACKEND configuration")


def test_complete_registration():
    """Test complete registration."""
    print("\n3. Testing complete registration...")
    print("   (Requires valid token from email)")

    url = f"{BASE_URL}/api/v1/auth/register/complete"
    payload = {
        "token": "test_token_123",
        "password": "secure_password_123",
        "virtual_email_username": "john_doe",
        "scene": "chat",
        "language": "en-US",
        "timezone": "UTC"
    }

    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )

    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    print("   Note: This will fail without valid token")


if __name__ == "__main__":
    print("=" * 60)
    print("Registration API Manual Tests")
    print("=" * 60)
    print("\nMake sure Django server is running on localhost:8000")
    print("Run: python manage.py runserver")

    try:
        test_check_username()
        test_send_registration_email()
        test_complete_registration()

        print("\n" + "=" * 60)
        print("✅ Registration API tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server")
        print("Please start Django server: python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Error: {e}")
