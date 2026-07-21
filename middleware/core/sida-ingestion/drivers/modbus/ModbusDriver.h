#ifndef DRIVERS_MODBUS_MODBUSDRIVER
#define DRIVERS_MODBUS_MODBUSDRIVER

#include "IProtocolDriver.h"

#include <modbus/modbus.h>

#include <vector>
#include <string>

namespace sida {

class ModbusDriver : public sida::IProtocolDriver {
  public:
    ModbusDriver(sida::DeviceConfig config);
    ~ModbusDriver() override;

    [[nodiscard]] bool connect() override;
    void disconnect() override;

    [[nodiscard]] std::vector<sida::TagRecord> pollData() override;

    [[nodiscard]] bool isConnected() const override;
    [[nodiscard]] std::string getId() const override;

  private:
    sida::DeviceConfig config_;
    modbus_t* ctx_;
    bool connected_;
    std::string driver_id_;

    uint32_t parserBytes(const uint16_t* tab_reg, int index, const std::string& data_type);
};

} // namespace sida

#endif /* DRIVERS_MODBUS_MODBUSDRIVER */
