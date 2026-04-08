#include "LoRaWan_APP.h"
#include "Arduino.h"
#include "driver/rtc_io.h"

// ---------------------------- CONFIGURATION ----------------------------

// LoRa settings
#define RF_FREQUENCY             915000000   // Frequency in Hz
#define TX_OUTPUT_POWER          14          // dBm
#define LORA_BANDWIDTH           0           // 0=125kHz, 1=250kHz, 2=500kHz
#define LORA_SPREADING_FACTOR    7           // SF7..SF12
#define LORA_CODINGRATE          1           // 1=4/5 .. 4=4/8
#define LORA_PREAMBLE_LENGTH     8
#define LORA_SYMBOL_TIMEOUT      0
#define LORA_FIX_LENGTH_PAYLOAD_ON false
#define LORA_IQ_INVERSION_ON     false

#define BUFFER_SIZE              30          // LoRa payload buffer size
#define RX_TIMEOUT_VALUE         1000

// Motion sensor & speaker pins
static const int SENSOR_OUT_PIN = 5; // Radar motion sensor output
static const int SPEAKER_PIN    = 6;  // Speaker input to amp

// Sound configuration
int pwmResolution = 8;      // PWM resolution for speaker
int dutyMid = 128;          // PWM duty cycle for sound
int freq = 2500;            // Tone frequency (Hz)
const unsigned long playDuration = 3000; // Sound duration (ms)
const unsigned long cooldownTime = 2000; // Minimum time between triggers
unsigned long lastTrigger = 0;           // Tracks last motion event

// ---------------------------- GLOBAL VARIABLES ----------------------------
char rxpacket[BUFFER_SIZE];       // LoRa receive buffer
bool lora_idle = true;            // Flag to indicate LoRa idle
uint32_t enter_deepsleep_number = 0; // Counter to decide when to sleep

int16_t rssi, rxSize;             // Signal strength and payload length
static RadioEvents_t RadioEvents; // LoRa events struct
int16_t txNumber;

// ---------------------------- UTILITY FUNCTIONS --------------------------

// Play a sound on the speaker for a specified duration
void playSound(unsigned long ms) {
    ledcWriteTone(SPEAKER_PIN, freq);  // Start PWM tone
    ledcWrite(SPEAKER_PIN, dutyMid);   // Set duty cycle
    delay(ms);                          // Wait for duration
    ledcWrite(SPEAKER_PIN, 0);         // Stop tone
    ledcWriteTone(SPEAKER_PIN, 0);
}

// Print the reason the ESP32 woke up from sleep
void print_wakeup_reason() {
    esp_sleep_wakeup_cause_t wakeup_reason;
    wakeup_reason = esp_sleep_get_wakeup_cause();

    switch (wakeup_reason) {
        case ESP_SLEEP_WAKEUP_EXT0:     Serial.println("Wakeup caused by external signal using RTC_IO"); break;
        case ESP_SLEEP_WAKEUP_EXT1:     Serial.println("Wakeup caused by external signal using RTC_CNTL"); break;
        case ESP_SLEEP_WAKEUP_TIMER:    Serial.println("Wakeup caused by timer"); break;
        case ESP_SLEEP_WAKEUP_TOUCHPAD: Serial.println("Wakeup caused by touchpad"); break;
        case ESP_SLEEP_WAKEUP_ULP:      Serial.println("Wakeup caused by ULP program"); break;
        default:                        Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason); break;
    }
}

// ---------------------------- SETUP ----------------------------
void setup() {
    Serial.begin(115200);          // Start serial for debugging
    delay(300);

    // Initialize sensor pin
    pinMode(SENSOR_OUT_PIN, INPUT_PULLUP);

    // Initialize speaker PWM channel
    if (!ledcAttach(SPEAKER_PIN, freq, pwmResolution)) {
        Serial.println("ledcAttach failed");
        while (1) delay(200);
    }
    ledcWrite(SPEAKER_PIN, 0);  // Start with speaker off

    Serial.println("Ready: motion detection + LoRa receiver");

    // Initialize LoRa MCU
    Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);  // Ensure correct board type

    // LoRa setup
    txNumber = 0;
    rssi = 0;
    RadioEvents.RxDone = OnRxDone;
    Radio.Init(&RadioEvents);
    Radio.SetChannel(RF_FREQUENCY);
    Radio.SetRxConfig(MODEM_LORA, LORA_BANDWIDTH, LORA_SPREADING_FACTOR,
                      LORA_CODINGRATE, 0, LORA_PREAMBLE_LENGTH,
                      LORA_SYMBOL_TIMEOUT, LORA_FIX_LENGTH_PAYLOAD_ON,
                      0, true, 0, 0, LORA_IQ_INVERSION_ON, true);

    // Print wakeup reason in case ESP32 woke from deep sleep
    print_wakeup_reason();
}

// ---------------------------- MAIN LOOP ----------------------------
void loop() {
    // Put LoRa in receive mode if idle
    if (lora_idle) {
        lora_idle = false;
        Serial.println("into RX mode");
        Radio.Rx(0);
    }

    Radio.IrqProcess();  // Process any LoRa interrupts

    // Check motion sensor
    int motion = digitalRead(SENSOR_OUT_PIN);
    if (motion == LOW) {  // Motion detected
        unsigned long now = millis();
        if (now - lastTrigger > cooldownTime) {
            lastTrigger = now;
            Serial.println("Detected motion -> playing sound");
            playSound(playDuration);
        }
    }

    // Decide when to enter deep sleep
    if (enter_deepsleep_number >= 5) {
        Serial.println("Preparing for deep sleep...");
        // Enable wake-up on LoRa GPIO
        esp_sleep_enable_ext0_wakeup((gpio_num_t)RADIO_DIO_1, 1);  // High level triggers wake-up
        rtc_gpio_pullup_dis((gpio_num_t)RADIO_DIO_1);
        rtc_gpio_pulldown_en((gpio_num_t)RADIO_DIO_1);

        Serial.println("Going to sleep now");
        delay(500);  // Small delay for debug prints
        esp_deep_sleep_start();  // Enter deep sleep
    }

    delay(20);  // Small loop delay to reduce CPU usage
}

// ---------------------------- LORA CALLBACK ----------------------------
void OnRxDone(uint8_t *payload, uint16_t size, int16_t rssi_val, int8_t snr) {
    rssi = rssi_val;
    rxSize = size;
    memcpy(rxpacket, payload, size);
    rxpacket[size] = '\0';

    Radio.Sleep();  // Put LoRa to sleep

    // Print received payload
    Serial.printf("\r\nreceived packet \"%s\" with rssi %d , length %d\r\n", rxpacket, rssi, rxSize);

    lora_idle = true;         // Mark LoRa as idle
    enter_deepsleep_number++; // Increment counter towards deep sleep
}