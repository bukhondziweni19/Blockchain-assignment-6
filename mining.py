"""
mining.py
Assignment 6: Mining and Proof-of-Work Lab
Blockchain module (BLCH9X2), Master of Financial Engineering, University of Johannesburg

WHAT THIS PROGRAM DOES
    Part A
        (a) Implements a proof-of-work miner that searches for a nonce meeting a numeric
            difficulty target: the block hash, read as a number, must fall at or below
            MAX_TARGET divided by the difficulty.
        (b) Runs a parameter study across five difficulty levels, reporting attempts and
            wall-clock time for each, and writes the timing table to timing_table.txt.
        (c) Pays a block reward to a miner address through a coinbase transaction, and
            shows that redirecting that reward after mining invalidates the block.
    Part B
        Implements simplified difficulty retargeting and demonstrates it twice: correcting
        a difficulty that was wrong to begin with, and adapting after the hash rate falls.

A NOTE ON THE TIMINGS
    Attempt counts, nonces and hashes are deterministic. Timestamps are fixed constants
    rather than clock readings and every nonce search starts at zero, so those values
    reproduce on any machine. Wall-clock seconds and hash rates do not: they are measured
    on whichever machine runs this file, and will differ from any figures quoted elsewhere.

HOW TO RUN
    python mining.py                      the full demonstration, roughly one minute
    python mining.py > console_log.txt    the same output saved to a file

    The program also writes timing_table.txt containing the Part A (b) timing table.
"""

import hashlib          # hashlib gives us SHA-256 (Secure Hash Algorithm 256-bit), the fingerprint function
import json             # json turns Python dictionaries into text in a controlled, repeatable way
import time             # time lets us measure wall-clock seconds, which the parameter study needs
import statistics       # statistics gives us mean and median for summarising repeated mining trials

# ===========================================================================
# CONFIGURATION
# ===========================================================================

MAX_TARGET = 2 ** 256 - 1        # the largest value a SHA-256 hash can take, which is difficulty 1 where every hash wins
BASE_TIMESTAMP = 1757894400      # a fixed Unix timestamp (15 September 2026, 00:00:00 UTC) used instead of the live clock

DIFFICULTY_LEVELS = [1024, 4096, 16384, 65536, 262144]   # the difficulties studied in Part A (b), each 4x the previous
TRIALS_PER_LEVEL = 5                                     # independent blocks mined at each difficulty; raise for tighter averages

BLOCK_SUBSIDY = 50.00            # units created by the rules and paid to whoever finds a block
FEE_PER_PAYMENT = 0.25           # a flat charge taken from each ordinary payment and paid to the miner
MINER_ADDRESS = "MINER-BK-01"    # the address credited when this miner finds a block

EPOCH_BLOCKS = 5                 # how many blocks are mined before the difficulty is reconsidered
TARGET_BLOCK_SECONDS = 0.20      # how long each block is meant to take on the machine running this
MAX_ADJUSTMENT_FACTOR = 4        # the difficulty may not move by more than this in one step, as in Bitcoin

# ===========================================================================
# TARGET ARITHMETIC AND HASHING
# ===========================================================================

def canonical_json(payload: dict) -> str:
    """Turn a dictionary into one single agreed text string, so hashing is repeatable."""
    # sort_keys=True   : fields always written in alphabetical order, so field order cannot change the hash
    # separators=(...) : no optional spaces, so spacing cannot change the hash
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    """Return the SHA-256 fingerprint of a piece of text, written as 64 hexadecimal characters."""
    encoded_text = text.encode("utf-8")                # convert the text into raw bytes, because hashing works on bytes
    return hashlib.sha256(encoded_text).hexdigest()    # hash those bytes and return readable hexadecimal


def target_for_difficulty(difficulty: int) -> int:
    """Convert a difficulty number into the ceiling a winning hash must fall below."""
    return MAX_TARGET // difficulty                    # integer division, so difficulty 256 gives a target 256 times smaller


def hash_to_number(hash_hex: str) -> int:
    """Read a 64 character hash as the very large whole number it actually is."""
    return int(hash_hex, 16)                           # base 16 because the hash is written in hexadecimal


def meets_target(hash_hex: str, target: int) -> bool:
    """Return True when this hash counts as a winning one, meaning it falls at or below the target."""
    return hash_to_number(hash_hex) <= target          # the single test that decides whether mining stops

# ===========================================================================
# BLOCK HEADERS AND THE MINER
# ===========================================================================

def build_header(index: int, previous_hash: str, transactions: list, difficulty: int,
                 timestamp: int = BASE_TIMESTAMP, nonce: int = 0) -> dict:
    """Assemble the fields a miner hashes over, with the nonce left as the field to be searched."""
    return {                                  # a dictionary holding everything the block commits to
        "index": index,                       # the position this block would occupy in a chain
        "previous_hash": previous_hash,       # the hash of the block before it, which links a chain together
        "transactions": transactions,         # the payments this block carries, including the miner's reward
        "difficulty": difficulty,             # committing to the difficulty stops a miner claiming easy work was hard
        "timestamp": timestamp,               # when the block was made, fixed here so nonces reproduce on any machine
        "nonce": nonce,                       # the only field the miner is free to change
    }


def header_hash(header: dict) -> str:
    """Fingerprint a block header as it currently stands."""
    return sha256_hex(canonical_json(header))          # one agreed text form, then SHA-256 over it


def mine(header: dict, difficulty: int) -> dict:
    """Search nonce values until the block hash meets the target, and measure the effort that took."""
    target = target_for_difficulty(difficulty)   # convert the difficulty into the ceiling the hash must fall below
    working_header = dict(header)                # copy the header so the caller's dictionary is not modified
    working_header["difficulty"] = difficulty    # make sure the header commits to the difficulty actually being mined
    attempts = 0                                 # counts every hash computed during this search
    nonce = 0                                    # the search always begins at zero, which keeps the nonce reproducible

    start_time = time.perf_counter()             # perf_counter is the clock meant for timing intervals

    while True:                                  # keep guessing until a winning hash appears
        working_header["nonce"] = nonce          # write the current guess into the header
        candidate_hash = header_hash(working_header)   # fingerprint the header with that guess in place
        attempts += 1                            # that was one more hash computed
        if meets_target(candidate_hash, target): # does this hash fall at or below the target?
            break                                # yes, so the block is mined and the search stops
        nonce += 1                               # no, so try the next nonce

    elapsed_seconds = time.perf_counter() - start_time    # wall-clock time the search took on this machine

    return {                                                              # everything the studies below need
        "nonce": nonce,                                                   # the winning nonce
        "hash": candidate_hash,                                           # the winning hash
        "attempts": attempts,                                             # how many hashes were computed
        "seconds": elapsed_seconds,                                       # how long that took in wall-clock seconds
        "hash_rate": attempts / elapsed_seconds if elapsed_seconds else 0, # hashes per second on this machine
        "header": working_header,                                         # the finished header, nonce included
    }


def mine_at_rate(header: dict, difficulty: int, extra_work: int = 0) -> dict:
    """Mine a block while optionally doing extra throwaway work per attempt, to imitate a slower miner."""
    target = target_for_difficulty(difficulty)       # the ceiling a winning hash must fall below
    working_header = dict(header)                    # copy the header so the caller's dictionary is untouched
    working_header["difficulty"] = difficulty        # commit to the difficulty actually being mined
    attempts = 0                                     # counts only real attempts, not the throwaway work
    nonce = 0                                        # the search begins at zero as always

    start_time = time.perf_counter()                 # clock reading before the search starts

    while True:                                                  # keep guessing until a winning hash appears
        working_header["nonce"] = nonce                          # write the current guess into the header
        candidate_hash = header_hash(working_header)             # fingerprint the header with that guess
        attempts += 1                                            # that was one real attempt
        for _ in range(extra_work):                              # burn processor time to imitate slower hardware
            header_hash(working_header)                          # one unit of extra work costs the same as one real attempt,
            # so extra_work=1 roughly halves the effective rate. The result is discarded: only the time spent matters.
        if meets_target(candidate_hash, target):                 # does the hash fall at or below the target?
            break                                                # yes, the block is mined
        nonce += 1                                               # no, try the next nonce

    elapsed_seconds = time.perf_counter() - start_time           # wall-clock time the search really took
    return {                                                     # the same shape of result as mine()
        "nonce": nonce,                                          # the winning nonce
        "hash": candidate_hash,                                  # the winning hash
        "attempts": attempts,                                    # real attempts, excluding throwaway work
        "seconds": elapsed_seconds,                              # measured wall-clock seconds
    }

# ===========================================================================
# TRANSACTIONS AND THE BLOCK REWARD
# ===========================================================================

def make_payment(sender: str, receiver: str, amount: float) -> dict:
    """Build one ordinary payment, which pays a flat fee to whichever miner includes it."""
    return {                                  # a dictionary holding the fields of one payment
        "type": "payment",                    # marks this as an ordinary transfer rather than a reward
        "sender": sender,                     # who is paying
        "receiver": receiver,                 # who is being paid
        "amount": round(float(amount), 2),    # the value, rounded to 2 decimals so cents stay exact
        "fee": FEE_PER_PAYMENT,               # what the sender pays the miner for including this payment
    }


def make_coinbase(miner_address: str, block_index: int, total_fees: float) -> dict:
    """Build the special first transaction that pays the miner for finding this block."""
    return {                                            # the coinbase has no sender: these units are newly created
        "type": "coinbase",                             # marks this as the reward rather than a transfer
        "receiver": miner_address,                      # the address being paid
        "subsidy": BLOCK_SUBSIDY,                       # the fixed amount the rules create
        "fees": round(total_fees, 2),                   # everything collected from the payments in this block
        "amount": round(BLOCK_SUBSIDY + total_fees, 2), # what the miner actually receives in total
        "block": block_index,                           # naming the block stops the same coinbase being reused elsewhere
    }


def mine_block_with_reward(index: int, previous_hash: str, payments: list,
                           difficulty: int, miner_address: str) -> dict:
    """Assemble a block with its coinbase in first place, mine it, and hand back the finished block."""
    total_fees = sum(payment["fee"] for payment in payments)          # add up the fees the payments will pay
    coinbase = make_coinbase(miner_address, index, total_fees)        # build the reward transaction
    transactions = [coinbase] + payments                             # the coinbase always goes first, as in Bitcoin

    header = build_header(                                           # assemble the header the miner will search over
        index=index,                                                 # this block's position
        previous_hash=previous_hash,                                 # the hash of the block before it
        transactions=transactions,                                   # the coinbase and the payments together
        difficulty=difficulty,                                       # the difficulty being mined at
    )
    result = mine(header, difficulty)                                # run the nonce search and measure it
    result["reward"] = coinbase["amount"]                            # remember what the miner earned from this block
    result["miner"] = miner_address                                  # and who earned it
    return result                                                    # the mining result, with the finished header inside


def apply_block_to_balances(header: dict, balances: dict):
    """Credit the miner and move the payments, updating the running ledger of who holds what."""
    for transaction in header["transactions"]:                                   # walk every transaction in the block
        if transaction["type"] == "coinbase":                                    # the reward transaction creates new units
            balances[transaction["receiver"]] = balances.get(transaction["receiver"], 0) + transaction["amount"]  # credit the miner
        else:                                                                    # an ordinary payment moves existing units
            total_cost = transaction["amount"] + transaction["fee"]              # the sender pays the amount plus the fee
            balances[transaction["sender"]] = balances.get(transaction["sender"], 0) - total_cost      # debit the sender
            balances[transaction["receiver"]] = balances.get(transaction["receiver"], 0) + transaction["amount"]  # credit the receiver
            # the fee is not credited here, because it was already included in the coinbase amount above

# ===========================================================================
# DIFFICULTY RETARGETING
# ===========================================================================

def retarget(old_difficulty: int, actual_seconds: float, expected_seconds: float) -> int:
    """Work out the difficulty for the next epoch from how long the last one actually took."""
    ratio = expected_seconds / actual_seconds        # above 1 means blocks came too fast, so difficulty must rise
    if ratio > MAX_ADJUSTMENT_FACTOR:                # refuse to raise difficulty by more than the clamp allows
        ratio = MAX_ADJUSTMENT_FACTOR                # cap the increase
    if ratio < 1 / MAX_ADJUSTMENT_FACTOR:            # refuse to lower it by more than the clamp allows either
        ratio = 1 / MAX_ADJUSTMENT_FACTOR            # cap the decrease
    new_difficulty = int(old_difficulty * ratio)     # apply the adjustment, rounding down to a whole number
    return max(1, new_difficulty)                    # never allow difficulty to fall below 1, which is no work at all


def mine_epoch_at_rate(start_index: int, difficulty: int, extra_work: int = 0) -> dict:
    """Mine one epoch at a given difficulty and a given handicap, and measure the whole epoch."""
    attempts_total = 0                                           # every real attempt made during this epoch
    epoch_start = time.perf_counter()                            # clock reading before the first block
    for offset in range(EPOCH_BLOCKS):                           # mine the blocks of the epoch in turn
        block_header = build_header(                             # each block gets its own header
            index=start_index + offset,                          # varying the index keeps the searches independent
            previous_hash="0" * 64,                              # a fixed placeholder parent, since this study is about timing
            transactions=[make_coinbase(MINER_ADDRESS, start_index + offset, 0.0)],  # just the reward, no payments
            difficulty=difficulty,                               # the difficulty for this epoch
        )
        block_result = mine_at_rate(block_header, difficulty, extra_work)  # mine it with the handicap applied
        attempts_total += block_result["attempts"]               # add its attempts to the epoch total
    epoch_seconds = time.perf_counter() - epoch_start            # wall-clock time for the whole epoch
    return {                                                                  # what the retargeting decision needs
        "attempts": attempts_total,                                           # real attempts across the epoch
        "seconds": epoch_seconds,                                             # wall-clock seconds the epoch took
        "seconds_per_block": epoch_seconds / EPOCH_BLOCKS,                    # the figure being steered to the target
        "hash_rate": attempts_total / epoch_seconds,                          # the effective rate, handicap included
    }

# ===========================================================================
# PART A (a): THE RULE THIS LAB DEFINES
# ===========================================================================

def show_target_arithmetic():
    """Print the relationship between difficulty, target and expected attempts."""
    print("PART A (a): THE DIFFICULTY TARGET")                                   # heading for this section
    print("=" * 78)                                                              # heavy divider line
    print("Rule: a block is mined when its hash, read as a number, is at or below")  # the rule in words
    print("MAX_TARGET divided by the difficulty. This is a numeric target, not a")   # the form chosen
    print("count of leading zeros.")                                                 # and what it is not
    print()                                                                          # blank line for readability

    print(f"{'Difficulty':<14}{'Target (first 20 hex characters)':<36}{'Expected attempts'}")  # table header
    print("-" * 78)                                                                            # divider
    for difficulty in [1, 16, 256, 65536, 1048576]:                              # five settings, each 16x the last
        target_as_hex = f"{target_for_difficulty(difficulty):064x}"               # write the target as 64 hex characters
        print(f"{difficulty:<14,}{target_as_hex[:20]:<36}{difficulty:,}")         # expected attempts equals the difficulty
    print("-" * 78)                                                               # divider under the table
    print("Expected attempts equals the difficulty because a hash is equally likely to")  # why the third column holds
    print("land anywhere in the range, so it falls below MAX_TARGET / d once in d tries.")  # the probability argument
    print()                                                                                 # blank line for readability


def mine_one_block():
    """Mine a single block and verify it, showing that work is costly to produce and cheap to check."""
    print("PART A (a): MINING ONE BLOCK")                                        # heading for this section
    print("=" * 78)                                                              # heavy divider line

    difficulty = 65536                                                           # difficulty 65,536, equal to four leading zeros
    header = build_header(                                                       # build a header to mine
        index=1,                                                                 # block number 1
        previous_hash="0" * 64,                                                  # 64 zeros, meaning there is no earlier block
        transactions=[{"sender": "BK", "receiver": "Thandi", "amount": 250.00}],  # one payment, for something to commit to
        difficulty=difficulty,                                                   # the difficulty being mined at
    )
    result = mine(header, difficulty)                                            # run the search and measure it

    print(f"Difficulty        : {difficulty:,}")                                 # the difficulty setting used
    print(f"Winning nonce     : {result['nonce']:,}")                            # the nonce the search landed on
    print(f"Winning hash      : {result['hash']}")                               # the hash that nonce produced
    print(f"Attempts needed   : {result['attempts']:,}")                         # how many hashes were computed
    print(f"Expected attempts : {difficulty:,}")                                 # what theory predicts on average
    print(f"Wall-clock time   : {result['seconds']:.3f} seconds")                # measured on this machine
    print(f"Hash rate         : {result['hash_rate']:,.0f} hashes per second")   # the speed this machine achieved
    print(f"  Hash meets the target          : {meets_target(result['hash'], target_for_difficulty(difficulty))}")  # must be True
    print(f"  Re-hashing reproduces the hash : {header_hash(result['header']) == result['hash']}")  # verification is one hash
    print()                                                                      # blank line for readability

# ===========================================================================
# PART A (b): THE PARAMETER STUDY
# ===========================================================================

def parameter_study() -> list:
    """Mine repeated blocks at several difficulties and report attempts and wall-clock time."""
    print("PART A (b): PARAMETER STUDY")                                             # heading for this section
    print("=" * 78)                                                                  # heavy divider line
    print(f"Difficulty levels : {', '.join(f'{d:,}' for d in DIFFICULTY_LEVELS)}")    # the settings being measured
    print(f"Trials per level  : {TRIALS_PER_LEVEL}")                                 # how many samples each figure rests on
    print("Every number below is measured on the machine running this program.")     # make the provenance explicit
    print()                                                                          # blank line for readability

    study_results = []                                       # collects one summary record per difficulty level

    for difficulty in DIFFICULTY_LEVELS:                     # work through the levels from easiest to hardest
        attempts_per_trial = []                              # every trial's attempt count at this difficulty
        seconds_per_trial = []                               # every trial's wall-clock time at this difficulty

        for trial_number in range(1, TRIALS_PER_LEVEL + 1):  # run the trials one after another
            trial_header = build_header(                     # build a header unique to this trial
                index=trial_number,                          # varying the index makes each trial independent
                previous_hash="0" * 64,                      # a fixed placeholder parent hash across all trials
                transactions=[{"note": f"parameter study trial {trial_number}"}],  # a marker record as block content
                difficulty=difficulty,                       # the difficulty being measured
            )
            trial_result = mine(trial_header, difficulty)    # mine it and measure the effort
            attempts_per_trial.append(trial_result["attempts"])   # record how many hashes this trial needed
            seconds_per_trial.append(trial_result["seconds"])     # record how long this trial took

        total_attempts = sum(attempts_per_trial)                              # all hashes computed at this difficulty
        total_seconds = sum(seconds_per_trial)                                # all time spent at this difficulty
        study_results.append({                                                # store the summary for the tables
            "difficulty": difficulty,                                         # the difficulty this record describes
            "attempts_list": attempts_per_trial,                              # the individual trial results
            "mean_attempts": statistics.mean(attempts_per_trial),             # average hashes needed
            "median_attempts": statistics.median(attempts_per_trial),         # the middle value
            "mean_seconds": statistics.mean(seconds_per_trial),               # average wall-clock time per block
            "total_attempts": total_attempts,                                 # total hashes at this difficulty
            "total_seconds": total_seconds,                                   # total time at this difficulty
            "hash_rate": total_attempts / total_seconds,                      # measured speed, hashes per second
        })
        print(f"  Difficulty {difficulty:>9,} done: "                          # progress line so the wait is not silent
              f"{total_attempts:>10,} hashes in {total_seconds:6.2f} seconds")  # what this level cost in total

    print()                                                                   # blank line for readability
    print("ATTEMPTS PER TRIAL")                                               # heading for the detail table
    print("-" * 78)                                                           # divider line
    trial_columns = "".join(f"Trial {n:<7}" for n in range(1, TRIALS_PER_LEVEL + 1))  # build the column headings
    print(f"{'Difficulty':<13}{trial_columns}")                               # table header
    print("-" * 78)                                                           # divider under the header
    for record in study_results:                                              # one row per difficulty level
        trial_cells = "".join(f"{a:<13,}" for a in record["attempts_list"])    # each trial's attempt count
        print(f"{record['difficulty']:<13,}{trial_cells}")                     # print the row
    print("-" * 78)                                                            # divider under the table
    print("The spread within a row is the point: mining is a random search, so single")  # why the spread matters
    print("runs scatter widely around the average.")                                     # and why one run proves little
    print()                                                                              # blank line for readability

    return study_results                                     # hand the records back so the table can be formatted


def format_timing_table(study_results: list) -> str:
    """Build the Part A (b) timing table as text, so it can be both printed and saved."""
    lines = []                                                                              # collects the lines of the table
    lines.append("TIMING TABLE (Part A (b))")                                               # title line
    lines.append("Measured on the machine that ran mining.py. Attempts are deterministic;")  # provenance note
    lines.append("wall-clock seconds and hash rates are not.")                               # what varies between machines
    lines.append("=" * 78)                                                                   # heavy divider
    lines.append(f"{'Difficulty':<12}{'Expected':<12}{'Mean':<12}{'Median':<12}{'Mean secs':<12}{'Hashes/sec'}")  # header
    lines.append("-" * 78)                                                                   # divider under the header
    for record in study_results:                                                             # one row per difficulty
        lines.append(f"{record['difficulty']:<12,}"                                          # the difficulty setting
                     f"{record['difficulty']:<12,}"                                          # expected attempts
                     f"{record['mean_attempts']:<12,.0f}"                                    # measured mean attempts
                     f"{record['median_attempts']:<12,.0f}"                                  # measured median attempts
                     f"{record['mean_seconds']:<12.3f}"                                      # measured mean seconds per block
                     f"{record['hash_rate']:,.0f}")                                          # measured hash rate
    lines.append("-" * 78)                                                                   # divider under the table

    overall_attempts = sum(r["total_attempts"] for r in study_results)                       # every hash in the study
    overall_seconds = sum(r["total_seconds"] for r in study_results)                         # every second in the study
    lines.append(f"Whole study: {overall_attempts:,} hashes in {overall_seconds:.2f} seconds, "  # the headline totals
                 f"{overall_attempts / overall_seconds:,.0f} hashes per second overall")        # and the overall rate

    slowest_rate = min(r["hash_rate"] for r in study_results)          # the lowest rate measured
    fastest_rate = max(r["hash_rate"] for r in study_results)          # the highest rate measured
    rate_spread = (fastest_rate / slowest_rate - 1) * 100              # how much the two differ, as a percentage
    lines.append(f"Hash rate ranged from {slowest_rate:,.0f} to {fastest_rate:,.0f} per second, "  # the measured spread
                 f"a difference of {rate_spread:.0f} percent.")                                   # stated, not assumed
    if rate_spread < 15:                                                                          # a narrow spread
        lines.append("Narrow enough to treat as constant, confirming that difficulty alone")      # what that means
        lines.append("changed between the levels.")                                               # the consistency check
    else:                                                                                         # a wide spread
        lines.append("Wide, and rising with difficulty rather than varying at random, which")     # describe the pattern
        lines.append("points at processor frequency scaling: the easiest levels finish before")   # the likely cause
        lines.append("the processor has ramped up from its idle clock speed. Re-running on a")    # what to do about it
        lines.append("warm machine should narrow it.")                                            # and the expected effect
    return "\n".join(lines)                                                                       # one block of text

# ===========================================================================
# PART A (c): THE BLOCK REWARD
# ===========================================================================

def block_reward_demonstration():
    """Mine three blocks, credit the miner, then try to redirect one reward after the fact."""
    print("PART A (c): THE BLOCK REWARD")                                        # heading for this section
    print("=" * 78)                                                              # heavy divider line
    print(f"Subsidy per block : {BLOCK_SUBSIDY:.2f} units")                      # the fixed reward the rules create
    print(f"Fee per payment   : {FEE_PER_PAYMENT:.2f} units")                    # what each payment contributes
    print(f"Miner address     : {MINER_ADDRESS}")                                # who gets paid in this run
    print()                                                                      # blank line for readability

    difficulty = 16384                                       # a modest difficulty so this section runs quickly
    balances = {}                                            # the running ledger, empty before the first block
    previous_hash = "0" * 64                                 # the first block has no parent
    mined_blocks = []                                        # collects each finished block

    blocks_to_mine = [                                                               # the payments each block carries
        [make_payment("BK", "Thandi", 1500.00), make_payment("Sipho", "BK", 320.50)],   # block 1: two payments
        [make_payment("Thandi", "Lerato", 250.00)],                                      # block 2: one payment
        [make_payment("Lerato", "Naledi", 90.00), make_payment("BK", "Sipho", 40.00)],   # block 3: two payments
    ]

    print(f"{'Block':<8}{'Nonce':<12}{'Attempts':<12}{'Seconds':<10}{'Fees':<8}{'Reward':<10}{'Hash (first 16)'}")  # header
    print("-" * 78)                                                                                                # divider

    for block_number, payments in enumerate(blocks_to_mine, start=1):            # mine each block in turn
        result = mine_block_with_reward(                                         # assemble, mine and reward
            index=block_number,                                                  # the block's position
            previous_hash=previous_hash,                                         # link it to the block before
            payments=payments,                                                   # the payments it carries
            difficulty=difficulty,                                               # the difficulty being mined at
            miner_address=MINER_ADDRESS,                                         # the address to credit
        )
        apply_block_to_balances(result["header"], balances)                      # update the ledger
        mined_blocks.append(result)                                              # keep the result for the check below
        previous_hash = result["hash"]                                           # the next block points at this one

        fees_collected = result["header"]["transactions"][0]["fees"]             # the fee portion of the coinbase
        print(f"{block_number:<8}{result['nonce']:<12,}{result['attempts']:<12,}"  # block number, nonce, attempts
              f"{result['seconds']:<10.3f}{fees_collected:<8.2f}"                  # seconds and fees collected
              f"{result['reward']:<10.2f}{result['hash'][:16]}")                   # reward and the winning hash

    print("-" * 78)                                                                # divider under the table
    print()                                                                        # blank line for readability

    print("BALANCES AFTER THREE BLOCKS")                                           # heading for the ledger listing
    for address in sorted(balances):                                               # list every address alphabetically
        print(f"  {address:<16}{balances[address]:>12,.2f}")                       # the address and what it holds
    total_mined = sum(block["reward"] for block in mined_blocks)                    # everything the miner earned
    print(f"Miner earned {total_mined:,.2f} units, of which "                       # the headline earnings figure
          f"{BLOCK_SUBSIDY * len(mined_blocks):,.2f} is newly created subsidy.")    # and how much is new money
    print("Sending addresses go negative because no balance check is performed:")   # an honest simplification note
    print("this lab measures mining, not transaction validity.")                    # and what it does instead
    print()                                                                         # blank line for readability

    print("REDIRECTING THE REWARD AFTER MINING")                                          # heading for this test
    print("-" * 78)                                                                       # divider line
    stolen_header = dict(mined_blocks[0]["header"])                                       # copy block 1's finished header
    stolen_header["transactions"] = list(stolen_header["transactions"])                   # copy the transaction list
    stolen_header["transactions"][0] = dict(stolen_header["transactions"][0])             # and the coinbase within it
    stolen_header["transactions"][0]["receiver"] = "THIEF-01"                             # THE EDIT: redirect the reward

    print(f"  Original hash           : {mined_blocks[0]['hash']}")                       # the mined hash
    print(f"  Hash after redirection  : {header_hash(stolen_header)}")                    # the hash once the address changed
    print(f"  Still meets the target? : {meets_target(header_hash(stolen_header), target_for_difficulty(difficulty))}")  # False
    print("Changing who gets paid changes the hash, so the thief would have to redo the")  # why the theft fails
    print("proof of work, and would then be mining their own block rather than stealing.") # and why that gains nothing
    print()                                                                                # blank line for readability

# ===========================================================================
# PART B: RETARGETING
# ===========================================================================

def retarget_convergence() -> float:
    """Start from a deliberately wrong difficulty and let the algorithm correct it."""
    print("PART B: RETARGETING FROM A WRONG STARTING DIFFICULTY")                    # heading for this section
    print("=" * 78)                                                                  # heavy divider line
    print(f"Epoch length {EPOCH_BLOCKS} blocks, target block time "                  # the settings in force
          f"{TARGET_BLOCK_SECONDS:.2f} seconds, clamp {MAX_ADJUSTMENT_FACTOR}x.")    # including the clamp
    print()                                                                          # blank line for readability

    current_difficulty = 256                                       # deliberately far too easy for a modern processor
    expected_epoch_seconds = EPOCH_BLOCKS * TARGET_BLOCK_SECONDS   # how long a well-tuned epoch should take
    epoch_history = []                                             # collects one record per epoch

    print(f"{'Epoch':<8}{'Difficulty':<14}{'Secs/block':<14}{'Ratio':<10}{'Next difficulty'}")  # table header
    print("-" * 78)                                                                            # divider

    for epoch_number in range(1, 9):                                        # run eight epochs
        epoch = mine_epoch_at_rate(                                         # mine one epoch at the current difficulty
            start_index=epoch_number * 100,                                 # spaced indexes keep searches independent
            difficulty=current_difficulty,                                  # the difficulty this epoch uses
            extra_work=0,                                                   # no handicap in this study
        )
        next_difficulty = retarget(                                         # decide the difficulty for the next epoch
            old_difficulty=current_difficulty,                              # what was just used
            actual_seconds=epoch["seconds"],                                # how long the epoch really took
            expected_seconds=expected_epoch_seconds,                        # how long it should have taken
        )
        ratio = expected_epoch_seconds / epoch["seconds"]                   # the raw adjustment before the clamp

        epoch_history.append(epoch)                                         # keep the record for the summary
        print(f"{epoch_number:<8}{current_difficulty:<14,}"                 # epoch number and difficulty used
              f"{epoch['seconds_per_block']:<14.4f}{ratio:<10.2f}{next_difficulty:,}")  # block time, ratio, next difficulty
        current_difficulty = next_difficulty                                # carry the new difficulty forward

    print("-" * 78)                                                          # divider under the table

    measured_hash_rate = statistics.mean(e["hash_rate"] for e in epoch_history)   # average speed across the run
    ideal_difficulty = measured_hash_rate * TARGET_BLOCK_SECONDS                  # the difficulty that suits this machine
    print(f"Mean hash rate {measured_hash_rate:,.0f} per second, so the difficulty that fits")  # the machine's speed
    print(f"this machine is {ideal_difficulty:,.0f}. The algorithm finished at {current_difficulty:,}.")  # where it landed
    print("The early epochs show the clamp binding: the raw ratio demanded far more than a")   # what the early rows show
    print("fourfold jump and the algorithm refused, which is why Bitcoin reaches a correct")   # the consequence
    print("difficulty over several epochs rather than one. Afterwards the figure oscillates")  # the later behaviour
    print("rather than settling, because five blocks is far too few to measure a block time.") # and why
    print()                                                                                    # blank line for readability

    return ideal_difficulty                                  # hand the figure to the next study


def hash_rate_change(ideal_difficulty: float):
    """Cut the effective hash rate part way through and watch the difficulty adapt."""
    print("PART B: RETARGETING AFTER A CHANGE IN HASH RATE")                         # heading for this section
    print("=" * 78)                                                                  # heavy divider line
    print("Epochs 1 to 3 run at full speed. From epoch 4 each attempt carries one")  # what the study does
    print("extra hash of equal cost, so the effective rate falls by roughly half.")   # and the effect
    print()                                                                          # blank line for readability

    adaptive_difficulty = max(1024, int(ideal_difficulty))         # start near the correct difficulty
    expected_epoch_seconds = EPOCH_BLOCKS * TARGET_BLOCK_SECONDS   # how long a well-tuned epoch should take
    history = []                                                   # collects one record per epoch

    print(f"{'Epoch':<8}{'Speed':<12}{'Difficulty':<14}{'Secs/block':<14}{'Hashes/sec':<14}{'Next'}")  # table header
    print("-" * 78)                                                                                   # divider

    for epoch_number in range(1, 9):                                        # run eight epochs
        extra_work = 0 if epoch_number <= 3 else 1                          # the handicap switches on at epoch 4
        speed_label = "full" if extra_work == 0 else "halved"               # a readable label for the table

        epoch = mine_epoch_at_rate(                                         # mine the epoch at this difficulty and speed
            start_index=1000 + epoch_number * 100,                          # spaced indexes keep searches independent
            difficulty=adaptive_difficulty,                                 # the difficulty currently in force
            extra_work=extra_work,                                          # the handicap, zero or one
        )
        next_difficulty = retarget(                                         # decide the difficulty for the next epoch
            old_difficulty=adaptive_difficulty,                             # what was just used
            actual_seconds=epoch["seconds"],                                # how long the epoch really took
            expected_seconds=expected_epoch_seconds,                        # how long it should have taken
        )
        epoch["extra_work"] = extra_work                                    # remember whether the handicap was on
        history.append(epoch)                                               # keep the record for the summary

        print(f"{epoch_number:<8}{speed_label:<12}{adaptive_difficulty:<14,}"    # epoch, speed and difficulty
              f"{epoch['seconds_per_block']:<14.4f}{epoch['hash_rate']:<14,.0f}"  # block time and effective rate
              f"{next_difficulty:,}")                                             # the difficulty chosen next
        adaptive_difficulty = next_difficulty                               # carry the new difficulty forward

    print("-" * 78)                                                          # divider under the table

    full_rate = statistics.mean(e["hash_rate"] for e in history if e["extra_work"] == 0)          # rate before the change
    slow_rate = statistics.mean(e["hash_rate"] for e in history if e["extra_work"] == 1)          # rate after it
    full_block = statistics.mean(e["seconds_per_block"] for e in history if e["extra_work"] == 0) # block time before
    slow_block = statistics.mean(e["seconds_per_block"] for e in history if e["extra_work"] == 1) # block time after

    print(f"Hash rate fell from {full_rate:,.0f} to {slow_rate:,.0f} per second, "        # the measured change
          f"a reduction of {(1 - slow_rate / full_rate) * 100:.0f} percent.")             # stated as measured
    print(f"Mean block time was {full_block:.4f} seconds before and {slow_block:.4f} after, "  # block times either side
          f"against a target of {TARGET_BLOCK_SECONDS:.4f}.")                                  # and the target
    print("Losing half the mining power costs one slow epoch, after which the difficulty")  # what the table shows
    print("falls and block times recover. What changes permanently is the security budget,")  # the lasting effect
    print("because less work now stands behind each block.")                                  # and why it matters
    print()                                                                                   # blank line for readability

# ===========================================================================
# MAIN
# ===========================================================================

def main():
    """Run every part of the lab in order and save the Part A (b) timing table."""
    print("=" * 78)                                                          # heavy divider at the top of the output
    print("MINING AND PROOF-OF-WORK LAB - ASSIGNMENT 6")                     # title of the program
    print("=" * 78)                                                          # heavy divider
    print("Attempts, nonces and hashes are deterministic and reproduce anywhere.")  # what repeats on any machine
    print("Wall-clock seconds and hash rates are measured on this machine only.")   # what does not
    print()                                                                         # blank line for readability

    show_target_arithmetic()                    # Part A (a): the rule and the arithmetic behind it
    mine_one_block()                            # Part A (a): one block mined and verified
    study_results = parameter_study()           # Part A (b): the parameter study across difficulty levels

    timing_table = format_timing_table(study_results)   # build the timing table as text
    print(timing_table)                                 # show it on screen
    print()                                             # blank line for readability

    with open("timing_table.txt", "w", encoding="utf-8") as output_file:  # open the file for writing in UTF-8
        output_file.write(timing_table + "\n")                            # save the table for submission

    block_reward_demonstration()                        # Part A (c): the block reward and the redirection test
    ideal_difficulty = retarget_convergence()           # Part B: correcting a wrong starting difficulty
    hash_rate_change(ideal_difficulty)                  # Part B: adapting after the hash rate falls

    print("Timing table written to timing_table.txt")   # confirm the file was produced
    print("Demonstration complete.")                    # confirm the end of the run


if __name__ == "__main__":   # this block runs only when the file is executed directly, not when imported
    main()                   # start the demonstration
