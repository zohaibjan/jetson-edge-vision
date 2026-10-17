#include "edge/decode.hpp"
#include "nvdsinfer_custom_impl.h"
#include <exception>
extern "C" bool NvDsInferParseEdgeYolo(
    std::vector<NvDsInferLayerInfo> const& layers,NvDsInferNetworkInfo const& network,
    NvDsInferParseDetectionParams const& params,std::vector<NvDsInferObjectDetectionInfo>& objects) {
    if(layers.size()!=1||layers[0].dataType!=FLOAT||!layers[0].buffer) return false;
    const auto& dims=layers[0].inferDims;
    unsigned offset=0;
    if(dims.numDims==3&&dims.d[0]==1) offset=1;
    else if(dims.numDims!=2) return false;
    const unsigned channels=4+params.numClassesConfigured;
    int d0=dims.d[offset],d1=dims.d[offset+1];
    if(d0<=0||d1<=0) return false;
    edge::Layout layout;std::size_t count;
    if(unsigned(d0)==channels&&unsigned(d1)!=channels){layout=edge::Layout::channels_first;count=d1;}
    else if(unsigned(d1)==channels&&unsigned(d0)!=channels){layout=edge::Layout::candidates_first;count=d0;}
    else return false;
    try {
        auto decoded=edge::decode(static_cast<const float*>(layers[0].buffer),dims.numElements,
            count,params.numClassesConfigured,layout,network.width,network.height,params.perClassPreclusterThreshold);
        for(auto const& d:decoded){
            NvDsInferObjectDetectionInfo o{};
            o.classId=d.class_id;o.detectionConfidence=d.confidence;
            o.left=d.left;o.top=d.top;o.width=d.width;o.height=d.height;objects.push_back(o);
        }
        return true;
    }catch(const std::exception&){return false;}
}
CHECK_CUSTOM_PARSE_FUNC_PROTOTYPE(NvDsInferParseEdgeYolo);
