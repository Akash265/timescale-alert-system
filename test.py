import random
from itertools import product
from tqdm import tqdm  # Import tqdm for progress bar

# Define parameter ranges
w_range = range(70, 96, 5)  # Winning chance (40% to 80%)
x_range = range(0, 30, 10)    # Increase on win (1% to 10%)
y_range = range(0, -50, -10)     # Increase on loss (1% to 5%)
p_range = range(100, 200, 50)  # Profit target ($100 to $1000)
l_range = range(10, 50, 10)  # Loss limit ($50 to $500)
b_range = range(1, 4, 1)     # Initial bet ($1 to $20)
n_range = range(10, 101, 10)  # Max bets (10 to 100)

# Simulation function
def simulate_betting(w, x, y, p, l, b, n, iterations=1000):
    total_profit = 0
    for _ in range(iterations):
        current_w = w
        current_bet = b
        profit = 0
        loss = 0
        bets_placed = 0
        while bets_placed < n and profit < p and loss < l:
            if random.randint(0, 100) <= current_w:
                profit += (100-current_w ) * x * current_bet/100
                current_w += x
                current_bet = b
            else:
                loss += current_bet
                current_w += y
                current_bet *= 2
            bets_placed += 1
        total_profit += profit - loss
    return total_profit / iterations  # Average profit per iteration

# Grid search to find the best combination
best_profit = -float('inf')
best_params = None

# Calculate total number of combinations for tqdm
total_combinations = (
    len(w_range) * len(x_range) * len(y_range) * len(p_range) * len(l_range) * len(b_range) * len(n_range)
)

# Iterate over all combinations of parameters with tqdm progress bar
for w, x, y, p, l, b, n in tqdm(product(w_range, x_range, y_range, p_range, l_range, b_range, n_range), total=total_combinations):
    avg_profit = simulate_betting(w, x, y, p, l, b, n)
    if avg_profit > best_profit:
        best_profit = avg_profit
        best_params = (w, x, y, p, l, b, n)

# Output the best combination
print("\nBest Combination:")
print(f"w={best_params[0]}, x={best_params[1]}, y={best_params[2]}, p={best_params[3]}, l={best_params[4]}, b={best_params[5]}, n={best_params[6]}")
print(f"Best Average Profit: {best_profit}")