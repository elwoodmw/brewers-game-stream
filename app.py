import datetime
import math
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import streamlit as st
import statsapi

# 1. Page Configuration & Inter Font Dark Styling
st.set_page_config(page_title="Milwaukee Brewers Live Companion", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #121212 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    h1, h2, h3, h4, p, span, label, div {
        font-family: 'Inter', sans-serif !important;
        color: #FFFFFF !important;
    }
    
    .title-banner {
        padding: 0.2rem 0rem;
        border-bottom: 1px solid #2D2D2D;
        margin-top: -1.0rem !important;
        margin-bottom: 1.5rem;
    }
    
    .main-title {
        font-size: 2.0rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.05em !important;
        color: #FFFFFF !important;
        margin-bottom: 0px !important;
    }
    
    .scorebug-container {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 20px;
        margin-bottom: 20px;
    }
    
    [data-testid="stSidebar"] {visibility: hidden; width: 0px; display: none;}
    [data-testid="stHeader"] {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 0rem !important;}
    </style>
""", unsafe_allow_html=True)

# Minimalist Title Banner
st.markdown("""
    <div class="title-banner">
        <h1 class="main-title">Milwaukee Brewers Live Statcast Companion</h1>
    </div>
""", unsafe_allow_html=True)

BREWERS_TEAM_ID = 158

# 2. Data Fetching Utilities
@st.cache_data(ttl=60)
def get_today_brewers_game():
    """Fetch today's Brewers game_pk using MLB Stats API."""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    try:
        schedule = statsapi.schedule(date=today_str, team=BREWERS_TEAM_ID)
        if schedule:
            game = schedule[0]
            return game['game_id'], f"{game['away_name']} @ {game['home_name']} ({game['status']})"
    except Exception:
        pass
    return None, "No Milwaukee Brewers game scheduled today."

def fetch_live_game_feed(game_pk):
    """Fetch raw live feed JSON from MLB API."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

def convert_hc_to_field_feet(hc_x, hc_y):
    """
    Transforms Gameday hit coordinates (hc_x, hc_y) to feet relative to Home Plate (0,0).
    Home plate is roughly at (126, 204) in coordinate space.
    """
    if hc_x is None or hc_y is None:
        return None, None
    x_feet = (hc_x - 126) * 2.29
    y_feet = (204 - hc_y) * 2.29
    return x_feet, y_feet

# 3. Full Ballpark Diagram Generator (American Family Field dimensions)
def draw_full_baseball_field(batted_balls, runners):
    """Draws a full dark-theme ballpark (Infield + Outfield Wall + Base Runners + Ball Landing Locations)."""
    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    # Outfield Wall Arc (Scaled to ~400ft center field wall like American Family Field)
    foul_len = 345
    center_len = 400
    
    # Draw Foul Lines
    ax.plot([0, -foul_len * math.sin(math.pi/4)], [0, foul_len * math.cos(math.pi/4)], color='#64748B', linewidth=1.5)
    ax.plot([0, foul_len * math.sin(math.pi/4)], [0, foul_len * math.cos(math.pi/4)], color='#64748B', linewidth=1.5)

    # Draw Outfield Wall
    wall_angles = [i * (math.pi / 2 / 100) - math.pi / 4 for i in range(101)]
    wall_x = [center_len * math.sin(a) for a in wall_angles]
    wall_y = [center_len * math.cos(a) for a in wall_angles]
    ax.plot(wall_x, wall_y, color='#1E293B', linewidth=3)
    ax.plot(wall_x, wall_y, color='#00B4D8', linewidth=1.2, linestyle='--')

    # Draw Infield Diamond
    infield_x = [0, 63.6, 0, -63.6, 0]
    infield_y = [0, 63.6, 127.3, 63.6, 0]
    ax.plot(infield_x, infield_y, color='#334155', linewidth=1.5)

    # Bases setup
    bases_coords = {'1b': (63.6, 63.6), '2b': (0, 127.3), '3b': (-63.6, 63.6)}
    for base, (bx, by) in bases_coords.items():
        is_occ = runners.get(base, False)
        fc = '#FFD166' if is_occ else '#1E293B'
        ec = '#FFD166' if is_occ else '#64748B'
        sq = patches.Rectangle((bx - 5, by - 5), 10, 10, angle=45, rotation_point='center', facecolor=fc, edgecolor=ec)
        ax.add_patch(sq)

    # Home Plate
    hp = patches.Polygon([[0, -2], [4, 0], [4, 4], [-4, 4], [-4, 0]], facecolor='#FFFFFF', edgecolor='#FFFFFF')
    ax.add_patch(hp)

    # Plot Batted Ball Landing Coordinates with Baseball Markers
    if batted_balls:
        for ball in batted_balls:
            hx, hy = ball.get('x_feet'), ball.get('y_feet')
            if hx is not None and hy is not None:
                # Plot landing location as a baseball marker
                ax.plot(
                    hx, hy, 
                    marker='o', 
                    markersize=9, 
                    markerfacecolor='#FFFFFF', 
                    markeredgecolor='#FFD166', 
                    markeredgewidth=1.5,
                    zorder=6
                )

    ax.set_xlim(-280, 280)
    ax.set_ylim(-20, 420)
    ax.axis('off')
    ax.set_title("BALLPARK SPRAY CHART & RUNNERS", fontsize=10, fontweight='bold', color='#8E9AAF', pad=10)
    return fig

# 4. Main App Logic
game_pk, game_summary = get_today_brewers_game()
st.subheader(f"Game Status: {game_summary}")

@st.fragment(run_every=15)
def render_brewers_dashboard(game_pk):
    if not game_pk:
        st.info("Awaiting today's Milwaukee Brewers game schedule.")
        return

    feed = fetch_live_game_feed(game_pk)
    if not feed or 'liveData' not in feed:
        st.info("Game feed loading or pre-game status...")
        return

    live_data = feed['liveData']
    linescore = live_data.get('linescore', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    # Score Bug Bar
    teams = feed['gameData']['teams']
    away_name = teams['away']['clubName']
    home_name = teams['home']['clubName']
    
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

    st.markdown(f"""
        <div class="scorebug-container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 1.5rem; font-weight: 900;">
                    {away_name.upper()} <span style="color:#FFD166;">{away_runs}</span> &nbsp;@&nbsp; 
                    <span style="color:#FFD166;">{home_runs}</span> {home_name.upper()}
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #94A3B8;">
                    {inning_state} {inning_num} | {outs} Outs
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 0.9rem; color: #CBD5E1;">
                <strong>Pitching:</strong> {pitcher_name} &nbsp;|&nbsp; <strong>At Bat:</strong> {batter_name}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Extract Pitching and Hit Coordinates Data
    pitch_list = []
    batted_balls = []

    for play in plays:
        p_events = play.get('playEvents', [])
        batter = play.get('matchup', {}).get('batter', {}).get('fullName', 'Unknown')
        pitcher = play.get('matchup', {}).get('pitcher', {}).get('fullName', 'Unknown')
        
        for e in p_events:
            # Check Pitch Data
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

            # Check Hit Coordinates
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

    # Side-By-Side Visuals
    col_field, col_pitch = st.columns([1.2, 1.8])

    with col_field:
        runners = {
            '1b': 'first' in offense,
            '2b': 'second' in offense,
            '3b': 'third' in offense
        }
        fig_field = draw_full_baseball_field(batted_balls, runners)
        st.pyplot(fig_field)
        plt.close(fig_field)

    with col_pitch:
        st.markdown("**Live Pitch Movement Profile**")
        if pitch_list:
            df_pitches = pd.DataFrame(pitch_list)
            latest_p = df_pitches.iloc[-1]

            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(4.5, 4.5))
            fig.patch.set_facecolor('#121212')
            ax.set_facecolor('#121212')

            sns.scatterplot(
                data=df_pitches, x='horiz_break_in', y='vert_break_in',
                hue='pitch_type', s=45, alpha=0.6, ax=ax
            )

            # Highlight Latest Pitch
            ax.scatter(
                latest_p['horiz_break_in'], latest_p['vert_break_in'],
                color='#FFFFFF', s=140, edgecolor='#00B4D8', linewidth=2.0, label='LATEST', zorder=5
            )

            ax.axhline(0, color='#2D2D2D', linewidth=1.2)
            ax.axvline(0, color='#2D2D2D', linewidth=1.2)
            ax.set_xlim(25, -25)
            ax.set_ylim(-25, 25)
            ax.set_xlabel("← Glove Side | Arm Side →", fontsize=8, color='#8E9AAF')
            ax.set_ylabel("Induced Vertical Break (in)", fontsize=8, color='#8E9AAF')

            legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False, fontsize=7)
            for t in legend.get_texts():
                t.set_color('#FFFFFF')

            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("Awaiting pitch telemetry...")

    # Batted Ball Log Table
    st.markdown("### Statcast Batted Ball Log")
    if batted_balls:
        df_hits = pd.DataFrame(batted_balls)[['Batter', 'Result', 'Exit Velo (MPH)', 'Launch Angle (°)', 'Distance (ft)', 'xBA']].iloc[::-1]
        st.dataframe(df_hits, use_container_width=True, hide_index=True)
    else:
        st.info("No balls put in play yet for this game.")

render_brewers_dashboard(game_pk)
