#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for Flask production deployment
Run this and copy the output to your environment variables
"""
import secrets

if __name__ == "__main__":
    secret_key = secrets.token_hex(32)
    print("\n" + "="*60)
    print("PRODUCTION SECRET KEY GENERATOR")
    print("="*60)
    print("\nYour SECRET_KEY (copy this to environment variables):\n")
    print(f"SECRET_KEY={secret_key}")
    print("\n" + "="*60)
    print("\nWARNING: NEVER commit this key to git!")
    print("ACTION: Add it to your deployment platform's environment variables")
    print("\n")
