# 116117-suche
Dingens dass mir Chatgpt gebastelt hat zum Ergebnisse von der 116117 Website (Arzt/Therapeutensuche) in eine csv Tabelle zu konvertieren und nach jetzt "anrufbaren" Ergebnissen zu sortieren. Dient primär meinem privatem Gebrauch, ich bin kein Programmierer sondern bin nur zu faul einzeln immer rauszusuchen wann ich wo anrufen kann. Vielleicht hilft das ja noch irgendwem. Ich übernehme keine Haftung oder so falls irgendwas nicht funktioniert.  

Anleitung: 
In den .py Skripten steht nochmal alles genauer (glaube ich)
1. ```
   cd ~/Desktop && mkdir -p ~/Desktop 116117suche && cd ~/Desktop/116117suche && curl -O https://raw.githubusercontent.com/tresitresen/116117-suche/main/116117_parser_html.py && curl -O https://raw.githubusercontent.com/tresitresen/116117-suche/main/jetzt_erreichbar.py
   ```
2. copy Element von #app > div > div > div.main-content-inner-container.no-focus-outline > div > div > div.outer-list-container > div > div.search-results-container 
3. ```
   pbpaste > ~/Desktop/116117suche/ergebnisse.html
   ```
4. ```
   pip install beautifulsoup4
   ```
   (falls noch nicht installiert)
5. ```
   python3 116117_parser_html.py
   ```
6. ```
   python3 jetzt_erreichbar.py
   ```
7. als csv auslesen oder via html gui 
