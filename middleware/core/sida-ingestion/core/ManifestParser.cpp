#include "ManifestParser.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>

using json = nlohmann::json;

namespace sida {

ManifestParser::ManifestParser(std::string file_path) 
    : manifest_path_(std::move(file_path)), gateway_id_("unknown_gateway") {}

std::string ManifestParser::getGatewayId() const {
    return gateway_id_;
}

std::vector<sida::DeviceConfig> ManifestParser::parseEnabledDevices() {
    std::vector<sida::DeviceConfig> enabled_devices;

    std::ifstream file(manifest_path_);
    if (!file.is_open()) {
        std::cerr << "[ManifestParser] Failed to open manifest file: " << manifest_path_ << std::endl;
        return enabled_devices;
    }

    json manifest;
    try {
        file >> manifest;
    } catch (const json::parse_error& e) {
        std::cerr << "[ManifestParser] JSON parse error: " << e.what() << std::endl;
        return enabled_devices;
    }

    gateway_id_ = manifest.value("gateway_id", "sida_default_gw");

    if (!manifest.contains("config") || !manifest["config"].contains("plant") || !manifest["config"]["plant"].contains("areas")) {
        std::cerr << "[ManifestParser] Missing required configuration in manifest." << std::endl;
        return enabled_devices;
    }

    auto areas = manifest["config"]["plant"]["areas"];

    for (auto& [area_id, area_obj] : areas.items()) {

        if (!area_obj.contains("lines")) continue;
        auto lines = area_obj["lines"];

        for (auto& [line_id, line_obj] : lines.items()) {
            
            if (!line_obj.contains("devices")) continue;
            auto devices = line_obj["devices"];
            
            for (auto& [device_id, dev_obj] : devices.items()) {
                
                if (dev_obj.value("enabled", false) == false) continue;

                auto conn = dev_obj["connection"];
                std::string protocol = conn.value("protocol", "");

                if (protocol == "modbus_tcp" || protocol == "opcua") {
                    sida::DeviceConfig d_cfg;
                    d_cfg.device_id = device_id;
                    d_cfg.enabled = true;
                    d_cfg.protocol = protocol;
                    d_cfg.host = conn.value("host", "127.0.0.1");
                    d_cfg.port = conn.value("port", 502);
                    d_cfg.unit_id = conn.value("unit_id", 1);
                    d_cfg.scan_rate_ms = conn.value("scan_rate_ms", 1000);
                    d_cfg.byte_order = conn.value("byte_order", "ABCD");
                    d_cfg.endpoint_url = conn.value("endpoint_url", "");

                    if (dev_obj.contains("metrics_mapping")) {
                        auto metrics = dev_obj["metrics_mapping"];
                        for (auto& [metric_key, met_obj] : metrics.items()) {
                            sida::MetricMappingConfig m_cfg;
                            m_cfg.name = met_obj.value("name", metric_key);
                            m_cfg.data_type = met_obj.value("data_type", "int16");
                            m_cfg.register_type = met_obj.value("register_type", "holding");
                            m_cfg.unit = met_obj.value("unit", "");
                            m_cfg.scale_factor = met_obj.value("scale_factor", 1.0);
                            m_cfg.address = met_obj.value("node_id", metric_key);
                            
                            d_cfg.metrics[metric_key] = m_cfg;
                        }
                    }

                    enabled_devices.push_back(d_cfg);
                }
            }
        }
    }
    std::cout << "[ManifestParser] Total enabled devices parsed: " << enabled_devices.size() << std::endl;
    return enabled_devices;
}

} // namespace sida