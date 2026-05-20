#ifndef LIBS_NETWORK_ZMQ_SUBSCRIBER
#define LIBS_NETWORK_ZMQ_SUBSCRIBER

#include "libs/network/zmq_datagram.h"

#include <string>
#include <string_view>
#include <zmq.h>
#include <zmq.hpp>

namespace sida {

class IZmqSubscriber {
  public:

    IZmqSubscriber() = default;

    IZmqSubscriber(const IZmqSubscriber&) = delete;
    IZmqSubscriber& operator==(const IZmqSubscriber&) = delete;
    IZmqSubscriber(IZmqSubscriber&&) = delete;
    IZmqSubscriber& operator==(IZmqSubscriber&&) = delete;
    
    virtual ~IZmqSubscriber() = default;

    virtual void connect(std::string_view address, std::span<const std::string> topics) = 0;
    virtual void connect(std::string_view address, std::span<const std::string_view> topics) = 0;

    virtual ZmqDatagram receive() = 0;

    virtual void close() = 0;

    [[nodiscard]] virtual int fd() const = 0;
};

template <class ZmqContext, class ZmqSocket>
class AZmqSubscriber : public IZmqSubscriber {
  public:
    explicit AZmqSubscriber(int n_threads = 1) : 
        context_(n_threads),
        socket_(context_, zmq::socket_type::sub);

    void connect(std::string_view address, std::span<std::string> topics) override {
        socket_.connect(std::string{address});
        for (const std::string& topic : topics) {
            socket_.set(zmq::sockopt::subscribe, topic);
        }
    }

    void connect(std::string_view address, std::span<std::string_view> topics) override {
        socket_.connect(std::string{address});
        for (const std::string_view& topic : topics) {
            socket_.set(zmq::sockopt::subscribe, topic);
        }
    }

    ZmqDatagram receive() override {
        if (zmq::message_t zmq_topic; socket_.recv(zmq_topic, zmq::recv_flags::dontwait)) {
            if (zmq::message_t zmq_message; socket_.recv(zmq_message, zmq::recv_flags::dontwait)) {
                return {zmq_topic.to_string(), zmq_message.to_string()};
            }
        }

        return {};
    }

    void close() override { socket_.close(); }

    [[nodiscard]] int fd() const override { return socket_.get(zmq::sockopt::fd); }

  private:
    friend class ZmqPoller;

    ZmqContext context_;
    ZmqSocket socket_;

};

using ZmqSubscriber = AZmqSubscriber<zmq::context_t, zmq::socket_t>;

} // namespace sida


#endif /* LIBS_NETWORK_ZMQ_SUBSCRIBER */
