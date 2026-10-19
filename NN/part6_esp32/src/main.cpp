/* Part 6: 7-segment decoder on the ESP32, driven by the forward-only neural net from Part 5.
 *
 * Type a digit 0-9 in the serial monitor (115200 baud). The digit becomes a 4-bit BCD input,
 * the network computes segments A-G and the matching GPIOs light the display.
 * Weights come from models/7seg_net.h (compiled in, no file system needed).
 */
#include <Arduino.h>

#include "7seg_net.h"
#include "nn_from_header.h"

/* Segment A-G -> GPIO, wiring table from Aufgabenstellung.pdf (each with a ~330 Ohm resistor) */
static const uint8_t SEGMENT_PINS[7] = {0, 4, 16, 17, 5, 18, 19};
static const char SEGMENT_NAMES[] = "ABCDEFG";
static const float THRESHOLD = 0.5f;

/* Common cathode: HIGH lights a segment. Build with -DCOMMON_ANODE for a common-anode display. */
#ifdef COMMON_ANODE
static const uint8_t SEGMENT_ON = LOW, SEGMENT_OFF = HIGH;
#else
static const uint8_t SEGMENT_ON = HIGH, SEGMENT_OFF = LOW;
#endif

static Network net;
static bool net_ready = false;

static void show_segments(const float *outputs)
{
    for (int s = 0; s < 7; s++)
        digitalWrite(SEGMENT_PINS[s], outputs[s] >= THRESHOLD ? SEGMENT_ON : SEGMENT_OFF);
}

static void decode_digit(int digit)
{
    float inputs[4];
    for (int b = 0; b < 4; b++)
        inputs[b] = (float)((digit >> (3 - b)) & 1);  /* MSB first, like the training data */
    float outputs[7];
    nn_predict(&net, inputs, outputs);
    show_segments(outputs);

    Serial.printf("digit %d -> input %d%d%d%d -> segments ", digit,
                  (int)inputs[0], (int)inputs[1], (int)inputs[2], (int)inputs[3]);
    for (int s = 0; s < 7; s++)
        Serial.printf("%c", outputs[s] >= THRESHOLD ? SEGMENT_NAMES[s] : '-');
    Serial.printf("  (");
    for (int s = 0; s < 7; s++)
        Serial.printf("%s%c=%.3f", s ? " " : "", SEGMENT_NAMES[s], outputs[s]);
    Serial.printf(")\n");
}

void setup()
{
    Serial.begin(115200);
    for (int s = 0; s < 7; s++) {
        pinMode(SEGMENT_PINS[s], OUTPUT);
        digitalWrite(SEGMENT_PINS[s], SEGMENT_OFF);
    }
    net_ready = nn_init_from_header(&net) == 0;
    if (!net_ready) {
        Serial.println("error: could not initialize the network");
        return;
    }
    Serial.printf("7-segment neural net ready (%d-%d-%d). Type a digit 0-9.\n",
                  NN_LAYER_SIZES[0], NN_LAYER_SIZES[1], NN_LAYER_SIZES[2]);
}

void loop()
{
    if (!net_ready || Serial.available() <= 0)
        return;
    int c = Serial.read();
    if (c >= '0' && c <= '9')
        decode_digit(c - '0');
    else if (c != '\n' && c != '\r' && c != ' ')
        Serial.printf("ignored '%c': send a digit 0-9\n", (char)c);
}
