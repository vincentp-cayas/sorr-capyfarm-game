import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Tuple
import random
import itertools

import json
import os

class TextManager:
    def __init__(self, texts_dict):
        self.texts = texts_dict
    def get(self, key):
        return self.texts.get(key, f"[{key}]")

def load_texts():
    file_path = os.path.join(os.path.dirname(__file__), 'texts.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

TEXTS = TextManager(load_texts())

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title=TEXTS.get("page_title"),
    page_icon="🦫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# DATA LOADING & PREPARATION
# ============================================================================
@st.cache_data
def load_returns_data():
    """Load and parse returns data with European decimal format."""
    df = pd.read_csv('Returns.csv', sep=';')
    # Replace European decimal format (comma) with English format (dot)
    df['Real return'] = df['Real return'].astype(str).str.replace(',', '.').astype(float)
    return df
    

@st.cache_data
def extract_5year_blocks(returns_df):
    """Extract 5-year non-overlapping blocks from the returns data."""
    blocks = []
    for year_start in range(1995, 2021, 5):  # Non-overlapping blocks: 1995, 2000, 2005, 2010, 2015, 2020
        year_end = year_start + 4  # 5 years total
        block_returns = returns_df[returns_df['Year'].between(year_start, year_end)]['Real return'].tolist()
        blocks.append({
            'start_year': year_start,
            'end_year': year_end,
            'returns': block_returns
        })
    return blocks

@st.cache_data
def compute_strategy_envelopes(blocks):
    """Compute all permutations for baseline strategies to draw envelopes."""
    simulator = PortfolioSimulator()
    strategies = {
        "100% Stocks": [100, 100, 100, 100, 100, 100],
        "75% Stocks": [75, 75, 75, 75, 75, 75],
        "50/50 Mix": [50, 50, 50, 50, 50, 50],
        "25% Stocks": [25, 25, 25, 25, 25, 25],
        "Pilotage du risque simple": [75, 50, 25, 100, 100, 100]
    }
    
    # Get all permutations of the 6 blocks
    sequences = list(itertools.permutations([b['returns'] for b in blocks]))
        
    results = {}
    for name, allocs in strategies.items():
        all_vals = []
        bust_count = 0
        for seq in sequences:
            vals, _, _, bust, _ = simulator.simulate_full_game(allocs, seq)
            if bust:
                bust_count += 1
                # Ne pas inclure la valeur négative de faillite dans l'enveloppe
                if len(vals) > 0 and vals[-1] < 0:
                    vals = vals[:-1]
            # Pad the array with zeros if the simulation busted early
            if len(vals) < 31:
                vals.extend([0] * (31 - len(vals)))
            all_vals.append(vals)
        
        all_vals = np.array(all_vals)
        results[name] = {
            'min': np.min(all_vals, axis=0).tolist(),
            'max': np.max(all_vals, axis=0).tolist(),
            'median': np.round(np.median(all_vals, axis=0), -2).tolist(),
            'bust_rate': (bust_count / len(sequences)) * 100
        }
    return results

    

# ============================================================================
# SIMULATION ENGINE
# ============================================================================
class PortfolioSimulator:
    def __init__(self, initial_capital=10000, annual_savings=5000, purchase_year=15, 
                 purchase_amount=85000, total_years=30):
        self.initial_capital = initial_capital
        self.annual_savings = annual_savings
        self.purchase_year = purchase_year
        self.purchase_amount = purchase_amount
        self.total_years = total_years
    
    def simulate_period(self, portfolio_value, allocation_pct, returns_block, global_year_start=0):
        """
        Simulate a 5-year period.
        Returns: (yearly_values, yearly_stocks, yearly_cash, bust)
        """
        yearly_values = [portfolio_value]
        yearly_stocks = []
        yearly_cash = []
        bust = False
        current_value = portfolio_value
        
        for year_offset, annual_return in enumerate(returns_block):
            # Calculate stock and cash portions at start of year
            stock_portion = current_value * (allocation_pct / 100)
            cash_portion = current_value - stock_portion
            
            # Apply annual return to stock portion
            stock_portion *= (1 + annual_return)
            
            # Add annual savings (rebalance)
            total_with_savings = stock_portion + cash_portion + self.annual_savings
            current_value = round(total_with_savings, -2)
            
            # Check for purchase at year 15
            global_year = global_year_start + len(yearly_values)  # Current year in the overall simulation
            if global_year == self.purchase_year and current_value < self.purchase_amount:
                bust = True
                current_value -= self.purchase_amount
                yearly_values.append(current_value)
                yearly_stocks.append(0)
                yearly_cash.append(current_value)
                break
            
            # Deduct purchase
            if global_year == self.purchase_year:
                current_value -= self.purchase_amount
                
            # Recalculate portions after rounding/purchase
            stock_portion = current_value * (allocation_pct / 100)
            cash_portion = current_value - stock_portion
            
            yearly_values.append(current_value)
            yearly_stocks.append(round(stock_portion, -2))
            yearly_cash.append(round(cash_portion, -2))
        
        return yearly_values, yearly_stocks, yearly_cash, bust, current_value
    
    def simulate_full_game(self, allocation_sequence, returns_blocks_sequence):
        """
        Simulate the full 25-year game with given allocations and returns blocks.
        """
        yearly_values = [self.initial_capital]
        yearly_stocks = []
        yearly_cash = []
        bust = False
        current_value = self.initial_capital
        
        for period, (allocation, returns_block) in enumerate(zip(allocation_sequence, returns_blocks_sequence)):
            for year_offset, annual_return in enumerate(returns_block):
                # Calculate stock and cash portions
                stock_portion = current_value * (allocation / 100)
                cash_portion = current_value - stock_portion
                
                # Apply annual return to stock portion
                stock_portion *= (1 + annual_return)
                
                # Add annual savings
                total_with_savings = stock_portion + cash_portion + self.annual_savings
                current_value = round(total_with_savings, -2)
                
                # Check for purchase at year 15
                global_year = len(yearly_values)
                if global_year == self.purchase_year and current_value < self.purchase_amount:
                    bust = True
                    current_value -= self.purchase_amount
                    yearly_values.append(current_value)
                    yearly_stocks.append(0)
                    yearly_cash.append(current_value)
                    break
                
                # Deduct purchase
                if global_year == self.purchase_year:
                    current_value -= self.purchase_amount
                    
                # Recalculate portions after rounding/purchase
                stock_portion = current_value * (allocation / 100)
                cash_portion = current_value - stock_portion
                
                yearly_values.append(current_value)
                yearly_stocks.append(round(stock_portion, -2))
                yearly_cash.append(round(cash_portion, -2))
            
            if bust:
                break
        
        return yearly_values, yearly_stocks, yearly_cash, bust, current_value

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def init_session_state():
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'intro'
    if 'current_period' not in st.session_state:
        st.session_state.current_period = 0
    if 'portfolio_values' not in st.session_state:
        st.session_state.portfolio_values = [10000]  # Starting capital
    if 'allocations' not in st.session_state:
        st.session_state.allocations = []
    if 'bust' not in st.session_state:
        st.session_state.bust = False
    if 'game_over' not in st.session_state:
        st.session_state.game_over = False
    if 'final_value' not in st.session_state:
        st.session_state.final_value = None
    if 'selected_blocks' not in st.session_state:
        st.session_state.selected_blocks = []
    if 'all_yearly_values' not in st.session_state:
        st.session_state.all_yearly_values = [10000]
    if 'all_yearly_stocks' not in st.session_state:
        st.session_state.all_yearly_stocks = []
    if 'all_yearly_cash' not in st.session_state:
        st.session_state.all_yearly_cash = []

# ============================================================================
# UI & MAIN APP
# ============================================================================
def main():
    init_session_state()
    
    # Injection du style CSS personnalisé (UI moderne, épurée, type SaaS fintech comme Cayas)
    st.markdown("""
    <style>
        /* Police moderne (Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Boutons d'action stylisés */
        .stButton > button {
            background-color: #0F172A !important; /* Bleu nuit / Ardoise - très pro */
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.2rem !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        .stButton > button:hover {
            background-color: #1E293B !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        }
        
        /* Métriques sous forme de cartes élégantes (compatible mode clair/sombre) */
        [data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.05);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 12px;
            padding: 1rem 1.5rem;
        }
        
        /* Nettoyage de l'UI par défaut de Streamlit */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    # Load data
    returns_df = load_returns_data()
    blocks = extract_5year_blocks(returns_df)
    simulator = PortfolioSimulator()
    strategies = {
        "100% Stocks": [100, 100, 100, 100, 100, 100],
        "75% Stocks": [75, 75, 75, 75, 75, 75],
        "50/50 Mix": [50, 50, 50, 50, 50, 50],
        "25% Stocks": [25, 25, 25, 25, 25, 25],
        "Pilotage du risque simple": [75, 50, 25, 100, 100, 100]
    }
    

    
    # Sidebar info
    with st.sidebar:
        st.subheader(TEXTS.get("sidebar_title"))
        st.info(TEXTS.get("sidebar_rules"))
    
    if st.session_state.current_view == 'intro':
        st.title(TEXTS.get("intro_title"))
        st.markdown(TEXTS.get("intro_text"), unsafe_allow_html=True)
        
        st.markdown("<div style='text-align: center; font-size: 80px;'>🌾 🦫 🏡 💰</div>", unsafe_allow_html=True)
        st.write("")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button(TEXTS.get("btn_start"), width="stretch"):
                st.session_state.current_view = 'game'
                st.rerun()


    elif st.session_state.current_view == 'game':
        st.title(TEXTS.get("game_title"))
        
        col1, col2 = st.columns([1, 2.5])
        
        with col1:
            if not st.session_state.game_over and not st.session_state.bust:
                # Current period info
                period_num = st.session_state.current_period + 1
                st.write(TEXTS.get("game_round").format(period_num))
                
                # Portfolio value display
                current_portfolio = st.session_state.portfolio_values[-1] if st.session_state.portfolio_values else 10000
                st.metric(TEXTS.get("metric_portfolio"), f"{current_portfolio:,.0f} €".replace(",", " "))
                
                allocation = st.slider(
                    TEXTS.get("slider_allocation"),
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=10,
                    help=TEXTS.get("slider_help")
                )
                
                if st.button(TEXTS.get("btn_simulate"), width="stretch"):
                    available_blocks = [b for i, b in enumerate(blocks) if i not in st.session_state.selected_blocks]
                    
                    if available_blocks:
                        selected_block = random.choice(available_blocks)
                        block_idx = blocks.index(selected_block)
                        st.session_state.selected_blocks.append(block_idx)
                        
                        current_value = st.session_state.portfolio_values[-1]
                        global_year_start = st.session_state.current_period * 5
                        yearly_vals, yearly_stk, yearly_cash, bust, final_val = simulator.simulate_period(
                            current_value, allocation, selected_block['returns'], global_year_start
                        )
                        
                        st.session_state.allocations.append(allocation)
                        st.session_state.all_yearly_values.extend(yearly_vals[1:])
                        st.session_state.all_yearly_stocks.extend(yearly_stk)
                        st.session_state.all_yearly_cash.extend(yearly_cash)
                        st.session_state.portfolio_values.append(final_val)
                        
                        if bust:
                            st.session_state.bust = True
                        
                        st.session_state.current_period += 1
                        if st.session_state.current_period >= 6 or bust:
                            st.session_state.game_over = True
                            st.session_state.final_value = final_val if not bust else 0
                        
                        st.rerun()
            
            # Results section
            if st.session_state.game_over or st.session_state.bust:
                st.subheader(TEXTS.get("results_title"))
                
                if st.session_state.bust:
                    st.error(TEXTS.get("bust_title"))
                    st.write(TEXTS.get("bust_text"))
                    st.metric(TEXTS.get("score_final"), "0 €")
                else:
                    final_value = st.session_state.final_value
                    st.success(TEXTS.get("success_title"))
                    st.write(TEXTS.get("success_text"))
                    st.metric(TEXTS.get("metric_final_size"), f"{final_value:,.0f} €".replace(",", " "))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(TEXTS.get("btn_replay"), use_container_width=True):
                        st.session_state.clear()
                        st.session_state.current_view = 'game'
                        st.rerun()
                with col_btn2:
                    if st.button(TEXTS.get("btn_analysis"), use_container_width=True):
                        st.session_state.current_view = 'analysis'
                        st.rerun()
        
        with col2:
            chart_container = st.container()
            
            show_allcash = False
            show_100stocks = False
            show_5050 = False
            show_target = False
            show_25stocks = False
            show_75stocks = False
            
            if st.session_state.game_over or st.session_state.bust:
                st.write(TEXTS.get("compare_title"))
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1:
                    show_allcash = st.checkbox(TEXTS.get("strategy_cash"), value=True)
                with col2:
                    show_25stocks = st.checkbox(TEXTS.get("strategy_25"))
                with col3:
                    show_5050 = st.checkbox(TEXTS.get("strategy_50"))
                with col4:
                    show_75stocks = st.checkbox(TEXTS.get("strategy_75"))
                with col5:
                    show_100stocks = st.checkbox(TEXTS.get("strategy_100"))
                with col6:
                    show_target = st.checkbox(TEXTS.get("strategy_target"))
                
            with chart_container:
                if len(st.session_state.all_yearly_values) > 1:
                    years = list(range(len(st.session_state.all_yearly_values)))
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=years,
                        y=st.session_state.all_yearly_values,
                        name=TEXTS.get("chart_your_portfolio"),
                        mode='lines',
                        line=dict(color='#1f77b4', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.2)'
                    ))
                    
                    num_periods = len(st.session_state.selected_blocks)

                    if st.session_state.game_over or st.session_state.bust:
                        
                        if show_allcash:
                            all_cash_values = [10000]

                            for year in range(1, len(st.session_state.all_yearly_values)):
                                if year == 15:
                                    all_cash_values.append(all_cash_values[-1] + 5000 - 85000)
                                else:
                                    all_cash_values.append(all_cash_values[-1] + 5000)
                            fig.add_trace(go.Scatter(
                                    x=years, y=all_cash_values, name=TEXTS.get("strategy_cash"),
                                mode='lines', line=dict(dash='dash', color='green')
                            ))
                        
                    if show_25stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [25] * num_periods
                        vals_25, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_25))), y=vals_25, name=TEXTS.get("strategy_25"),
                            mode='lines', line=dict(dash='dash', color='teal')
                        ))
                    
                    if show_100stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [100] * num_periods
                        vals_100, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_100))), y=vals_100, name=TEXTS.get("strategy_100"),
                            mode='lines', line=dict(dash='dash', color='purple')
                        ))
                    
                    if show_5050:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [50] * num_periods
                        vals_5050, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_5050))), y=vals_5050, name=TEXTS.get("strategy_50"),
                            mode='lines', line=dict(dash='dash', color='orange')
                        ))
                    
                    if show_75stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [75] * num_periods
                        vals_75, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_75))), y=vals_75, name=TEXTS.get("strategy_75"),
                            mode='lines', line=dict(dash='dash', color='brown')
                        ))
                    
                    if show_target:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        if num_periods >= 6: alloc_seq = [75, 50, 25, 100, 100, 100]
                        elif num_periods == 5: alloc_seq = [75, 50, 25, 100, 100]
                        elif num_periods == 4: alloc_seq = [75, 50, 25, 100]
                        elif num_periods == 3: alloc_seq = [75, 50, 25]
                        elif num_periods == 2: alloc_seq = [75, 50]
                        else: alloc_seq = [75]
                        vals_target, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_target))), y=vals_target, name=TEXTS.get("strategy_target"),
                            mode='lines', line=dict(dash='dash', color='red')
                        ))
                    
                    fig.add_vline(x=15, line_dash="dash", line_color="red")
                    
                    fig.add_trace(go.Scatter(
                        x=[15],
                        y=[85000],
                        mode='markers+text',
                        marker=dict(color='red', size=10),
                        text=[TEXTS.get("chart_farm_cost")],
                        textposition="top center",
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    fig.update_layout(
                        title=TEXTS.get("chart_main_title"),
                        xaxis_title=TEXTS.get("chart_x_axis"),
                        yaxis_title=TEXTS.get("chart_y_axis"),
                        hovermode='x unified',
                        height=380,
                        margin=dict(t=50, b=20, l=20, r=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        template='plotly_white'
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info(TEXTS.get("info_waiting_chart"))

    elif st.session_state.current_view == 'analysis':
        st.title(TEXTS.get("analysis_title"))
        
        if st.button(TEXTS.get("btn_back_casino")):
            st.session_state.current_view = 'game'
            st.rerun()
            
        st.divider()
        
        st.subheader(TEXTS.get("analysis_seq_title"))
        st.markdown(TEXTS.get("analysis_seq_text"))
        
        seq_cols = st.columns(6)
        for i in range(6):
            with seq_cols[i]:
                if i < len(st.session_state.selected_blocks):
                    block_idx = st.session_state.selected_blocks[i]
                    block = blocks[block_idx]
                    
                    cum_ret = [1.0]
                    for r in block['returns']:
                        cum_ret.append(cum_ret[-1] * (1 + r))
                    comp_ret = cum_ret[-1] - 1.0
                    
                    color = "green" if comp_ret >= 0 else "red"
                    
                    mini_fig = go.Figure(go.Scatter(
                        y=cum_ret, 
                        mode='lines',
                        line=dict(color=color, width=3)
                    ))
                    mini_fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        height=60,
                        xaxis=dict(visible=False, fixedrange=True),
                        yaxis=dict(visible=False, fixedrange=True),
                        showlegend=False,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    
                    st.markdown(f"<div style='text-align: center; font-size: 14px;'><b>{block['start_year']} - {block['end_year']}</b></div>", unsafe_allow_html=True)
                    st.plotly_chart(mini_fig, width="stretch", config={'displayModeBar': False})
                    st.markdown(f"<div style='text-align: center; color: {color}; font-size: 16px;'><b>{comp_ret*100:+.1f}%</b></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='text-align: center; font-size: 14px; color: gray;'><b>{TEXTS.get('analysis_round_missing').format(i+1)}</b></div>", unsafe_allow_html=True)
                    st.markdown("<div style='height: 60px; display: flex; align-items: center; justify-content: center; background-color: rgba(128,128,128,0.1); border-radius: 5px; margin: 10px 0; color: gray;'>?</div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader(TEXTS.get("analysis_prob_title"))
        st.markdown(TEXTS.get("analysis_prob_intro"))
        
        envelopes = compute_strategy_envelopes(blocks)
        
        strategy_options = {
            "100% Stocks": TEXTS.get("strategy_100"),
            "75% Stocks": TEXTS.get("strategy_75"),
            "50/50 Mix": TEXTS.get("strategy_50"),
            "25% Stocks": TEXTS.get("strategy_25"),
            "Pilotage du risque simple": TEXTS.get("strategy_target")
        }
        rev_strategy_options = {v: k for k, v in strategy_options.items()}
        
        selected_env_label = st.radio(
            TEXTS.get("analysis_select_strategy"),
            options=list(strategy_options.values()),
            horizontal=True
        )
        
        selected_env_strategy = rev_strategy_options[selected_env_label]
        env_data = envelopes[selected_env_strategy]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(TEXTS.get("metric_bust_rate"), f"{env_data['bust_rate']:.1f}%")
        with col_m2:
            st.metric(TEXTS.get("metric_median_final"), f"{env_data['median'][-1]:,.0f} €".replace(",", " "))
        with col_m3:
            st.metric(TEXTS.get("metric_max_final"), f"{env_data['max'][-1]:,.0f} €".replace(",", " "))
        
        fig_env = go.Figure()
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['min'],
            name=TEXTS.get("chart_worst_case"),
            mode='lines',
            line=dict(width=0),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['max'],
            name=TEXTS.get("chart_best_case"),
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)',
            mode='lines',
            line=dict(width=0),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['median'],
            name=TEXTS.get("chart_median"),
            mode='lines',
            line=dict(color='rgb(31, 119, 180)', width=3),
            showlegend=True
        ))
        
        strategies_allocs = {
            "100% Stocks": [100, 100, 100, 100, 100, 100],
            "75% Stocks": [75, 75, 75, 75, 75, 75],
            "50/50 Mix": [50, 50, 50, 50, 50, 50],
            "25% Stocks": [25, 25, 25, 25, 25, 25],
            "Pilotage du risque simple": [75, 50, 25, 100, 100, 100]
        }
        alloc_seq = strategies_allocs[selected_env_strategy]
        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
        vals_seq, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
        
        fig_env.add_trace(go.Scatter(
            x=list(range(len(vals_seq))),
            y=vals_seq,
            name=TEXTS.get("chart_your_sequence").format(selected_env_label),
            mode='lines',
            line=dict(color='black', width=2, dash='dash'),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(len(st.session_state.all_yearly_values))),
            y=st.session_state.all_yearly_values,
            name=TEXTS.get("chart_your_portfolio"),
            mode='lines',
            line=dict(color='#ff7f0e', width=3),
            showlegend=True
        ))
        
        fig_env.add_vline(x=15, line_dash="dash", line_color="red", opacity=0.5)
        
        fig_env.add_trace(go.Scatter(
            x=[15],
            y=[85000],
            mode='markers+text',
            marker=dict(color='red', size=10),
            text=[TEXTS.get("chart_farm_cost")],
            textposition="top center",
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig_env.update_layout(
            title=TEXTS.get("chart_env_title").format(selected_env_label),
            xaxis_title=TEXTS.get("chart_x_axis"),
            yaxis_title=TEXTS.get("chart_env_y_axis"),
            yaxis_range=[-50000, 500000],
            hovermode='x unified',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_env, width="stretch")
        
        st.info(TEXTS.get("analysis_prob_legend"))

if __name__ == "__main__":
    main()
