# Hawaii Poker Ledger

This program distributes Venmo transactions among the winners and losers in a medium stakes online poker game. 

The script parses a Google Sheets document with all of the game results and figures out a reasonable way to distribute cash in the post-game settlement. This allows the game to run without having a centralized "banker" deal with all of the accounting.

## How To Run

Setup a virtualenv and install the `requirements.txt` (Python 3.6+) if you haven't already

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then, source the setup script to create environment variables that store the API key and the Spreadsheet ID. Email jarry.xiao@gmail.com to request the API Key.

You can also make your own:

Guide - https://developers.google.com/sheets/api/quickstart/python

Console - https://console.developers.google.com/apis/

```
source setup.sh
```

Lastly, run the script with the start and end dates of the settle. By default, it uses today's date for both `start` and `end`. If you don't include an end parameter it will default to the `start` date.

## Examples

```
# Settle today's game(s)
python ledger.py

# Settle games between 2020-09-01 and 2020-09-06 (inclusive)
python ledger.py --start 2020-09-01 --end 2020-09-06

# Settle games on 2020-09-01
python ledger.py --start 2020-09-01
```
