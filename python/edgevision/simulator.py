"""Synthetic metadata only: never represents camera/model inference."""
import argparse
import json
import math
import time
import zmq

def event(frame: int) -> dict:
    return {"schema": "edge.detections.v1", "source_id": "synthetic-camera", "frame_id": frame,
        "timestamp_ms": int(time.time()*1000), "width": 1280, "height": 720, "simulated": True,
        "objects": [{"class_id": i, "label": label, "confidence": 0.9-i*0.04,
            "bbox": {"left": 160+i*320+80*math.sin(frame/20+i), "top": 180+i*35,
                     "width": 130+i*40, "height": 220-i*50}}
            for i,label in enumerate(["person","vehicle","package"])]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--endpoint",default="tcp://127.0.0.1:5556")
    parser.add_argument("--frames",type=int,default=0,help="0 runs until interrupted")
    args=parser.parse_args()
    context=zmq.Context()
    socket=context.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM,32)
    socket.setsockopt(zmq.LINGER,0)
    socket.bind(args.endpoint)
    try:
        time.sleep(0.3)
        frame=0
        while args.frames==0 or frame<args.frames:
            socket.send_multipart([b"edge.detections.v1",json.dumps(event(frame)).encode()])
            frame+=1
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        socket.close()
        context.term()

if __name__=="__main__":
    main()
