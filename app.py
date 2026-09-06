import datetime
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import streamlit as st
import statsapi

# 1. Page Configuration & Dark Aesthetics
st.set_page_config(page_title="MLB Live Broadcast Companion", layout="wide")

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
    .block-container {padding-top: 1.0rem !important;}
    </style>
""", unsafe_allow_html=True)

# 2. Helper Functions
@st.cache_data(ttl=60)
def get_todays_games():
    """Fetch all MLB games scheduled for today."""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    try:
        schedule = statsapi.schedule(date=today_str)
        games_dict = {}
        for g in schedule:
            label = f"{g['away_name']} @ {g['home_name']} ({g['status']})"
            games_dict[label] = g['game_id']
        return games_dict
    except Exception:
        return {}

def fetch_live_game_feed(game_pk):
    """Fetch raw live feed JSON from MLB API."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

def draw_baseball_diamond(runners):
    """Draw a dark-themed baseball diamond with active base runners."""
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    # Draw dirt/grass diamond outline
    diamond_x = [0, 1, 0, -1, 0]
    diamond_y = [0, 1, 2, 1, 0]
    ax.plot(diamond_x, diamond_y, color='#334155', linewidth=2)

    # Base coordinates
    bases = {
        '1b': (1, 1),
        '2b': (0, 2),
        '3b': (-1, 1)
    }

    # Draw bases
    for base, (x, y) in bases.items():
        is_occupied = runners.get(base, False)
        face_color = '#FFD166' if is_occupied else '#1E293B'
        edge_color = '#FFD166' if is_occupied else '#64748B'
        
        square = patches.Rectangle((x - 0.1, y - 0.1), 0.2, 0.2, angle=45, rotation_point='center',
                                   facecolor=face_color, edgecolor=edge_color, linewidth=1.5)
        ax.add_patch(square)

    # Home plate
    home = patches.Polygon([[0, -0.08], [0.08, 0], [0.08, 0.08], [-0.08, 0.08], [-0.08, 0]], 
                           facecolor='#FFFFFF', edgecolor='#FFFFFF')
    ax.add_patch(home)

    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-0.3, 2.3)
    ax.axis('off')
    return fig

# 3. Top Control Bar: Select Game
st.markdown("### ⚾ MLB Live Broadcast Companion")
all_games = get_todays_games()

if not all_games:
    st.warning("No games scheduled today or error connecting to MLB API.")
    selected_game_pk = None
else:
    selected_game_label = st.selectbox("Select Game:", options=list(all_games.keys()))
    selected_game_pk = all_games[selected_game_label]

# 4. Main Live Auto-Refreshing Fragment
@st.fragment(run_every=15)
def render_dashboard(game_pk):
    if not game_pk:
        return

    feed = fetch_live_game_feed(game_pk)
    if not feed or 'liveData' not in feed:
        st.info("Awaiting live data feed...")
        return

    live_data = feed['liveData']
    linescore = live_data.get('linescore', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    # --- A. SCORE BUG HEADER ---
    teams = feed['gameData']['teams']
    away_name = teams['away']['clubName']
    home_name = teams['home']['clubName']
    
    teams_line = linescore.get('teams', {})
    away_runs = teams_line.get('away', {}).get('runs', 0)
    home_runs = teams_line.get('home', {}).get('runs', 0)
    
    inning_state = linescore.get('inningState', 'Pre-Game')
    inning_num = linescore.get('currentInning', 1)
    outs = linescore.get('outs', 0)

    # Current matchup info
    offense = linescore.get('offense', {})
    defense = linescore.get('defense', {})
    
    batter_name = offense.get('batter', {}).get('fullName', 'N/A')
    pitcher_name = defense.get('pitcher', {}).get('fullName', 'N/A')

    st.markdown(f"""
        <div class="scorebug-container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 1.5rem; font-weight: 900;">
                    {away_name.upper()} <span style="color:#FFD166;">{away_runs}</span>  @  
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

    # --- B. FIELD DIAMOND & STATCAST METRICS ---
    col_field, col_pitch = st.columns([1.2, 1.8])

    with col_field:
        st.markdown("**Base Runners & Field State**")
        runners = {
            '1b': 'first' in offense,
            '2b': 'second' in offense,
            '3b': 'third' in offense
        }
        fig_diamond = draw_baseball_diamond(runners)
        st.pyplot(fig_diamond)
        plt.close(fig_diamond)

    # --- C. EXTRACT PITCH & HIT DATA FROM PLAYS ---
    pitch_list = []
    batted_balls = []

    for play in plays:
        p_events = play.get('playEvents', [])
        batter = play.get('matchup', {}).get('batter', {}).get('fullName', 'Unknown')
        pitcher = play.get('matchup', {}).get('pitcher', {}).get('fullName', 'Unknown')
        
        for e in p_events:
            # Check for pitch data
            pitch_data = e.get('pitchData', {})
            pfx = pitch_data.get('coordinates', {})
            
            if 'pfxX' in pfx and 'pfxZ' in pfx:
                pitch_type = e.get('details', {}).get('type', {}).get('code', 'UN')
                rel_speed = pitch_data.get('startSpeed')
                spin = pitch_data.get('breaks', {}).get('spinRate')
                
                pitch_list.append({
                    'pitcher': pitcher,
                    'pitch_type': pitch_type,
                    'horiz_break_in': pfx['pfxX'], # Inches
                    'vert_break_in': pfx['pfxZ'],  # Inches
                    'speed': rel_speed,
                    'spin': spin
                })

            # Check for hit/batted ball metrics
            hit_data = e.get('hitData', {})
            if hit_data:
                batted_balls.append({
                    'Batter': batter,
                    'Result': play.get('result', {}).get('event', 'In Play'),
                    'Exit Velo (MPH)': hit_data.get('launchSpeed', 'N/A'),
                    'Launch Angle (°)': hit_data.get('launchAngle', 'N/A'),
                    'Distance (ft)': hit_data.get('totalDistance', 'N/A'),
                    'xBA': hit_data.get('expectedBattingAverage', 'N/A')
                })

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
                hue='pitch_type', s=50, alpha=0.6, ax=ax
            )

            # Highlight last pitch
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

    # --- D. BATTED BALL STATCAST METRICS TABLE ---
    st.markdown("### 💥 Statcast Batted Ball Log (Both Teams)")
    if batted_balls:
        df_hits = pd.DataFrame(batted_balls).iloc[::-1] # Show newest hits on top
        st.dataframe(df_hits, use_container_width=True, hide_index=True)
    else:
        st.info("No balls put in play yet for this game.")

render_dashboard(selected_game_pk)
