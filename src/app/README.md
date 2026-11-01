# src/app

`streamlit_app.py`: the investor chat, in Hebrew (right to left).

```bash
streamlit run src/app/streamlit_app.py      # or ./run_app.sh / run_app.bat
```

- **שיחה**: the chat with the agents. Under every answer: the work rail (router, agent, each
  tool call with its evidence reference, the verifier), the number of figures checked and how
  many are grounded, and the evidence behind each [E#].
- **הזדמנויות**: the deterministic opportunity table with filters. It works without the agents,
  as the charter requires.
- **יומן ראיות**: every tool result of the session and the running groundedness (criterion 7).

Without an API key the chat answers in fallback mode (the opportunity table). Without the data
bundle, the sidebar builds a synthetic demo repository, labelled as such.
