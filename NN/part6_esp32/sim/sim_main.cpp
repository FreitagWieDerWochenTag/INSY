/* Host runner for the ESP32 sketch: setup() once, loop() until stdin is used up.
 * After every handled character it prints the levels of all output pins as one line:
 *   #GPIO 0=1 4=1 16=1 ...
 * Example: echo 5 | part4_5_c/build/esp32_sim
 */
#include "Arduino.h"

void setup();
void loop();

namespace sim {
int pin_mode[NUM_PINS];
int pin_level[NUM_PINS];
int read_char() { return std::getchar(); }
}
SimSerial Serial;

static void print_pins()
{
    std::printf("#GPIO");
    for (int p = 0; p < sim::NUM_PINS; p++)
        if (sim::pin_mode[p] == OUTPUT)
            std::printf(" %d=%d", p, sim::pin_level[p]);
    std::printf("\n");
}

int main()
{
    for (int p = 0; p < sim::NUM_PINS; p++)
        sim::pin_mode[p] = -1;
    setup();
    print_pins();
    while (Serial.available()) {
        loop();
        print_pins();
    }
    return 0;
}
