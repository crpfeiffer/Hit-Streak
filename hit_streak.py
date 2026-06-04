import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from thefuzz import fuzz
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- CONFIG ---
ERA_THRESHOLD = 4.00
MIN_STREAK = 5
HR_SLUG_THRESHOLD = 0.600

def get_live_streaks():
    print("🔍 [1/3] Scraping Baseball Musings (Streak List)...")
    url = "https://www.baseballmusings.com/cgi-bin/CurStreak.py"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, 'html.parser')
    streaks = []
    table = soup.find('table')
    if not table: return pd.DataFrame()
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 12:
            try:
                name = cols[0].text.strip()
                streak_len = int(cols[1].text.strip())
                hrs = int(cols[5].text.strip())
                slug = float(cols[11].text.strip())
                if streak_len >= MIN_STREAK:
                    streaks.append({'Hitter': name, 'Streak': streak_len, 'HR': hrs, 'Slug': slug})
            except: continue
    df = pd.DataFrame(streaks)
    print(f"✅ Found {len(df)} hot hitters.")
    return df

def get_live_lineups():
    print("🔍 [2/3] Scraping RotoWire (Daily Lineups)...")
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, 'html.parser')
    matchups = []

    game_boxes = soup.find_all('div', class_='lineup__box')
    print(f"📊 Scanning {len(game_boxes)} games...")

    for box in game_boxes:
        teams = box.find_all('div', class_='lineup__team')
        v_team = teams[0].text.strip() if len(teams) > 0 else "VIS"
        h_team = teams[1].text.strip() if len(teams) > 1 else "HOME"

        p_divs = box.find_all('div', class_=re.compile('lineup__player-highlight'))
        if len(p_divs) < 2: continue

        def parse_pitcher_data(div):
            full_text = div.get_text(separator=" ", strip=True)
            era_matches = re.findall(r'(\d*\.\d+)', full_text)
            p_era = float(era_matches[-1]) if era_matches else 0.0

            name_tag = div.find('a')
            if name_tag:
                p_name = name_tag.get('title', name_tag.text).split(' Stats')[0].strip()
            else:
                p_name = re.split(r'[\(\d]', full_text)[0].strip()

            return p_name, p_era

        v_p_name, v_p_era = parse_pitcher_data(p_divs[0])
        h_p_name, h_p_era = parse_pitcher_data(p_divs[1])

        print(f"   ⚾ {v_p_name} ({v_p_era} ERA) vs {h_p_name} ({h_p_era} ERA)")

        u_lists = box.find_all('ul', class_='lineup__list')
        if len(u_lists) >= 2:
            for li in u_lists[0].find_all('li'):
                a = li.find('a')
                if a:
                    h_name = a.get('title', a.text).split(' Stats')[0].strip()
                    matchups.append({'Hitter': h_name, 'OppPitcher': h_p_name, 'ERA': h_p_era, 'Game': f"{v_team} @ {h_team}"})

            for li in u_lists[1].find_all('li'):
                a = li.find('a')
                if a:
                    h_name = a.get('title', a.text).split(' Stats')[0].strip()
                    matchups.append({'Hitter': h_name, 'OppPitcher': v_p_name, 'ERA': v_p_era, 'Game': f"{v_team} @ {h_team}"})

    return pd.DataFrame(matchups)

def send_email(content):
    api_key = os.environ.get('SENDGRID_API_KEY')
    to_email_string = os.environ.get('MY_EMAIL')
    
    if not api_key or not to_email_string:
        print("⚠️ Missing email configuration variables. Skipping email.")
        return

    # Clean up the email string and handle multiple emails if they exist
    # This splits them by commas and removes any accidental spaces
    recipient_list = [email.strip() for email in to_email_string.split(',') if email.strip()]

    # SendGrid prefers the first email in the list as the primary 'to', 
    # and the rest can be passed cleanly.
    message = Mail(
        from_email=recipient_list[0],  # Must be your verified SendGrid sender address
        to_emails=recipient_list,      # Handles a single email or a list of emails perfectly
        subject='💣 Daily MLB HR Alerts & Matchups',
        html_content=f"<pre style='font-family: monospace;'>{content}</pre>"
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"📧 Email sent successfully! Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Email failed to send: {e}")

def run_app():
    df_s = get_live_streaks()
    df_l = get_live_lineups()

    # --- Start building HTML Email Styling ---
    email_html = """
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; color: #333333; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
            .header { text-align: center; border-bottom: 3px solid #1a365d; padding-bottom: 15px; margin-bottom: 25px; }
            .header h1 { color: #1a365d; margin: 0; font-size: 24px; }
            .header p { color: #718096; margin: 5px 0 0 0; font-size: 14px; }
            .matchup-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: #ffffff; }
            .badge { display: inline-block; padding: 4px 12px; font-weight: bold; border-radius: 20px; font-size: 12px; margin-bottom: 10px; text-transform: uppercase; }
            .badge-ultra { background-color: #ffeeee; color: #cc0000; border: 1px solid #ffcccc; }
            .badge-potential { background-color: #fff6e6; color: #d47a00; border: 1px solid #ffe6cc; }
            .badge-solid { background-color: #e6f9ed; color: #00872e; border: 1px solid #ccf2d9; }
            .info-row { margin: 6px 0; font-size: 15px; }
            .label { font-weight: bold; color: #4a5568; display: inline-block; width: 75px; }
            .stat { font-weight: 600; color: #1a202c; }
            .no-matches { text-align: center; color: #718096; padding: 40px 20px; font-size: 16px; }
            .footer { text-align: center; font-size: 11px; color: #a0aec0; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚾ Daily MLB HR Matchup Report</h1>
                <p>Live Home Run Alerts & Analytics Pipeline</p>
            </div>
    """

    found_count = 0
    
    if not df_s.empty and not df_l.empty:
        for _, s in df_s.iterrows():
            for _, l in df_l.iterrows():
                score = fuzz.token_set_ratio(s['Hitter'], l['Hitter'])
                if score >= 80:
                    if l['ERA'] >= ERA_THRESHOLD:
                        found_count += 1

                        is_hr_threat = s['Slug'] >= HR_SLUG_THRESHOLD or s['HR'] >= 2
                        is_bad_pitcher = l['ERA'] >= 6.00

                        # Determine Badge Style and Status Label
                        if is_hr_threat and is_bad_pitcher:
                            badge_class = "badge-ultra"
                            status_text = "💣💣 ULTRA HR ALERT 💣💣"
                        elif is_hr_threat or is_bad_pitcher:
                            badge_class = "badge-potential"
                            status_text = "🔥 HR POTENTIAL"
                        else:
                            badge_class = "badge-solid"
                            status_text = "✅ SOLID PICK"

                        slug_str = "{:.3f}".format(s['Slug']).lstrip('0')
                        
                        # Append a clean HTML block for this card
                        email_html += f"""
                        <div class="matchup-card">
                            <span class="badge {badge_class}">{status_text}</span>
                            <div class="info-row"><span class="label">Hitter:</span><span class="stat">{s['Hitter']}</span> ({s['Streak']}G Streak | {slug_str} SLG)</div>
                            <div class="info-row"><span class="label">Pitcher:</span><span class="stat">{l['OppPitcher']}</span> ({l['ERA']} ERA)</div>
                            <div class="info-row"><span class="label">Game:</span><span class="stat">{l['Game']}</span></div>
                        </div>
                        """

    if found_count == 0:
        email_html += f"""
        <div class="no-matches">
            ☀️ <strong>No premium matches found today.</strong><br>
            <span style="font-size: 13px; color: #a0aec0; display: inline-block; margin-top: 5px;">
                Criteria scanned: Streak 5+ Games, Opposing Pitcher ERA {ERA_THRESHOLD}+
            </span>
        </div>
        """

    # Close layout tags
    email_html += """
            <div class="footer">
                Automated Analytics System • Generated via GitHub Actions
            </div>
        </div>
    </body>
    </html>
    """

    print(f"📊 Processed job. Matches found: {found_count}. Preparing transmission...")
    send_email(email_html)