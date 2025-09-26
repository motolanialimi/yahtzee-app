import random
from collections import Counter
import streamlit as st

# ===============================
# Core game constants & helpers
# ===============================
CATEGORIES = [
    "Ones", "Twos", "Threes", "Fours", "Fives", "Sixes",
    "Three of a Kind", "Four of a Kind", "Full House",
    "Small Straight", "Large Straight", "Yahtzee", "Chance"
]
UPPER = {"Ones":1, "Twos":2, "Threes":3, "Fours":4, "Fives":5, "Sixes":6}

def roll_all():
    return [random.randint(1, 6) for _ in range(5)]

def roll_selected(dice, holds):
    return [d if i in holds else random.randint(1, 6) for i, d in enumerate(dice)]

def is_small_straight(dice):
    s = set(dice)
    return ({1,2,3,4} <= s) or ({2,3,4,5} <= s) or ({3,4,5,6} <= s)

def is_large_straight(dice):
    s = set(dice)
    return s == {1,2,3,4,5} or s == {2,3,4,5,6}

def score_upper(dice, face):
    return sum(d for d in dice if d == face)

def score_category(dice, category):
    from collections import Counter
    counts = Counter(dice)
    mx = max(counts.values())
    total = sum(dice)

    if category in UPPER:
        return score_upper(dice, UPPER[category])
    if category == "Three of a Kind":
        return total if mx >= 3 else 0
    if category == "Four of a Kind":
        return total if mx >= 4 else 0
    if category == "Full House":
        return 25 if sorted(counts.values()) == [2,3] else 0
    if category == "Small Straight":
        return 30 if is_small_straight(dice) else 0
    if category == "Large Straight":
        return 40 if is_large_straight(dice) else 0
    if category == "Yahtzee":
        return 50 if mx == 5 else 0
    if category == "Chance":
        return total
    return 0

def score_totals(card):
    upper_total = sum(v for k,v in card.items() if k in UPPER and v is not None)
    lower_total = sum(v for k,v in card.items() if k not in UPPER and v is not None)
    bonus = 35 if upper_total >= 63 else 0
    grand = upper_total + bonus + lower_total
    return upper_total, lower_total, bonus, grand

# ===============================
# State init/reset
# ===============================
def new_game():
    st.session_state.players = ["Player 1", "Player 2"]
    st.session_state.current = 0  # index of current player
    st.session_state.turns_used = {p: 0 for p in st.session_state.players}  # 0..13
    st.session_state.scorecards = {p: {cat: None for cat in CATEGORIES} for p in st.session_state.players}
    st.session_state.available = {p: CATEGORIES.copy() for p in st.session_state.players}

    st.session_state.dice = roll_all()
    st.session_state.holds = set()
    st.session_state.rolls_left = 3
    st.session_state.phase = "rolling"  # "rolling" | "scoring" | "done"

def ensure_state():
    if "players" not in st.session_state:
        new_game()

# ===============================
# UI helpers
# ===============================
def dice_button(label, key, on_click=None):
    return st.button(label, key=key, use_container_width=True, on_click=on_click)

def render_scoreboard():
    st.subheader("Scoreboard")
    cols = st.columns(2)
    for i, p in enumerate(st.session_state.players):
        with cols[i]:
            st.write(f"### {p}")
            upper_total, lower_total, bonus, grand = score_totals(st.session_state.scorecards[p])
            st.metric("Upper subtotal", upper_total)
            st.metric("Upper bonus", bonus)
            st.metric("Lower total", lower_total)
            st.metric("Grand Total", grand)

            # details table
            rows = [{"Category": cat, "Score": "-" if st.session_state.scorecards[p][cat] is None else st.session_state.scorecards[p][cat]} for cat in CATEGORIES]
            st.dataframe(rows, hide_index=True, use_container_width=True)

def switch_to_next_player():
    # advance to next player who still has turns remaining
    players = st.session_state.players
    next_idx = (st.session_state.current + 1) % len(players)

    # If both finished, mark done; else keep alternating
    if all(st.session_state.turns_used[p] >= 13 for p in players):
        st.session_state.phase = "done"
        return

    # choose next active player (if one finished early)
    # Loop up to len(players) times to find someone with turns left
    for _ in range(len(players)):
        if st.session_state.turns_used[players[next_idx]] < 13:
            st.session_state.current = next_idx
            break
        next_idx = (next_idx + 1) % len(players)

    # Start the new player's turn
    st.session_state.rolls_left = 3
    st.session_state.dice = roll_all()
    st.session_state.holds = set()
    st.session_state.phase = "rolling"

def finish_and_pass_turn(chosen_cat):
    # score current player
    p = st.session_state.players[st.session_state.current]
    pts = score_category(st.session_state.dice, chosen_cat)
    st.session_state.scorecards[p][chosen_cat] = pts
    st.session_state.available[p].remove(chosen_cat)
    st.session_state.turns_used[p] += 1

    # if this was player’s 13th turn and the other is also done -> game over
    if all(st.session_state.turns_used[x] >= 13 for x in st.session_state.players):
        st.session_state.phase = "done"
        return

    # pass to next player
    switch_to_next_player()

# ===============================
# Streamlit app
# ===============================
st.set_page_config(page_title="Yahtzee 2-Player", page_icon="🎲", layout="centered")
ensure_state()

st.title("🎲 Yahtzee — Two Players")
st.caption("Alternate turns. Each player gets 13 turns. Click a die to hold/unhold before rolling again.")

# Top controls
left, mid, right = st.columns([1,1,1])
with left:
    st.metric("Current Player", st.session_state.players[st.session_state.current])
with mid:
    p = st.session_state.players[st.session_state.current]
    st.metric("Turn (this player)", f"{st.session_state.turns_used[p]+1 if st.session_state.turns_used[p] < 13 else 13}/13")
with right:
    st.metric("Rolls left", st.session_state.rolls_left)

b1, b2 = st.columns([1,1])
with b1:
    if st.button("🆕 New Game", use_container_width=True):
        new_game()
        st.rerun()  # hard reset rerun
with b2:
    # "Refresh UI" just re-runs without clearing state
    if st.button("🔁 Refresh UI", use_container_width=True):
        st.rerun()

st.divider()

# Dice row
st.subheader("Your Dice")
dice_cols = st.columns(5)

def toggle_hold(i):
    if i in st.session_state.holds:
        st.session_state.holds.remove(i)
    else:
        st.session_state.holds.add(i)

for i, c in enumerate(dice_cols):
    with c:
        held = i in st.session_state.holds
        # Big button showing the die value; click toggles hold
        if st.button(f"{'🔒' if held else '⚪️'} {st.session_state.dice[i]}", key=f"die_{i}", use_container_width=True):
            toggle_hold(i)

# Roll / Score controls
roll_col, score_col = st.columns([1,1])

def do_roll():
    if st.session_state.rolls_left <= 0 or st.session_state.phase != "rolling":
        return
    st.session_state.rolls_left -= 1
    st.session_state.dice = roll_selected(st.session_state.dice, st.session_state.holds)
    if st.session_state.rolls_left == 0:
        st.session_state.phase = "scoring"

with roll_col:
    disabled = st.session_state.rolls_left <= 0 or st.session_state.phase != "rolling"
    st.button("🎲 Roll", type="primary", disabled=disabled, use_container_width=True, on_click=do_roll)

with score_col:
    def go_score():
        st.session_state.phase = "scoring"
    st.button("✅ Score this roll", disabled=(st.session_state.phase == "scoring"), use_container_width=True, on_click=go_score)

st.divider()

# Scoring pane for current player
if st.session_state.phase == "scoring":
    current_player = st.session_state.players[st.session_state.current]
    st.subheader(f"Pick a Category — {current_player}")
    avail = st.session_state.available[current_player]
    preview = {cat: score_category(st.session_state.dice, cat) for cat in avail}

    cat = st.selectbox(
        "Available categories:",
        options=sorted(avail),
        format_func=lambda x: f"{x}  — would score {preview[x]}",
        key="select_cat"
    )

    col_a, col_b = st.columns([1,3])
    with col_a:
        st.write(f"**Selected:** {cat}")
        st.write(f"**Score now:** {preview[cat]}")
        if st.button("💾 Save Score & Pass Turn", type="primary", use_container_width=True):
            finish_and_pass_turn(cat)
            st.rerun()
    with col_b:
        st.info("Tip: If no category fits well, you can ‘zero’ one by choosing it and saving (score will be 0).")

# Scoreboard for both players
render_scoreboard()

# Endgame banner
if st.session_state.phase == "done":
    # Compute winners
    totals = {}
    for p in st.session_state.players:
        _, _, _, grand = score_totals(st.session_state.scorecards[p])
        totals[p] = grand
    winner = max(totals, key=totals.get)
    # Check tie
    if list(totals.values()).count(totals[winner]) > 1:
        st.success(f"🏁 Game over! It's a tie at {totals[winner]} points.")
    else:
        st.success(f"🏁 Game over! **{winner}** wins with **{totals[winner]}** points.")
    st.info("Press **New Game** to start again, or **Refresh UI** if something looks out of sync.")
