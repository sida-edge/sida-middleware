#ifndef SIDA_INGESTION_CORE_MANIFESTPARSER
#define SIDA_INGESTION_CORE_MANIFESTPARSER

#include "Types.h"
#include <string>
#include <vector>

namespace sida {

class ManifestParser {
  public:
    ManifestParser(std::string manifest_path);

    std::vector<DeviceConfig> parseEnabledDevices();

    std::string getGatewayId() const;

  private:
    std::string manifest_path_;
    std::string gateway_id_;
};

} // namespace sida

#endif /* SIDA_INGESTION_CORE_MANIFESTPARSER */
