import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Streamlit layout
st.set_page_config(layout="wide")

# Simulatiefunctie
def simulate(start_capital, monthly_start, monthly_end, years_build, spend_schedule,
             annual_return_mean, annual_return_std, inflation=0.02, n_scenarios=2000):

    # Inleg (koopkracht → nominaal)
    months_total = years_build * 12
    contribs_real = np.linspace(monthly_start, monthly_end, months_total)
    contribs_nominal = [contribs_real[m] * ((1+inflation)**(m//12)) for m in range(months_total)]
    yearly_contribs = [sum(contribs_nominal[i*12:(i+1)*12]) for i in range(years_build)]

    # Uitgaven (drie fasen) → inflatie vanaf einde opbouw
    yearly_spends = []
    for block in spend_schedule:
        block_vals = np.linspace(block["start"], block["end"], block["years"]*12)
        block_nom = [block_vals[m] * ((1+inflation)**(years_build + m//12)) for m in range(len(block_vals))]
        yearly_spends.extend([sum(block_nom[i*12:(i+1)*12]) for i in range(block["years"])])
    withdrawals = [0]*years_build + yearly_spends
    total_years = years_build + len(yearly_spends)

    # Simulaties
    results = np.zeros((n_scenarios, total_years))
    rng = np.random.default_rng()
    for s in range(n_scenarios):
        capital = start_capital
        for year in range(total_years):
            r = rng.normal(annual_return_mean, annual_return_std)
            contrib = yearly_contribs[year] if year < years_build else 0
            withdraw = withdrawals[year] if year < len(withdrawals) else 0
            capital = capital * (1+r) + contrib - withdraw
            if capital < 0:
                capital = 0
            results[s, year] = capital

    return results, withdrawals


# -------- Streamlit interface --------
st.title("💰 Interactieve Vermogenssimulatie")

# Leeftijd
start_age = st.slider("Leeftijd bij start", 18, 60, 25)
pension_age = 69
pension_year = pension_age - start_age

# Basisparameters
start_capital = st.slider("Startkapitaal (€)", 0, 100000, 10000, 1000)
monthly_start = st.slider("Begininleg per maand (€)", 0, 2000, 300, 10)
monthly_end = st.slider("Eindinleg per maand (€)", 0, 2000, 800, 10)
years_build = st.slider("Jaren opbouw", 1, 40, 30)
annual_return_mean = st.slider("Gemiddeld rendement (%)", 0, 15, 7, 1) / 100
annual_return_std = st.slider("Volatiliteit rendement (%)", 0, 30, 15, 1) / 100

# Opname fasen
st.subheader("Opnamefase (max 3 blokken)")
spend_schedule = []
for i in range(3):
    col1, col2, col3 = st.columns(3)
    with col1: years = st.slider(f"Fase {i+1} - jaren", 0, 40, 10, 1, key=f"y{i}")
    with col2: start = st.slider(f"Fase {i+1} - begin (€)", 0, 6000, 3000, 100, key=f"s{i}")
    with col3: end = st.slider(f"Fase {i+1} - eind (€)", 0, 6000, 3000, 100, key=f"e{i}")
    if years > 0:
        spend_schedule.append({"years": years, "start": start, "end": end})

# Run simulatie
results, withdrawals = simulate(start_capital, monthly_start, monthly_end, years_build,
                   spend_schedule, annual_return_mean, annual_return_std)

# Percentielen
percentiles = [10, 20, 40, 50, 60, 80, 90]
curves = {p: np.percentile(results, p, axis=0) for p in percentiles}

# Wanneer gaat vermogen naar 0?
zero_years = {}
for p in percentiles:
    series = curves[p]
    idx = np.where(series <= 0)[0]
    zero_years[p] = int(idx[0]) if len(idx) > 0 else None

# Kleuren rood → groen
colors = ['darkred', 'red', 'orange', 'gold', 'limegreen', 'green', 'darkgreen']
names = [
    "Pessimistisch (10%)", "Laag (20%)", "Onder gemiddeld (40%)",
    "Mediaan (50%)", "Boven gemiddeld (60%)", "Hoog (80%)", "Optimistisch (90%)"
]

# Plotly grafiek
fig = go.Figure()

for p, c, name in zip(percentiles, colors, names):
    fig.add_trace(go.Scatter(
        x=list(range(len(curves[p]))),
        y=curves[p],
        mode="lines",
        name=name,
        line=dict(color=c, width=3)
    ))

# Verticale lijnen
fig.add_vline(x=(years_build-1), line_dash="dot", line_color="magenta",
              annotation_text="Einde opbouw", annotation_position="top left")
if 0 < pension_year <= results.shape[1]:
    fig.add_vline(x=pension_year, line_dash="dash", line_color="red",
                  annotation_text=f"Pensioen ({pension_age})", annotation_position="top left")

fig.update_layout(
    title=f"📊 Monte Carlo Vermogenssimulatie ({results.shape[0]} scenario’s)<br>"
          f"Startleeftijd: {start_age}, Pensioen: {pension_age}, "
          f"Startkapitaal: €{start_capital:,}, Inleg: €{monthly_start}→{monthly_end}/mnd, "
          f"Rendement: {annual_return_mean*100:.1f}% ± {annual_return_std*100:.1f}%",
    xaxis_title="Jaar",
    yaxis_title="Vermogen (€)",
    template="plotly_white",
    legend=dict(font=dict(size=14)),
    font=dict(size=16),
    height=800
)

st.plotly_chart(fig, use_container_width=True)

# Uitleg onder de grafiek
st.markdown("""
### ℹ️ Uitleg bij de grafiek
- **Kleurige lijnen**: verschillende scenario’s (percentielen, van pessimistisch naar optimistisch).  
- **Paarse stippellijn**: einde van de opbouwfase (inleg stopt).  
- **Rode stippellijn**: je pensioenleeftijd (69 − startleeftijd).  
- **Kruisjes**: jaar waarin het vermogen in dat scenario op nul komt.  \
- De percentages die bij de lijnen worden weergegeven zijn de kansen dat het in de realiteit eronder ligt. 

#### Aannames
- Inleg en opname zijn opgegeven in **koopkracht van nu** en omgerekend naar **nominale euro’s** met inflatie (2% p/j).  
- Rendement wordt gesimuleerd met een Monte Carlo-methode: gemiddelde en volatiliteit instelbaar.  
- Alle bedragen in de grafiek zijn **nominaal** (wat je werkelijk op je rekening zou zien).

""")















