import streamlit as st
import pandas as pd
from  scipy.stats import binom
from functools import lru_cache
from random import randint
import altair as alt


# Memoized Fibonacci calculation
@lru_cache(None)
def fib(n):
    if n <= 3:
        return 1
    return fib(n - 2) + fib(n - 3)


# Session class and main simulation logic
class Session:
    def __init__(self, balance, unit_bet, max_bet, target_profit):
        self.start_balance = balance
        self.balance = balance
        self.unit_bet = unit_bet
        self.max_bet = 0 if max_bet is None else max_bet
        self.target_profit = target_profit
        self.current_bet = unit_bet
        self.fib_index = 1  # Start at Fibonacci index 1
        self.largest_fib_index = 1
        self.largest_multiplier = 1
        self.cycle = 1
        self.spins = 0
        self.wins = 0
        self.losses = 0

    def place_bet(self, won):
        # Sets the current fib index
        current_fib_index = self.fib_index
                
        # Ensures the largest fib index of the session is tracked
        if current_fib_index > self.largest_fib_index:
            self.largest_fib_index = current_fib_index
            self.largest_fib_multiplier = fib(current_fib_index)

        # Sets the current bet
        self.current_bet = self.unit_bet * fib(current_fib_index)

        # Current bet is always the minimum of current bet, balance, max bet (if applicable)
        if self.max_bet > 0:
            self.current_bet = min(self.current_bet, self.balance, self.max_bet)
        else:
            self.current_bet = min(self.current_bet, self.balance)

        # By placing the bet, balances reduces
        self.balance -= self.current_bet

        # On a win you get 3x your bet, the fib index resets to 1, and number of wins is incremented
        if won:
            self.balance += self.current_bet * 6
            self.fib_index = 1
            self.wins += 1
        
        # On a loss, the fib index and number of losses is incremented
        else:
            self.fib_index += 1
            self.losses += 1

        # Regardles of outcome, the number of spins increments.
        self.spins += 1
        
        return current_fib_index

    # Dynamic profit calculation
    @property
    def actual_profit(self):
        return self.balance - self.start_balance
    
    # End the session if profit exceeds target or balance is 0
    def reached_target(self):
        #return self.balance - self.start_balance >= self.target_profit or self.balance <= 0
        return self.actual_profit >= self.target_profit or self.balance <= 0


def spin_roulette():
    spin_result = randint(0, 36)
    return spin_result, 31 <= spin_result <= 36

def format_number(value):
    return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"

def cdf_message(value):
    if value <= 0.1: # 0-10% (10% band)
        return f'Very bad luck, there was a'
    elif value <= 0.25: # 10-25% (15% band)
        return f'Unlucky, there was a'
    elif value <= 0.5: # 25-50% (25% band)
        return f'Below average, there was a'
    elif value <= 0.75: # 50-75% (25% band)
        return f'Above average, there was only a'
    elif value <= 0.9: # 75-90% (15% band)
        return f'Fortunate, there was only a'
    else: # 90-100% (10% band)
        return f'Very lucky! There was only a'

# Streamlit interface
st.title("Fibonacci Dozens Betting Simulator")

# User inputs
start_balance = st.number_input("Starting Balance", 
                                min_value=0.01, 
                                step=0.01, 
                                value=1500.00,
                                format="%.2f",
                                placeholder="Enter a starting balance"
                                )
unit_bet = st.number_input("Unit Bet", 
                                min_value=0.01, 
                                step=0.01, 
                                value=5.00,
                                format="%.2f",
                                placeholder="Enter a unit bet"
                                )
max_bet = st.number_input("Maximum Bet (optional)",
                                min_value=0.0, 
                                step=0.01, 
                                value=None,
                                format="%.2f", 
                                placeholder="Leave blank for no max bet"
                                )
target_profit = st.number_input("Target Profit", 
                                min_value=0.0, 
                                step=0.01, 
                                value=100.00,
                                format="%.2f",
                                placeholder="Enter a profit target (£)"
                                )
max_spins = st.number_input("Maximum Spins (optional)", 
                                min_value=1, 
                                step=1, 
                                value=None, 
                                format="%d", 
                                placeholder="Leave blank for infinite spins"
                                )

if st.button("Run Simulation"):
    # Create a session object
    session = Session(start_balance, unit_bet, max_bet or None, target_profit)
    

    
    # Initialize an empty list to store results of each spin for this session
    results = []

    # Continue to make bets until max spins reached or profit target reached or run out of money
    while (max_spins is None or session.spins < max_spins) and not session.reached_target():
        pre_spin_balance = session.balance
        number, win = spin_roulette()
        
        current_fib_index = session.place_bet(win)
        fib_multiplier = fib(current_fib_index)
        post_spin_balance = session.balance

        results.append({
            'spin': session.spins,
            'balance_pre_spin': pre_spin_balance,
            'cycle': session.cycle,
            'fib_index': current_fib_index,
            'fib_multiplier': fib_multiplier,
            'current_bet': session.current_bet,
            'number': number,
            'won_or_lost': "Won" if win else "Lost",
            'winnings': post_spin_balance - pre_spin_balance + session.current_bet if win else 0,
            'balance_post_spin': post_spin_balance,
            'profit': post_spin_balance - session.start_balance,
            'profit_pct': (post_spin_balance / session.start_balance) - 1,
            'wins': session.wins,
            'losses': session.losses,
            'win_pct': session.wins / session.spins,
            'loss_pct': session.losses / session.spins
        })

        # Increment cycle number if still playing (and starting new cycle)
        session.cycle += 1 if (win and not session.reached_target()) else 0

    ########## Create dataframe of results ##########
    results_table = pd.DataFrame(results)

    ########## Formatted stats ##########
    stats_target_amount = format_number(session.target_profit)
    stats_target_pct = "{:.2%}".format(session.target_profit / session.start_balance)
    stats_target_units = format_number(session.target_profit / session.unit_bet)

    stats_result_amount = format_number(session.actual_profit)
    stats_result_pct = "{:.2%}".format(session.actual_profit / session.start_balance)
    stats_result_units = format_number(session.actual_profit / session.unit_bet)

    stats_total_spins = "{:,.0f}".format(session.spins)
    stats_wins = "{:,.0f}".format(session.wins)
    stats_win_pct = "{:.2%}".format(session.wins / session.spins)
    stats_cycles = "{:,.0f}".format(session.cycle)
    stats_losses = "{:,.0f}".format(session.losses)
    
    stats_fib_index = "{:,.0f}".format(session.largest_fib_index)
    stats_odds = "{:.2%}".format((31 / 37) ** session.largest_fib_index)
    
    if session.max_bet > 0:
        stats_largest_multiplier = "{:,.0f}".format(min(session.largest_fib_multiplier, session.max_bet / session.unit_bet))
        stats_largest_bet = format_number(min(session.largest_fib_multiplier * session.unit_bet, session.max_bet))
    else:
        stats_largest_multiplier = "{:,.0f}".format(session.largest_fib_multiplier)
        stats_largest_bet = format_number(session.largest_fib_multiplier * session.unit_bet)
    
    # Calculate the cumulative distribution function of this session.
    cdf = binom.cdf(session.wins, session.spins, 6/37)
    #stats_cdf = "{:.2%}".format(cdf)
    message = f'{cdf_message(cdf)} {"{:.2%}".format(1-cdf)} chance to have more wins than this.'

    ########## Create two columns (for session stats and line graph) ##########
    col1, col2 = st.columns([1, 1])

    ########## First column for session stats ##########
    with col1:
        # Display results
        st.subheader("Simulation Results")
        
        st.text(f"""
                Target: £{stats_target_amount} ({stats_target_pct}) ({stats_target_units} units)
                Result: £{stats_result_amount} ({stats_result_pct}) ({stats_result_units} units)
                
                Total Spins: {stats_total_spins} (Wins: {stats_wins} / Losses: {stats_losses})
                Cycles: {stats_cycles}
                Win Rate: {stats_win_pct}     (vs expected 16.21%)
                Likelihood: {message} 
                            
                Largest Bet: £{stats_largest_bet} (Index: {stats_fib_index} / Multipler: {stats_largest_multiplier}x)
                Odds on largest Fib Index: {stats_odds}
                """)
    
    ########## Second column for line graph ##########
    with col2:
        st.subheader("Profit Over Time")
        # Set 'spin' as the index to make the x-axis the spin number
        line_chart_data = results_table[['spin', 'profit']]

        # Create the main chart: a line with points (no config yet)
        main_chart = (
            alt.Chart(line_chart_data)
            .mark_line(point=True)  # line + points
            .encode(
                x=alt.X('spin:Q', title='Spin'),
                y=alt.Y('profit:Q', title='Profit')
            )
        )

        # Create a rule (horizontal line) at y=0 (no config yet)
        zero_line = (
            alt.Chart(pd.DataFrame({'y': [0]}))
            .mark_rule(color='white')
            .encode(y='y:Q')
        )

        # Layer the main chart with the zero line, then configure
        final_chart = (
            alt.layer(main_chart, zero_line)
            .properties(width=600, height=300)
            .configure_mark(color='white')       # Make line and points white
            .configure_view(strokeWidth=0)       # Remove border around chart
        )

        st.altair_chart(final_chart, use_container_width=True)
 
    ########## Spin by spin results ##########    
    st.subheader("Detailed Spin Results")
    #st.dataframe(results_table, hide_index=True, use_container_width=False)

    # Check to see if integers or floats should be used
    use_integer = True if session.start_balance % 1 == 0 and session.unit_bet % 1 == 0 else False
    
    currency_cols = ['balance_pre_spin', 'current_bet', 'balance_post_spin', 'winnings', 'profit']
    pct_cols = ['profit_pct', 'win_pct', 'loss_pct']
    
    currency_format = '£{:,.0f}' if use_integer else '£{:,.2f}'
    pct_format = '{:,.2%}'

    # Apply formatting to the DataFrame
    # Assuming results_table is already created as a pandas DataFrame
    styled_df = results_table.style.format({
        **{col: currency_format for col in currency_cols},  # Apply currency formatting to selected columns
        **{col: pct_format for col in pct_cols}  # Apply currency formatting to selected columns
    }) 
    
    st.write(styled_df)

# To Add:

# Wheel number colours
# Bold where Fib index = 1
# Alternate red and blue for cycles
# Winnings "" where nil
# Profit column heatmap

# Checkbox to switch between units
# Better way to handle cycle

