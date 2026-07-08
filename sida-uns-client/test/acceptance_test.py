"""SIDA UNS Web Client — acceptance test (SDD section 3.1).

Drives the REAL containerized web client against an ISOLATED test Mosquitto
broker, publishing a simulated NBIRTH -> DBIRTH -> DDATA -> DDATA -> NDEATH
sequence and asserting the UI behaviour end-to-end via a headless browser.

Run through run.sh, which brings up the stack, compiles the proto and installs
deps. Exit code 0 = all steps passed.
"""
import os
import sys
import time

import paho.mqtt.client as mqtt
from playwright.sync_api import sync_playwright

import sparkplug_encode as spb

CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:18080")
BROKER_HOST = os.environ.get("BROKER_HOST", "localhost")
BROKER_TCP_PORT = int(os.environ.get("BROKER_TCP_PORT", "18831"))
USER = "sida"
PASSWORD = "sida123"

GROUP = "Plant_A"
NODE = "Line_1"
DEVICE = "Pump_01"

T_TEMP = f"spBv1.0/{GROUP}/DDATA/{NODE}/{DEVICE}"
TEMP_METRIC_ID = f"{GROUP}/{NODE}/{DEVICE}/Temperature"
RUN_METRIC_ID = f"{GROUP}/{NODE}/{DEVICE}/Running"

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


class Publisher:
    def __init__(self):
        self.c = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="acceptance-pub", protocol=mqtt.MQTTv311,
        )
        self.c.username_pw_set(USER, PASSWORD)
        last = None
        for _ in range(30):
            try:
                self.c.connect(BROKER_HOST, BROKER_TCP_PORT, 30)
                break
            except Exception as e:  # broker not up yet
                last = e
                time.sleep(1)
        else:
            raise RuntimeError(f"não conectou ao broker de teste: {last}")
        self.c.loop_start()

    def pub(self, topic, payload):
        info = self.c.publish(topic, payload, qos=0, retain=False)
        info.wait_for_publish(timeout=5)

    def stop(self):
        self.c.loop_stop()
        self.c.disconnect()


def wait_history_len(page, metric_id, n, timeout=10000):
    page.wait_for_function(
        """([id, n]) => window.__SIDA_DEBUG__ &&
                         (window.__SIDA_DEBUG__.history(id).length >= n)""",
        arg=[metric_id, n], timeout=timeout,
    )


def main():
    pub = Publisher()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        console = []
        page.on("console", lambda m: console.append(m.text))
        # wait for the client container to be serving
        last = None
        for _ in range(30):
            try:
                page.goto(CLIENT_URL, timeout=5000)
                break
            except Exception as e:
                last = e
                time.sleep(1)
        else:
            raise RuntimeError(f"client web não respondeu: {last}")

        # ---- login (valid credentials) --------------------------------------
        page.fill("#username", USER)
        page.fill("#password", PASSWORD)
        page.click("#login-btn")
        page.wait_for_selector("#dashboard-view:not([hidden])", timeout=15000)
        page.wait_for_function(
            "() => /conectado/i.test(document.getElementById('conn-banner').textContent)",
            timeout=15000,
        )
        check("login + conexao WS + subscribe (S1/S3)", True)

        # ---- publish birth sequence AFTER subscription ----------------------
        pub.pub(f"spBv1.0/{GROUP}/NBIRTH/{NODE}", spb.nbirth())
        pub.pub(f"spBv1.0/{GROUP}/DBIRTH/{NODE}/{DEVICE}", spb.dbirth())
        pub.pub(T_TEMP, spb.ddata_temp(61.2, seq=2))

        # Step 2: device appears in the tree at the correct path.
        wait_history_len(page, TEMP_METRIC_ID, 2)  # DBIRTH 60.5 + DDATA 61.2
        for label in (GROUP, NODE, DEVICE, "Temperature", "Running"):
            check(
                f"arvore contem '{label}'",
                page.locator(f".tree-label .name:text-is('{label}')").count() > 0,
            )

        # Step 2: numeric chart first point (value + unit).
        page.locator(".metric-leaf .name:text-is('Temperature')").click()
        page.wait_for_selector("#detail-content:not([hidden])")
        page.wait_for_selector("canvas")
        temp_hist = page.evaluate("(id)=>window.__SIDA_DEBUG__.history(id)", TEMP_METRIC_ID)
        check("primeiro ponto Temperature = 60.5", abs(temp_hist[0]["v"] - 60.5) < 1e-6,
              f"got {temp_hist[0]['v'] if temp_hist else None}")
        unit_shown = page.locator("#detail-content .munit").inner_text()
        check("unidade engUnit '°C' exibida", "°C" in unit_shown, f"got '{unit_shown}'")

        # Step 2: boolean metric reflected.
        page.locator(".metric-leaf .name:text-is('Running')").click()
        page.wait_for_selector(".bool-indicator")
        bool_txt = page.locator(".bool-indicator").inner_text()
        check("metrica booleana Running = TRUE", "TRUE" in bool_txt, f"got '{bool_txt}'")

        # ---- Step 3: second DDATA increments (does not replace) -------------
        pub.pub(T_TEMP, spb.ddata_temp(62.0, seq=3))
        wait_history_len(page, TEMP_METRIC_ID, 3)
        temp_hist = page.evaluate("(id)=>window.__SIDA_DEBUG__.history(id)", TEMP_METRIC_ID)
        check("DDATA incremental: 3 pontos acumulados",
              len(temp_hist) == 3, f"len={len(temp_hist)}")
        check("historico preserva ordem [60.5, 61.2, 62.0]",
              [round(p["v"], 3) for p in temp_hist] == [60.5, 61.2, 62.0],
              str([p["v"] for p in temp_hist]))

        # ---- Step 4: NDEATH signals offline WITHOUT clearing history --------
        pub.pub(f"spBv1.0/{GROUP}/NDEATH/{NODE}", spb.ndeath())
        page.wait_for_function(
            """() => { const d = window.__SIDA_DEBUG__.liveness();
                       return d['%s/%s'] === 'offline'; }""" % (GROUP, NODE),
            timeout=10000,
        )
        # node label shows offline visually
        node_offline = page.locator(f".tree-label.offline .name:text-is('{NODE}')").count() > 0
        check("NDEATH: no marcado offline na arvore", node_offline)
        temp_hist_after = page.evaluate("(id)=>window.__SIDA_DEBUG__.history(id)", TEMP_METRIC_ID)
        check("NDEATH nao apaga historico (3 pontos mantidos)",
              len(temp_hist_after) == 3, f"len={len(temp_hist_after)}")

        # ---- Caso 6: NDEATH then a new NBIRTH/DBIRTH (node rebirth) ----------
        # Per Sparkplug, a rebirth re-issues NBIRTH (resets aliases) then DBIRTH;
        # the previously accumulated history must NOT be wiped.
        pub.pub(f"spBv1.0/{GROUP}/NBIRTH/{NODE}", spb.nbirth())
        pub.pub(f"spBv1.0/{GROUP}/DBIRTH/{NODE}/{DEVICE}", spb.dbirth())
        pub.pub(T_TEMP, spb.ddata_temp(63.0, seq=2))
        wait_history_len(page, TEMP_METRIC_ID, 5)  # 3 old + DBIRTH(60.5) + DDATA(63.0)
        r0 = page.evaluate(
            """() => window.__SIDA_DEBUG__.liveness()['%s/%s']""" % (GROUP, NODE)
        )
        temp_hist_reborn = page.evaluate("(id)=>window.__SIDA_DEBUG__.history(id)", TEMP_METRIC_ID)
        check("caso 6: no volta a online apos novo NBIRTH", r0 == "online", f"liveness={r0}")
        check("caso 6: historico anterior preservado no religamento",
              [round(p["v"], 3) for p in temp_hist_reborn[:3]] == [60.5, 61.2, 62.0]
              and len(temp_hist_reborn) == 5,
              str([p["v"] for p in temp_hist_reborn]))

        # ---- extra edge cases (SDD 5.3) -------------------------------------
        # Caso 5: corrupted payload on a spBv1.0 topic -> dropped, no crash.
        pub.pub(T_TEMP, b"\xde\xad\xbe\xef not-a-protobuf \xff\xff")
        time.sleep(1.0)
        still_alive = page.evaluate("() => !!window.__SIDA_DEBUG__")
        len_before = len(temp_hist_reborn)  # 5 points accumulated so far
        temp_hist_corrupt = page.evaluate("(id)=>window.__SIDA_DEBUG__.history(id)", TEMP_METRIC_ID)
        check("payload corrompido nao quebra a app", still_alive)
        check("payload corrompido nao adiciona ponto",
              len(temp_hist_corrupt) == len_before, f"len={len(temp_hist_corrupt)} expected={len_before}")

        # Caso 3: DDATA on an unborn node -> dropped, no new metric id.
        pub.pub("spBv1.0/Ghost/DDATA/UnbornNode/Dev", spb.ddata_temp(1.0, seq=1))
        time.sleep(1.0)
        ghost = page.evaluate(
            "() => window.__SIDA_DEBUG__.metricIds().some(i => i.startsWith('Ghost/'))"
        )
        check("caso 3: DDATA sem NBIRTH descartado", not ghost)

        # ---- Caso 2: invalid credentials rejected (fresh session) -----------
        page2 = browser.new_page()
        for _ in range(30):
            try:
                page2.goto(CLIENT_URL, timeout=5000); break
            except Exception:
                time.sleep(1)
        page2.fill("#username", USER)
        page2.fill("#password", "wrong-password")
        page2.click("#login-btn")
        try:
            page2.wait_for_selector("#login-error:not([hidden])", timeout=15000)
            err_shown = True
        except Exception:
            err_shown = False
        dash_hidden = page2.locator("#dashboard-view").get_attribute("hidden") is not None
        no_subscribe = page2.evaluate(
            "() => window.__SIDA_DEBUG__.metricIds().length === 0"
        )
        check("caso 2: credenciais invalidas mostram erro", err_shown)
        check("caso 2: sem acesso ao dashboard", dash_hidden)
        check("caso 2: nenhuma subscricao/dado apos rejeicao", no_subscribe)
        page2.close()

        browser.close()
    pub.stop()

    print("\n==== RESULTADO ====")
    print(f"PASS: {len(PASSED)}  FAIL: {len(FAILED)}")
    if FAILED:
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    print("TODOS OS PASSOS DO TESTE DE ACEITE (3.1) PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
