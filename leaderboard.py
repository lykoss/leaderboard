#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time

parser = argparse.ArgumentParser(description="Generate a leaderboard for Werewolf.")
required = parser.add_argument_group("required arguments")
required.add_argument("--channel", required=True,
                    help="the channel where the game is played")
required.add_argument("--db-path", required=True,
                    help="path to the bot's SQL database")
required.add_argument("--max-players", type=int, required=True,
                    help="the maximum number of players to display on the leaderboard")
required.add_argument("--min-games", type=int, required=True,
                    help="the minimum number of games required to appear on the leaderboard")
required.add_argument("--activity-cutoff", type=int, required=True,
                    help="the number of days in which a user must have recently played to appear on the leaderboard")
#parser.add_argument("--json", action="store_true",
#                    help="output as JSON instead of a human-readable form")
args = parser.parse_args()

generated = time.gmtime()

data = {
    "info": {
        "channel": args.channel,
        "generated": time.strftime("%FT%TZ", generated),
        "max_players": args.max_players,
        "min_games": args.min_games,
        "cutoff": args.activity_cutoff
    },
    "leaderboards": {
        "01_win_ratio": {
            "display_header": "win ratio",
        },
        "02_games": {
            "display_header": "games played",
        },
        "03_wins": {
            "display_header": "wins",
        },
    },
}

def generate_board(cursor, suffix="", floats=False):
    rows = cursor.fetchall()

    def find_min_precision(precision=0):
        nums = {}

        for (_, num) in rows:
            rnd = round(num, precision)

            if rnd in nums and nums[rnd] != num:
                return find_min_precision(precision + 1)
            else:
                nums[rnd] = num

        return precision

    if floats:
        precision = find_min_precision()
    else:
        precision = 0

    tie_length = 0
    last_num = None
    last_cnt = None
    last_tie = None

    board = {
        "display_precision": precision,
        "display_suffix": suffix,
        "entries": [],
    }

    for (num, row) in enumerate(rows):
        num = num + max(tie_length - 1, 1)
        (pl, cnt) = row

        if cnt == last_cnt:
            num = last_num
            tie_length += 1
        else:
            tie_length = 0
            last_tie = pl

        last_num = num
        last_cnt = cnt

        board["entries"].append({
            "position": num,
            "player": pl,
            "value": cnt,
            "tie": (tie_length > 0)
        })

        if tie_length:
            for entry in board["entries"]:
                if entry["player"] == last_tie:
                    entry["tie"] = True

    return board


tmp = tempfile.NamedTemporaryFile()

with open(args.db_path, "rb") as fd:
    tmp.write(fd.read())

with sqlite3.connect(tmp.name) as conn:
    c = conn.cursor()
    data["info"]["total_games"] = c.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    min_games = data["info"]["min_games"]
    max_players = data["info"]["max_players"]
    cutoff = "-{0} days".format(data["info"]["cutoff"])

    c.execute("""SELECT
                   COALESCE(pp.account, pp.hostmask),
                   (CAST(SUM(team_win OR indiv_win) AS FLOAT) / COUNT(*)) * 100 as winratio
                 FROM person pe
                 JOIN player pl
                   ON pl.person = pe.id
                 JOIN player pp
                   ON pp.id = pe.primary_player
                 JOIN game_player gp
                   ON gp.player = pl.id
                 JOIN game g
                   ON g.id = gp.game
                 GROUP BY pe.id
                 HAVING COUNT(*) >= :min_games AND MAX(g.started) >= date('now', :cutoff)
                 ORDER BY winratio DESC
                 LIMIT :max_players""", {"min_games": min_games, "max_players": max_players, "cutoff": cutoff})

    data["leaderboards"]["01_win_ratio"].update(generate_board(c, suffix="%", floats=True))

    c.execute("""SELECT
                   COALESCE(pp.account, pp.hostmask),
                   COUNT(*) as cnt
                 FROM person pe
                 JOIN player pl
                   ON pl.person = pe.id
                 JOIN player pp
                   ON pp.id = pe.primary_player
                 JOIN game_player gp
                   ON gp.player = pl.id
                 JOIN game g
                   ON g.id = gp.game
                 GROUP BY pe.id
                 HAVING cnt >= :min_games AND MAX(g.started) >= date('now', :cutoff)
                 ORDER BY cnt DESC
                 LIMIT :max_players""", {"min_games": min_games, "max_players": max_players, "cutoff": cutoff})

    data["leaderboards"]["02_games"].update(generate_board(c, suffix=" games"))

    c.execute("""SELECT
                   COALESCE(pp.account, pp.hostmask),
                   SUM(gp.team_win OR gp.indiv_win) AS wins
                 FROM person pe
                 JOIN player pl
                   ON pl.person = pe.id
                 JOIN player pp
                   ON pp.id = pe.primary_player
                 JOIN game_player gp
                   ON gp.player = pl.id
                 JOIN game g
                   ON g.id = gp.game
                 GROUP BY pe.id
                 HAVING COUNT(*) > :min_games AND MAX(g.started) >= date('now', :cutoff)
                 ORDER BY wins DESC
                 LIMIT :max_players""", {"min_games": min_games, "max_players": max_players, "cutoff": cutoff})

    data["leaderboards"]["03_wins"].update(generate_board(c, suffix=" wins"))


print(json.dumps(data, indent=2, sort_keys=True))
