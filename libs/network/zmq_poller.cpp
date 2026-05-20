#include "libs/network/zmq_poller.h"

#include "libs/network/zmq_datagram.h"
#include "libs/network/zmq_subscriber.h"

#include <zmq.h>
#include <zmq.hpp>

namespace sida {

void ZmqPoller::push(IZmqSubscriber& socket) {
    pollitems_.emplace_back(nullptr, socket.fd(), ZMQ_POLLIN, 0);
}

void ZmqPoller::poll(int64_t timeout_ms) {
    ::zmq::poll(pollitems_, std::chrono::milliseconds{timeout_ms});
}

ZmqDatagram ZmqPoller::receive(IZmqSubscriber& socket) const {
    for (const auto& pollitem : pollitems_) {
        if (pollitem.fd == socket.fd() && static_cast<bool>(pollitem.revents & ZMQ_POLLIN))
            return socket.receive();
    }

    return ZmqDatagram{};
}

} // namespace sida