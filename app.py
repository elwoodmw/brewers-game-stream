import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import statsapi
from pybaseball import statcast_single_game

# 1. Page Configuration
st.set_page_config(page_title="Brewers Live Companion", layout="wide")

# Custom Styling (Dark Mode Aesthetic)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #121212 !important;
        font-family: 'Inter', sans-serif !important;
    }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; }
    [data-testid="stHeader"] { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }
    </style>
""", unsafe_allow_html=True)

BREWERS_TEAM_ID = 158

# Cache today's game lookup so it doesn't slam the API unnecessarily
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

# 2. Main Title Banner
st.title("🍺 Milwaukee Brewers Live Statcast Companion")

game_pk, game_summary = get_today_brewers_game()
st.subheader(f"Game Status: {game_summary}")

# 3. Built-In Live Auto-Refreshing Fragment (Updates every 20s without extra packages)
@st.fragment(run_every=20)
def render_live_dashboard(selected_game_pk):
    if not selected_game_pk:
        st.info("Waiting for a live or scheduled Brewers game. If a game is played today, live pitch metrics will load here automatically.")
        return

    try:
        # Pull Statcast pitch-by-pitch data for this specific game
        raw_data = statcast_single_game(selected_game_pk)
        
        if raw_data.empty or 'pfx_x' not in raw_data.columns:
            st.warning("Game data found, but no Statcast pitch metrics have logged yet. Check back closer to first pitch!")
            return

        # Clean and calculate break metrics in inches
        movement_data = raw_data.dropna(subset=['pfx_x', 'pfx_z']).copy()
        movement_data['horiz_break_in'] = movement_data['pfx_x'] * 12
        movement_data['vert_break_in'] = movement_data['pfx_z'] * 12

        if movement_data.empty:
            st.warning("Awaiting first pitch data...")
            return

        # Latest pitch logged in the press box
        latest_pitch = movement_data.iloc[0]

        # Top Display Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Pitcher", str(latest_pitch.get('player_name', 'Unknown')))
        c2.metric("Last Pitch Type", str(latest_pitch.get('pitch_type', 'N/A')))
        
        rel_speed = latest_pitch.get('release_speed')
        c3.metric("Velocity", f"{rel_speed:.1f} MPH" if pd.notnull(rel_speed) else "N/A")
        
        spin_rate = latest_pitch.get('release_spin_rate')
        c4.metric("Spin Rate", f"{int(spin_rate)} RPM" if pd.notnull(spin_rate) else "N/A")

        # Movement Chart Setup
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(5.5, 5.5))
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')

        # Plot all pitch trajectory profiles logged so far in the game
        sns.scatterplot(
            data=movement_data, 
            x='horiz_break_in', 
            y='vert_break_in',
            hue='pitch_type', 
            s=50, 
            alpha=0.5, 
            ax=ax
        )

        # Highlight the most recent pitch with a distinct point
        ax.scatter(
            latest_pitch['horiz_break_in'], 
            latest_pitch['vert_break_in'],
            color='#FFD166', 
            s=160, 
            edgecolor='#FFFFFF', 
            linewidth=1.5,
            label='LATEST PITCH', 
            zorder=5
        )

        ax.axhline(0, color='#2D2D2D', linewidth=1.2)
        ax.axvline(0, color='#2D2D2D', linewidth=1.2)

        ax.set_xlim(25, -25) # Inverted for catcher's perspective
        ax.set_ylim(-25, 25)
        ax.set_title("Current Game Pitch Movement", fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel("← Glove Side Break (in) | Arm Side Run (in) →", fontsize=8, color='#8E9AAF')
        ax.set_ylabel("Induced Vertical Break (Inches)", fontsize=8, color='#8E9AAF')
        ax.grid(True, linestyle=':', alpha=0.15)

        legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False, fontsize=8)
        for text in legend.get_texts():
            text.set_color('#FFFFFF')

        st.pyplot(fig)
        plt.close(fig)

    except Exception as e:
        st.error(f"Error fetching live pitch metrics: {e}")

# Render live dashboard loop
render_live_dashboard(game_pk)
