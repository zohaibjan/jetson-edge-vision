#include <gst/base/gstbasetransform.h>
#include <json-glib/json-glib.h>
#include <math.h>
#include "gstnvdsmeta.h"
#include "edge/publisher.h"
typedef struct {GstBaseTransform parent;gchar* endpoint;EdgePublisher* publisher;guint width,height;} GstEdgeEvents;
typedef struct {GstBaseTransformClass parent;} GstEdgeEventsClass;
G_DEFINE_TYPE(GstEdgeEvents,gst_edge_events,GST_TYPE_BASE_TRANSFORM)
static GstStaticPadTemplate sink_template=GST_STATIC_PAD_TEMPLATE("sink",GST_PAD_SINK,GST_PAD_ALWAYS,GST_STATIC_CAPS_ANY);
static GstStaticPadTemplate src_template=GST_STATIC_PAD_TEMPLATE("src",GST_PAD_SRC,GST_PAD_ALWAYS,GST_STATIC_CAPS_ANY);
static void integer(JsonBuilder*b,const char*n,gint64 v){json_builder_set_member_name(b,n);json_builder_add_int_value(b,v);}
static void number(JsonBuilder*b,const char*n,double v){json_builder_set_member_name(b,n);json_builder_add_double_value(b,v);}
static void string(JsonBuilder*b,const char*n,const char*v){json_builder_set_member_name(b,n);json_builder_add_string_value(b,v);}
static gboolean start(GstBaseTransform*base){
    GstEdgeEvents*self=(GstEdgeEvents*)base;self->publisher=edge_publisher_new(self->endpoint);
    if(!self->publisher)GST_ELEMENT_ERROR(self,RESOURCE,OPEN_WRITE,("Cannot bind event endpoint"),(NULL));
    return self->publisher!=NULL;
}
static gboolean stop(GstBaseTransform*base){
    GstEdgeEvents*self=(GstEdgeEvents*)base;edge_publisher_free(self->publisher);self->publisher=NULL;return TRUE;
}
static GstFlowReturn transform(GstBaseTransform*base,GstBuffer*buffer){
    GstEdgeEvents*self=(GstEdgeEvents*)base;NvDsBatchMeta*batch=gst_buffer_get_nvds_batch_meta(buffer);
    if(!batch)return GST_FLOW_OK;
    for(NvDsMetaList*it=batch->frame_meta_list;it;it=it->next){
        NvDsFrameMeta*frame=(NvDsFrameMeta*)it->data;
        JsonBuilder*b=json_builder_new();json_builder_begin_object(b);
        string(b,"schema","edge.detections.v1");string(b,"source_id","camera-0");
        integer(b,"frame_id",frame->frame_num);integer(b,"timestamp_ms",g_get_real_time()/1000);
        integer(b,"width",self->width);integer(b,"height",self->height);
        json_builder_set_member_name(b,"simulated");json_builder_add_boolean_value(b,FALSE);
        json_builder_set_member_name(b,"objects");json_builder_begin_array(b);
        unsigned count=0;
        for(NvDsMetaList*obj=frame->obj_meta_list;obj&&count<128;obj=obj->next){
            NvDsObjectMeta*o=(NvDsObjectMeta*)obj->data;
            if(!isfinite(o->confidence)||o->confidence<0||o->confidence>1||
               !isfinite(o->rect_params.left)||!isfinite(o->rect_params.top)||
               !isfinite(o->rect_params.width)||!isfinite(o->rect_params.height)||
               o->rect_params.width<=0||o->rect_params.height<=0)continue;
            json_builder_begin_object(b);integer(b,"class_id",o->class_id);
            gchar*label=g_strndup(o->obj_label,MAX_LABEL_SIZE);
            if(!g_utf8_validate(label,-1,NULL)){g_free(label);label=g_strdup("object");}
            string(b,"label",label);g_free(label);number(b,"confidence",o->confidence);
            json_builder_set_member_name(b,"bbox");json_builder_begin_object(b);
            number(b,"left",fmax(0,o->rect_params.left));number(b,"top",fmax(0,o->rect_params.top));
            number(b,"width",o->rect_params.width);number(b,"height",o->rect_params.height);
            json_builder_end_object(b);json_builder_end_object(b);++count;
        }
        json_builder_end_array(b);json_builder_end_object(b);
        JsonNode*root=json_builder_get_root(b);JsonGenerator*g=json_generator_new();
        json_generator_set_root(g,root);gsize length=0;gchar*payload=json_generator_to_data(g,&length);
        edge_publisher_submit(self->publisher,payload,(unsigned)length);
        g_free(payload);json_node_free(root);g_object_unref(g);g_object_unref(b);
    }
    return GST_FLOW_OK;
}
static void set_property(GObject*object,guint id,const GValue*value,GParamSpec*spec){
    GstEdgeEvents*s=(GstEdgeEvents*)object;
    if(id==1){g_free(s->endpoint);s->endpoint=g_value_dup_string(value);}
    else if(id==2)s->width=g_value_get_uint(value);
    else if(id==3)s->height=g_value_get_uint(value);
    else G_OBJECT_WARN_INVALID_PROPERTY_ID(object,id,spec);
}
static void get_property(GObject*object,guint id,GValue*value,GParamSpec*spec){
    GstEdgeEvents*s=(GstEdgeEvents*)object;
    if(id==1)g_value_set_string(value,s->endpoint);
    else if(id==2)g_value_set_uint(value,s->width);
    else if(id==3)g_value_set_uint(value,s->height);
    else G_OBJECT_WARN_INVALID_PROPERTY_ID(object,id,spec);
}
static void finalize(GObject*object){
    g_free(((GstEdgeEvents*)object)->endpoint);G_OBJECT_CLASS(gst_edge_events_parent_class)->finalize(object);
}
static void gst_edge_events_class_init(GstEdgeEventsClass*klass){
    GObjectClass*object=G_OBJECT_CLASS(klass);GstElementClass*element=GST_ELEMENT_CLASS(klass);
    GstBaseTransformClass*transform_class=GST_BASE_TRANSFORM_CLASS(klass);
    object->set_property=set_property;object->get_property=get_property;object->finalize=finalize;
    g_object_class_install_property(object,1,g_param_spec_string("endpoint","Endpoint","ZeroMQ PUB bind endpoint","tcp://127.0.0.1:5556",G_PARAM_READWRITE|GST_PARAM_MUTABLE_READY));
    g_object_class_install_property(object,2,g_param_spec_uint("frame-width","Width","Mux surface width",1,32768,640,G_PARAM_READWRITE|GST_PARAM_MUTABLE_READY));
    g_object_class_install_property(object,3,g_param_spec_uint("frame-height","Height","Mux surface height",1,32768,640,G_PARAM_READWRITE|GST_PARAM_MUTABLE_READY));
    gst_element_class_set_static_metadata(element,"Edge detection events","Filter/Metadata","Bounded asynchronous publisher","Muhammad Zohaib Jan");
    gst_element_class_add_static_pad_template(element,&sink_template);gst_element_class_add_static_pad_template(element,&src_template);
    transform_class->start=start;transform_class->stop=stop;transform_class->transform_ip=transform;
}
static void gst_edge_events_init(GstEdgeEvents*self){
    self->endpoint=g_strdup("tcp://127.0.0.1:5556");self->publisher=NULL;self->width=640;self->height=640;
    gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self),TRUE);
    gst_base_transform_set_passthrough(GST_BASE_TRANSFORM(self),FALSE);
}
gboolean edge_events_register(GstPlugin*plugin){
    return gst_element_register(plugin,"edgeevents",GST_RANK_NONE,gst_edge_events_get_type());
}
