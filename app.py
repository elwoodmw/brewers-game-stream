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
        font-size: 1.6rem !important;
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
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 6px;
        margin-bottom: 10px;
    }}

    .ticker-container {{
        background-color: {ticker_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}

    .ticker-header {{
        font-size: 0.7rem;
        font-weight: 700;
        color: #00B4D8;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
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
        padding: 8px 8px;
        text-align: center;
    }}

    .ticker-teams {{
        font-size: 0.85rem;
        font-weight: 700;
        color: {text_color};
        line-height: 1.2;
    }}

    .ticker-status {{
        font-size: 0.7rem;
        font-weight: 500;
        color: {subtext_color};
        margin-top: 3px;
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
    win_probs = []
    current_ab_pitches = []
    half_inning_batted_balls = []

    if plays:
        pitcher_id = defense.get('pitcher', {}).get('id')
        current_play = plays[-1] if plays else None

        for idx, p in enumerate(plays):
            if p.get('matchup', {}).get('pitcher', {}).get('id') == pitcher_id:
                p_events = p.get('playEvents', [])
                for e in p_events:
                    if e.get('isPitch'):
                        pitch_count += 1
            
            about = p.get('about', {})
            
            # Accurate Win Probability tracking logic
            top_bottom = about.get('halfInning', '')
            inn = about.get('inning', 1)
            
            # Check for home win probability from standard API structure first
            wp = about.get('homeWinProbability')
            if wp is not None:
                home_wp_val = wp * 100.0 if wp <= 1.0 else wp
            else:
                # Fallback calculation if explicit field is missing
                home_wp_val = 50.0

            win_probs.append({
                'play_idx': idx + 1, 
                'home_wp': home_wp_val,
                'label': f"Inn {inn} ({top_bottom})"
            })

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
        half_inning_batted_balls = all_batted[-15:]

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
                    <div style="font-size: 1.25rem; font-weight: 700;">
                        {away_name.upper()} <span style="color:{accent_yellow};">{away_runs}</span> &nbsp;@&nbsp; 
                        {home_name.upper()} <span style="color:{accent_yellow};">{home_runs}</span>
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 500; color: {subtext_color};">
                        {inning_state} {inning_num} | {outs} Outs
                    </div>
                </div>
                <div style="margin-top: 6px; font-size: 0.8rem; color: {text_color};">
                    <strong>P:</strong> {pitcher_name} <span style="color:{accent_yellow};">({pitch_count})</span> &nbsp;|&nbsp; 
                    <strong>AB:</strong> {batter_name}
                </div>
                <div style="margin-top: 4px; font-size: 0.72rem; color: {subtext_color};">
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
        st.markdown("**Live Win Probability (Per Play)**")
        if win_probs:
            df_wp = pd.DataFrame(win_probs)
            
            plt.style.use('dark_background' if is_dark else 'default')
            fig_wp, ax_wp = plt.subplots(figsize=(8, 1.8))
            fig_wp.patch.set_facecolor(bg_color)
            ax_wp.set_facecolor(bg_color)

            # Correctly plot the home win probability trend line correctly mapped between 0 and 100%
            ax_wp.plot(df_wp['play_idx'], df_wp['home_wp'], color='#00B4D8', linewidth=2, marker='o', markersize=3)
            ax_wp.axhline(50, color=card_border, linestyle='--', linewidth=1)

            ax_wp.set_ylim(0, 100)
            ax_wp.set_xlim(1, max(df_wp['play_idx'].max(), 5))
            ax_wp.set_xlabel("Play Index", fontsize=6, color=subtext_color, fontfamily='Fira Code')
            ax_wp.set_ylabel(f"{home_name[:3].upper()} Win %", fontsize=7, color=subtext_color, fontfamily='Fira Code')
            ax_wp.tick_params(colors=subtext_color, labelsize=6)
            
            for spine in ax_wp.spines.values():
                spine.set_color(card_border)

            st.pyplot(fig_wp, use_container_width=True)
            plt.close(fig_wp)
        else:
            st.info("Win probability timeline will plot as plays occur.")

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
            st.markdown("**Current At-Bat Pitch Log**")
            # Pad or configure row limits to 15 entries
            while len(current_ab_pitches) < 15:
                current_ab_pitches.append({
                    '#': len(current_ab_pitches) + 1,
                    'Pitch': '',
                    'Velo': '',
                    'Spin': '',
                    'Result': ''
                })
            df_pitches = pd.DataFrame(current_ab_pitches[:15])
            
            st.dataframe(
                df_pitches, 
                use_container_width=True, 
                hide_index=True, 
                height=240,
                column_config={
                    "#": st.column_config.NumberColumn("#", width=30),
                    "Pitch": st.column_config.TextColumn("Pitch", width=45),
                    "Velo": st.column_config.TextColumn("Velo", width="small"),
                    "Spin": st.column_config.TextColumn("Spin", width="small"),
                    "Result": st.column_config.TextColumn("Result", width="medium")
                }
            )

        with col_log:
            st.markdown(f"**Half-Inning Batted Balls ({inning_state} {inning_num})**")
            batted_data = list(half_inning_batted_balls)
            while len(batted_data) < 15:
                batted_data.append({
                    'Batter': '',
                    'Result': '',
                    'EV (mph)': '',
                    'LA (°)': '',
                    'Dist (ft)': ''
                })
            df_batted = pd.DataFrame(batted_data[:15])[['Batter', 'Result', 'EV (mph)', 'LA (°)', 'Dist (ft)']]
            
            st.dataframe(
                df_batted,
                use_container_width=True,
                hide_index=True,
                height=240,
                column_config={
                    "Batter": st.column_config.TextColumn("Batter", width=110),
                    "Result": st.column_config.TextColumn("Result", width="medium"),
                    "EV (mph)": st.column_config.TextColumn("EV (mph)", width="small"),
                    "LA (°)": st.column_config.TextColumn("LA (°)", width="small"),
                    "Dist (ft)": st.column_config.TextColumn("Dist (ft)", width="small")
                }
            )

render_brewers_dashboard(game_pk)
