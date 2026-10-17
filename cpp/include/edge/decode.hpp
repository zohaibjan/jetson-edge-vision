#pragma once
#include <cstddef>
#include <vector>
namespace edge {
struct Detection { unsigned class_id; float confidence, left, top, width, height; };
enum class Layout { channels_first, candidates_first };
// Decoded xywh + class probabilities, batch one, FP32. NMS belongs to nvinfer.
std::vector<Detection> decode(const float*, std::size_t elements, std::size_t candidates,
    unsigned classes, Layout, unsigned width, unsigned height, const std::vector<float>& thresholds);
}
