# 🏦 Ask the Bank — English-to-SQL on real bank data

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://text2sql-berka-vo65rfwbcbpgh2szarr2vz.streamlit.app/)

**🔗 Live demo:** https://text2sql-berka-vo65rfwbcbpgh2szarr2vz.streamlit.app/

<img width="956" height="421" alt="image" src="https://github.com/user-attachments/assets/6c60830a-4f76-41fd-bc7d-95966cc2698b" />

## Features
- **Natural-language querying** — ask in plain English; an LLM (Groq · Llama 3.3 70B) writes the SQL.
- **Real relational data** — the Berka Czech-bank dataset: 8 tables, real joins and aggregations.
- **Read-only by design** — only single `SELECT` queries run, enforced by a guard *and* a read-only connection.
- **Self-correcting** — if a query errors, the model gets the error back and retries once.
- **Charts** — numeric results can be plotted as bar / line / area charts.

📊 [Database schema & data dictionary](SCHEMA.md)

Type a question in plain English (*"What is the average loan amount by status?"*),
and this app uses an LLM to turn it into a SQL query, runs it against a real
anonymised bank database, and shows you both the generated SQL and the results.

Everything here runs in the cloud and in the browser — no local install needed —
and on free tiers only.

**Stack:** Streamlit · SQLite · Groq free API · the Berka dataset.

---

## How it works

```
your question ──▶ prompt (question + DB schema) ──▶ LLM ──▶ SQL
                                                            │
                          results table ◀── run (read-only) ◀┘
```

The LLM never sees the data — only the schema. The generated SQL is checked to be
a single read-only `SELECT`, and is executed over a read-only database connection,
so it can never modify anything. If a query errors, the app sends the error back
to the model once for a self-correction.

| File | Purpose |
|------|---------|
| `build_db.py` | Builds `berka.db` from the data files in `data/` |
| `schema.py` | Extracts the schema + plain-English hints for the prompt |
| `llm.py` | Calls the LLM (Groq by default, Gemini optional) |
| `sql_guard.py` | Cleans the SQL and blocks anything that isn't a read-only `SELECT` |
| `app.py` | The Streamlit UI |

---

## The dataset (Berka)

The [Berka dataset](https://www.kaggle.com/datasets/marceloventura/the-berka-dataset)
(PKDD'99) is real anonymised data from a Czech bank: 8 related tables covering
clients, accounts, ~1M transactions, permanent orders, loans, credit cards, and
district demographics — ideal for SQL because answering questions needs real joins
and aggregations.

> `build_db.py` caps each table at 100,000 rows (`MAX_ROWS_PER_TABLE`) so the built
> `berka.db` stays small enough to commit and host for free. Set it to `None` to
> load everything. Columns that are fully numeric are stored as numbers so `SUM`,
> `AVG`, and comparisons behave correctly.

---

## Setup (100% in the browser)

You don't need anything installed locally. Use **GitHub Codespaces** (a cloud VS
Code that runs on your repo — open your repo on GitHub, press `.` or click
**Code ▸ Codespaces ▸ Create**).

1. **Get the data.** Download the Berka files from Kaggle (link above) and put the
   8 files into the `data/` folder (`account`, `client`, `disp`, `trans`, `order`,
   `loan`, `card`, `district`). `.csv`, `.asc`, and `.tsv` all work.

2. **Build the database** (in the Codespaces terminal):
   ```bash
   pip install -r requirements.txt
   python build_db.py        # creates berka.db
   ```

3. **Get a free API key** and add it as a secret. Create
   `.streamlit/secrets.toml` from the example file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Then paste your key in. Gemini keys are free at
   <https://aistudio.google.com/apikey>; Groq keys at
   <https://console.groq.com/keys>. To use Groq, set `LLM_PROVIDER = "groq"`.

4. **Run it:**
   ```bash
   streamlit run app.py
   ```

5. **Commit `berka.db`** so the deployed app has the data:
   ```bash
   git add berka.db && git commit -m "Add built database" && git push
   ```
   (The raw `data/` files stay out of git via `.gitignore`.)

---

## Deploy a public live demo (free)

1. Push this repo to GitHub.
2. Go to <https://share.streamlit.io>, sign in with GitHub, and pick this repo
   with `app.py` as the entry point.
3. In the app's **Settings ▸ Secrets**, paste the same lines from your
   `secrets.toml` (your API key + `LLM_PROVIDER`).
4. Deploy. It redeploys automatically on every `git push`.

The exact same code also runs on [Hugging Face Spaces](https://huggingface.co/spaces)
(choose the Streamlit SDK and add the key under the Space's *Settings ▸ Secrets*).

> GitHub Pages can't host this — it only serves static sites and can't run the
> Python backend or call the LLM.

---

## Example questions to try

- How many clients are there?
- What is the average loan amount by loan status?
- Show the 10 accounts with the most transactions.
- Total loan amount granted in each year.
- How many credit cards of each type were issued?

---

## Safety & limitations

- **Read-only by design:** only single `SELECT`/`WITH` queries run, write keywords
  are rejected, and the DB connection is opened read-only.
- **Not perfect:** the model can still write SQL that's valid but answers a
  slightly different question than you meant — always check the SQL it shows.
- **Free-tier limits** (requests per day, etc.) apply and change over time; check
  your provider's dashboard.
- This is a learning/portfolio project, not production software.

## License

MIT — see `LICENSE`.
