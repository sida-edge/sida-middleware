#ifndef SIDA_INGESTION_CORE_TYPES
#define SIDA_INGESTION_CORE_TYPES

#include <string>
#include <variant>
#include <vector>
#include <cstdint>
#include <chrono>
#include <map>

using TagValue = std::variant<bool, int32_t, int64_t, float, double, std::string>;

namespace sida {

struct MetricMappingConfig {
    std::string name;
    double scale_factor;
    std::string unit;
    std::string data_type;       // "float", "int16", "int32", "uint16", "bool", "string"
    std::string register_type;   // "holding", "input", "coil", "discrete"
    std::string address;         // For Modbus: register address; For OPC UA: node ID
};

struct DeviceConfig {
    std::string device_id;
    std::string protocol;
    std::string host;
    int port;
    int unit_id;
    int scan_rate_ms;
    std::string byte_order;
    bool enabled;

    std::string username; // For OPC UA
    std::string password; // For OPC UA

    std::string security_policy; // For OPC UA
    std::string security_mode;   // For OPC UA

    std::string endpoint_url; // For OPC UA

    std::map<std::string, MetricMappingConfig> metrics;
};

struct TagRecord {
    std::string device_id;
    std::string tag_name;
    TagValue value;
    std::string unit; // Optional: unit of the value
    uint64_t timestamp; // Timestamp in milliseconds
    bool quality; // true for good quality, false for bad quality

    TagRecord(std::string dev_id, std::string tag, TagValue val, std::string u, bool quality = true)
        : device_id(std::move(dev_id)), 
          tag_name(std::move(tag)), 
          value(std::move(val)),
          unit(std::move(u)),
          quality(quality)
    {   
        timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count();
    }
};

} // namespace sida

#endif /* SIDA_INGESTION_CORE_TYPES */
