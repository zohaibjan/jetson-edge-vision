#pragma once
#ifdef __cplusplus
extern "C" {
#endif
typedef struct EdgePublisher EdgePublisher;
EdgePublisher* edge_publisher_new(const char* endpoint);
int edge_publisher_submit(EdgePublisher*,const char* json,unsigned length);
void edge_publisher_free(EdgePublisher*);
#ifdef __cplusplus
}
#endif
