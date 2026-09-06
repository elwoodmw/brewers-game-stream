import datetime
import math
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st
import statsapi

# 1. Page Configuration
st.set_page_config(page_title="Milwaukee Brewers Live Statcast Companion", layout="wide")

# Initialize Session State for Theme Toggle
if 'is_dark' not in st.session_state:
    st.session_state.is_dark = True

# Callback for Dark Mode Toggle
def toggle_dark_mode():
    st.session_state.is_dark = st.session_state.dark_mode_toggle

# Top Header Layout with Top-Right Theme Toggle
col_header, col_toggle = st.columns([5, 1])

with col_toggle:
    st.toggle(
        "Dark Mode", 
        value=st.session_state.is_dark, 
        key="dark_mode_toggle", 
        on_change=toggle_dark_mode
    )

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
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {bg_color} !important;
        font-family: 'Fira Code', monospace !important;
    }}
    
    h1, h2, h3, h4, p, span, label, div {{
        font-family: 'Fira Code', monospace !important;
        color: {text_color} !important;
    }}
    
    .title-banner {{
        padding: 0.2rem 0rem;
        margin-top: -1.0rem !important;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: baseline;
        gap: 12px;
        flex-wrap: wrap;
    }}
    
    .main-title {{
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        color: {text_color} !important;
        margin-bottom: 0px !important;
    }}

    .disclaimer-text {{
        font-size: 0.75rem !important;
        color: {subtext_color} !important;
        font-weight: 400 !important;
    }}
    
    .scorebug-container {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 24px 18px;
        height: 165px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 6px;
        margin-bottom: 10px;
        box-sizing: border-box;
    }}

    .ticker-container {{
        background-color: {ticker_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 24px 18px;
        margin-top: 0px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 165px;
        box-sizing: border-box;
    }}

    .ticker-header {{
        font-size: 0.85rem;
        font-weight: 700;
        color: #00B4D8;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }}

    .ticker-games-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        align-items: center;
    }}

    .ticker-card {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 5px;
        padding: 12px 6px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
    }}

    .ticker-teams {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {text_color};
        line-height: 1.2;
    }}

    .ticker-status {{
        font-size: 0.9rem;
        font-weight: 600;
        color: {subtext_color};
        margin-top: 6px;
    }}

    .table-wrapper {{
        width: 100%;
        height: 540px;
        overflow-x: auto;
        overflow-y: hidden;
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        margin-top: 4px;
    }}

    .custom-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'Fira Code', monospace;
        font-size: 0.78rem;
        white-space: nowrap;
    }}

    .custom-table th, .custom-table td {{
        padding: 8px 10px;
        border-bottom: 1px solid {card_border};
        color: {text_color};
        text-align: left;
        height: 33px;
    }}

    .custom-table th {{
        background-color: {ticker_bg};
        font-weight: 700;
        font-size: 0.75rem;
    }}

    .custom-table tr:last-child td {{
        border-bottom: none;
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
            <span class="disclaimer-text">Data belongs to Major League Baseball and is managed through pybaseball</span>
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

# 2. Data Fetching & Coordinate Utilities
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

def convert_hc_to_field_feet(hc_x, hc_y, total_dist=None):
    if hc_x is None or hc_y is None:
        return None, None
    x = 2.5 * (hc_x - 125.42)
    y = 2.5 * (198.27 - hc_y)
    
    if total_dist and total_dist > 0:
        raw_dist = math.hypot(x, y)
        if raw_dist > 0:
            scale = total_dist / raw_dist
            x *= scale
            y *= scale

    return x, y

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
def draw_full_baseball_field(batted_balls, runners_info, field_title_label, is_dark):
    fig, ax = plt.subplots(figsize=(7, 7.5))
    bg_c = '#121212' if is_dark else '#F8FAFC'
    border_c = '#1E293B' if is_dark else '#CBD5E1'
    line_c = '#475569' if is_dark else '#94A3B8'
    
    fig.patch.set_facecolor(bg_c)
    ax.set_facecolor(bg_c)
    ax.set_aspect('equal', adjustable='box')

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
    
    ax.plot(wall_x, wall_y, color=border_c, linewidth=3)
    ax.plot(wall_x, wall_y, color='#00B4D8', linewidth=1.2, linestyle='--')

    dirt_arc = patches.Arc((0, 60.5), 190, 190, angle=0, theta1=225, theta2=315, color=border_c, linewidth=1.5)
    ax.add_patch(dirt_arc)

    infield_x = [0, 63.64, 0, -63.64, 0]
    infield_y = [0, 63.64, 127.28, 63.64, 0]
    ax.plot(infield_x, infield_y, color=line_c, linewidth=1.5)

    mound = patches.Circle((0, 60.5), radius=9, facecolor=border_c, edgecolor=line_c, linewidth=1)
    rubber = patches.Rectangle((-1.25, 60), 2.5, 0.8, facecolor='#FFFFFF', edgecolor='#FFFFFF')
    ax.add_patch(mound)
    ax.add_patch(rubber)

    bases_coords = {'1b': (63.64, 63.64), '2b': (0, 127.28), '3b': (-63.64, 63.64)}
    for base, (bx, by) in bases_coords.items():
        runner = runners_info.get(base)
        is_occ = runner is not None
        fc = '#FFD166' if is_occ else border_c
        ec = '#FFD166' if is_occ else '#94A3B8'
        sq = patches.Rectangle((bx - 3.5, by - 3.5), 7, 7, angle=45, rotation_point='center', facecolor=fc, edgecolor=ec, zorder=5)
        ax.add_patch(sq)
        
        if is_occ and runner:
            name_parts = runner.split(' ')
            short_name = name_parts[-1] if len(name_parts) > 1 else runner
            ax.text(
                bx, by + 10, short_name,
                fontsize=7,
                fontweight='bold',
                color='#FFD166',
                fontfamily='Fira Code',
                ha='center',
                zorder=8
            )

    hp = patches.Polygon([[0, 0], [2.5, 2.5], [2.5, 5], [-2.5, 5], [-2.5, 2.5]], facecolor='#FFFFFF', edgecolor='#FFFFFF', zorder=5)
    ax.add_patch(hp)

    if batted_balls:
        for ball in batted_balls:
            hx, hy = ball.get('x_feet'), ball.get('y_feet')
            batter_name = ball.get('Batter', '')
            short_name = batter_name.split(' ')[-1] if batter_name else ''
            if hx is not None and hy is not None:
                ax.plot(
                    hx, hy, 
                    marker='o', 
                    markersize=8, 
                    markerfacecolor='#FFD166', 
                    markeredgecolor='#FFFFFF', 
                    markeredgewidth=1.5,
                    zorder=6
                )
                if short_name:
                    ax.text(
                        hx + 6, hy + 6, short_name,
                        fontsize=7,
                        fontweight='bold',
                        color='#FFFFFF' if is_dark else '#0F172A',
                        fontfamily='Fira Code',
                        zorder=7
                    )

    ax.set_xlim(-250, 250)
    ax.set_ylim(-20, 420)
    ax.axis('off')
    ax.set_title(field_title_label, fontsize=10, fontweight='bold', color=subtext_color, pad=12, fontfamily='Fira Code')
    return fig

# Helper to render clean exactly 15-slot HTML tables with fixed height and zero vertical scrollbars
def render_custom_table(headers, rows, n_slots=15, omit_last_number=False):
    padded_rows = list(rows)
    for i in range(len(padded_rows), n_slots):
        padded_rows.append({h: "" for h in headers})
    padded_rows = padded_rows[:n_slots]
    
    th_html = "".join([f"<th>{h}</th>" for h in headers])
    tr_html = ""
    for idx, r in enumerate(padded_rows):
        row_dict = dict(r)
        if headers[0] == '#' and not row_dict.get('#'):
            if omit_last_number and idx == n_slots - 1:
                row_dict['#'] = ""
            else:
                row_dict['#'] = idx + 1
            
        tds = "".join([f"<td>{row_dict.get(h, '')}</td>" for h in headers])
        tr_html += f"<tr>{tds}</tr>"
        
    return f"""
    <div class="table-wrapper">
        <table class="custom-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{tr_html}</tbody>
        </table>
    </div>
    """

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
    players_dict = game_data.get('players', {})

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

    on_deck_id = offense.get('onDeck', {}).get('id')
    in_hole_id = offense.get('inHole', {}).get('id')

    on_deck_name = players_dict.get(f"ID{on_deck_id}", {}).get('fullName', 'N/A') if on_deck_id else 'N/A'
    in_hole_name = players_dict.get(f"ID{in_hole_id}", {}).get('fullName', 'N/A') if in_hole_id else 'N/A'

    pitch_count = 0
    current_ab_pitches = []
    half_inning_batted_balls = []

    if plays:
        pitcher_id = defense.get('pitcher', {}).get('id')
        current_play = plays[-1] if plays else None

        for p in plays:
            if p.get('matchup', {}).get('pitcher', {}).get('id') == pitcher_id:
                p_events = p.get('playEvents', [])
                for e in p_events:
                    if e.get('isPitch'):
                        pitch_count += 1

        # 1. Pitch-By-Pitch for Current At-Bat
        if current_play:
            p_events = current_play.get('playEvents', [])
            pitch_events_list = [e for e in p_events if e.get('isPitch')]
            
            p_num = 1
            for e in pitch_events_list:
                p_data = e.get('pitchData', {})
                details = e.get('details', {})
                
                type_info = details.get('type', {})
                pitch_abbrev = type_info.get('code', type_info.get('description', 'P'))
                
                velo = p_data.get('startSpeed', 'N/A')
                spin = p_data.get('breaks', {}).get('spinRate', 'N/A')
                res = details.get('description', 'N/A')

                current_ab_pitches.append({
                    '#': p_num,
                    'Pitch': pitch_abbrev,
                    'Velo': f"{velo} mph" if velo != 'N/A' else 'N/A',
                    'Spin': f"{spin} rpm" if spin != 'N/A' else 'N/A',
                    'Result': res
                })
                p_num += 1

        # 2. Batted Balls Log & Spray Chart
        target_half = 'top' if inning_state.lower() in ['top', 'top 1', 't'] else 'bottom'
        current_inning_plays = [
            p for p in plays 
            if p.get('about', {}).get('inning') == inning_num 
            and p.get('about', {}).get('halfInning', '').lower() == target_half
        ]

        all_batted = []
        for p in current_inning_plays:
            batter = p.get('matchup', {}).get('batter', {}).get('fullName', 'Unknown')
            for e in p.get('playEvents', []):
                hit_data = e.get('hitData', {})
                if hit_data:
                    dist = hit_data.get('totalDistance')
                    fx, fy = convert_hc_to_field_feet(
                        hit_data.get('coordinates', {}).get('coordX'),
                        hit_data.get('coordinates', {}).get('coordY'),
                        total_dist=dist
                    )
                    all_batted.append({
                        'Batter': batter,
                        'Result': p.get('result', {}).get('event', 'In Play'),
                        'EV (mph)': hit_data.get('launchSpeed', 'N/A'),
                        'LA (°)': hit_data.get('launchAngle', 'N/A'),
                        'Dist (ft)': dist if dist is not None else 'N/A',
                        'x_feet': fx,
                        'y_feet': fy
                    })
        half_inning_batted_balls = all_batted[:15]

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

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.html(f'''
            <div class="scorebug-container">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.45rem; font-weight: 700;">
                        {away_name.upper()} <span style="color:{accent_yellow};">{away_runs}</span> &nbsp;@&nbsp; 
                        {home_name.upper()} <span style="color:{accent_yellow};">{home_runs}</span>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: {subtext_color};">
                        {inning_state} {inning_num} | {outs} Outs
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 0.92rem; color: {text_color};">
                    <strong>P:</strong> {pitcher_name} <span style="color:{accent_yellow};">({pitch_count})</span> &nbsp;|&nbsp; 
                    <strong>AB:</strong> {batter_name}
                </div>
                <div style="margin-top: 6px; font-size: 0.82rem; color: {subtext_color};">
                    <strong>On Deck:</strong> {on_deck_name} &nbsp;|&nbsp; 
                    <strong>In Hole:</strong> {in_hole_name}
                </div>
            </div>
        ''')

        runners_info = {
            '1b': offense.get('first', {}).get('fullName') if 'first' in offense else None,
            '2b': offense.get('second', {}).get('fullName') if 'second' in offense else None,
            '3b': offense.get('third', {}).get('fullName') if 'third' in offense else None
        }
        fig_field = draw_full_baseball_field(half_inning_batted_balls, runners_info, field_title_label, is_dark)
        st.pyplot(fig_field, use_container_width=True)
        plt.close(fig_field)

    with col_right:
        st.html(f'''
            <div class="ticker-container">
                <div class="ticker-header">OUT-OF-TOWN SCOREBOARD ↻ 15s</div>
                <div class="ticker-games-grid">
                    {ticker_cards_html}
                </div>
            </div>
        ''')

        col_pitch, col_log = st.columns([1, 1])

        with col_pitch:
            st.markdown("<div style='height: 24px; display: flex; align-items: center;'><b>Current At-Bat Pitch Log</b></div>", unsafe_allow_html=True)
            pitch_headers = ['#', 'Pitch', 'Velo', 'Spin', 'Result']
            pitch_html = render_custom_table(pitch_headers, current_ab_pitches, n_slots=15, omit_last_number=True)
            st.html(pitch_html)

        with col_log:
            st.markdown(f"<div style='height: 24px; display: flex; align-items: center;'><b>Batted Balls ({inning_state[:3]} {inning_num})</b></div>", unsafe_allow_html=True)
            batted_headers = ['#', 'Batter', 'Result', 'EV (mph)', 'LA (°)', 'Dist (ft)']
            batted_html = render_custom_table(batted_headers, half_inning_batted_balls, n_slots=15, omit_last_number=False)
            st.html(batted_html)

render_brewers_dashboard(game_pk)
