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