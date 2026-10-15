# Portfolio agents: sygnały kupna/sprzedaży dla instrumentów XTB

Zestaw agentów, które zbierają publiczne dane o transakcjach ważnych inwestorów i wiadomościach rynkowych,
łączą je w sygnały **KUP / SPRZEDAJ / OBSERWUJ** dla instrumentów z listy XTB i wysyłają alerty na telefon
(aplikacja [ntfy](https://ntfy.sh)). Uruchamia się co 30 minut w dni robocze przez GitHub Actions.

> Sygnały są informacyjne. Nic nie handluje automatycznie, a progi nie są jeszcze sprawdzone na danych historycznych.

## Agenci

| Agent | Źródło | Jak często | Co wykrywa |
|---|---|---|---|
| **Insider** | SEC Form 4 (`data.sec.gov`) | kilka dni po transakcji | zakupy i sprzedaże na rynku przez osoby z dostępem do spółki (np. Trump jako insider w DJT) |
| **Fundusze** | SEC 13F-HR | kwartalnie, do 45 dni po kwartale | nowe, zwiększone, zmniejszone i zamknięte pozycje (np. Berkshire, Pershing Square, Bridgewater) |
| **Newsy** | RSS: CNBC, MarketWatch, Forbes, Google News + Claude | co 30 min | nagłówki o spółkach z listy: sentyment i istotność oceniane przez model |
| **Ręczny** | `data/manual_signals.json` | ręcznie | transakcje, które nie mają API, np. raporty 278-T prezydenta USA (PDF) |
| **Techniczny** | Yahoo Finance | tylko dla kandydatów | SMA20, SMA50, RSI14. Filtr potwierdzający, nie generator sygnałów |
| **Koordynator** | | | łączy zdarzenia, stosuje progi i cooldown, wysyła alerty |

## Ważne ograniczenia

- **Portfela Trumpa nie da się śledzić na żywo.** Publicznie są: Form 4 (tylko dla spółek, w których jest insiderem,
  np. DJT), roczne oświadczenia majątkowe (OGE 278e) i raporty transakcji (278-T). Te ostatnie są publikowane
  z opóźnieniem jako PDF. Form 4 agent obsługuje sam. Transakcje z 278-T wpisujesz ręcznie do `data/manual_signals.json`.
- **Opóźnienia:** Form 4 pojawia się po ok. 2 dniach roboczych, 13F do 45 dni po kwartale. To sygnały strukturalne, nie intraday.
- **Zakres:** agenci filingów działają dla spółek z numerem SEC (głównie akcje USA). Indeksy, surowce, forex i kryptowaluty z XTB
  nie mają filingów, więc mogą pojawić się tylko w newsach.
- **Uniwersum XTB:** `data/xtb_universe.csv` to na razie przykładowe 11 spółek. Pełną listę (akcje, ETF-y, indeksy, towary,
  waluty, krypto) generuje eksport z Twojego konta, patrz sekcja „Pełne uniwersum XTB” niżej. Instrumenty spoza pliku są ignorowane.
- **Brak backtestu:** progi są ustawione ręcznie. Nie ma dowodu, że sygnały zarabiają. Zanim podejmiesz na ich podstawie decyzję, sprawdź je na historii.
- **To nie jest porada inwestycyjna.**
- GitHub Actions może opóźnić uruchomienie o kilka–kilkanaście minut.

## Pełne uniwersum XTB (akcje, ETF-y, indeksy, towary, waluty)

Lista instrumentów pochodzi z xAPI XTB, czyli z Twojego konta. Eksport uruchamiasz lokalnie:

```bash
pip install -r portfolio_agents/requirements.txt
XTB_USER_ID=<numer konta> python -m portfolio_agents.xtb_export          # konto realne
python -m portfolio_agents.xtb_export --mode demo --out /tmp/demo.csv   # konto demo, do sprawdzenia
```

Hasło do xAPI program zapyta w terminalu (albo weź je ze zmiennej `XTB_PASSWORD`). Nie wklejaj go w czacie
ani do repozytorium. Eksport zapisuje `data/xtb_universe.csv`. Potem zatwierdź ten plik w repozytorium.

Co z tego wynika:
- **Akcje i ETF-y** (symbol z sufiksem giełdy, np. `AAPL.US`) dostają analizę techniczną tylko dla USA, bo Yahoo
  notuje je pod tickerem. Dla innych giełd pole `price_symbol` trzeba uzupełnić ręcznie.
- **Indeksy, towary, waluty, CFD** (np. `US500`) są wyszukiwane w newsach po nazwie, bez raportów SEC i bez technik,
  dopóki nie uzupełnisz `price_symbol`.
- **Kolizje tickerów** (ten sam ticker na kilku giełdach) zostawiają notowanie w USA.
- Pełna lista to tysiące wierszy. Agent newsowy dopasowuje nazwy wszystkich, więc więcej nagłówków trafia do Claude.
  Limit `MAX_LLM_ITEMS` nadal obowiązuje.

**Niezweryfikowane w tej sesji** (brak dostępu do XTB): endpoint `wss://ws.xtb.com/real`, nazwy pól odpowiedzi
i kształt sufiksów giełdowych (`.US`) wzięte z publicznych klientów xAPI. Przy pierwszym eksporcie sprawdź, czy liczba
wierszy i nazwy są zgodne z aplikacją.

## Konfiguracja (jednorazowo)

1. **Telefon.** Zainstaluj aplikację **ntfy** (Android lub iOS) i zasubskrybuj temat. Wybierz długą, losową nazwę,
   np. `pa-7f3k9x2qLm8`. Każdy, kto zna nazwę tematu, może go czytać, więc nie używaj prostej nazwy.
2. **Sekrety w GitHubie** (Settings → Secrets and variables → Actions):
   - `NTFY_TOPIC`: nazwa tematu z kroku 1 (wymagane)
   - `SEC_CONTACT_EMAIL`: Twój e-mail w nagłówku User-Agent dla SEC (wymagane przez SEC)
   - `ANTHROPIC_API_KEY`: klucz API do Claude (opcjonalne; bez niego newsy oceniane są słowami kluczowymi)
3. **CIK osób i funduszy** w `data/watchlist.json`:
   - znajdź CIK na sec.gov (wyszukiwarka firm i osób) i wpisz 10 cyfr w polu `cik`,
   - **numery CIK funduszy w repo wpisałem z pamięci. Zweryfikuj je na sec.gov przed uruchomieniem.**
   - pole `cik` dla Trumpa jest puste, więc agent go pomija. Wpisz tam jego CIK z EDGAR jako osoby zgłaszającej (insider).
4. **Lista XTB.** Uzupełnij `data/xtb_universe.csv`. Kolumny: `symbol` (np. `AAPL.US`), `ticker`, `name`,
   `aliases` (oddzielone `;`), `cusip` (opcjonalnie, poprawia dopasowanie 13F).
5. **Moje pozycje.** Wpisz tickery posiadanych spółek do `my_positions`. Wtedy alerty SPRZEDAJ dotyczą tylko ich.
   Pusta lista oznacza alerty dla wszystkich.
6. **Gałąź domyślna.** GitHub uruchamia harmonogram tylko z gałęzi domyślnej. Dopóki zmiany nie trafią tam,
   uruchamiaj workflow ręcznie: Actions → `portfolio-agents` → Run workflow.

## Uruchomienie lokalnie

```bash
pip install -r portfolio_agents/requirements.txt
python -m unittest discover -s portfolio_agents/tests -t .      # testy (bez sieci)

SEC_CONTACT_EMAIL=ty@example.com NTFY_TOPIC=twoj-temat python -m portfolio_agents --dry-run
```

- `--dry-run`: wypisuje alerty na konsoli. Nie wysyła ich i nie zapisuje stanu.
- `--no-llm`: agent newsowy działa bez Claude.

## Logika sygnałów

- `wynik = Σ waga_źródła × kierunek × siła`. Wagi są w `data/watchlist.json` (`weights`).
- **KUP:** wynik ≥ 0.30 i co najmniej dwa niezależne źródła są zgodne, albo jedno mocne zdarzenie insidera lub ręczne (siła ≥ 0.8).
- **SPRZEDAJ:** tak samo, w dół. Wysyłany tylko dla spółek z `my_positions`.
- **OBSERWUJ:** wynik między 0.15 a 0.30. Tylko w logach, bez powiadomienia.
- **Filtr techniczny:** KUP przy trendzie spadkowym lub RSI > 75 zmienia się w OBSERWUJ. SPRZEDAJ przy trendzie wzrostowym
  lub RSI < 25 też zmienia się w OBSERWUJ.
- **Cooldown:** ten sam symbol i akcja nie częściej niż co 12 godzin.

## Koszt agenta newsowego

Claude jest wywoływany raz na uruchomienie, tylko gdy pojawią się nowe nagłówki z tickerami z listy (limit 40 nagłówków).
Domyślny model to `claude-opus-5-5`. Aby obniżyć koszt, ustaw zmienną `CLAUDE_MODEL=claude-haiku-5-5`
(np. w `env:` workflow). Rzeczywisty koszt sprawdzisz w konsoli Anthropic po kilku dniach pracy.

## Struktura

```
portfolio_agents/
  __main__.py          # python -m portfolio_agents
  runner.py            # pętla: agenci -> analiza techniczna -> koordynator -> alerty -> stan
  signals.py           # koordynator: progi, zgodność źródeł, filtr techniczny
  notify.py            # wysyłka na ntfy
  state.py             # deduplikacja, cooldown, poprzednie pozycje funduszy
  universe.py          # lista XTB i dopasowanie tekstu/emitentów do tickerów
  technicals.py        # SMA, RSI, dane z Yahoo Finance
  agents/
    insider.py         # Form 4
    holdings.py        # 13F
    news.py            # RSS + Claude (z trybem awaryjnym na słowach kluczowych)
    manual.py          # ręczne wpisy
  data/
    watchlist.json     # osoby, fundusze, kanały RSS, wagi, progi
    xtb_universe.csv   # instrumenty XTB
    manual_signals.json
  tests/               # testy jednostkowe na danych wejściowych (bez sieci)
```

Workflow: `.github/workflows/portfolio-agents.yml` (co 30 minut, pn–pt, 07:00–21:30 UTC).
