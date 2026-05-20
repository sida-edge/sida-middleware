# libs/network/CMakeLists.txt

sida_cpp_libs(
    NAME network
    HDRS zmq_datagram.h
         zmq_subscriber.h
         zmq_publisher.h
         zmq_poller.h
    SRCS zmq_datagram.cpp
         zmq_subscriber.cpp
         zmq_publisher.cpp
         zmq_poller.cpp
    DEPS cppzmq  # O CMake automaticamente acha a lib que demos o find_package na raiz
)