# src/app

`streamlit_app.py`: the investor workspace, in Hebrew (right to left).

```bash
streamlit run src/app/streamlit_app.py      # or ./run_app.sh / run_app.bat
```

- **סקירה**: the dashboard and the chat side by side.
  - A map of Amsterdam: every listing a faint dot, every neighbourhood a bubble sized and coloured
    by its best opportunity; click a bubble to filter the cards. Plotly, no map tiles or tokens.
  - The top opportunities as cards: score, the three components as bars, warning flags (low price
    certainty, few listings, a large gap from Inside Airbnb's occupancy estimate) and an
    "investigate" button that hands the opportunity to the agents.
  - The chat, which stays in view while the dashboard scrolls. While the agents work, a live panel
    shows the pipeline stage (input, router, agent, tools, verification) and each tool call with its
    evidence reference. Under every answer: the work rail, how many numbers were checked, and the
    evidence behind each [E#].
- **כל ההזדמנויות**: the deterministic opportunity table with filters; works without the agents.
- **יומן ראיות**: every tool result of the session and the running groundedness (criterion 7).

`requirements.txt` here is the dependency file Streamlit Community Cloud reads for this app.
The API key comes from the sidebar, a `.env` file, or the app's Secrets (`ANTHROPIC_API_KEY`).
