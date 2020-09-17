import os
import datetime
import argparse
from heapq import heapify, heappush, heappop
from googleapiclient.discovery import build
import pandas as pd


API_KEY = os.environ["API_KEY"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SERVICE = build("sheets", "v4", developerKey=API_KEY)
SHEET_API = SERVICE.spreadsheets()
METADATA = SHEET_API.get(spreadsheetId=SPREADSHEET_ID).execute()


def compute_transactions(ledger):
    assert round(sum(ledger.values()), 2) == 0
    neg = []
    pos = []
    for name, value in ledger.items():
        if value < 0:
            heappush(neg, (value, value, name))
        else:
            heappush(pos, (-value, value, name))
    transactions = []
    while neg and pos:
        _, debt, debtee = heappop(pos)
        _, payment, debtor = heappop(neg)
        unaccounted = round(debt + payment, 2)
        if unaccounted > 0:
            heappush(pos, (-unaccounted, unaccounted, debtee))
        elif unaccounted < 0:
            heappush(neg, (unaccounted, unaccounted, debtor))
        amount = min(debt, -payment)
        transactions.append((debtee, debtor, amount))
    assert len(neg) == 0
    assert len(pos) == 0
    transactions = sorted(transactions)
    return transactions


def get_venmo_data():
    form_responses = METADATA["sheets"][0]["properties"]["title"]
    data = (
        SHEET_API.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=form_responses)
        .execute()["values"]
    )
    venmo_table = pd.DataFrame(
        [row[1:4] for row in data[1:]], columns=data[0][1:4]
    ).dropna()
    venmo_table.columns = ["Name", "Venmo", "Alias"]
    for col in venmo_table:
        venmo_table[col] = venmo_table[col].str.strip()
    venmo_table["Key"] = venmo_table.Name.str.replace(" ", "").str.lower()
    has_at = ~venmo_table.Venmo.str.startswith("@")
    venmo_table.loc[has_at, "Venmo"] = "@" + venmo_table.loc[has_at, "Venmo"]
    real_names = venmo_table.dropna()[["Name", "Venmo", "Key"]]
    real_names["RealName"] = real_names["Name"]
    real_names["IsAlias"] = False
    aliases = venmo_table.dropna()[["Name", "Alias", "Venmo"]]
    aliases = aliases.rename(columns={"Alias": "Name", "Name": "RealName"})
    aliases["Key"] = aliases.Name.str.replace(" ", "").str.lower()
    aliases["IsAlias"] = True
    venmo = pd.concat([real_names, aliases]).reset_index(drop=True)
    venmo = venmo.drop_duplicates(["Key", "Venmo"])[
        ["Key", "Venmo", "RealName", "IsAlias"]
    ]
    venmo.RealName = venmo.RealName.str.title()
    return venmo


def get_ledger():
    ledger_sheet_name = METADATA["sheets"][1]["properties"]["title"]
    data = (
        SHEET_API.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=ledger_sheet_name)
        .execute()["values"]
    )
    ledger_df = pd.DataFrame([row for row in data[2:]], columns=data[0])
    ledger_df = ledger_df.rename(columns={"PnL": "Amount"})
    ledger_df.Name = ledger_df.Name.str.strip()
    ledger_df.Date = pd.to_datetime(ledger_df.Date)
    ledger_df.Amount = ledger_df.Amount.astype(float).round(2)
    ledger_df["Key"] = ledger_df.Name.str.replace(" ", "").str.lower()
    return ledger_df


if __name__ == "__main__":
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", dest="start", default=today)
    parser.add_argument("--end", dest="end", default=None)
    args = parser.parse_args()
    start = pd.to_datetime(args.start)
    end = start if args.end is None else pd.to_datetime(args.end)
    venmo = get_venmo_data()
    ledger_df = get_ledger()
    merged = ledger_df[["Date", "Key", "Amount"]].merge(venmo, on="Key", how="left")
    result = (
        merged.query("Date >= @start and Date <= @end")
        .groupby(["RealName", "Venmo"])[["Amount"]]
        .sum()
        .reset_index()
    )
    txns = compute_transactions(dict(result[["RealName", "Amount"]].values))
    payments = pd.DataFrame(txns, columns=["To", "From", "Amount"])
    payments = payments.merge(
        venmo[~venmo.IsAlias], left_on="From", right_on="RealName"
    )
    payments = payments.merge(
        venmo[~venmo.IsAlias], left_on="To", right_on="RealName", suffixes=["", "To"]
    )
    payments = payments.sort_values("To")
    totals = result[["RealName", "Amount", "Venmo"]].sort_values("RealName")
    print("Bills")
    print()
    print("======")
    print()
    for _, bill in totals.iterrows():
        sign = bill.Amount > 0
        amount = "${:.2f}".format(abs(bill.Amount))
        if not sign:
            amount = "-" + amount
        print(f"{bill.RealName} ({bill.Venmo}): {amount}")
    print()
    print("Transactions To Settle")
    print()
    print("======================")
    print()
    for _, tx in payments.iterrows():
        amount = "${:.2f}".format(abs(tx.Amount))
        print(f"{tx.To} ({tx.VenmoTo}) requests {amount} from {tx.From} ({tx.Venmo})")
