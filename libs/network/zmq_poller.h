#ifndef LIBS_NETWORK_ZMQ_POLLER
#define LIBS_NETWORK_ZMQ_POLLER

#include "libs/network/zmq_datagram.h"
#include "libs/network/zmq_subscriber.h"

#include <vector>
#include <zmq.hpp>

namespace sida {

class IZmqPoller {
  public: 
    IZmqPoller() = default;

    IZmqPoller(const IZmqPoller&) = delete;
    IZmqPoller& operator=(const IZmqPoller&) = delete;
    IZmqPoller(IZmqPoller&&) = delete;
    IZmqPoller& operator=(IZmqPoller&&) = delete;

    virtual ~IZmqPoller() = default;

    virtual void push(IZmqSubscriber& socket) = 0;
    virtual void poll(int64_t timeout_ms) = 0;

    virtual ZmqDatagram receive(IZmqSubscriber& socket) const override;

  private:
    std::vector<::zmq::pollitem_t> pollitems_;
};
 
} // namespace sida

#endif /* LIBS_NETWORK_ZMQ_POLLER */
