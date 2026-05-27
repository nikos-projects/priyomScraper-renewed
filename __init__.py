from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PriyomScrape:
    url = "https://priyom.org/number-stations/station-schedule"

    def __init__(self, headless: bool = True, driver_path: str | None = None):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = Service(executable_path=driver_path) if driver_path else Service()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait   = WebDriverWait(self.driver, timeout=20)
        self._loaded = False

    # ── internal ────────────────────────────────────────────────────────────────

    def _load(self):
        if not self._loaded:
            self.driver.get(self.url)
            # Wait for the first calendar-event div to appear
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendar-event")))
            self._loaded = True

    def _text(self, parent, class_name: str) -> str:
        try:
            return parent.find_element(By.CLASS_NAME, class_name).text.strip()
        except Exception:
            return ""

    # ── public API ──────────────────────────────────────────────────────────────

    def getSchedule(self) -> list[tuple]:
        """
        Returns a list of tuples:
          (time_str, station_id, frequency, mode, remarks)
        e.g. ('14:30', 'E11', '6959kHz', 'USB', '')

        Each tuple maps directly to one .calendar-event row on the page.
        """
        self._load()
        events = self.driver.find_elements(By.CLASS_NAME, "calendar-event")
        output = []
        for ev in events:
            time_str  = self._text(ev, "calendar-time")
            station   = self._text(ev, "calendar-station")
            frequency = self._text(ev, "calendar-frequency")
            mode      = self._text(ev, "calendar-mode")
            remarks   = self._text(ev, "calendar-remarks")
            if time_str and station and frequency:
                output.append((time_str, station, frequency, mode, remarks))
        return output

    def getNextStation(self) -> list[dict]:
        """
        Returns a list of dicts for the next upcoming transmission(s), plus a
        trailing {"TTN": "<minutes>"} entry (time-till-next, in minutes).

        Each dict: { stationID, frequency, mode, addInfo, href }
        """
        self._load()

        try:
            events_div = self.driver.find_element(By.ID, "events")
        except Exception:
            return [{"TTN": "0"}]

        # Heading text: "Next station in X minutes" / "Next station in a moment"
        try:
            heading   = events_div.find_element(By.TAG_NAME, "h3").text
            words     = heading.split()
            # "Next station in 4 minutes" → words[3] = "4"
            ttn_raw   = words[3] if len(words) > 3 else "0"
            ttn       = "0" if ttn_raw == "a" else ttn_raw
        except Exception:
            ttn = "0"

        output = []
        for li in events_div.find_elements(By.TAG_NAME, "li"):
            # Each <li> contains a single <a> whose text is e.g. "F06 14984kHz RTTY"
            try:
                a    = li.find_element(By.TAG_NAME, "a")
                href = a.get_attribute("href") or ""
                # Text format: "STATION FREQkHz MODE [addinfo]"
                parts = a.text.strip().split()
                if len(parts) < 3:
                    continue
                output.append({
                    "stationID": parts[0],
                    "frequency": parts[1],
                    "mode":      parts[2],
                    "addInfo":   " ".join(parts[3:]),
                    "href":      href,
                })
            except Exception:
                continue

        output.append({"TTN": ttn})
        return output

    def close(self):
        self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
