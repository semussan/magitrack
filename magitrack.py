# -*- coding: utf-8 -*-
# Copyright 2024-2025 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st
from dataclasses import dataclass, field
import uuid
import plotly.graph_objects as go
import random
import json
import requests

GIST_ID = st.secrets["GIST_ID"]
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GIST_FILENAME = "magitrack_data.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

st.set_page_config(page_title="Magi-Track", page_icon=":memo:", layout="wide")

# Declare alias for st.session_state, just for convenience.
state = st.session_state
cols = st.columns([1, 2])

@dataclass
class GameResult:
    text: str
    is_done: bool = False
    uid: uuid.UUID = field(default_factory=uuid.uuid4)

def load_data():
    r = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=HEADERS)
    r.raise_for_status()
    content = r.json()["files"][GIST_FILENAME]["content"]
    raw = json.loads(content).get("game_results", [])
    return [GameResult(text=item["text"], is_done=item.get("is_done", False)) for item in raw]

def save_data(data):
    serializable = {"game_results": [{"text": g.text, "is_done": g.is_done} for g in data]}
    payload = {"files": {GIST_FILENAME: {"content": json.dumps(serializable, indent=2)}}}
    r = requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=HEADERS, json=payload)
    r.raise_for_status()

if "game_results" not in state:
    state.game_results = load_data()


def remove_game_result(i):
    state.game_results.pop(i)
    save_data(state.game_results)


def add_game_result():
    state.game_results.append(GameResult(text=state.new_item_text))
    state.new_item_text = ""
    save_data(state.game_results)


def check_game_result(i, new_value):
    state.game_results[i].is_done = new_value
    save_data(state.game_results)



def delete_all_checked():
    state.game_results = [t for t in state.game_results if not t.is_done]
    save_data(state.game_results)


left_side = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

with left_side:
    with st.form(key="new_item_form", border=True):
        with st.container(
            horizontal=True,
            vertical_alignment="bottom",
        ):
            st.text_input(
                "New item",
                label_visibility="collapsed",
                placeholder="Winner1-Winner2,Loser1-Loser2,...",
                key="new_item_text",
            )

            st.form_submit_button(
                "",
                icon=":material/add:",
                on_click=add_game_result,
            )
    if state.game_results:
        with st.container(gap=None, border=True):
            for i, game_result in enumerate(state.game_results):
                with st.container(horizontal=True, vertical_alignment="center"):
                    st.checkbox(
                        game_result.text,
                        value=game_result.is_done,
                        width="stretch",
                        on_change=check_game_result,
                        args=[i, not game_result.is_done],
                        key=f"game_result-chk-{game_result.uid}",
                    )
                    st.button(
                        ":material/delete:",
                        type="tertiary",
                        on_click=remove_game_result,
                        args=[i],
                        key=f"delete_{i}",
                    )

        with st.container(horizontal=True, horizontal_alignment="center"):
            st.button(
                ":small[Delete all checked]",
                icon=":material/delete_forever:",
                type="tertiary",
                on_click=delete_all_checked,
            )

    else:
        st.info("No to-do items. Go fly a kite! :material/family_link:")


right_right= cols[1].container(
    border=True, height="stretch", vertical_alignment="center"
)


# Deck plotting
deck_id_len = 5
with right_right:
    print(state.game_results)
    decks = {}
    for game in state.game_results:
        try:
            teams = game.text.split(",")
            num_losers = len(teams)-1
            for i,team in enumerate(teams):
                decks_in_team = team.split("-")
                is_winner = i==0
                opponent_teams = [x[1] for x in enumerate(teams) if x[0] is not i]
                opponents = []
                for opponent_team in opponent_teams:
                    decks_in_opponent_team = opponent_team.split("-")
                    for deck_in_opponent_team in decks_in_opponent_team:
                        opponents.append(deck_in_opponent_team)

                for deck_name in decks_in_team:
                    deck_id = deck_name[0:deck_id_len]
                    if deck_id not in decks:
                        decks[deck_id] = {'wins':0,'losses':0, 'matchups':{}}
                    if is_winner:
                        decks[deck_id]['wins'] += num_losers #e.g. winning with 3 teams is 2 wins
                    else:
                        decks[deck_id]['losses'] += 1#e.g. losing with 3 teams is 1 loss
                    decks[deck_id]['n_games'] = decks[deck_id]['losses']+decks[deck_id]['wins']
                    decks[deck_id]['winrate'] = decks[deck_id]['wins']/decks[deck_id]['n_games']
                    for opponent in opponents:
                        if opponent not in decks[deck_id]['matchups']:
                            decks[deck_id]['matchups'][opponent] = {'wins':0,'losses':0}
                            if is_winner:
                                decks[deck_id]['matchups'][opponent]['wins'] += 1 
                            else:
                                decks[deck_id]['matchups'][opponent]['losses'] += 1#e.g. losing with 3 teams is 1 loss
                            decks[deck_id]['matchups'][opponent]['winrate'] = decks[deck_id]['matchups'][opponent]['wins']/(decks[deck_id]['matchups'][opponent]['losses']+decks[deck_id]['matchups'][opponent]['wins'])


        except Exception as e:
            print(f"couldnt process {game}...{e}")
    print(decks)


    decks_by_win_rate = [(x,decks[x]["winrate"],decks[x]["n_games"]) for x in decks]
    decks_by_win_rate.sort(key=lambda item:item[1], reverse=True)
    print(decks_by_win_rate)
    nodes = {}
    i = 0
    for deck, win_rate, n_games in decks_by_win_rate:
        nodes[deck] = (i,win_rate, n_games)
        i += 1
        
    

        
    fig = go.Figure()
##    nodes = {
##        0: (0, 0),
##        1: (random.random(), 1),
##        2: (4, 0),
##        3: (2, -1),
##    }
    edges = []
##    edges = [
##        (0, 1),
##        (1, 2),
##        (0, 3),
##        (3, 2),
##    ]
    # edges
    for a, b in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]

        fig.add_annotation(
            x=x2, y=y2,
            ax=x1, ay=y1,
            xref="x", yref="y",
            axref="x", ayref="y",
            showarrow=True,
            arrowhead=2,
        )

    # nodes
    xs = [nodes[i][0] for i in nodes]
    ys = [nodes[i][1] for i in nodes]
    n_games = [nodes[i][2] for i in nodes]

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        text=[str(i) for i in nodes],
        textposition="top center",
        hovertext=[
            json.dumps(decks[d]["matchups"], indent=2).replace("\n", "<br>").replace(" ", "&nbsp;")
            for d in nodes
        ],
        hoverinfo="text",
        marker=dict(size=25, color=["blue" if x > 1 else "gray" for x in n_games] ),
    ))

    fig.update_layout(
        clickmode="event+select",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    st.plotly_chart(fig, use_container_width=True)
