# 116117-suche
Dingens dass mir Chatgpt gebastelt hat zum Text von der 116117 Website in eine csv Tabelle zu konvertieren. 

Anleitung: 

1. cd ~/Desktop && mkdir -p ~/Desktop 116117suche && cd ~/Desktop/116117suche && curl -O https://raw.githubusercontent.com/tresitresen/116117-suche/main/116117_parser.py
2. outerHTML von #app > div > div > div.main-content-inner-container.no-focus-outline > div > div > div.outer-list-container > div > div.search-results-container kopieren
3. Text extrahieren + kopieren
4. pbpaste > ~/Desktop/116117suche/ergebnisse.txt
5. python3 116117_parser.py