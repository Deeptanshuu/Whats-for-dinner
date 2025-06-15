"""Vercel entry point: the Flask app as one Python function behind /api/*.

The app lives in server/. Everything is loaded here, at import, so a cold
start pays once and requests after it are fast.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import create_app  # noqa: E402

app = create_app(warm=False)
app.extensions["recommender"].warm()
