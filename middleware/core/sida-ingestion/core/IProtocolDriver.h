#ifndef SIDA_INGESTION_CORE_IPROTOCOLDRIVER
#define SIDA_INGESTION_CORE_IPROTOCOLDRIVER

#include "Types.h"
#include <vector>
#include <string>

namespace sida {

class IProtocolDriver {
  public:
    virtual ~IProtocolDriver() = default;

    [[nodiscard]] virtual bool connect() = 0;
    virtual void disconnect() = 0;
    
    [[nodiscard]] virtual std::vector<TagRecord> pollData() = 0;
    
    [[nodiscard]] virtual bool isConnected() const = 0;
    [[nodiscard]] virtual std::string getId() const = 0;
};

} // namespace sida

#endif /* SIDA_INGESTION_CORE_IPROTOCOLDRIVER */
