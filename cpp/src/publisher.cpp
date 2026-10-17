#include "edge/publisher.h"
#include <zmq.h>
#include <condition_variable>
#include <deque>
#include <future>
#include <mutex>
#include <string>
#include <thread>
#include <memory>
struct EdgePublisher {
    std::mutex mutex;std::condition_variable wake;std::deque<std::string> queue;
    bool stopping=false;std::thread worker;
};
extern "C" EdgePublisher* edge_publisher_new(const char* endpoint) {
    if(!endpoint||std::string(endpoint).rfind("tcp://",0)!=0) return nullptr;
    auto p=std::make_unique<EdgePublisher>();
    std::promise<bool> ready;auto result=ready.get_future();
    p->worker=std::thread([ptr=p.get(),address=std::string(endpoint),startup=std::move(ready)]()mutable {
        void* ctx=zmq_ctx_new();void* socket=ctx?zmq_socket(ctx,ZMQ_PUB):nullptr;
        int hwm=32,linger=0;
        if(socket){zmq_setsockopt(socket,ZMQ_SNDHWM,&hwm,sizeof(hwm));zmq_setsockopt(socket,ZMQ_LINGER,&linger,sizeof(linger));}
        if(!socket||zmq_bind(socket,address.c_str())!=0){
            startup.set_value(false);if(socket)zmq_close(socket);if(ctx)zmq_ctx_term(ctx);return;
        }
        startup.set_value(true);
        for(;;){
            std::string message;
            {std::unique_lock<std::mutex> lock(ptr->mutex);
             ptr->wake.wait(lock,[&]{return ptr->stopping||!ptr->queue.empty();});
             if(ptr->stopping)break;
             message=std::move(ptr->queue.front());ptr->queue.pop_front();}
            const char topic[]="edge.detections.v1";
            if(zmq_send(socket,topic,sizeof(topic)-1,ZMQ_SNDMORE|ZMQ_DONTWAIT)>=0)
                zmq_send(socket,message.data(),message.size(),ZMQ_DONTWAIT);
        }
        zmq_close(socket);zmq_ctx_term(ctx);
    });
    if(!result.get()){p->worker.join();return nullptr;}
    return p.release();
}
extern "C" int edge_publisher_submit(EdgePublisher* p,const char* json,unsigned length){
    if(!p||!json||length>262144)return 0;
    std::lock_guard<std::mutex> lock(p->mutex);
    if(p->stopping)return 0;
    if(p->queue.size()>=32)p->queue.pop_front();
    p->queue.emplace_back(json,length);p->wake.notify_one();return 1;
}
extern "C" void edge_publisher_free(EdgePublisher* p){
    if(!p)return;
    {std::lock_guard<std::mutex> lock(p->mutex);p->stopping=true;}
    p->wake.notify_one();p->worker.join();delete p;
}
