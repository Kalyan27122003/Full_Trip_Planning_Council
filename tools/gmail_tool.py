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
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Headers (lines starting with **)
    lines = text.split('\n')
    html_lines = []
    in_table = False
    table_rows = []

    for line in lines:
        stripped = line.strip()

        # Detect table rows
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            # Skip separator rows like |---|---|
            if re.match(r'^\|[-| :]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            table_rows.append(cells)
            continue
        else:
            if in_table and table_rows:
                # Flush table
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

        # Section headers (lines that are bold only)
        if re.match(r'^<strong>.+</strong>$', stripped) and len(stripped) < 120:
            html_lines.append(f'<h3 style="color:#1e3a8a;margin:20px 0 6px 0;font-size:15px;border-left:4px solid #2563eb;padding-left:10px;">{stripped}</h3>')
        # Bullet points
        elif stripped.startswith('* ') or stripped.startswith('- '):
            content = stripped[2:]
            html_lines.append(f'<li style="margin:4px 0;color:#374151;font-size:13px;">{content}</li>')
        # Numbered list
        elif re.match(r'^\d+\.', stripped):
            content = re.sub(r'^\d+\.\s*', '', stripped)
            html_lines.append(f'<li style="margin:4px 0;color:#374151;font-size:13px;">{content}</li>')
        # Empty line
        elif stripped == '':
            html_lines.append('<br>')
        # Normal paragraph
        else:
            html_lines.append(f'<p style="margin:4px 0;color:#374151;font-size:13px;line-height:1.6;">{stripped}</p>')

    # Flush any remaining table
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


def _build_html_email(destination: str, travel_dates: str, travelers: str, budget: str, body: str) -> str:
    """Build a beautiful professional HTML email."""
    content_html = _markdown_to_html(body)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Trip Itinerary</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4ff;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;padding:30px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

        <!-- HEADER BANNER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 60%,#0ea5e9 100%);
                     border-radius:16px 16px 0 0;padding:40px 36px;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">✈️</div>
            <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;letter-spacing:1px;">
              Your Trip to {destination}
            </h1>
            <p style="color:#bfdbfe;margin:10px 0 0 0;font-size:15px;">
              Personalized Itinerary — Crafted by AI Travel Council
            </p>
          </td>
        </tr>

        <!-- TRIP SUMMARY CARDS -->
        <tr>
          <td style="background:#1e40af;padding:0 36px 20px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">📅</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Dates</div>
                    <div style="color:#ffffff;font-size:11px;font-weight:600;margin-top:2px;">{travel_dates}</div>
                  </div>
                </td>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">👥</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Travelers</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{travelers}</div>
                  </div>
                </td>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">💰</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Budget</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">{budget}</div>
                  </div>
                </td>
                <td width="25%" style="text-align:center;padding:14px 8px;">
                  <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:12px 6px;">
                    <div style="font-size:22px;">🤖</div>
                    <div style="color:#bfdbfe;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Agents</div>
                    <div style="color:#ffffff;font-size:12px;font-weight:600;margin-top:2px;">9 AI Agents</div>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- DIVIDER -->
        <tr>
          <td style="background:#2563eb;height:4px;"></td>
        </tr>

        <!-- MAIN CONTENT -->
        <tr>
          <td style="background:#ffffff;padding:32px 36px;border-radius:0;">
            {content_html}
          </td>
        </tr>

        <!-- AGENT BADGES -->
        <tr>
          <td style="background:#f8fafc;padding:20px 36px;border:1px solid #e2e8f0;border-top:none;">
            <p style="margin:0 0 12px 0;color:#64748b;font-size:12px;text-align:center;text-transform:uppercase;letter-spacing:1px;">
              Powered by 9 Specialist AI Agents
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="text-align:center;">
                  {"".join([f'<span style="display:inline-block;background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;border-radius:20px;padding:4px 10px;font-size:11px;margin:3px;">{a}</span>'
                    for a in ["🗺️ Destination","💰 Budget","🏨 Hotel","🍜 Food & Culture",
                               "🚌 Transport","🌤️ Weather","🛡️ Safety","📅 Itinerary","📧 Notifier"]])}
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


def send_itinerary_email(to_email: str, subject: str, body: str,
                         destination: str = "Your Destination",
                         travel_dates: str = "", travelers: str = "2",
                         budget: str = "") -> str:
    """Send a beautiful HTML itinerary email via Gmail SMTP."""
    sender  = os.getenv("GMAIL_SENDER")
    app_pwd = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not app_pwd:
        return "⚠️ Gmail credentials not configured."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"✈️ Trip Planning Council <{sender}>"
        msg["To"]      = to_email

        # Plain text fallback
        plain = MIMEText(body, "plain")

        # Beautiful HTML version
        html_content = _build_html_email(destination, travel_dates, travelers, budget, body)
        html = MIMEText(html_content, "html")

        msg.attach(plain)
        msg.attach(html)   # HTML is preferred by email clients

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_pwd)
            server.sendmail(sender, to_email, msg.as_string())

        return f"✅ Itinerary sent successfully to {to_email}"
    except smtplib.SMTPAuthenticationError:
        return "❌ Gmail authentication failed. Check your App Password."
    except Exception as e:
        return f"❌ Email send error: {str(e)}"