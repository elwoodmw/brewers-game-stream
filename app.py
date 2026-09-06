import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import statsapi
from pybaseball import statcast_single_game, playerid_lookup, statcast_pitcher

# 1. Page Configuration
st.set_page_config(page_title="Brewers Live Statcast Companion", layout="wide")

# Custom Styling (Restored Inter font, dark background, hidden header/footer)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #121212 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    h1, h2, h3, p, span, label, div {
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
    
    [data-testid="stSidebar"] {visibility: hidden; width: 0px; display: none;}
    [data-testid="stHeader"] {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {padding-top: 0rem !important; padding-bottom: 1.5rem;}
    </style>
""", unsafe_allow_html=True)

# Minimalist Title Banner
st.markdown("""
    <div class="title-banner">
        <h1 class="main-title">Milwaukee Brewers Live Statcast Companion</h1>
    </div>
""", unsafe_allow_html=True)

BREWERS_TEAM_ID = 158

@st.cache_data(ttl=60)
def get_today_brewers_game():
    """Fetch today's Brewers game_pk and status summary."""
    try:
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        schedule = statsapi.schedule(date=today_str, team=BREWERS_TEAM_ID)
        if schedule:
            game = schedule[0]
            return game['game_id'], f"{game['away_name']} @ {game['home_name']} ({game['status']})"
    except Exception as e:
        return None, f"Error looking up schedule: {e}"
    return None, "No Milwaukee Brewers game scheduled today."

game_pk, game_summary = get_today_brewers_game()
st.subheader(f"Game Status: {game_summary}")

# Built-In Live Auto-Refreshing Fragment (Updates every 20s)
@st.fragment(run_every=20)
def render_live_dashboard(selected_game_pk):
    if not selected_game_pk:
        st.info("Waiting for a live or scheduled Brewers game. Live pitch metrics will load here automatically once first pitch occurs.")
        return

    try:
        # Pull Statcast pitch-by-pitch data for this specific game
        raw_data = statcast_single_game(selected_game_pk)
        
        # Check if returned object is None or empty (Pre-game state)
        if raw_data is None or (isinstance(raw_data, pd.DataFrame) and raw_data.empty):
            st.info("Game is currently in Pre-Game status. Statcast data will appear here live once the game begins!")
            return

        if 'pfx_x' not in raw_data.columns:
            st.warning("Game data found, but no Statcast pitch metrics have logged yet.")
            return

        # Clean and calculate break metrics in inches
        movement_data = raw_data.dropna(subset=['pfx_x', 'pfx_z']).copy()
        
        if movement_data.empty:
            st.info("Game started, but awaiting first pitch tracking coordinates...")
            return

        movement_data['horiz_break_in'] = movement_data['pfx_x'] * 12
        movement_data['vert_break_in'] = movement_data['pfx_z'] * 12

        # Latest pitch logged in the press box
        latest_pitch = movement_data.iloc[0]

        # Metric Display Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Pitcher", str(latest_pitch.get('player_name', 'Unknown')))
        c2.metric("Last Pitch Type", str(latest_pitch.get('pitch_type', 'N/A')))
        
        rel_speed = latest_pitch.get('release_speed')
        c3.metric("Velocity", f"{rel_speed:.1f} MPH" if pd.notnull(rel_speed) else "N/A")
        
        spin_rate = latest_pitch.get('release_spin_rate')
        c4.metric("Spin Rate", f"{int(spin_rate)} RPM" if pd.notnull(spin_rate) else "N/A")

        # Movement Chart Setup
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')

        # Colors for pitches
        top_pitches = movement_data['pitch_type'].value_counts().index.tolist()
        master_colors = {
            'FF': '#00B4D8', 'SI': '#00F5D4', 'FC': '#FFD166', 
            'SL': '#F77F00', 'ST': '#FF9F1C', 'CH': '#00A859', 
            'CU': '#7209B7', 'KC': '#9B5DE5', 'FS': '#FF006E', 'SV': '#E040FB'
        }
        color_palette = {p: master_colors.get(p, sns.color_palette("Set2")[i % 8]) for i, p in enumerate(top_pitches)}

        sns.scatterplot(
            data=movement_data, 
            x='horiz_break_in', 
            y='vert_break_in',
            hue='pitch_type', 
            palette=color_palette,
            s=45, 
            alpha=0.5, 
            ax=ax
        )

        # Highlight the most recent pitch
        ax.scatter(
            latest_pitch['horiz_break_in'], 
            latest_pitch['vert_break_in'],
            color='#FFFFFF', 
            s=140, 
            edgecolor='#00B4D8', 
            linewidth=2.0,
            label='LATEST PITCH', 
            zorder=5
        )

        ax.axhline(0, color='#2D2D2D', linewidth=1.2)
        ax.axvline(0, color='#2D2D2D', linewidth=1.2)

        ax.set_xlim(25, -25) # Inverted for catcher's perspective
        ax.set_ylim(-25, 25)
        ax.set_title("LIVE GAME PITCH MOVEMENT", fontsize=11, fontweight=900, fontfamily='Inter', color='#FFFFFF', pad=12, loc='left')
        ax.set_xlabel("← Glove Side Break (in) | Arm Side Run (in) →", fontsize=8, fontweight='bold', fontfamily='Inter', color='#8E9AAF')
        ax.set_ylabel("Induced Vertical Break (Inches)", fontsize=8, fontweight='bold', fontfamily='Inter', color='#8E9AAF')
        ax.grid(True, linestyle=':', alpha=0.1)

        legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=True, facecolor='#1E293B', edgecolor='#2D2D2D', fontsize=7)
        for text in legend.get_texts():
            text.set_color('#FFFFFF')

        st.pyplot(fig)
        plt.close(fig)

    except Exception as e:
        st.error(f"Error fetching live pitch metrics: {e}")

render_live_dashboard(game_pk)
