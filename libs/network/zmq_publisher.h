#ifndef LIBS_NETWORK_ZMQ_PUBLISHER
#define LIBS_NETWORK_ZMQ_PUBLISHER

#include "libs/network/zmq_datagram.h"

#include <string_view>
#include <zmq.h>
#include <zmq.hpp>

namespace sida {

class IZmqPublisher {
  public:

    IZmqPublisher() = default;

    IZmqPublisher(const IZmqPublisher&) = delete;
    IZmqPublisher& operator=(const IZmqPublisher&&) = delete;
    IZmqPublisher(IZmqPublisher&&) = delete;
    IZmqPublisher& operator=(IZmqPublisher&&) = delete;

    virtual ~IZmqPublisherSocket() = default;

    virtual void bind(std::string_view address) = 0;
    virtual void send(const ZmqDatagram& datagram) = 0;
    virtual void close() = 0;
};

template <class ZmqSocket, class ZmqContext>
class AZmqPublisher : public IZmqPublisher {
  public:
    
    explicit AZmqPublisher(int n_threads = 1) :
        context_(n_threads),
        socket_(context_, zmq::socket_type::pub) {}

    void bind(std::string_view address) override { socket_.bind(std::string{address}); }

    void send(const ZmqDatagram datagram) override {
        if (zmq::message_t zmq_topic(datagram.topic()); !socket_.send(zmq_topic, zmq::send_flags::sndmore))
            throw std::runtime_error("failed send topic.");

        if (zmq::message_t zmq_message(datagram.message()); !socket_.send(zmq_message, zmq::send_flags::dontwait))
            throw std::runtime_error("failed send message.");
    }

    void close() override { socket_.close(); }

  private:
    ZmqContext context_;
    ZmqSocket socket_;

};

using ZmqPublisher = AZmqPublisher<zmq::socket_t, zmq::context_t>;

}  // namespace sida


#endif /* LIBS_NETWORK_ZMQ_PUBLISHER */
