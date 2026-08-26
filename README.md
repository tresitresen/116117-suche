# 116117-suche
Dingens dass mir Chatgpt gebastelt hat zum Text von der 116117 Website in eine csv Tabelle zu konvertieren. 

Anleitung: 

1. ```
   cd ~/Desktop && mkdir -p ~/Desktop 116117suche && cd ~/Desktop/116117suche && curl -O https://raw.githubusercontent.com/tresitresen/116117-suche/main/116117_parser_html.py && curl -0 https://raw.githubusercontent.com/tresitresen/116117-suche/main/jetzt_erreichbar.py
   ```
2. copy Element von #app > div > div > div.main-content-inner-container.no-focus-outline > div > div > div.outer-list-container > div > div.search-results-container 
3. ```
   pbpaste > ~/Desktop/116117suche/ergebnisse.html
   ```
4. ```
   pip install beautifulsoup4
   ```
5. ```
   python3 116117_parser_html.py
   ```
6. ```
python3 jetzt_erreichbar.py
```