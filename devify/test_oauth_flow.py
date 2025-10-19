#!/usr/bin/env python
"""
Test script to verify OAuth configuration
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from accounts.adapters import CustomSocialAccountAdapter

def test_oauth_config():
    print("=" * 60)
    print("OAuth Configuration Test")
    print("=" * 60)
    
    # Test settings
    print("\n1. Django Settings:")
    print(f"   FRONTEND_URL: {settings.FRONTEND_URL}")
    print(f"   LOGIN_REDIRECT_URL: {settings.LOGIN_REDIRECT_URL}")
    print(f"   SOCIALACCOUNT_ADAPTER: {settings.SOCIALACCOUNT_ADAPTER}")
    print(f"   SOCIALACCOUNT_AUTO_SIGNUP: {settings.SOCIALACCOUNT_AUTO_SIGNUP}")
    print(f"   SOCIALACCOUNT_EMAIL_REQUIRED: {settings.SOCIALACCOUNT_EMAIL_REQUIRED}")
    print(f"   ACCOUNT_EMAIL_REQUIRED: {settings.ACCOUNT_EMAIL_REQUIRED}")
    print(f"   ACCOUNT_USERNAME_REQUIRED: {settings.ACCOUNT_USERNAME_REQUIRED}")
    print(f"   SOCIALACCOUNT_SIGNUP_FORM_CLASS: {getattr(settings, 'SOCIALACCOUNT_SIGNUP_FORM_CLASS', 'Not set')}")
    
    # Test adapter
    print("\n2. Custom Adapter:")
    adapter = CustomSocialAccountAdapter()
    print(f"   Adapter class: {adapter.__class__.__name__}")
    print(f"   is_auto_signup_allowed: {adapter.is_auto_signup_allowed(None, None)}")
    print(f"   Signup redirect URL: {adapter.get_signup_redirect_url(None)}")
    print(f"   Login redirect URL: {adapter.get_login_redirect_url(None)}")
    
    # Test Google OAuth config
    print("\n3. Google OAuth Provider:")
    google_config = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
    app_config = google_config.get('APP', {})
    client_id = app_config.get('client_id', '')
    print(f"   Client ID configured: {'Yes' if client_id else 'No'}")
    if client_id:
        print(f"   Client ID: {client_id[:20]}...")
    print(f"   Scopes: {google_config.get('SCOPE', [])}")
    
    # Test CORS settings
    print("\n4. CORS Configuration:")
    print(f"   CORS_ALLOW_CREDENTIALS: {settings.CORS_ALLOW_CREDENTIALS}")
    print(f"   CORS_ALLOW_ALL_ORIGINS: {settings.CORS_ALLOW_ALL_ORIGINS}")
    if not settings.CORS_ALLOW_ALL_ORIGINS:
        print(f"   CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}")
    
    # Test session settings
    print("\n5. Session/Cookie Configuration:")
    print(f"   SESSION_COOKIE_SAMESITE: {settings.SESSION_COOKIE_SAMESITE}")
    print(f"   SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
    print(f"   CSRF_COOKIE_SAMESITE: {settings.CSRF_COOKIE_SAMESITE}")
    print(f"   CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
    
    # Test authentication classes
    print("\n6. DRF Authentication:")
    auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
    for auth_class in auth_classes:
        print(f"   - {auth_class}")
    
    print("\n" + "=" * 60)
    print("Expected OAuth Flow:")
    print("=" * 60)
    print("1. User clicks 'Login with Google'")
    print("2. Redirect to Google authorization page")
    print("3. Google callback to: http://localhost:8000/accounts/google/login/callback/")
    print("4. Django processes OAuth:")
    print("   - Creates/logs in user")
    print("   - Sets session cookie")
    print("   - Auto-generates username")
    print("5. Django redirects to: http://localhost:3000/auth/google/callback")
    print("6. Frontend checks user status via API")
    print("7. If registration incomplete, show setup form")
    print("8. If complete, redirect to dashboard")
    print("=" * 60)
    
    # Summary
    print("\n✅ Configuration Summary:")
    checks = [
        (settings.FRONTEND_URL == 'http://localhost:3000', 
         "FRONTEND_URL points to port 3000"),
        (settings.SOCIALACCOUNT_AUTO_SIGNUP == True,
         "Auto-signup is enabled"),
        (settings.SOCIALACCOUNT_EMAIL_REQUIRED == False,
         "Email not required (will auto-fill from Google)"),
        (settings.ACCOUNT_USERNAME_REQUIRED == False,
         "Username not required (will auto-generate)"),
        (getattr(settings, 'SOCIALACCOUNT_SIGNUP_FORM_CLASS', None) is None,
         "No signup form will be shown"),
        (settings.SOCIALACCOUNT_ADAPTER == 'accounts.adapters.CustomSocialAccountAdapter',
         "Custom adapter is configured"),
        (settings.CORS_ALLOW_CREDENTIALS == True,
         "CORS credentials allowed"),
        ('SessionAuthentication' in str(auth_classes),
         "Session authentication enabled"),
    ]
    
    all_passed = True
    for passed, description in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {description}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! OAuth should work correctly.")
        print("\nNext steps:")
        print("1. Clear browser cache and cookies")
        print("2. Try Google OAuth login")
        print("3. Check browser console for any errors")
    else:
        print("\n⚠️  Some checks failed. Please review the configuration.")
    
    print("=" * 60)

if __name__ == '__main__':
    test_oauth_config()

