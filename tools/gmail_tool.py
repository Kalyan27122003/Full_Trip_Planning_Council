# tools/gmail_tool.py
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def _markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML for email rendering."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    lines = text.split('\n')
    html_lines = []
    in_table = False
    table_rows = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            if re.match(r'^\|[-| :]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            table_rows.append(cells)
            continue
        else:
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
                in_table = False
                table_rows = []

        if re.match(r'^<strong>.+</strong>$', stripped) and len(stripped) < 120:
            html_lines.append(f'<h3 style="color:#1e3a8a;margin:20px 0 6px 0;font-size:15px;border-left:4px solid #2563eb;padding-left:10px;">{stripped}</h3>')
        elif stripped.startswith('* ') or stripped.startswith('- '):
            html_lines.append(f'<li style="margin:4px 0;color:#374151;font-size:13px;">{stripped[2:]}</li>')
        elif re.match(r'^\d+\.', stripped):
            html_lines.append(f'<li style="margin:4px 0;color:#374151;font-size:13px;">{re.sub(r"^\d+\.\s*", "", stripped)}</li>')
        elif stripped == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p style="margin:4px 0;color:#374151;font-size:13px;line-height:1.6;">{stripped}</p>')

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

    return '\n'.join(html_lines)


def _build_html_email(destination: str, travel_dates: str, travelers: str,
                      budget: str, body: str, calendar_link: str = None) -> str:
    """Build a beautiful professional HTML email."""
    content_html = _markdown_to_html(body)

    # Build agent badges HTML (plain string, no f-string loop inside template)
    agents = [
        "🗺️ Destination", "💰 Budget", "🏨 Hotel", "🍜 Food & Culture",
        "🚌 Transport", "🌤️ Weather", "🛡️ Safety", "📅 Itinerary", "📧 Notifier"
    ]
    badge_style = ('display:inline-block;background:#eff6ff;color:#1e40af;'
                   'border:1px solid #bfdbfe;border-radius:20px;'
                   'padding:4px 10px;font-size:11px;margin:3px;')
    agent_badges_html = ''.join(
        f'<span style="{badge_style}">{a}</span>' for a in agents
    )

    # Calendar button
    if calendar_link:
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
        calendar_section = ''

    # Build full HTML — no nested f-strings, no loops inside template
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

        <!-- HEADER -->
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

        <!-- SUMMARY CARDS -->
        <tr>
          <td style="background:#1e40af;padding:0 36px 20px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">📅</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Dates</div>
                    <div style="color:#ffffff;font-size:11px;font-weight:600;margin-top:2px;">{travel_dates}</div>
                  </div>
                </td>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">👥</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Travelers</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{travelers}</div>
                  </div>
                </td>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">💰</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;margin-top:4px;">Budget</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{budget}</div>
                  </div>
                </td>
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

        <!-- BLUE DIVIDER -->
        <tr><td style="background:#2563eb;height:4px;"></td></tr>

        <!-- MAIN CONTENT -->
        <tr>
          <td style="background:#ffffff;padding:32px 36px;">
            {content_html}
          </td>
        </tr>

        <!-- CALENDAR BUTTON (if available) -->
        {calendar_section}

        <!-- AGENT BADGES -->
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

        <!-- FOOTER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e3a8a,#2563eb);
                     border-radius:0 0 16px 16px;padding:24px 36px;text-align:center;">
            <p style="color:#bfdbfe;font-size:13px;margin:0 0 8px 0;">
              🌍 Have an incredible journey to <strong style="color:#ffffff;">{destination}</strong>! Bon Voyage!
            </p>
            <p style="color:#93c5fd;font-size:11px;margin:0;">
              Generated by Full Trip Planning Council &nbsp;•&nbsp;
              Groq LLM + LangGraph + ChromaDB + MCP Tools
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
    Send ONE email to one or multiple recipients.
    to_email: str (single) or list of str (multiple).
    """
    sender  = os.getenv("GMAIL_SENDER")
    app_pwd = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not app_pwd:
        return "⚠️ Gmail credentials not configured."

    # Normalise to list
    if isinstance(to_email, str):
        recipients = [e.strip() for e in to_email.replace(";", ",").split(",") if "@" in e.strip()]
    else:
        recipients = [e.strip() for e in to_email if "@" in e.strip()]

    if not recipients:
        return "⚠️ No valid email addresses provided."

    if len(recipients) > 100:
        return f"⚠️ Too many recipients ({len(recipients)}). Max 100 per email."

    primary  = recipients[0]
    bcc_list = recipients[1:] if len(recipients) > 1 else []

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"✈️ Trip Planning Council <{sender}>"
        msg["To"]      = primary
        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        plain        = MIMEText(body, "plain")
        html_content = _build_html_email(destination, travel_dates, travelers,
                                         budget, body, calendar_link)
        html = MIMEText(html_content, "html")

        msg.attach(plain)
        msg.attach(html)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_pwd)
            server.sendmail(sender, recipients, msg.as_string())

        if len(recipients) == 1:
            return f"✅ Itinerary sent to {recipients[0]}"
        else:
            return f"✅ Itinerary sent to {len(recipients)} recipients (1 To + {len(bcc_list)} BCC)"

    except smtplib.SMTPAuthenticationError:
        return "❌ Gmail authentication failed. Check your App Password."
    except smtplib.SMTPRecipientsRefused as e:
        return f"⚠️ Some addresses rejected: {list(e.recipients.keys())}"
    except Exception as e:
        return f"❌ Email send error: {str(e)}"