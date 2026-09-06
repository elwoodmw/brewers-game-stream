import datetime
import math
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import streamlit as st
import statsapi

# 1. Page Configuration
st.set_page_config(page_title="Milwaukee Brewers Live Companion", layout="wide")

# Theme Selection State
if 'is_dark' not in st.session_state:
    st.session_state.is_dark = True

# Top Header Layout with Top-Right Theme Toggle
col_header, col_toggle = st.columns([5, 1])

with col_toggle:
    dark_mode = st.toggle("Dark Mode", value=st.session_state.is_dark)
    st.session_state.is_dark = dark_mode

is_dark = st.session_state.is_dark

# CSS Variables Based on Selected Theme
bg_color = "#121212" if is_dark else "#F8FAFC"
card_bg = "#1E293B" if is_dark else "#FFFFFF"
card_border = "#334155" if is_dark else "#E2E8F0"
text_color = "#FFFFFF" if is_dark else "#0F172A"
subtext_color = "#94A3B8" if is_dark else "#64748B"
accent_yellow = "#FFD166" if is_dark else "#D97706"
ticker_bg = "#0F172A" if is_dark else "#F1F5F9"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {bg_color} !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    h1, h2, h3, h4, p, span, label, div {{
        font-family: 'Inter', sans-serif !important;
        color: {text_color} !important;
    }}
    
    .title-banner {{
        padding: 0.2rem 0rem;
        margin-top: -1.0rem !important;
        margin-bottom: 0.5rem;
    }}
    
    .main-title {{
        font-size: 1.8rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.05em !important;
        color: {text_color} !important;
        margin-bottom: 0px !important;
    }}
    
    .scorebug-container {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 10px 16px;
        height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}

    .ticker-container {{
        background-color: {ticker_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 8px 14px;
        height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}

    .ticker-header {{
        font-size: 0.7rem;
        font-weight: 800;
        color: #00B4D8;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }}

    .ticker-games-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
        align-items: center;
    }}

    .ticker-card {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 5px;
        padding: 4px 8px;
        text-align: center;
    }}

    .ticker-teams {{
        font-size: 0.85rem;
        font-weight: 800;
        color: {text_color};
    }}

    .ticker-status {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {subtext_color};
        margin-top: 1px;
    }}
    
    [data-testid="stSidebar"] {{display: none;}}
    [data-testid="stHeader"] {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .block-container {{padding-top: 1rem !important;}}
    </style>
""", unsafe_allow_html=True)

with col_header:
    st.html(f"""
        <div class="title-banner">
            <h1 class="main-title">Milwaukee Brewers Live Statcast Companion</h1>
        </div>
    """)

BREWERS_TEAM_ID = 158

TEAM_ABBREVS = {
    108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC",  119: "LAD", 120: "WSH", 121: "NYM", 133: "OAK",
    134: "PIT", 135: "SD",  136: "SEA", 137: "SF",  138: "STL",
    139: "TB",  140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL"
}

STADIUM_DIMENSIONS = {
    'Great American Ball Park': {'lf': 328, 'lcf': 379, 'cf': 404, 'rcf': 370, 'rf': 325},
    'American Family Field': {'lf': 344, 'lcf': 371, 'cf': 400, 'rcf': 374, 'rf': 345},
}

DEFAULT_DIMS = {'lf': 330, 'lcf': 375, 'cf': 400, 'rcf': 375, 'rf': 330}

# 2. Data Fetching Utilities
@st.cache_data(ttl=60)
def get_today_brewers_game():
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    try:
        schedule = statsapi.schedule(date=today_str, team=BREWERS_TEAM_ID)
        if schedule:
            game = schedule[0]
            return game['game_id'], f"{game['away_name']} @ {game['home_name']} ({game['status']})"
    except Exception:
        pass
    return None, "No Milwaukee Brewers game scheduled today."

@st.cache_data(ttl=120)
def get_league_scoreboard():
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    try:
        schedule = statsapi.schedule(date=today_str)
        out_of_town = [
            g for g in schedule 
            if g.get('away_id') != BREWERS_TEAM_ID and g.get('home_id') != BREWERS_TEAM_ID
        ]
        return out_of_town
    except Exception:
        return []

def fetch_live_game_feed(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

def convert_hc_to_field_feet(hc_x, hc_y):
    if hc_x is None or hc_y is None:
        return None, None
    x_feet = (hc_x - 126) * 2.29
    y_feet = (204 - hc_y) * 2.29
    return x_feet, y_feet

def format_compact_status(status_str):
    if any(k in status_str for k in ["Inning", "Top", "Bottom", "Bot", "Mid", "End"]):
        return status_str.replace("Top ", "T").replace("Bottom ", "B").replace("Bot ", "B").replace("End ", "E").replace("Mid ", "M")
    elif "Final" in status_str:
        return "FINAL"
    elif "Scheduled" in status_str or "Pre-Game" in status_str:
        return "PRE"
    elif "Warmup" in status_str:
        return "WARM"
    return status_str[:6].upper()

# 3. Field Plotting
def draw_full_baseball_field(batted_balls, runners, field_title_label, is_dark):
    fig, ax = plt.subplots(figsize=(6, 6))
    bg_c = '#121212' if is_dark else '#F8FAFC'
    border_c = '#1E293B' if is_dark else '#CBD5E1'
    line_c = '#475569' if is_dark else '#94A3B8'
    
    fig.patch.set_facecolor(bg_c)
    ax.set_facecolor(bg_c)

    venue_key = next((k for k in STADIUM_DIMENSIONS if k.lower() in field_title_label.lower()), None)
    dims = STADIUM_DIMENSIONS.get(venue_key, DEFAULT_DIMS)

    num_points = 50
    angles = [(-math.pi/4) + (i * (math.pi/2) / (num_points - 1)) for i in range(num_points)]
    
    wall_x, wall_y = [], []
    for a in angles:
        if a < 0:
            t = (a + math.pi/4) / (math.pi/4)
            dist = dims['lf'] * (1 - t) + dims['cf'] * t
        else:
            t = a / (math.pi/4)
            dist = dims['cf'] * (1 - t) + dims['rf'] * t
            
        wall_x.append(dist * math.sin(a))
        wall_y.append(dist * math.cos(a))

    ax.plot([0, wall_x[0]], [0, wall_y[0]], color='#64748B', linewidth=1.5)
    ax.plot([0, wall_x[-1]], [0, wall_y[-1]], color='#64748B', linewidth=1.5)
    ax.plot(wall_x, wall_y, color=border_c, linewidth=4)
    ax.plot(wall_x, wall_y, color='#00B4D8', linewidth=1.5, linestyle='--')

    dirt_arc = patches.Arc((0, 60.5), 190, 190, angle=0, theta1=20, theta2=160, color=border_c, linewidth=1.5)
    ax.add_patch(dirt_arc)

    infield_x = [0, 63.6, 0, -63.6, 0]
    infield_y = [0, 63.6, 127.3, 63.6, 0]
    ax.plot(infield_x, infield_y, color=line_c, linewidth=1.8)

    mound = patches.Circle((0, 60.5), radius=9, facecolor=border_c, edgecolor=line_c, linewidth=1)
    rubber = patches.Rectangle((-1.5, 60), 3, 1, facecolor='#FFFFFF', edgecolor='#FFFFFF')
    ax.add_patch(mound)
    ax.add_patch(rubber)

    bases_coords = {'1b': (63.6, 63.6), '2b': (0, 127.3), '3b': (-63.6, 63.6)}
    for base, (bx, by) in bases_coords.items():
        is_occ = runners.get(base, False)
        fc = '#FFD166' if is_occ else border_c
        ec = '#FFD166' if is_occ else '#94A3B8'
        sq = patches.Rectangle((bx - 4.5, by - 4.5), 9, 9, angle=45, rotation_point='center', facecolor=fc, edgecolor=ec, zorder=5)
        ax.add_patch(sq)

    hp = patches.Polygon([[0, 0], [2.5, 2.5], [2.5, 5], [-2.5, 5], [-2.5, 2.5]], facecolor='#FFFFFF', edgecolor='#FFFFFF', zorder=5)
    ax.add_patch(hp)

    if batted_balls:
        for ball in batted_balls:
            hx, hy = ball.get('x_feet'), ball.get('y_feet')
            if hx is not None and hy is not None:
                ax.plot(
                    hx, hy, 
                    marker='o', 
                    markersize=8, 
                    markerfacecolor='#FFFFFF', 
                    markeredgecolor='#FFD166', 
                    markeredgewidth=1.5,
                    zorder=6
                )

    ax.set_xlim(-260, 260)
    ax.set_ylim(-20, 430)
    ax.axis('off')
    ax.set_title(field_title_label, fontsize=9, fontweight='bold', color=subtext_color, pad=10)
    return fig

# 4. Main Application
game_pk, game_summary = get_today_brewers_game()

if 'ticker_idx' not in st.session_state:
    st.session_state.ticker_idx = 0

@st.fragment(run_every=15)
def render_brewers_dashboard(game_pk):
    if not game_pk:
        st.info("Awaiting today's Milwaukee Brewers game schedule.")
        return

    feed = fetch_live_game_feed(game_pk)
    if not feed or 'liveData' not in feed:
        st.info("Game feed loading or pre-game status...")
        return

    game_data = feed.get('gameData', {})
    venue_info = game_data.get('venue', {})
    venue_name = venue_info.get('name', 'Unknown Ballpark')
    city_name = venue_info.get('location', {}).get('city', '')
    
    weather_info = game_data.get('weather', {})
    temp = weather_info.get('temp', '')
    condition = weather_info.get('condition', '')
    wind = weather_info.get('wind', '')
    
    weather_str = f"{temp}°F, {condition} ({wind})" if temp else "Weather Data N/A"
    city_str = f" • {city_name}" if city_name else ""
    field_title_label = f"{venue_name.upper()}{city_str.upper()} | {weather_str.upper()}"

    live_data = feed['liveData']
    linescore = live_data.get('linescore', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    teams = game_data.get('teams', {})
    away_name = teams.get('away', {}).get('clubName', 'AWAY')
    home_name = teams.get('home', {}).get('clubName', 'HOME')
    
    teams_line = linescore.get('teams', {})
    away_runs = teams_line.get('away', {}).get('runs', 0)
    home_runs = teams_line.get('home', {}).get('runs', 0)
    
    inning_state = linescore.get('inningState', 'Pre-Game')
    inning_num = linescore.get('currentInning', 1)
    outs = linescore.get('outs', 0)

    offense = linescore.get('offense', {})
    defense = linescore.get('defense', {})
    
    batter_name = offense.get('batter', {}).get('fullName', 'N/A')
    pitcher_name = defense.get('pitcher', {}).get('fullName', 'N/A')

    # Pitch Count calculation
    pitch_count = 0
    win_probs = []

    if plays:
        pitcher_id = defense.get('pitcher', {}).get('id')
        for idx, p in enumerate(plays):
            # Track pitch count
            if p.get('matchup', {}).get('pitcher', {}).get('id') == pitcher_id:
                p_events = p.get('playEvents', [])
                for e in p_events:
                    if e.get('isPitch'):
                        pitch_count += 1
            
            # Track Win Probability
            p_end = p.get('playEndTime')
            play_wp = p.get('about', {}).get('homeWinProbability')
            if play_wp is not None:
                win_probs.append({'play_idx': idx + 1, 'home_wp': play_wp})

    # Out-of-town scores setup
    oot_games = get_league_scoreboard()
    cards = []
    
    if oot_games:
        n_games = len(oot_games)
        st.session_state.ticker_idx = (st.session_state.ticker_idx + 3) % n_games
        selected_games = [oot_games[(st.session_state.ticker_idx + i) % n_games] for i in range(min(3, n_games))]
        
        for g in selected_games:
            away_id = g.get('away_id')
            home_id = g.get('home_id')
            
            away_abbrev = TEAM_ABBREVS.get(away_id, g.get('away_name', 'AWY')[:3]).upper()
            home_abbrev = TEAM_ABBREVS.get(home_id, g.get('home_name', 'HME')[:3]).upper()
            
            a_score = g.get('away_score', 0)
            h_score = g.get('home_score', 0)
            status = format_compact_status(g.get('status', 'PRE'))
            
            cards.append(f'''
                <div class="ticker-card">
                    <div class="ticker-teams">{away_abbrev} <span style="color:{accent_yellow};">{a_score}</span> @ {home_abbrev} <span style="color:{accent_yellow};">{h_score}</span></div>
                    <div class="ticker-status">{status}</div>
                </div>
            ''')
        ticker_cards_html = "".join(cards)
    else:
        ticker_cards_html = f'<div style="color: {subtext_color}; font-size: 0.85rem; text-align: center;">No out-of-town games active</div>'

    # Scorebug Header Section
    col_scorebug, col_ticker = st.columns([1, 1])

    with col_scorebug:
        st.html(f'''
            <div class="scorebug-container">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.25rem; font-weight: 900;">
                        {away_name.upper()} <span style="color:{accent_yellow};">{away_runs}</span> &nbsp;@&nbsp; 
                        {home_name.upper()} <span style="color:{accent_yellow};">{home_runs}</span>
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: {subtext_color};">
                        {inning_state} {inning_num} | {outs} Outs
                    </div>
                </div>
                <div style="margin-top: 4px; font-size: 0.8rem; color: {text_color};">
                    <strong>P:</strong> {pitcher_name} <span style="color:{accent_yellow};">({pitch_count})</span> &nbsp;|&nbsp; <strong>AB:</strong> {batter_name}
                </div>
            </div>
        ''')

    with col_ticker:
        st.html(f'''
            <div class="ticker-container">
                <div class="ticker-header">OUT-OF-TOWN SCOREBOARD ↻ 15s</div>
                <div class="ticker-games-grid">
                    {ticker_cards_html}
                </div>
            </div>
        ''')

    # --- WIN PROBABILITY GRAPH ---
    st.markdown("**Live Win Probability**")
    if win_probs:
        df_wp = pd.DataFrame(win_probs)
        
        plt.style.use('dark_background' if is_dark else 'default')
        fig_wp, ax_wp = plt.subplots(figsize=(12, 1.8))
        fig_wp.patch.set_facecolor(bg_color)
        ax_wp.set_facecolor(bg_color)

        ax_wp.plot(df_wp['play_idx'], df_wp['home_wp'], color='#00B4D8', linewidth=2)
        ax_wp.axhline(50, color=card_border, linestyle='--', linewidth=1)

        ax_wp.set_ylim(0, 100)
        ax_wp.set_ylabel(f"{home_name} Win %", fontsize=8, color=subtext_color)
        ax_wp.set_xlabel("Plays", fontsize=8, color=subtext_color)
        ax_wp.tick_params(colors=subtext_color, labelsize=7)
        
        for spine in ax_wp.spines.values():
            spine.set_color(card_border)

        st.pyplot(fig_wp, use_container_width=True)
        plt.close(fig_wp)
    else:
        st.info("Win probability timeline will plot as plays occur.")

    # Process Plays Data for Field Plot & Statcast Metrics
    pitch_list = []
    batted_balls = []

    for play in plays:
        p_events = play.get('playEvents', [])
        batter = play.get('matchup', {}).get('batter', {}).get('fullName', 'Unknown')
        pitcher = play.get('matchup', {}).get('pitcher', {}).get('fullName', 'Unknown')
        
        for e in p_events:
            pitch_data = e.get('pitchData', {})
            pfx = pitch_data.get('coordinates', {})
            if 'pfxX' in pfx and 'pfxZ' in pfx:
                pitch_type = e.get('details', {}).get('type', {}).get('code', 'UN')
                pitch_list.append({
                    'pitcher': pitcher,
                    'pitch_type': pitch_type,
                    'horiz_break_in': pfx['pfxX'],
                    'vert_break_in': pfx['pfxZ'],
                })

            hit_data = e.get('hitData', {})
            if hit_data:
                hc_x = hit_data.get('coordinates', {}).get('coordX')
                hc_y = hit_data.get('coordinates', {}).get('coordY')
                fx, fy = convert_hc_to_field_feet(hc_x, hc_y)
                
                batted_balls.append({
                    'Batter': batter,
                    'Result': play.get('result', {}).get('event', 'In Play'),
                    'Exit Velo (MPH)': hit_data.get('launchSpeed', 'N/A'),
                    'Launch Angle (°)': hit_data.get('launchAngle', 'N/A'),
                    'Distance (ft)': hit_data.get('totalDistance', 'N/A'),
                    'xBA': hit_data.get('expectedBattingAverage', 'N/A'),
                    'x_feet': fx,
                    'y_feet': fy
                })

    # Lower Section: Field, Pitch Movement, Batted Ball Log
    col_field, col_pitch, col_log = st.columns([2, 1, 1])

    with col_field:
        runners = {
            '1b': 'first' in offense,
            '2b': 'second' in offense,
            '3b': 'third' in offense
        }
        fig_field = draw_full_baseball_field(batted_balls, runners, field_title_label, is_dark)
        st.pyplot(fig_field, use_container_width=True)
        plt.close(fig_field)

    with col_pitch:
        st.markdown("**Live Pitch Movement**")
        if pitch_list:
            df_pitches = pd.DataFrame(pitch_list)
            latest_p = df_pitches.iloc[-1]

            plt.style.use('dark_background' if is_dark else 'default')
            fig, ax = plt.subplots(figsize=(4, 4.5))
            fig.patch.set_facecolor(bg_color)
            ax.set_facecolor(bg_color)

            sns.scatterplot(
                data=df_pitches, x='horiz_break_in', y='vert_break_in',
                hue='pitch_type', s=45, alpha=0.6, ax=ax
            )

            ax.scatter(
                latest_p['horiz_break_in'], latest_p['vert_break_in'],
                color='#FFFFFF' if is_dark else '#000000', s=120, edgecolor='#00B4D8', linewidth=2.0, label='LATEST', zorder=5
            )

            ax.axhline(0, color=card_border, linewidth=1.2)
            ax.axvline(0, color=card_border, linewidth=1.2)
            ax.set_xlim(25, -25)
            ax.set_ylim(-25, 25)
            ax.set_xlabel("← Glove | Arm →", fontsize=7, color=subtext_color)
            ax.set_ylabel("IVB (in)", fontsize=7, color=subtext_color)

            legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False, fontsize=6)
            if legend:
                for t in legend.get_texts():
                    t.set_color(text_color)

            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("Awaiting pitch telemetry...")

    with col_log:
        st.markdown("**Batted Ball Log**")
        if batted_balls:
            df_hits = pd.DataFrame(batted_balls)[['Batter', 'Result', 'Exit Velo (MPH)', 'Launch Angle (°)', 'Distance (ft)', 'xBA']].iloc[::-1]
            st.dataframe(df_hits, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No balls in play yet.")

render_brewers_dashboard(game_pk)
