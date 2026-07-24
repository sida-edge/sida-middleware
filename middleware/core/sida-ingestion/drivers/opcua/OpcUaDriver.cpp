#include "OpcUaDriver.h"

#include <iostream>

namespace sida {

OpcUaDriver::OpcUaDriver(DeviceConfig config) 
    : config_(std::move(config)),
      connected_(false) 
{
    driver_id_ = "OpcUa_" + config_.device_id;

    client_ = UA_Client_new();
    UA_ClientConfig_setDefault(UA_Client_getConfig(client_));
}

OpcUaDriver::~OpcUaDriver() {
    disconnect();
    if (client_) {
        UA_Client_delete(client_);
    }
}

bool OpcUaDriver::connect() {
    if (client_ == nullptr) return false;

    UA_StatusCode status = UA_Client_connect(client_, config_.host.c_str());
    if (status != UA_STATUSCODE_GOOD) {
        std::cerr << "[DRIVE_OPCUA] Connection failed: " << UA_StatusCode_name(status) << "\n";
        connected_ = false;
        return false;
    }

    connected_ = true;
    std::cout << "[DRIVE_OPCUA] Connected to " << config_.device_id << "\n";

    return connected_;
}

void OpcUaDriver::disconnect() {
    if (client_ && connected_) {
        UA_Client_disconnect(client_);
        connected_ = false;
        std::cout << "[DRIVE_OPCUA] Disconnected from " << config_.device_id << "\n";
    }
}

TagValue OpcUaDriver::readNodeValue(const std::string& node_id_str, bool& quality_ok) {
    quality_ok = false;
    TagValue defaultValue = 0;
    
    UA_NodeId nodeId = UA_NODEID_STRING_ALLOC(1, node_id_str.c_str());
    UA_Variant value;
    UA_Variant_init(&value);

    UA_StatusCode status = UA_Client_readValueAttribute(client_, nodeId, &value);
    quality_ok = (status == UA_STATUSCODE_GOOD);

    if (quality_ok) {
        if (UA_Variant_isScalar(&value)) {
            if (value.type == &UA_TYPES[UA_TYPES_DOUBLE]) {
                defaultValue = *static_cast<double*>(value.data);
            } else if (value.type == &UA_TYPES[UA_TYPES_INT32]) {
                defaultValue = *static_cast<int32_t*>(value.data);
            } else if (value.type == &UA_TYPES[UA_TYPES_BOOLEAN]) {
                defaultValue = *static_cast<bool*>(value.data);
            } else {
                std::cerr << "[DRIVE_OPCUA] Unsupported data type for node " << node_id_str << "\n";
                quality_ok = false;
            }
        } else {
            std::cerr << "[DRIVE_OPCUA] Non-scalar value for node " << node_id_str << "\n";
            quality_ok = false;
        }
    } else {
        std::cerr << "[DRIVE_OPCUA] Failed to read value for node " << node_id_str << ": " 
                  << UA_StatusCode_name(status) << "\n";
    }

    UA_NodeId_clear(&nodeId);
    UA_Variant_clear(&value);

    return defaultValue;
}

std::vector<sida::TagRecord> OpcUaDriver::pollData() {
    std::vector<sida::TagRecord> data;
    if (!connected_ || client_ == nullptr) {
        std::cerr << "[DRIVE_OPCUA] Device " << config_.device_id << " is not connected.\n";
        return data;
    }

    for (const auto& [metric_key, metric] : config_.metrics) {
        bool quality_ok = false;

        TagValue value = readNodeValue(metric.address, quality_ok);

        if (quality_ok) {
            data.emplace_back(config_.device_id, metric.name, value, metric.unit, quality_ok);
        } else {
            std::cerr << "[DRIVE_OPCUA] Failed to read metric " << metric.name << "\n";
        }
    }

    UA_SecureChannelState channelState;
    UA_SessionState sessionState;
    UA_StatusCode connectStatus;
    
    UA_Client_getState(client_, &channelState, &sessionState, &connectStatus);

    if (sessionState != UA_SESSIONSTATE_ACTIVATED) {
        std::cerr << "[DRIVE_OPCUA] Session is not active. Disconnecting...\n";
        disconnect();
    }

    return data;

}

bool OpcUaDriver::isConnected() const {
    return connected_;
}

std::string OpcUaDriver::getId() const {
    return driver_id_;
}

} // namespace sida