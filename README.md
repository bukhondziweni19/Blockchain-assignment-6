# Blockchain Assignment 6: Mining and Proof-of-Work Lab

A proof-of-work miner in pure Python, built to measure what mining actually costs and how a
network keeps that cost steady as hardware changes.

Course work for **BLCH9X2 Blockchain**, Master of Financial Engineering, University of Johannesburg.
Part A implements the miner, measures it and pays the block reward. Part B implements difficulty
retargeting. Part C asks what any of it means for a regulated financial market infrastructure.

## The rule

A SHA-256 hash is 64 hexadecimal characters, which is a very large whole number. A block is mined
when that number falls at or below a ceiling:

```
target = MAX_TARGET / difficulty
block is valid when int(hash, 16) <= target
```

This is a numeric target rather than a count of leading zeros. Two reasons. Retargeting has to
multiply the target by fractional amounts, which a count of zeros cannot express since zeros move
only in steps of sixteen. And expected attempts then equals the difficulty exactly, because a hash
lands at or below `MAX_TARGET / d` once in every `d` tries, which gives the measurements below a
theoretical column to be checked against.

Difficulty 65,536 gives the target `0000ffff...`, which is the familiar four-leading-zeros rule.
Difficulty 16,384 gives `0003ffff...`, and the lab mines a valid block whose hash begins `0003cbbd`.
That value is inexpressible under a leading-zeros rule, which is the design choice earning its keep.

## What mining costs

Five difficulty levels, five independent blocks mined at each:

| Difficulty | Expected attempts | Mean attempts | Median attempts | Mean seconds | Hashes/sec |
|---|---|---|---|---|---|
| 1,024 | 1,024 | 1,155 | 671 | 0.017 | 67,498 |
| 4,096 | 4,096 | 4,594 | 3,290 | 0.069 | 66,747 |
| 16,384 | 16,384 | 13,652 | 13,639 | 0.206 | 66,355 |
| 65,536 | 65,536 | 51,113 | 18,359 | 0.787 | 64,923 |
| 262,144 | 262,144 | 281,999 | 208,667 | 4.200 | 67,143 |

1,762,564 hashes in 26.39 seconds, 66,777 per second overall.

Attempt counts are deterministic and will reproduce exactly. Timings are from the machine that ran
it and will not.

Two things worth noticing. Mean time per block rises fourfold for each fourfold rise in difficulty,
because hash rate is a property of the processor rather than of the difficulty. And the attempt
counts are far noisier than the means suggest: the five trials at difficulty 65,536 needed 1,313,
2,438, 39,395, 18,359 and 194,061 attempts, a spread of 148 times inside one difficulty level.
Mining attempts follow a geometric distribution whose standard deviation is roughly its mean, so
five samples cannot pin the average down.

## The block reward

A coinbase transaction sits first in every block, paying a fixed subsidy of 50 units plus the fees
from the payments in that block. It has no sender, because those units did not exist before the
block was found.

The miner's address is protected by the proof of work rather than by a rule forbidding edits.
Redirecting a mined block's reward to another address changes its hash from `0001a42b68b4232d...`
to `bd743d194e737634...`, which no longer meets the target. The thief would have to redo the search,
and having done so would be mining their own block rather than stealing this one.

## Difficulty retargeting

Bitcoin measures how long the last 2,016 blocks took and multiplies the target by the ratio of
actual to expected time, clamped to a factor of four. `mining.py` runs the same arithmetic with
epochs of 5 blocks and a target block time of 0.20 seconds.

Starting from a difficulty set far too low, the algorithm climbs in clamped fourfold steps and lands
at 10,933 against an ideal of 11,312 for the machine it ran on. The clamp binds downwards too: one
epoch produced 0.8180 seconds per block, a raw ratio of 0.24, which the one-quarter floor held at
0.25.

The second study cuts the effective hash rate part way through, honestly rather than by simulation:
each attempt performs one extra hash of equal cost, so the processor genuinely slows. The measured
rate fell 47 percent, and the difficulty roughly halved in response. Mean block time was 0.1947
seconds before the change and 0.2581 after, against a target of 0.2000.

Losing half the mining power costs one slow epoch, not half the chain. What changes permanently is
the security budget, since less work now stands behind each block.

## Why the lab fixes difficulty elsewhere

Reproducibility, mainly: with fixed difficulty and fixed timestamps every nonce and hash reproduces
on any machine, whereas retargeting makes difficulty a function of local processor speed. Beyond
that, the parameter study needs one variable at a time; there is no network here and no adversarial
clock, so retargeting demonstrates the arithmetic rather than the problem it was designed to solve;
and five-block epochs are too short to measure a block time, as the oscillation above shows.

## Running it

Python 3.8 or later. No dependencies beyond the standard library. Roughly one minute.

```bash
python mining.py                      # the full demonstration
python mining.py > console_log.txt    # the same output saved to a file
```

It also writes `timing_table.txt` containing the timing table above, regenerated on your machine.

## Files

| File | What it is |
|---|---|
| `mining.py` | The miner, the parameter study, the block reward and retargeting |
| `timing_table.txt` | The timing table, written by the program |
| Notebook (`.ipynb`) | The same work cell by cell, with commentary and outputs |
| Report (`.pdf`) | Written report, including the proof of work against proof of stake essay |

## Scope

One processor thread running interpreted Python, so the rates say nothing about a real network.
Blocks are mined in isolation rather than chained, since this lab measures mining rather than chain
integrity, which Assignment 5 covered. There are no digital signatures and no balance checks, so
sending addresses go negative. Retargeting runs against a single honest clock, whereas Bitcoin
retargets on timestamps reported by miners who may lie, which is why its clamp and median-of-eleven
timestamp rule exist.
