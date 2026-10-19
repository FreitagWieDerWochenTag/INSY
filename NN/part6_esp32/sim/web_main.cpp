/* Browser runner for the ESP32 sketch (WebAssembly, built with `make -C part4_5_c web`).
 * The web page calls these functions instead of a serial port and GPIO pins:
 *   sim_start()         pinMode/setup() once
 *   sim_send(c)         one character "typed in the serial monitor", then loop() until it is handled
 *   sim_pin_mode(p), sim_pin_level(p)   what the sketch did with GPIO p
 * Serial.printf output goes to stdout, which the page shows as the serial monitor.
 */
#include "Arduino.h"

#include <emscripten/emscripten.h>

void setup();
void loop();

namespace sim {
int pin_mode[NUM_PINS];
int pin_level[NUM_PINS];
static int pending = EOF;
int read_char() { int c = pending; pending = EOF; return c; }
}
SimSerial Serial;

extern "C" {
EMSCRIPTEN_KEEPALIVE void sim_start()
{
    for (int p = 0; p < sim::NUM_PINS; p++)
        sim::pin_mode[p] = -1;
    setup();
    std::fflush(stdout);
}

EMSCRIPTEN_KEEPALIVE void sim_send(int c)
{
    sim::pending = c;
    while (Serial.available())
        loop();
    std::fflush(stdout);
}

EMSCRIPTEN_KEEPALIVE int sim_pin_mode(int pin) { return pin >= 0 && pin < sim::NUM_PINS ? sim::pin_mode[pin] : -1; }
EMSCRIPTEN_KEEPALIVE int sim_pin_level(int pin) { return pin >= 0 && pin < sim::NUM_PINS ? sim::pin_level[pin] : 0; }
}
