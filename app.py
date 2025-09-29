import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Streamlit layout
st.set_page_config(layout="wide")

# Simulatiefunctie
def simulate(start_capital, monthly_start, monthly_end, years_build, spend_schedule,
             annual_return_mean, annual_return_std, inflation=0.02, n_scenarios=10000):

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
    withdrawals = [0]*(years_build+1) + yearly_spends
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
st.title("Interactieve Vermogenssimulatie")

# Leeftijd
start_age = st.slider("Leeftijd bij start", 18, 50, 25)
pension_age = 70
pension_year = pension_age - start_age

# Basisparameters
start_capital = st.slider("Startkapitaal (€)", 0, 100000, 10000, 1000)
monthly_start = st.slider("Begininleg per maand (€)", 0, 2000, 300, 50)
monthly_end = st.slider("Eindinleg per maand (€)", 0, 3000, 800, 50)
years_build = st.slider("Jaren opbouw", 1, 50, 30)
annual_return_mean = st.slider("Gemiddeld rendement (%)", 0, 15, 7, 1) / 100
annual_return_std = st.slider("Volatiliteit rendement (%)", 0, 30, 15, 1) / 100

# Opname fasen
st.subheader("Opnamefase (3 blokken)")
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
    zero_years[p] = idx[0] if len(idx) > 0 else None  # geen +1 meer!

# Kleuren rood → groen
colors = ['darkred', 'red', 'orange', 'gold', 'limegreen', 'green', 'darkgreen']

# Plot
fig, ax = plt.subplots(figsize=(28,14), dpi=200)

for p, c in zip(percentiles, colors):
    ax.plot(curves[p], label=f"{p}e perc.", color=c, linewidth=2)

    # Label bij einde opbouw (jaar = years_build, waarde index = years_build)
    val_build = curves[p][years_build]
    ax.text(years_build, min(val_build, 3_000_000),
            f"{int(val_build):,}", color="black", fontsize=14, fontweight="bold",
            ha="left", va="bottom")

    # Marker bij nulvermogen (exact jaar, niet +1)
    if zero_years[p] is not None:
        ax.scatter(zero_years[p], 0, color=c, marker="x", s=120,
                   label=f"{p}e perc. op=0 in jaar {zero_years[p]}")

# Verticale lijnen
ax.axvline(years_build, color="black", linestyle=":", label="Einde opbouwfase")
if 0 < pension_year <= results.shape[1]:
    ax.axvline(pension_year, color="red", linestyle="--", label=f"Pensioen {pension_age} jr")
    for p in percentiles:
        val = curves[p][pension_year]
        ax.text(pension_year, min(val, 3_000_000),
                f"{int(val):,}", color="black", fontsize=14, fontweight="bold",
                ha="left", va="bottom")

ax.set_xlabel("Jaar", fontsize=16)
ax.set_ylabel("Vermogen (€)", fontsize=16)
ax.set_ylim(-100000, 3_000_000)

# Dynamische titel
ax.set_title(
    f"Monte Carlo Vermogenssimulatie ({len(results)} scenario's)\n"
    f"Leeftijd start: {start_age}, Pensioen: {pension_age}, "
    f"Startkapitaal: €{start_capital:,}, "
    f"Inleg: {monthly_start}→{monthly_end} €/mnd reëel ({years_build} jr), "
    f"Rendement: {annual_return_mean*100:.1f}% ± {annual_return_std*100:.1f}%"
, fontsize=18)

ax.legend(ncol=2, fontsize=14)
ax.grid(True)

st.pyplot(fig, use_container_width=True)

# Uitleg onder de grafiek
st.markdown("""
### 📊 Uitleg bij de grafiek

De grafiek toont hoe jouw vermogen zich kan ontwikkelen onder verschillende scenario’s.  
De berekening is gebaseerd op **duizenden Monte Carlo-simulaties**.

#### Wat de lijnen en markeringen betekenen
- **Kleurige lijnen**: percentielen van de uitkomsten  
  - **10e percentiel (rood)**: slechts 1 op 10 scenario’s doet het slechter → pessimistisch pad.  
  - **50e percentiel (middelste lijn)**: de mediane uitkomst → helft van de scenario’s beter, helft slechter.  
  - **90e percentiel (groen)**: slechts 1 op 10 scenario’s doet het beter → optimistisch pad.  
- **Zwarte stippellijn**: einde van de **opbouwfase**. Labels tonen hier het opgebouwde vermogen.  
- **Rode stippellijn**: je **pensioenleeftijd** (70 − startleeftijd). Labels tonen hier het vermogen op dat moment.  
- **Kruisjes**: jaar waarin het vermogen in dat scenario op nul komt.  

#### Over de fasen
- **Opbouwfase**: je legt maandelijks in, van begin- naar eindinleg (koopkracht van nu), omgerekend naar **nominale euro’s** met inflatie (2%).  
- **Opnamefase**: bestaat uit maximaal drie blokken (fasen). Binnen elk blok loopt je opname lineair van een beginbedrag naar een eindbedrag (koopkracht van nu), ook omgerekend naar **nominale euro’s**.  

#### Aannames
- **Inflatie**: vast 2% per jaar.  
- **Rendement**: per jaar getrokken uit een normale verdeling met het gekozen gemiddelde en volatiliteit.  
- **Weergave**: alle bedragen zijn in **nominale euro’s** (wat je daadwerkelijk op je rekening zou zien).
""")









