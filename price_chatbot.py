#!/usr/bin/env python3
"""rm5_pricing_chatbot.py

Flask chatbot for initial and during-listing pricing advice.

Flow:
  1. /          — AWS credentials (auto-detected from AWS_PROFILE if set)
  2. /setup     — Stage of sale, goals, FSBO context
  3. /chat      — Multi-turn dialog powered by Bedrock Haiku 4.5
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from markupsafe import escape
from flask import Flask, redirect, render_template_string, request, session, url_for

APP_PORT = 8084
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

app = Flask(__name__)
app.secret_key = "dev-secret-for-local-testing"


# ---------------------------------------------------------------------------
# Strategy reference
# ---------------------------------------------------------------------------

def _load_price_strategy() -> str:
    p = Path("PRICE_STRATEGY.md")
    return p.read_text(encoding="utf-8") if p.exists() else "(PRICE_STRATEGY.md not found)"

PRICE_STRATEGY_TEXT = _load_price_strategy()


# ---------------------------------------------------------------------------
# Bedrock helper (uses Converse API for native multi-turn)
# ---------------------------------------------------------------------------

def call_bedrock_converse(
    messages: list[dict],
    system_prompt: str,
    profile: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1",
) -> tuple[Optional[str], Optional[str]]:
    """Call Claude via Bedrock Converse API.

    Returns (reply_text, error_message). Exactly one of them will be None.
    """
    try:
        import boto3
    except ImportError:
        return None, "boto3 is not installed. Run: pip install boto3"

    try:
        if profile:
            sess = boto3.Session(profile_name=profile, region_name=region)
        elif access_key and secret_key:
            sess = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
        else:
            sess = boto3.Session(region_name=region)
        client = sess.client("bedrock-runtime")
    except Exception as exc:
        return None, f"Could not create AWS session: {exc}"

    try:
        resp = client.converse(
            modelId=DEFAULT_BEDROCK_MODEL,
            system=[{"text": system_prompt}],
            messages=messages,
        )
        return resp["output"]["message"]["content"][0]["text"], None
    except Exception as exc:
        return None, f"Bedrock API error: {exc}"


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(stage: str, goal: str, seller_type: str) -> str:
    stage_label = "setting an initial listing price" if stage == "initial" else "evaluating/adjusting price during an active listing"
    goal_label = "a quick sale" if goal == "quick" else "the highest possible price"
    seller_label = "a For-Sale-By-Owner (FSBO) seller" if seller_type == "fsbo" else "a seller who may be working with or considering an agent"

    return f"""You are an expert real-estate pricing advisor. Your job is to guide the user through {stage_label}.

Seller profile:
- Goal: {goal_label}
- Seller type: {seller_label}

Use the professional pricing framework below as your primary reference. Apply it to whatever comps, market signals, and property details the user shares. Be concise, practical, and specific — give concrete numbers and price ranges whenever possible. Ask follow-up questions to gather missing details (comps, days on market, showings, saves/views, square footage, beds/baths).

=== PRICING STRATEGY REFERENCE ===
{PRICE_STRATEGY_TEXT}
=== END REFERENCE ===

Rules:
- Always recommend a specific price or range, not just vague guidance.
- Respect search bracket thresholds ($25k / $50k increments).
- For FSBO sellers, apply the FSBO-specific advice from the reference.
- If the user pastes raw data (comps, stats), analyse it before advising.
- Keep responses focused — 3–5 short paragraphs maximum unless detail is needed.
"""


# ---------------------------------------------------------------------------
# HTML base template
# ---------------------------------------------------------------------------

BASE_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Homeseller's AI Agent - Pricing Advisor</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      background: #f5f5f5;
      padding: 20px;
      color: #333;
    }
    .container { max-width: 860px; margin: 0 auto; }
    h1 { color: #333; margin-bottom: 6px; }
    .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; }
    h2 {
      color: #333;
      margin-bottom: 15px;
      font-size: 18px;
      border-bottom: 2px solid #4CAF50;
      padding-bottom: 8px;
    }
    .card {
      background: white;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      margin: 12px 0 4px;
      color: #333;
    }
    .note { font-size: 12px; color: #888; font-weight: 400; }
    input, select, textarea {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      font-family: inherit;
    }
    textarea { resize: vertical; }
    input:focus, select:focus, textarea:focus { outline: 2px solid #4CAF50; border-color: transparent; }
    .btn {
      background: #4CAF50;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
    }
    .btn:hover { background: #45a049; }
    .btn-secondary {
      background: #757575;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      text-decoration: none;
      display: inline-block;
    }
    .btn-secondary:hover { background: #616161; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 16px; }
    .history { display: flex; flex-direction: column; gap: 14px; max-height: 480px; overflow-y: auto; padding: 4px 0 12px; }
    .turn { display: flex; flex-direction: column; gap: 3px; }
    .turn-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: #888; }
    .bubble { padding: 10px 14px; border-radius: 6px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; font-size: 14px; }
    .user-bubble { background: #e8f5e9; align-self: flex-end; max-width: 82%; }
    .bot-bubble { background: #f8f9fa; max-width: 90%; border-left: 3px solid #4CAF50; }
    .tag {
      display: inline-block;
      background: #e8f5e9;
      color: #2e7d32;
      font-size: 12px;
      padding: 3px 10px;
      border-radius: 4px;
      margin: 2px;
      font-weight: 500;
    }
    hr { border: none; border-top: 1px solid #eee; margin: 16px 0; }
    .error { color: #c62828; font-size: 13px; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Homeseller's AI Agent - Pricing Advisor</h1>
    <p class="subtitle">AI-Powered Pricing Guidance</p>
    {{ content|safe }}
    <footer style="text-align:center; padding:30px 0 10px; color:#999; font-size:12px; border-top:1px solid #eee; margin-top:20px;">
      Real Estate Pricing Advisor &nbsp;|&nbsp; For educational and research purposes
    </footer>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/index.html")
def index_html():
    return redirect(url_for("index"))


@app.route("/", methods=["GET"])
def index():
    aws_profile = os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")
    parts = []
    parts.append('<div class="card">')
    parts.append('<h2>AWS Credentials</h2>')
    parts.append('<form method="post" action="/credentials">')

    if aws_profile:
        parts.append(f'<p>Detected AWS profile <strong>{escape(aws_profile)}</strong> — will be used automatically.</p>')
        parts.append(f'<input type="hidden" name="aws_profile" value="{escape(aws_profile)}" />')
        parts.append('<p class="note">You can override by entering keys below, or leave blank to use the profile.</p>')

    parts.append('<label>AWS Access Key ID <span class="note">(optional if profile detected)</span></label>')
    parts.append('<input name="access_key" placeholder="AKIA..." autocomplete="off" />')
    parts.append('<label>AWS Secret Access Key</label>')
    parts.append('<input name="secret_key" type="password" placeholder="wJalr..." autocomplete="off" />')
    parts.append('<label>Region</label>')
    parts.append('<input name="region" placeholder="us-east-1" value="us-east-1" />')
    parts.append('<br/><div class="row">')
    parts.append('<button class="btn" type="submit">Continue &rarr;</button>')
    parts.append('</div></form></div>')

    return render_template_string(BASE_HTML, content="\n".join(parts))


@app.route("/credentials", methods=["POST"])
def credentials():
    aws_profile = request.form.get("aws_profile", "").strip()
    access_key = request.form.get("access_key", "").strip()
    secret_key = request.form.get("secret_key", "").strip()
    region = request.form.get("region", "us-east-1").strip() or "us-east-1"

    # prefer explicit key/secret over profile if both provided
    if access_key and secret_key:
        session["access_key"] = access_key
        session["secret_key"] = secret_key
        session["aws_profile"] = None
    elif aws_profile:
        session["aws_profile"] = aws_profile
        session.pop("access_key", None)
        session.pop("secret_key", None)
    else:
        session["aws_profile"] = None
        session.pop("access_key", None)
        session.pop("secret_key", None)

    session["region"] = region
    session.modified = True
    return redirect(url_for("setup"))


@app.route("/setup", methods=["GET"])
def setup():
    parts = []
    parts.append('<div class="card">')
    parts.append('<h2>Tell me about your situation</h2>')
    parts.append('<form method="post" action="/begin">')

    parts.append('<label>What stage are you at?</label>')
    parts.append('<select name="stage">')
    parts.append('<option value="initial">Setting an initial listing price</option>')
    parts.append('<option value="during">Evaluating / adjusting price (already listed)</option>')
    parts.append('</select>')

    parts.append('<label>What is your primary goal?</label>')
    parts.append('<select name="goal">')
    parts.append('<option value="quick">Quick sale — I need to sell fast</option>')
    parts.append('<option value="top">Top dollar — I want maximum price, willing to wait</option>')
    parts.append('</select>')

    parts.append('<label>Are you selling without an agent (FSBO)?</label>')
    parts.append('<select name="seller_type">')
    parts.append('<option value="fsbo">Yes — I am selling FSBO</option>')
    parts.append('<option value="agent">No — I have / am considering an agent</option>')
    parts.append('<option value="opinion">I want a second opinion on my agent\'s pricing</option>')
    parts.append('</select>')

    parts.append('<label>Describe your property and paste any data you have <span class="note">(comps, address, beds/baths/sqft, current price, days on market, showings, Zillow saves — anything helps)</span></label>')
    parts.append('<textarea name="initial_info" rows="6" placeholder="E.g., 3 bed 2 bath 1,850 sqft in Austin TX. Comps: $510k (sold 2 wks ago), $495k (sold 1 mo ago), $525k (pending). Listed at $530k for 18 days. 12 showings, 0 offers. Zillow shows 47 saves."></textarea>')

    parts.append('<br/><div class="row">')
    parts.append('<button class="btn" type="submit">Start Conversation</button>')
    parts.append('<a href="/" class="btn btn-ghost btn-sm">Back</a>')
    parts.append('</div></form></div>')

    return render_template_string(BASE_HTML, content="\n".join(parts))


@app.route("/begin", methods=["POST"])
def begin():
    stage = request.form.get("stage", "initial")
    goal = request.form.get("goal", "quick")
    seller_type = request.form.get("seller_type", "fsbo")
    initial_info = request.form.get("initial_info", "").strip()

    session["stage"] = stage
    session["goal"] = goal
    session["seller_type"] = seller_type
    session["messages"] = []  # Converse API message list

    # Seed conversation with the initial property info if provided
    if initial_info:
        session["messages"].append({"role": "user", "content": [{"text": initial_info}]})

    session.modified = True
    return redirect(url_for("chat"))


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "stage" not in session:
        return redirect(url_for("index"))

    messages: list[dict] = session.get("messages", [])
    stage = session.get("stage", "initial")
    goal = session.get("goal", "quick")
    seller_type = session.get("seller_type", "fsbo")
    error_msg = ""

    if request.method == "POST":
        user_text = request.form.get("message", "").strip()
        if user_text:
            messages.append({"role": "user", "content": [{"text": user_text}]})

    # If the last message is from the user, get a reply
    if messages and messages[-1]["role"] == "user":
        system_prompt = build_system_prompt(stage, goal, seller_type)
        reply, error_msg = call_bedrock_converse(
            messages=messages,
            system_prompt=system_prompt,
            profile=session.get("aws_profile"),
            access_key=session.get("access_key"),
            secret_key=session.get("secret_key"),
            region=session.get("region", "us-east-1"),
        )
        if reply:
            messages.append({"role": "assistant", "content": [{"text": reply}]})

    session["messages"] = messages
    session.modified = True

    # --- Render ---
    stage_label = "Initial Pricing" if stage == "initial" else "Price Adjustment"
    goal_label = "Quick Sale" if goal == "quick" else "Top Dollar"
    seller_label = "FSBO" if seller_type == "fsbo" else ("Second Opinion" if seller_type == "opinion" else "With Agent")

    parts = []

    # Tag bar
    parts.append('<div style="margin-bottom:12px">')
    parts.append(f'<span class="tag">{escape(stage_label)}</span>')
    parts.append(f'<span class="tag">{escape(goal_label)}</span>')
    parts.append(f'<span class="tag">{escape(seller_label)}</span>')
    parts.append('</div>')

    # Conversation history
    parts.append('<div class="card">')
    parts.append('<div class="history" id="history">')

    if not messages:
        parts.append('<p style="color:var(--muted);font-size:.9rem">Describe your property and I\'ll help you price it.</p>')

    for m in messages:
        text = m["content"][0]["text"]
        if m["role"] == "user":
            parts.append('<div class="turn" style="align-items:flex-end">')
            parts.append('<span class="turn-label">You</span>')
            parts.append(f'<div class="bubble user-bubble">{escape(text)}</div>')
            parts.append('</div>')
        else:
            parts.append('<div class="turn">')
            parts.append('<span class="turn-label">Advisor</span>')
            parts.append(f'<div class="bubble bot-bubble">{escape(text)}</div>')
            parts.append('</div>')

    parts.append('</div>')  # history

    if error_msg:
        parts.append(f'<p class="error">{escape(error_msg)}</p>')

    # Input form
    parts.append('<hr class="divider" />')
    parts.append('<form method="post" action="/chat" id="chat-form">')
    parts.append('<textarea name="message" rows="4" placeholder="Share comps, market signals, questions…" id="msg-input"></textarea>')
    parts.append('<br/><div class="row" style="margin-top:8px">')
    parts.append('<button class="btn" type="submit">Send</button>')
    parts.append('<a href="/setup" class="btn btn-ghost btn-sm">New conversation</a>')
    parts.append('<a href="/" class="btn btn-ghost btn-sm">Change credentials</a>')
    parts.append('</div></form>')
    parts.append('</div>')  # card

    # Auto-scroll to bottom
    parts.append("""<script>
  var h = document.getElementById('history');
  if (h) h.scrollTop = h.scrollHeight;
  var f = document.getElementById('chat-form');
  if (f) f.addEventListener('submit', function() {
    f.querySelector('button[type=submit]').disabled = true;
  });
</script>""")

    return render_template_string(BASE_HTML, content="\n".join(parts))


if __name__ == "__main__":
    print(f"Starting Pricing Advisor on http://localhost:{APP_PORT}")
    app.run(host="0.0.0.0", port=APP_PORT, debug=False)
