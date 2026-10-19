/* Minimal host mock of the Arduino API used by src/main.cpp (not used on the real ESP32).
 * Serial reads characters from sim::read_char() and writes to stdout, digitalWrite records the pin levels.
 * Lets `make -C part4_5_c` build and run the unchanged sketch on the PC (sim_main.cpp: stdin) and
 * in the browser as WebAssembly (web_main.cpp: characters typed on the web page).
 */
#ifndef SIM_ARDUINO_H
#define SIM_ARDUINO_H

#include <cstdarg>
#include <cstdint>
#include <cstdio>

#define LOW 0
#define HIGH 1
#define INPUT 0
#define OUTPUT 1

namespace sim {
constexpr int NUM_PINS = 40;
extern int pin_mode[NUM_PINS];    /* -1 = never configured */
extern int pin_level[NUM_PINS];
int read_char();                  /* next serial input character or EOF, defined by the runner */
}

inline void pinMode(uint8_t pin, uint8_t mode) { sim::pin_mode[pin] = mode; }
inline void digitalWrite(uint8_t pin, uint8_t level) { sim::pin_level[pin] = level; }

class SimSerial {
public:
    void begin(unsigned long) {}
    int available() { fill(); return next_ != EOF ? 1 : 0; }
    int read() { fill(); int c = next_; next_ = NONE; return c; }
    void println(const char *text) { std::printf("%s\n", text); }
    int printf(const char *fmt, ...) __attribute__((format(printf, 2, 3)))
    {
        va_list args;
        va_start(args, fmt);
        int n = std::vprintf(fmt, args);
        va_end(args);
        return n;
    }

private:
    static constexpr int NONE = -2;
    int next_ = NONE;
    void fill() { if (next_ == NONE || next_ == EOF) next_ = sim::read_char(); }  /* EOF: ask again later */
};

extern SimSerial Serial;

#endif /* SIM_ARDUINO_H */
