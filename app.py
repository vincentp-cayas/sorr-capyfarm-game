import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Tuple
import random
import itertools

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Dompter la séquence des rendements. Et des capybaras.",
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
        st.subheader(" Les Règles du Casino")
        st.info("""
        • **Magot de départ** : 10 000 €
        • **Épargne annuelle** : 5 000 €/an
        • **L'objectif décisif** : Sortir 85 000 € à l'année 15.
        • **6 décisions** : Vous ajustez la voilure (actions/monétaire) tous les 5 ans.
        • **Le marché** : 5 années historiques tirées au sort (1995-2025). Pas de triche.
        • **Score** : Vos pépettes finales (0 si vous finissez sous les ponts).
        """)
    
    if st.session_state.current_view == 'intro':
        st.title("🦫 Le Jeu de l'Élevage de Capybaras")
        st.markdown("""
        Bienvenue dans la vraie vie de l'investisseur ! On vous a sûrement déjà parlé de la magie des intérêts composés. 
        Mais la Bourse, ce n'est pas un long fleuve tranquille : c'est un **grand 8**. 
        
        Découvrez par la pratique le fameux **Risque de Séquence des Rendements**.[1]
        
        **Votre Mission :**
        - Dompter la volatilité pour réunir 85 000 € dans 15 ans et acheter votre élevage de capybaras.
        - Faire grossir votre caillasse d'ici l'année 30 pour faire un don généreux à la Fondation Capybara.
        
        *L'astuce ? Vous ne pouvez pas prédire le marché. Mais vous pouvez ajuster vos voiles en choisissant votre niveau de risque à chaque manche.*
        
        ---
        <small>[1] En jargon, c'est le risque que la scoumoune frappe pile au moment où vous avez besoin de votre argent. Et ça, ça fait très mal.</small>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='text-align: center; font-size: 80px;'>🌾 🦫 🏡 💰</div>", unsafe_allow_html=True)
        st.write("")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("🎮 Prendre les commandes", width="stretch"):
                st.session_state.current_view = 'game'
                st.rerun()


    elif st.session_state.current_view == 'game':
        st.title("🦫 Le Jeu de l'Élevage de Capybaras")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if not st.session_state.game_over and not st.session_state.bust:
                # Current period info
                period_num = st.session_state.current_period + 1
                st.write(f"**Manche : {period_num}/6**")
                st.write(f"**Années : {period_num*5 - 4}-{period_num*5}**")
                
                # Portfolio value display
                current_portfolio = st.session_state.portfolio_values[-1] if st.session_state.portfolio_values else 10000
                st.metric("Valeur de votre magot", f"{current_portfolio:,.0f} €".replace(",", " "))
                
                allocation = st.slider(
                    "Dose d'actions en % (le moteur risqué)",
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=10,
                    help="0% = 100% Monétaire (le matelas), 100% = 100% Actions (le grand 8)"
                )
                
                if st.button("🎲 Voyons ce que les 5 prochaines années nous réservent", width="stretch"):
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
                st.subheader("📈 Résultats Finaux")
                
                if st.session_state.bust:
                    st.error("**FAILLITE ! Vous êtes lessivé. ❌**")
                    st.write("La machine à laver du marché vous a essoré au pire moment. Vous n'avez pas les fonds pour l'élevage de capybaras...")
                    st.metric("Score Final", "0 €")
                else:
                    final_value = st.session_state.final_value
                    st.success("**SUCCÈS ! Papy Capy est fier de vous. ✅**")
                    st.write("Vous avez survécu aux montagnes russes et accumulé un très beau magot !")
                    st.metric("Taille finale de la boule de neige", f"{final_value:,.0f} €".replace(",", " "))
                
                if st.button("🔄 Rejouer", width="stretch"):
                    st.session_state.clear()
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
                st.write("**Où vous situez-vous par rapport aux autres ?**")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    show_allcash = st.checkbox("100% Monétaire", value=True)
                    show_25stocks = st.checkbox("25% Actions")
                with col_b:
                    show_5050 = st.checkbox("50% Actions")
                    show_75stocks = st.checkbox("75% Actions")
                with col_c:
                    show_100stocks = st.checkbox("100% Actions")
                    show_target = st.checkbox("Pilotage du risque simple")
                
                st.write("")
                col_spacer, col_btn = st.columns([2, 1])
                with col_btn:
                    if st.button("📊 Les coulisses (Décortiquer)", width="stretch"):
                        st.session_state.current_view = 'analysis'
                        st.rerun()
            
            with chart_container:
                if len(st.session_state.all_yearly_values) > 1:
                    years = list(range(len(st.session_state.all_yearly_values)))
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=years,
                        y=st.session_state.all_yearly_values,
                        name="Votre Portefeuille",
                        mode='lines',
                        line=dict(color='#1f77b4', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.2)'
                    ))
                    
                    if st.session_state.game_over or st.session_state.bust:
                        num_periods = len(st.session_state.selected_blocks)
                        
                        if show_allcash:
                            all_cash_values = [10000]
                            for year in range(1, len(st.session_state.all_yearly_values)):
                                if year == 15:
                                    all_cash_values.append(all_cash_values[-1] + 5000 - 85000)
                                else:
                                    all_cash_values.append(all_cash_values[-1] + 5000)
                            fig.add_trace(go.Scatter(
                                x=years, y=all_cash_values, name="100% Monétaire",
                                mode='lines', line=dict(dash='dash', color='green')
                            ))
                        
                    if show_25stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [25] * num_periods
                        vals_25, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_25))), y=vals_25, name="25% Actions",
                            mode='lines', line=dict(dash='dash', color='teal')
                        ))
                    
                    if show_100stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [100] * num_periods
                        vals_100, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_100))), y=vals_100, name="100% Actions",
                            mode='lines', line=dict(dash='dash', color='purple')
                        ))
                    
                    if show_5050:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [50] * num_periods
                        vals_5050, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_5050))), y=vals_5050, name="50% Actions",
                            mode='lines', line=dict(dash='dash', color='orange')
                        ))
                    
                    if show_75stocks:
                        blocks_seq = [blocks[i]['returns'] for i in st.session_state.selected_blocks]
                        alloc_seq = [75] * num_periods
                        vals_75, _, _, _, _ = simulator.simulate_full_game(alloc_seq, blocks_seq)
                        fig.add_trace(go.Scatter(
                            x=list(range(len(vals_75))), y=vals_75, name="75% Actions",
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
                            x=list(range(len(vals_target))), y=vals_target, name="Pilotage du risque simple",
                            mode='lines', line=dict(dash='dash', color='red')
                        ))
                    
                    fig.add_vline(x=15, line_dash="dash", line_color="red", 
                                 annotation_text="Achat !", annotation_position="top right")
                    
                    fig.add_hline(y=85000, line_dash="dash", line_color="orange",
                                 annotation_text="Cible (85 k€)", annotation_position="right")
                    
                    fig.update_layout(
                        title="Votre parcours de zinzins sur 30 Ans",
                        xaxis_title="Année",
                        yaxis_title="Pépettes accumulées (€)",
                        hovermode='x unified',
                        height=500,
                        template='plotly_white'
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("📌 Le grand 8 se dessinera ici au fur et à mesure de vos lancers.")

    elif st.session_state.current_view == 'analysis':
        st.title("📊 Les coulisses : on décortique tout")
        
        if st.button("⬅️ Retour au casino"):
            st.session_state.current_view = 'game'
            st.rerun()
            
        st.divider()
        
        st.subheader("Le hasard de la pioche (Votre Séquence)")
        st.markdown("""
        **Explication :** En investissement, la destination compte, mais le chemin aussi. 
        Un krach boursier quand on accumule ses billes, c'est les soldes. Mais un krach juste avant de devoir décaisser 85 000 € pour vos capybaras (les séquences qui font transpirer), c'est la tuile absolue. 
        C’est ça, le risque de séquence : être forcé de vendre ses actifs dans le creux de la vague. Une fois ce cap périlleux passé, le but est de maximiser la taille de la boule de neige, puisqu'on ne risque plus la ruine.
        """)
        
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
                    st.markdown(f"<div style='text-align: center; font-size: 14px; color: gray;'><b>Manche {i+1}</b></div>", unsafe_allow_html=True)
                    st.markdown("<div style='height: 60px; display: flex; align-items: center; justify-content: center; background-color: rgba(128,128,128,0.1); border-radius: 5px; margin: 10px 0; color: gray;'>?</div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🌍 L'éventail des possibles (Vos probabilités)")
        st.markdown("""
        **Comment lire ce graphique :** 
        L'image des intérêts composés qui grimpent de façon lisse est une illusion. Dans la vraie vie, vos rendements se situent dans un éventail de probabilités. Ce graphique montre les 720 trajectoires possibles de notre jeu. 
        - La **zone bleue** représente l'éventail des résultats selon votre chance. La ligne du bas, c'est le championnat de la scoumoune. Celle du haut, c'est l'hyper-chance.
        - La **ligne bleue épaisse** est la médiane (ce qui se passe au milieu).
        - La **ligne noire en pointillés** est ce qu'aurait donné cette stratégie avec *votre* tirage (votre veine ou votre scoumoune exacte).
        - La **ligne orange**, c’est *votre* véritable parcours de zinzins.
        """)
        
        envelopes = compute_strategy_envelopes(blocks)
        
        strategy_options = {
            "100% Stocks": "100% Actions",
            "75% Stocks": "75% Actions",
            "50/50 Mix": "50% Actions",
            "25% Stocks": "25% Actions",
            "Pilotage du risque simple": "Pilotage du risque simple"
        }
        rev_strategy_options = {v: k for k, v in strategy_options.items()}
        
        selected_env_label = st.radio(
            "Sélectionnez une stratégie pour voir son enveloppe :",
            options=list(strategy_options.values()),
            horizontal=True
        )
        
        selected_env_strategy = rev_strategy_options[selected_env_label]
        env_data = envelopes[selected_env_strategy]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Taux de Faillite", f"{env_data['bust_rate']:.1f}%")
        with col_m2:
            st.metric("Médiane finale", f"{env_data['median'][-1]:,.0f} €".replace(",", " "))
        with col_m3:
            st.metric("Max final", f"{env_data['max'][-1]:,.0f} €".replace(",", " "))
        
        fig_env = go.Figure()
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['min'],
            name="Pire Cas",
            mode='lines',
            line=dict(width=0),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['max'],
            name="Meilleur Cas",
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)',
            mode='lines',
            line=dict(width=0),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(31)),
            y=env_data['median'],
            name="Médiane",
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
            name=f"{selected_env_label} (Votre Séquence)",
            mode='lines',
            line=dict(color='black', width=2, dash='dash'),
            showlegend=True
        ))
        
        fig_env.add_trace(go.Scatter(
            x=list(range(len(st.session_state.all_yearly_values))),
            y=st.session_state.all_yearly_values,
            name="Votre Portefeuille",
            mode='lines',
            line=dict(color='#ff7f0e', width=3),
            showlegend=True
        ))
        
        fig_env.add_vline(x=15, line_dash="dash", line_color="red", opacity=0.5, annotation_text="Achat")
        fig_env.add_hline(y=85000, line_dash="dash", line_color="orange", opacity=0.5, annotation_text="Cible")
        
        fig_env.update_layout(
            title=f"Éventail des résultats pour la stratégie : {selected_env_label}",
            xaxis_title="Année",
            yaxis_title="Caillasse en €",
            yaxis_range=[-50000, 500000],
            hovermode='x unified',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_env, width="stretch")
        
if __name__ == "__main__":
    main()
