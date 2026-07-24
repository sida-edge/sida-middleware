#ifndef DRIVERS_OPCUA_OPCUADRIVER
#define DRIVERS_OPCUA_OPCUADRIVER

#include "IProtocolDriver.h"

#include <open62541/client_config_default.h>
#include <open62541/client_highlevel.h>

#include <string>
#include <vector>

namespace sida {

class OpcUaDriver : public IProtocolDriver {
  public:
    explicit OpcUaDriver(DeviceConfig config);
    ~OpcUaDriver() override;

    [[nodiscard]] bool connect() override;
    void disconnect() override;

    [[nodiscard]] std::vector<TagRecord> pollData() override;

    [[nodiscard]] bool isConnected() const override;
    [[nodiscard]] std::string getId() const override;

  private:
    DeviceConfig config_;
    UA_Client* client_;
    bool connected_;
    std::string driver_id_;

    TagValue readNodeValue(const std::string& node_id_str, bool& quality_ok);
};

} // namespace sida

#endif /* DRIVERS_OPCUA_OPCUADRIVER */
