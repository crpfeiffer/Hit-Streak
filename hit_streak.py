import os
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ... keep your get_live_streaks() and get_live_lineups() functions exactly the same ...

def send_email(content):
    # Retrieve the API key and Email addresses from environment variables (set up in GitHub)
    api_key = os.environ.get('SENDGRID_API_KEY')
    to_email = os.environ.get('MY_EMAIL')
    
    if not api_key or not to_email:
        print("⚠️ Missing email configuration variables. Skipping email.")
        return

    message = Mail(
        from_email=to_email,  # SendGrid allows you to send to yourself
        to_emails=to_email,
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

    # Create a string buffer to hold the text we want to email
    email_output = "🔍 Cross-Referencing Matchups...\n"
    email_output += "=" * 50 + "\n\n"

    found_count = 0
    for _, s in df_s.iterrows():
        for _, l in df_l.iterrows():
            score = fuzz.token_set_ratio(s['Hitter'], l['Hitter'])
            if score >= 80:
                if l['ERA'] >= ERA_THRESHOLD:
                    found_count += 1

                    is_hr_threat = s['Slug'] >= HR_SLUG_THRESHOLD or s['HR'] >= 2
                    is_bad_pitcher = l['ERA'] >= 6.00

                    if is_hr_threat and is_bad_pitcher:
                        status = "💣💣 ULTRA HR ALERT 💣💣"
                    elif is_hr_threat or is_bad_pitcher:
                        status = "🔥 HR POTENTIAL"
                    else:
                        status = "✅ SOLID PICK"

                    slug_str = "{:.3f}".format(s['Slug']).lstrip('0')
                    
                    # Append everything to our email string instead of just printing
                    email_output += f"{status}\n"
                    email_output += f"Hitter:  {s['Hitter']} ({s['Streak']}G Streak | {slug_str} SLG)\n"
                    email_output += f"Pitcher: {l['OppPitcher']} ({l['ERA']} ERA)\n"
                    email_output += f"Game:    {l['Game']}\n"
                    email_output += "-" * 40 + "\n"

    if found_count == 0:
        email_output += f"No matches found meeting criteria today (Streak 5+, ERA {ERA_THRESHOLD}+).\n"

    # Print to console so it's still in the GitHub logs, then send the email
    print(email_output)
    send_email(email_output)

if __name__ == "__main__":
    run_app()