#include "edge/decode.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace edge {
std::vector<Detection> decode(const float* data, std::size_t elements,
    std::size_t count, unsigned classes, Layout layout, unsigned width,
    unsigned height, const std::vector<float>& thresholds) {
    if (!data || !classes || classes>1000 || count>100000 || !width || !height
        || thresholds.size()!=classes || elements!=count*(4u+classes))
        throw std::invalid_argument("Unsupported YOLO tensor dimensions");
    for (float t:thresholds)
        if (!std::isfinite(t)||t<0||t>1) throw std::invalid_argument("Invalid threshold");
    auto at=[&](std::size_t n,unsigned c) {
        return data[layout==Layout::channels_first ? c*count+n : n*(4u+classes)+c];
    };
    std::vector<Detection> result;
    for (std::size_t n=0;n<count;++n) {
        float best=-1;unsigned id=0;
        for (unsigned c=0;c<classes;++c) {
            float score=at(n,4+c);
            if (std::isfinite(score)&&score>=0&&score<=1&&score>best) {best=score;id=c;}
        }
        if (best<0||best<thresholds[id]) continue;
        float cx=at(n,0),cy=at(n,1),w=at(n,2),h=at(n,3);
        if (!std::isfinite(cx)||!std::isfinite(cy)||!std::isfinite(w)||!std::isfinite(h)||w<=0||h<=0) continue;
        float x1=std::clamp(cx-w/2,0.0f,float(width)),y1=std::clamp(cy-h/2,0.0f,float(height));
        float x2=std::clamp(cx+w/2,0.0f,float(width)),y2=std::clamp(cy+h/2,0.0f,float(height));
        if (x2>x1&&y2>y1) result.push_back({id,best,x1,y1,x2-x1,y2-y1});
    }
    return result;
}
}
