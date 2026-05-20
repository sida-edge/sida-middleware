#ifndef LIBS_NETWORK_ZMQ_DATAGRAM
#define LIBS_NETWORK_ZMQ_DATAGRAM

#include <string>
#include <string_view>

namespace sida {

class ZmqDatagram {
  public:
    ZmqDatagram() = default;
    ZmqDatagram(std::string_view topic, std::string_view message);

    [[nodiscard]] std::string_view topic() const;
    [[nodiscard]] std::string_view message() const;
    [[nodiscard]] bool empty() const ;

    friend inline bool operator==(const ZmqDatagram& lhs, const ZmqDatagram& rhs) = default;

  private:
    std::string topic_;
    std::string message_;

};

} // namespace sida


#endif /* LIBS_NETWORK_ZMQ_DATAGRAM */
