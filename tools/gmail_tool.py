# tools/gmail_tool.py
# This module handles sending beautifully formatted HTML travel itinerary emails via Gmail.

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart  # For creating emails with multiple parts (plain + HTML)
from email.mime.text import MIMEText            # For attaching plain text or HTML content to the email
from dotenv import load_dotenv

# Load environment variables from .env file (GMAIL_SENDER, GMAIL_APP_PASSWORD)
load_dotenv()


def _markdown_to_html(text: str) -> str:
    """
    Converts a markdown-formatted string into HTML for rendering in emails.

    Handles:
      - **bold** → <strong>
      - Markdown tables → styled <table> HTML
      - Bullet points (* or -) → <li>
      - Numbered lists → <li>
      - Bold-only lines → styled <h3> headings
      - Empty lines → <br>
      - Everything else → <p> paragraph
    """
    # Convert **bold text** to <strong>bold text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    lines = text.split('\n')
    html_lines = []

    # Track whether we're currently inside a markdown table
    in_table = False
    table_rows = []  # Accumulate table rows before converting to HTML

    for line in lines:
        stripped = line.strip()

        # ── TABLE DETECTION ─────────────────────────────────────────────
        if stripped.startswith('|') and stripped.endswith('|'):
            # This line looks like a markdown table row
            if not in_table:
                in_table = True
                table_rows = []

            # Skip the separator row (e.g., |---|---|) — it's just for formatting
            if re.match(r'^\|[-| :]+\|$', stripped):
                continue

            # Parse cells by splitting on '|' and stripping whitespace
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            table_rows.append(cells)
            continue

        else:
            # We've exited the table — now convert accumulated rows to HTML
            if in_table and table_rows:
                thtml = '<table style="width:100%;border-collapse:collapse;margin:12px 0;">'
                for i, row in enumerate(table_rows):
                    tag = 'th' if i == 0 else 'td'          # First row = header
                    bg  = '#1e3a8a' if i == 0 else ('#f0f4ff' if i % 2 == 0 else '#ffffff')  # Alternating row colors
                    color = 'white' if i == 0 else '#1e293b'
                    thtml += '<tr>'
                    for cell in row:
                        thtml += f'<{tag} style="padding:10px 14px;border:1px solid #e2e8f0;background:{bg};color:{color};font-size:13px;">{cell}</{tag}>'
                    thtml += '</tr>'
                thtml += '</table>'
                html_lines.append(thtml)
                in_table = False
                table_rows = []

        # ── LINE-BY-LINE CONVERSION ──────────────────────────────────────

        # If the entire line is bold and short → treat as a section heading
        if re.match(r'^<strong>.+</strong>$', stripped) and len(stripped) < 120:
            html_lines.append(
                f'<h3 style="color:#1e3a8a;margin:20px 0 6px 0;font-size:15px;'
                f'border-left:4px solid #2563eb;padding-left:10px;">{stripped}</h3>'
            )
        # Bullet point starting with * or -
        elif stripped.startswith('* ') or stripped.startswith('- '):
            html_lines.append(
                f'<li style="margin:4px 0;color:#374151;font-size:13px;">{stripped[2:]}</li>'
            )
        # Numbered list item (e.g., "1. Do this")
        elif re.match(r'^\d+\.', stripped):
            # Strip the "1. " prefix before wrapping in <li>
            html_lines.append(
                f'<li style="margin:4px 0;color:#374151;font-size:13px;">'
                f'{re.sub(r"^\\d+\\.\\s*", "", stripped)}</li>'
            )
        # Empty line → line break
        elif stripped == '':
            html_lines.append('<br>')
        # Default → wrap in a paragraph tag
        else:
            html_lines.append(
                f'<p style="margin:4px 0;color:#374151;font-size:13px;line-height:1.6;">{stripped}</p>'
            )

    # ── FLUSH REMAINING TABLE (if file ends while still inside a table) ──
    if in_table and table_rows:
        thtml = '<table style="width:100%;border-collapse:collapse;margin:12px 0;">'
        for i, row in enumerate(table_rows):
            tag = 'th' if i == 0 else 'td'
            bg  = '#1e3a8a' if i == 0 else ('#f0f4ff' if i % 2 == 0 else '#ffffff')
            color = 'white' if i == 0 else '#1e293b'
            thtml += '<tr>'
            for cell in row:
                thtml += f'<{tag} style="padding:10px 14px;border:1px solid #e2e8f0;background:{bg};color:{color};font-size:13px;">{cell}</{tag}>'
            thtml += '</tr>'
        thtml += '</table>'
        html_lines.append(thtml)

    # Join all HTML lines and return the final HTML string
    return '\n'.join(html_lines)


def _build_html_email(destination: str, travel_dates: str, travelers: str,
                      budget: str, body: str, calendar_link: str = None) -> str:
    """
    Builds a complete, styled HTML email for the travel itinerary.

    Structure:
      - Header with destination name
      - Summary cards (dates, travelers, budget, agent count)
      - Main itinerary content (converted from markdown)
      - Optional Google Calendar button
      - AI agent badges footer
      - Branded footer

    Returns the full HTML string ready to be embedded in the email.
    """
    # Convert the markdown itinerary body to HTML
    content_html = _markdown_to_html(body)

    # List of AI agents used in the travel planning system
    agents = [
        "🗺️ Destination", "💰 Budget", "🏨 Hotel", "🍜 Food & Culture",
        "🚌 Transport", "🌤️ Weather", "🛡️ Safety", "📅 Itinerary", "📧 Notifier"
    ]

    # CSS style for each agent badge pill
    badge_style = (
        'display:inline-block;background:#eff6ff;color:#1e40af;'
        'border:1px solid #bfdbfe;border-radius:20px;'
        'padding:4px 10px;font-size:11px;margin:3px;'
    )

    # Build all agent badges as a single HTML string (avoids nested f-string loops)
    agent_badges_html = ''.join(
        f'<span style="{badge_style}">{a}</span>' for a in agents
    )

    # ── OPTIONAL GOOGLE CALENDAR BUTTON ─────────────────────────────────
    if calendar_link:
        # If a calendar link was provided, render a styled button linking to the event
        calendar_section = f'''
        <tr>
          <td style="background:#eff6ff;padding:20px 36px;text-align:center;
                     border:1px solid #bfdbfe;border-top:none;">
            <p style="margin:0 0 12px 0;color:#1e40af;font-size:14px;font-weight:600;">
              📅 Add This Trip to Your Google Calendar
            </p>
            <a href="{calendar_link}"
               style="display:inline-block;background:#2563eb;color:#ffffff;
                      text-decoration:none;padding:12px 28px;border-radius:8px;
                      font-size:14px;font-weight:600;">
              📅 View in Google Calendar
            </a>
          </td>
        </tr>'''
    else:
        # No calendar link → leave this section empty
        calendar_section = ''

    # ── FULL HTML EMAIL TEMPLATE ─────────────────────────────────────────
    # Uses inline CSS for maximum email client compatibility
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Trip Itinerary</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;padding:30px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

        <!-- HEADER: gradient banner with destination name -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 60%,#0ea5e9 100%);
                     border-radius:16px 16px 0 0;padding:40px 36px;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">✈️</div>
            <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;">
              Your Trip to {destination}
            </h1>
            <p style="color:#bfdbfe;margin:10px 0 0 0;font-size:15px;">
              Personalized Itinerary — Crafted by AI Travel Council
            </p>
          </td>
        </tr>

        <!-- SUMMARY CARDS: 4 key trip details shown as icon cards -->
        <tr>
          <td style="background:#1e40af;padding:0 36px 20px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <!-- Card 1: Travel Dates -->
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">📅</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Dates</div>
                    <div style="color:#ffffff;font-size:11px;font-weight:600;margin-top:2px;">{travel_dates}</div>
                  </div>
                </td>
                <!-- Card 2: Number of Travelers -->
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">👥</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Travelers</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{travelers}</div>
                  </div>
                </td>
                <!-- Card 3: Budget -->
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">💰</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Budget</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{budget}</div>
                  </div>
                </td>
                <!-- Card 4: Number of AI Agents used -->
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">🤖</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Agents</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">9 AI Agents</div>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- DECORATIVE DIVIDER -->
        <tr><td style="background:#2563eb;height:4px;"></td></tr>

        <!-- MAIN CONTENT: the full itinerary rendered from markdown -->
        <tr>
          <td style="background:#ffffff;padding:32px 36px;">
            {content_html}
          </td>
        </tr>

        <!-- GOOGLE CALENDAR BUTTON (only shown if calendar_link was provided) -->
        {calendar_section}

        <!-- AI AGENT BADGES: shows which agents contributed to the plan -->
        <tr>
          <td style="background:#f8fafc;padding:20px 36px;border:1px solid #e2e8f0;border-top:none;">
            <p style="margin:0 0 12px 0;color:#64748b;font-size:12px;text-align:center;
                      text-transform:uppercase;letter-spacing:1px;">
              Powered by 9 Specialist AI Agents
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="text-align:center;">
                  {agent_badges_html}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- FOOTER: branding and tech stack info -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e3a8a,#2563eb);
                     border-radius:0 0 16px 16px;padding:24px 36px;text-align:center;">
            <p style="color:#bfdbfe;font-size:13px;margin:0 0 8px 0;">
              🌍 Have an incredible journey to <strong style="color:#ffffff;">{destination}</strong>! Bon Voyage!
            </p>
            <p style="color:#93c5fd;font-size:11px;margin:0;">
              Generated by Full Trip Planning Council &nbsp;•&nbsp;
              Groq LLM + LangGraph + Tavily Web Search + MCP Tools
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return html


def send_itinerary_email(to_email, subject: str, body: str,
                         destination: str = "Your Destination",
                         travel_dates: str = "", travelers: str = "2",
                         budget: str = "",
                         calendar_link: str = None) -> str:
    """
    Sends a styled HTML travel itinerary email to one or multiple recipients.

    Args:
        to_email:      A single email string OR a list of email strings.
                       Multiple addresses can be comma/semicolon separated.
        subject:       The email subject line.
        body:          The markdown-formatted itinerary content.
        destination:   Name of the travel destination (used in the email template).
        travel_dates:  Date range string shown in the summary card.
        travelers:     Number/description of travelers shown in the summary card.
        budget:        Budget description shown in the summary card.
        calendar_link: Optional Google Calendar event URL for the button.

    Returns:
        A status string — success message or error description.

    Notes:
        - First recipient goes in "To:", remaining go in "BCC:" (privacy).
        - Maximum 100 recipients per call.
        - Requires GMAIL_SENDER and GMAIL_APP_PASSWORD in .env file.
    """
    # Read Gmail credentials from environment variables
    sender  = os.getenv("GMAIL_SENDER")
    app_pwd = os.getenv("GMAIL_APP_PASSWORD")

    # Abort early if credentials are missing
    if not sender or not app_pwd:
        return "⚠️ Gmail credentials not configured."

    # ── NORMALIZE RECIPIENT LIST ─────────────────────────────────────────
    if isinstance(to_email, str):
        # Handle comma or semicolon-separated string of addresses
        recipients = [e.strip() for e in to_email.replace(";", ",").split(",") if "@" in e.strip()]
    else:
        # Already a list — just clean and validate each entry
        recipients = [e.strip() for e in to_email if "@" in e.strip()]

    if not recipients:
        return "⚠️ No valid email addresses provided."

    # Enforce a safe upper limit on recipient count
    if len(recipients) > 100:
        return f"⚠️ Too many recipients ({len(recipients)}). Max 100 per email."

    # First recipient goes in "To:", the rest go in "BCC:" to protect privacy
    primary  = recipients[0]
    bcc_list = recipients[1:] if len(recipients) > 1 else []

    try:
        # ── BUILD THE EMAIL MESSAGE ──────────────────────────────────────
        msg = MIMEMultipart("alternative")  # "alternative" = plain text + HTML (email client picks best)
        msg["Subject"] = subject
        msg["From"]    = f"✈️ Trip Planning Council <{sender}>"
        msg["To"]      = primary

        # Add BCC header only if there are additional recipients
        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        # Plain text version (fallback for email clients that don't render HTML)
        plain = MIMEText(body, "plain")

        # HTML version — fully styled email built from the body markdown
        html_content = _build_html_email(destination, travel_dates, travelers,
                                         budget, body, calendar_link)
        html = MIMEText(html_content, "html")

        # Attach both parts — email clients will use the last/best one they support
        msg.attach(plain)
        msg.attach(html)

        # ── SEND VIA GMAIL SMTP (SSL on port 465) ───────────────────────
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_pwd)           # Authenticate with App Password
            server.sendmail(sender, recipients, msg.as_string())  # Send to all recipients

        # Return a friendly success message
        if len(recipients) == 1:
            return f"✅ Itinerary sent to {recipients[0]}"
        else:
            return f"✅ Itinerary sent to {len(recipients)} recipients (1 To + {len(bcc_list)} BCC)"

    # ── ERROR HANDLING ───────────────────────────────────────────────────
    except smtplib.SMTPAuthenticationError:
        # Wrong email or App Password
        return "❌ Gmail authentication failed. Check your App Password."
    except smtplib.SMTPRecipientsRefused as e:
        # One or more addresses were rejected by Gmail's server
        return f"⚠️ Some addresses rejected: {list(e.recipients.keys())}"
    except Exception as e:
        # Catch-all for any other unexpected errors
        return f"❌ Email send error: {str(e)}"