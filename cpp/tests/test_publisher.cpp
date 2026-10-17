#include "edge/publisher.h"
#include <zmq.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cassert>
#include <chrono>
#include <cstring>
#include <string>

int main() {
    // Ask the OS for an available loopback port before starting the worker.
    int probe = socket(AF_INET, SOCK_STREAM, 0);
    assert(probe >= 0);
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0;
    assert(bind(probe, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    socklen_t length = sizeof(address);
    assert(getsockname(probe, reinterpret_cast<sockaddr*>(&address), &length) == 0);
    auto endpoint = "tcp://127.0.0.1:" + std::to_string(ntohs(address.sin_port));
    close(probe);
    EdgePublisher* publisher = edge_publisher_new(endpoint.c_str());
    assert(publisher);
    assert(edge_publisher_new("inproc://unsupported") == nullptr);
    // Bind conflicts must fail promptly, without a hanging thread.
    assert(edge_publisher_new(endpoint.c_str()) == nullptr);
    void* context = zmq_ctx_new();
    void* subscriber = zmq_socket(context, ZMQ_SUB);
    const char topic[] = "edge.detections.v1";
    int linger = 0;
    zmq_setsockopt(subscriber, ZMQ_LINGER, &linger, sizeof(linger));
    assert(zmq_setsockopt(subscriber, ZMQ_SUBSCRIBE, topic, sizeof(topic)-1) == 0);
    assert(zmq_connect(subscriber, endpoint.c_str()) == 0);
    const char payload[] = "{\"frame_id\":42}";
    bool received = false;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (!received && std::chrono::steady_clock::now() < deadline) {
        assert(edge_publisher_submit(publisher, payload, sizeof(payload)-1) == 1);
        zmq_pollitem_t item{subscriber, 0, ZMQ_POLLIN, 0};
        if (zmq_poll(&item, 1, 25) > 0 && (item.revents & ZMQ_POLLIN)) {
            char buffer[256]{};
            int size = zmq_recv(subscriber, buffer, sizeof(buffer), 0);
            assert(size == static_cast<int>(sizeof(topic)-1));
            assert(std::memcmp(buffer, topic, sizeof(topic)-1) == 0);
            size = zmq_recv(subscriber, buffer, sizeof(buffer), 0);
            assert(size == static_cast<int>(sizeof(payload)-1));
            assert(std::memcmp(buffer, payload, sizeof(payload)-1) == 0);
            received = true;
        }
    }
    assert(received);
    assert(edge_publisher_submit(publisher, payload, 262145) == 0);
    // Backpressure must stay bounded and teardown must join the worker.
    for (int i = 0; i < 10000; ++i)
        assert(edge_publisher_submit(publisher, payload, sizeof(payload)-1) == 1);
    edge_publisher_free(publisher);
    edge_publisher_free(nullptr);
    zmq_close(subscriber);
    zmq_ctx_term(context);
}
