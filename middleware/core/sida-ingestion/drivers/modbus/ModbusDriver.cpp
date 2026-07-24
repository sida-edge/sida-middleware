#include "ModbusDriver.h"
#include <iostream>

namespace sida {

ModbusDriver::ModbusDriver(DeviceConfig config)
    : config_(std::move(config)),
      ctx_(nullptr),
      connected_(false) 
{
    driver_id_ = "ModbusTCP_" + config_.device_id;

    ctx_ = modbus_new_tcp(config_.host.c_str(), config_.port);
    if (ctx_ == nullptr) {
        std::cerr << "[DRIVE_MODBUS] Failed to create Modbus context\n";
    }
}

ModbusDriver::~ModbusDriver() {
    disconnect();
    if (ctx_) {
        modbus_free(ctx_);
    }
}

bool ModbusDriver::connect() {
    if (ctx_ == nullptr) return false;

    modbus_set_slave(ctx_, config_.unit_id);
    modbus_set_response_timeout(ctx_, 2, 0);

    if (modbus_connect(ctx_) == -1) {
        std::cerr << "[DRIVE_MODBUS] Connection failed: " << modbus_strerror(errno) << "\n";
        connected_ = false;
        return false;
    }

    connected_ = true;
    std::cout << "[DRIVE_MODBUS] Connected to " << config_.device_id << "\n";

    return connected_;
}

void ModbusDriver::disconnect() {
    if (ctx_ && connected_) {
        modbus_close(ctx_);
        connected_ = false;
        std::cout << "[DRIVE_MODBUS] Disconnected from " << config_.device_id << "\n";
    }
}

std::vector<sida::TagRecord> ModbusDriver::pollData() {
    std::vector<sida::TagRecord> data;
    if (!connected_ || ctx_ == nullptr) {
        std::cerr << "[DRIVE_MODBUS] Device " << config_.device_id << " is not connected.\n";
        return data;
    }

    for (const auto& [metric_key, metric] : config_.metrics) {
        int rc = -1;

        int num_regs = 1;
        if (metric.data_type == "int32" || metric.data_type == "float") {
            num_regs = 2;
        }

        std::vector<uint16_t> raw_data(num_regs);
        
        int address = std::stoi(metric.address);
        if (metric.register_type == "holding" || metric.register_type.empty()) {
            rc = modbus_read_registers(ctx_, address, num_regs, raw_data.data()); 
        } else if (metric.register_type == "input") {
            rc = modbus_read_input_registers(ctx_, address, num_regs, raw_data.data());
        } 
        else {
            std::cerr << "[DRIVE_MODBUS] Unsupported register type: " << metric.register_type << "\n";
            continue;
        }

        if (rc == -1) {
            std::cerr << "[DRIVE_MODBUS] Read failed for " << metric.name << ": " << modbus_strerror(errno) << "\n";
            break;
        }

        TagValue value;
        
        if (metric.data_type == "bool") {
            value = static_cast<bool>(raw_data[0] > 0);
        } else if (metric.data_type == "int32") {
            value = (raw_data[0] << 16) | raw_data[1];
        } else if (metric.data_type == "float") {
            value = modbus_get_float_abcd(raw_data.data());
        } else {
            value = static_cast<int32_t>(raw_data[0]);
        }

        data.emplace_back(config_.device_id, metric.name, value, metric.unit, true);
    }

    if (!connected_) {
        std::cerr << "[DRIVE_MODBUS] Device " << config_.device_id << " is not connected.\n";
        disconnect();
    }

    return data;
}

bool ModbusDriver::isConnected() const {
    return connected_;
}

std::string ModbusDriver::getId() const {
    return driver_id_;
}
    
} // namespace sida