from flask import Flask, render_template
import json
from datetime import datetime

app = Flask(__name__)

boards = {
    "default": "/home/werewolf/leaderboard.json"
}

def get_leaderboard(name=None):
    if name not in boards:
        name = "default"

    with open(boards[name], "rt") as f:
        return boards[name], json.load(f)

@app.context_processor
def helpers():
    return dict(
        sorted=sorted,
        format_date=lambda d: datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S (UTC)"),
        with_precision=lambda n, precision: format(n, ".{}f".format(precision))
    )

@app.route("/")
@app.route("/<board_name>/")
def get_board(board_name="default"):
    url, board = get_leaderboard(board_name)

    return render_template("index.html", url=url, board=board)

if __name__ == '__main__':
    app.run(port=5000)
