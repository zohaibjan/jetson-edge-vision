#include "edge/decode.hpp"
#include <limits>
#include <iostream>
#include <stdexcept>
void check(bool ok) {if(!ok) throw std::runtime_error("decoder regression failed");}
int main() {
    using namespace edge;
    std::vector<float> thresholds{.5f,.5f};
    float first[]{50,150,50,60,20,30,40,20,.8f,.1f,.2f,.9f};
    float last[]{50,50,20,40,.8f,.2f,150,60,30,20,.1f,.9f};
    auto a=decode(first,12,2,2,Layout::channels_first,200,100,thresholds);
    auto b=decode(last,12,2,2,Layout::candidates_first,200,100,thresholds);
    check(a.size()==2&&b.size()==2&&a[0].class_id==0&&b[1].class_id==1);
    check(a[0].left==40&&a[0].top==30&&a[1].width==30);
    last[2]=-1;
    check(decode(last,12,2,2,Layout::candidates_first,200,100,thresholds).size()==1);
    last[2]=20;last[0]=std::numeric_limits<float>::quiet_NaN();
    check(decode(last,12,2,2,Layout::candidates_first,200,100,thresholds).size()==1);
    float clip[]{0,0,20,40,.8f,.1f};
    auto c=decode(clip,6,1,2,Layout::candidates_first,200,100,thresholds);
    check(c.size()==1&&c[0].left==0&&c[0].width==10&&c[0].height==20);
    bool rejected=false;
    try{decode(first,11,2,2,Layout::channels_first,200,100,thresholds);}
    catch(const std::invalid_argument&){rejected=true;}
    check(rejected);
    float low[]{50,50,20,20,.2f,.3f};
    check(decode(low,6,1,2,Layout::candidates_first,200,100,thresholds).empty());
    std::cout<<"6 decoder regression scenarios passed\n";
}
