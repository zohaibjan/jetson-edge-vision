#include <gst/gst.h>
#include <initializer_list>
extern "C" gboolean edge_events_register(GstPlugin*);
typedef struct {GstBin parent;GstElement* infer;gchar* config;} GstEdgeYolo;
typedef struct {GstBinClass parent;} GstEdgeYoloClass;
G_DEFINE_TYPE(GstEdgeYolo,gst_edge_yolo,GST_TYPE_BIN)
static GstStaticPadTemplate sink_template=GST_STATIC_PAD_TEMPLATE("sink",GST_PAD_SINK,GST_PAD_ALWAYS,GST_STATIC_CAPS_ANY);
static GstStaticPadTemplate src_template=GST_STATIC_PAD_TEMPLATE("src",GST_PAD_SRC,GST_PAD_ALWAYS,GST_STATIC_CAPS_ANY);
static void set_property(GObject*o,guint id,const GValue*v,GParamSpec*s){
    auto*self=(GstEdgeYolo*)o;
    if(id==1){g_free(self->config);self->config=g_value_dup_string(v);
        if(self->infer)g_object_set(self->infer,"config-file-path",self->config,nullptr);
    }else G_OBJECT_WARN_INVALID_PROPERTY_ID(o,id,s);
}
static void get_property(GObject*o,guint id,GValue*v,GParamSpec*s){
    if(id==1)g_value_set_string(v,((GstEdgeYolo*)o)->config);else G_OBJECT_WARN_INVALID_PROPERTY_ID(o,id,s);
}
static GstStateChangeReturn change_state(GstElement*element,GstStateChange transition){
    auto*self=(GstEdgeYolo*)element;
    if(transition==GST_STATE_CHANGE_NULL_TO_READY&&(!self->infer||!self->config||!*self->config)){
        GST_ELEMENT_ERROR(element,RESOURCE,SETTINGS,("nvinfer and a generated config-file are required"),(nullptr));
        return GST_STATE_CHANGE_FAILURE;
    }
    return GST_ELEMENT_CLASS(gst_edge_yolo_parent_class)->change_state(element,transition);
}
static void finalize(GObject*object){g_free(((GstEdgeYolo*)object)->config);G_OBJECT_CLASS(gst_edge_yolo_parent_class)->finalize(object);}
static void gst_edge_yolo_class_init(GstEdgeYoloClass*klass){
    auto*object=G_OBJECT_CLASS(klass);auto*element=GST_ELEMENT_CLASS(klass);
    object->set_property=set_property;object->get_property=get_property;object->finalize=finalize;element->change_state=change_state;
    g_object_class_install_property(object,1,g_param_spec_string("config-file","Config","Generated nvinfer configuration",nullptr,static_cast<GParamFlags>(G_PARAM_READWRITE|GST_PARAM_MUTABLE_READY)));
    gst_element_class_set_static_metadata(element,"Edge YOLO inference","Bin/Video","nvinfer adapter with TensorRT caching","Muhammad Zohaib Jan");
    gst_element_class_add_static_pad_template(element,&sink_template);gst_element_class_add_static_pad_template(element,&src_template);
}
static void gst_edge_yolo_init(GstEdgeYolo*self){
    self->config=nullptr;self->infer=gst_element_factory_make("nvinfer","infer");if(!self->infer)return;
    gst_bin_add(GST_BIN(self),self->infer);
    for(const char*name:{"sink","src"}){
        GstPad*target=gst_element_get_static_pad(self->infer,name);
        gst_element_add_pad(GST_ELEMENT(self),gst_ghost_pad_new(name,target));gst_object_unref(target);
    }
}
static gboolean plugin_init(GstPlugin*plugin){
    return gst_element_register(plugin,"edgeyolo",GST_RANK_NONE,gst_edge_yolo_get_type())&&edge_events_register(plugin);
}
GST_PLUGIN_DEFINE(GST_VERSION_MAJOR,GST_VERSION_MINOR,edgevision,"Jetson edge vision reference",
    plugin_init,"0.1.0","MIT","jetson-edge-vision","https://github.com/zohaibjan/jetson-edge-vision")
